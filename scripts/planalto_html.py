"""Shared Planalto HTML primitives: decoding, source evidence and unit markers.

No candidate preparation, reader association, network access or publication.
"""
from pathlib import Path
import re
from official_html import OfficialHTML, ARTICLE_IDENTIFIER as ARTICLE

ROOT = Path(__file__).resolve().parents[1]
FILES = {'cf':'Constituição.html', 'penal':'DEL2848.html', 'cpp':'Del3689.html',
         'clt':'Del5452compilado.html', 'civil':'L10406compilada.html',
         'cpc':'L13105compilada.html', 'licitacoes':'L14133.html',
         'ctn':'L5172COMPILADO.html', 'lep':'L7210.html', 'eca':'L8069.html',
         'cdc':'L8078compilado.html', 'improbidade':'L8429.html',
         'maria-penha':'Lei nº 11.340.html'}
NOTE = re.compile(r'\((?:Redação|Incluíd[oa]|Acrescid[oa]|Alterad[oa]|Revogad[oa]|Vide\b|Vigência\b|Produção de efeitos?\b|Suspens[ao])', re.I)
SENSITIVE = re.compile(r'\b(?:VETAD[OA]|Revogad[oa]|Suspens[ao]|ADIN?|ADPF)\b', re.I)
PARA = re.compile(r'^(?:§\s*(\d+)\s*(?-i:[º°o])?(-[A-Z])?|Parágrafo\s+único)', re.I)
ITEM = re.compile(r'^([IVXLCDM]+)\s*[-–—]')
ITEM_NO_DASH = re.compile(r'^([IVXLCDM]+)\s+(?=[a-záéíóúâêôãõç])')
BARE_NOTE = re.compile(r'\bVide art\.\s*\d+\s*[-–—]\s*ADCT\b', re.I)
LETTER = re.compile(r'^([a-z])\)')
PENALTY = re.compile(r'\bPenas?\s*[-–—:]')


def spaces(value):
    return re.sub(r'\s+', ' ', value).strip()


def decode(raw):
    if raw.startswith((b'\xff\xfe', b'\xfe\xff')):
        encoding = 'utf-16'
    elif raw.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    elif match := re.search(br'charset\s*=\s*["\']?\s*([\w-]+)', raw[:8192], re.I):
        encoding = match[1].decode('ascii')
    else:
        try:
            raw.decode('utf-8', errors='strict')
            encoding = 'utf-8'
        except UnicodeDecodeError:
            encoding = 'cp1252'
    return raw.decode(encoding, errors='strict'), encoding


class EvidenceHTML(OfficialHTML):
    """Keep exact decoded text and link offsets on the existing deletion stack.

    No Unicode rewriting: whitespace is normalized only in the final body.
    BR is a whitespace separator, not a complete legal-unit boundary.
    """
    boundaries = OfficialHTML.boundaries - {'br'}

    def __init__(self, source):
        super().__init__()
        self.source = source
        self.offsets = [0]+[m.end() for m in re.finditer('\n', source)]
        self.start = None
        self.anchors = []
        self.link_stack = []
        self.start_location = None
        self.context_tags = []

    def pos(self):
        line, column = self.getpos()
        return self.offsets[line-1]+column

    def handle_starttag(self, tag, attrs):
        super().handle_starttag(tag, attrs)
        attrs = dict(attrs)
        self.link_stack = [item for item in self.link_stack if item[0] <= len(self.stack)]
        if tag in self.boundaries:
            self.start = self.pos()
            self.start_location = self.getpos()
            self.context_tags = [entry[0] for entry in self.stack]
        if attrs.get('id') or attrs.get('name'):
            self.anchors.append(attrs.get('id') or attrs['name'])
        if tag == 'a' and attrs.get('href'):
            self.link_stack.append((len(self.stack), attrs['href']))
        if tag == 'br':
            self.handle_data(' ')

    def handle_endtag(self, tag):
        super().handle_endtag(tag)
        self.link_stack = [item for item in self.link_stack if item[0] <= len(self.stack)]

    def handle_data(self, text):
        if self.stack and self.stack[-1][1]:
            if self.stack[-1][0] == 'style' and 'line-through' in text.lower():
                self.deletion_styles.add(text)
            return
        if self.start is None:
            self.start, self.start_location = self.pos(), self.getpos()
            self.context_tags = [entry[0] for entry in self.stack]
        self.runs.append({'text':text, 'deleted':self.stack[-1][2] if self.stack else False,
                          'href':self.link_stack[-1][1] if self.link_stack else None})

    def flush(self):
        if any(run['text'].strip() for run in self.runs):
            end = self.pos()
            # Include the closing boundary tag when flush was called by its end.
            closing = re.match(r'</(?:p|div|li|tr|h[1-6])\s*>', self.source[end:], re.I)
            if closing:
                end += closing.end()
            self.blocks.append(dict(runs=self.runs, anchors=self.anchors,
                start=self.start, end=end, line=(self.start_location or (1,0))[0],
                contextTags=self.context_tags,
                rawHtml=self.source[self.start:end]))
        self.runs, self.anchors = [], []
        self.start, self.start_location = None, None


def split_notes(raw):
    ranges, notes, cursor = [], [], 0
    while match := NOTE.search(raw, cursor):
        depth = 0
        for i in range(match.start(), len(raw)):
            depth += (raw[i]=='(')-(raw[i]==')')
            if depth == 0:
                ranges.append((match.start(), i+1))
                notes.append(spaces(raw[match.start():i+1]))
                cursor = i+1
                break
        else:
            raise ValueError('incomplete_editorial_note')
    for match in BARE_NOTE.finditer(raw):
        if any(a <= match.start() < b for a,b in ranges):
            continue
        # Explicit editorial cross-reference, never a free-form tail.
        ranges.append((match.start(), match.end()))
        notes.append(spaces(match[0]))
    ordered = sorted(zip(ranges, notes))
    ranges, notes = [r for r,n in ordered], [n for r,n in ordered]
    chars = [c for i,c in enumerate(raw) if not any(a <= i < b for a,b in ranges)]
    return spaces(''.join(chars)), notes, ranges


def unit(text):
    if m := ARTICLE.match(text):
        return 'caput', m[1].replace('.', '')+(m[2] or '').replace('–','-'), 'caput', m.end()
    if m := PARA.match(text):
        return 'paragraph', None, '§ '+m[1]+(m[2] or '') if m[1] else 'Parágrafo único', m.end()
    if m := ITEM.match(text):
        return 'item', None, 'inciso '+m[1], m.end()
    if m := LETTER.match(text):
        return 'letter', None, 'alínea '+m[1], m.end()
    return None
