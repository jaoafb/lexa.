"""Pure official HTML parsing: no downloads, persistence or publication."""
from html.parser import HTMLParser
import re
import unicodedata

ARTICLE_NUMBER = r'(?:\d+(?:\.\d{3})*|l\d{2,3})'
ARTICLE_IDENTIFIER = re.compile(
    rf'^Art\.?\s*({ARTICLE_NUMBER})(?:\s*[º°o])?'
    r'((?:[-–][A-Z]{1,2}(?=[.\s:\-–]))*)\s*[.:-]?\s*'
)
ARTICLE_RANGE = re.compile(
    r'^Arts?\.\s*(\d+(?:\.\d{3})*)(?:\s*[º°o])?\.?\s+a\s+'
    r'(\d+(?:\.\d{3})*)(?:\s*[º°o])?\.?\s*',
    re.I,
)


def article_base(value):
    """Read a documented article marker without rewriting its source text."""
    compact = value.replace('.', '')
    if compact.startswith('l') and compact[1:].isdigit():
        compact = '1' + compact[1:]
    return int(compact)

def tidy(text):
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text.replace('\xa0', ' ').replace('\xad', '')))


class OfficialHTML(HTMLParser):
    """Extract visible paragraphs and deletion marks without running HTML."""
    boundaries = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'br'}
    hidden = {'head', 'script', 'style', 'noscript', 'svg'}
    void = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.blocks = []
        self.runs = []
        self.deletion_styles = set()

    def flush(self):
        if not any(run['text'].strip() for run in self.runs):
            self.runs = []
            return
        # A whitespace-only inline span may precede a struck article. Strip
        # boundary whitespace until reaching actual text, not just the first run.
        while self.runs and not self.runs[0]['text'].strip():
            self.runs.pop(0)
        while self.runs and not self.runs[-1]['text'].strip():
            self.runs.pop()
        self.runs[0]['text'] = self.runs[0]['text'].lstrip()
        self.runs[-1]['text'] = self.runs[-1]['text'].rstrip()
        self.blocks.append([r for r in self.runs if r['text']])
        self.runs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in self.boundaries:
            self.flush()
        parent_hidden = self.stack[-1][1] if self.stack else False
        parent_deleted = self.stack[-1][2] if self.stack else False
        style = attrs.get('style', '').lower()
        hidden = parent_hidden or tag in self.hidden or 'hidden' in attrs or bool(re.search(r'display\s*:\s*none\b', style))
        deleted = parent_deleted or tag in {'del', 'strike', 's'} or bool(re.search(r'text-decoration(?:-line)?\s*:[^;]*line-through', style))
        if tag not in self.void:
            # Planalto's old HTML often omits </p>; a fresh paragraph closes it.
            if tag == 'p' and any(item[0] == 'p' for item in self.stack):
                pindex = max(i for i, item in enumerate(self.stack) if item[0] == 'p')
                self.stack = self.stack[:pindex]
                parent_hidden = self.stack[-1][1] if self.stack else False
                parent_deleted = self.stack[-1][2] if self.stack else False
                hidden = parent_hidden or tag in self.hidden
                deleted = parent_deleted or bool(re.search(r'text-decoration(?:-line)?\s*:[^;]*line-through', style))
            self.stack.append((tag, hidden, deleted))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.boundaries:
            self.flush()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                self.stack = self.stack[:i]
                break

    def handle_data(self, text):
        if self.stack and self.stack[-1][0] == 'style':
            # A change to stylesheet-based strikeouts must also trigger review.
            if 'line-through' in text.lower():
                self.deletion_styles.add(tidy(text).strip())
        if self.stack and self.stack[-1][1]:
            return
        deleted = self.stack[-1][2] if self.stack else False
        value = tidy(text)
        if self.runs and self.runs[-1]['deleted'] == deleted:
            self.runs[-1]['text'] = tidy(self.runs[-1]['text'] + value)
        else:
            self.runs.append({'text': value, 'deleted': deleted})


def parse_html(raw, encoding=None):
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):
        encoding='utf-16'
        # Some official pages append raw ASCII padding after complete UTF-16 HTML.
        endian='utf-16-le' if raw.startswith(b'\xff\xfe') else 'utf-16-be'
        closing='</html>'.encode(endian)
        end=raw.lower().rfind(closing)
        if end>=0 and not raw[end+len(closing):].strip(b' \t\r\n\x00'):
            raw=raw[:end+len(closing)]
    elif raw.startswith(b'\xef\xbb\xbf'):
        encoding='utf-8-sig'
    if not encoding:
        match = re.search(br'charset\s*=\s*["\']?\s*([\w-]+)', raw[:8192], re.I)
        if match:
            encoding = match[1].decode('ascii')
        else:
            # Legacy Planalto pages often omit the charset entirely. Browsers
            # accept Windows-1252; prefer strict UTF-8 when it is actually valid.
            try:
                raw.decode('utf-8', errors='strict')
                encoding = 'utf-8'
            except UnicodeDecodeError:
                encoding = 'cp1252'
    aliases = {'iso-8859-1': 'cp1252', 'latin1': 'cp1252'}
    encoding = aliases.get(encoding.lower(), encoding)
    try:
        text = raw.decode(encoding, errors='strict')
    except (LookupError, UnicodeDecodeError) as error:
        raise ValueError('Codificação do documento inválida ou desconhecida') from error
    parser = OfficialHTML()
    parser.feed(text)
    parser.close()
    parser.flush()
    return {'blocks': parser.blocks, 'deletion_styles': sorted(parser.deletion_styles)}
