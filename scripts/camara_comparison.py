"""Compare Câmara consolidations with the Lexa reader without rewriting either."""

import re

from import_official import article_version, digest, version_signature

ARTICLE_PREFIX = re.compile(
    r'^Arts?\.\s*(?P<number>[0-9]+(?:\.[0-9]{3})*(?:[-–][A-Z]{1,2})?)'
    r'(?:\s*[º°]|o(?=\s|[.:-])|\s+o(?=\s+[A-ZÀ-Ú]|[.:-]))?'
    r'(?=\s|[.:-]|$)\s*[.\-–—]?\s*'
)
UNIT_PREFIX = re.compile(
    r'^(?P<marker>§\s*[0-9]+[º°]?|Parágrafo único|[IVXLCDM]+(?=\s*[-–—]))\s*[.\-–—]?\s*'
)
NUMBER_RANGE = re.compile(
    r'^Arts?\.\s*[0-9]+(?:\.[0-9]{3})*(?:\s*[º°o])?\.?\s+a\s+'
    r'[0-9]+(?:\.[0-9]{3})*(?:\s*[º°o])?\.?\s+',
    re.I,
)
STATUS = re.compile(
    r'^\((?P<status>revogad|vetad|suprimid)[oa]s?'
    r'(?: pel[oa] (?P<reference>(?:Lei|Decreto[- ]Lei|Emenda Constitucional|Medida Provisória)\b[^()]*))?'
    r'\)\s*[.;]?(?:\s+Vigência)?$', re.I,
)
STATUS_REFERENCE = re.compile(
    r'^(?P<act>Lei|Decreto[- ]Lei|Emenda Constitucional|Medida Provisória)\s+n[º°.]?\s*(?P<number>[0-9.]+)'
    r'\s*,\s*de\s+(?:(?P<day>[0-9]{1,2})[/.](?P<month>[0-9]{1,2})[/.])?(?P<year>[0-9]{4})'
    r'(?:,\s*publicad[oa] no DOU de (?P<gazette>[0-9]{1,2}[/.][0-9]{1,2}[/.][0-9]{4}))?'
    r'(?:,\s*em vigor (?P<delay>[0-9]+ (?:dias?|meses|anos?) após a publicação|'
    r'após [0-9]+ (?:dias?|meses|anos?) da publicação))?$',
    re.I,
)
EDITORIAL_NOTE = re.compile(
    r'^(?:vigência|produção de efeitos|'
    r'vide\s+(?:a\s+|o\s+)?(?:art\.|lei\b|decreto\b|adin?\b|adc\b|adpf\b|'
    r'emenda constitucional\b|medida provisória\b).*|'
    r'(?:(?:artigo|parágrafo|inciso|alínea|item|[“"\']caput[”"\'])(?: do artigo)? com )?'
    r'(?:redação dada|incluíd[oa]|acrescid[oa]|renumerad[oa])\s+pel[oa]\s+'
    r'(?:lei\b|decreto[- ]lei\b|emenda constitucional\b|medida provisória\b).*)$',
    re.I,
)
STATUS_CHANGE = re.compile(r'\b(?:revogad[oa]s?|suprimid[oa]s?|vetad[oa]s?)\b', re.I)
ENDED_TERM_NOTE = re.compile(r'^(?:\(Vigência encerrada\)|Vigência encerrada)$', re.I)
VETO_NOTE = re.compile(r'^\(Vetad[oa] na (?P<reference>Lei\b[^()]+)\)$', re.I)


def citation_evidence(reference):
    act = reference['act'].casefold()
    if act == 'decreto lei':
        act = 'decreto-lei'
    identity = (act, reference['number'].replace('.', ''), reference['year'])
    issued = (int(reference['day']), int(reference['month'])) if reference['day'] else None
    gazette = tuple(map(int, re.split(r'[/.]', reference['gazette']))) if reference['gazette'] else None
    delay = re.search(r'([0-9]+) (dia|mes|ano)', reference['delay'] or '', re.I)
    return identity, issued, gazette, (int(delay[1]), delay[2].lower()) if delay else None


def strip_editorial_tail(text):
    """Strip only recognised trailing notes from the comparison string."""
    text = text.strip()
    while text.endswith(')'):
        depth = 1
        for index in range(len(text) - 2, -1, -1):
            if text[index] == ')':
                depth += 1
            elif text[index] == '(':
                depth -= 1
                if depth == 0:
                    break
        if depth or index == 0 or not text[index - 1].isspace():
            break
        note = text[index + 1:-1]
        if not EDITORIAL_NOTE.fullmatch(note) or STATUS_CHANGE.search(note):
            break
        text = text[:index].rstrip()
    return text


def normalized_paragraph(text, *, range_header=False):
    text = strip_editorial_tail(text)
    match = NUMBER_RANGE.match(text) if range_header else ARTICLE_PREFIX.match(text)
    if match:
        body = text[match.end():]
        marker = 'article' if range_header else 'article:' + match['number'].replace('.', '').replace('–', '-')
    elif unit := UNIT_PREFIX.match(text):
        body = text[unit.end():]
        marker = ' '.join(unit['marker'].replace('°', 'º').split())
    else:
        return tuple(text.split()), None

    if status := STATUS.fullmatch(body):
        if not status['reference']:
            return (marker, 'status:' + status['status'].lower() + 'o'), None
        if reference := STATUS_REFERENCE.fullmatch(status['reference']):
            return (marker, 'status:' + status['status'].lower() + 'o'), citation_evidence(reference)
    return (marker, *body.split()), None


def comparison_signatures(article):
    if article is None:
        return None, None, {}
    active = []
    historical = []
    references = {}
    for paragraph in article['paragraphs']:
        runs = paragraph['runs']
        live = ''.join(run['text'] for run in runs if not run['deleted']).strip()
        deleted = ''.join(run['text'] for run in runs if run['deleted'])
        if deleted.strip():
            historical.append(tuple(deleted.split()))
        if live:
            normalized, basis = normalized_paragraph(live, range_header=not active and 'rangeEnd' in article)
            if basis:
                references[len(active)] = basis
            active.append(normalized)
    return (article.get('title'), tuple(active)), tuple(historical), references


def status_ranges(articles):
    ranges = {}
    for article in articles.values():
        end = article.get('rangeEnd')
        if end is None or not article['number'].isascii() or not article['number'].isdigit():
            continue
        start = int(article['number'])
        signature, _, _ = comparison_signatures(article)
        if not 0 < start < end <= 10000 or signature[1] not in (
            (('article', 'status:revogado'),), (('article', 'status:suprimido'),), (('article', 'status:vetado'),)
        ):
            continue
        scope = article['scope']
        prefix = 'adct-' if scope == 'adct' else ''
        for number in range(start + 1, end + 1):
            key = prefix + str(number)
            if key in articles or key in ranges:
                raise ValueError(f'Intervalos sobrepostos ou artigo duplicado na comparação: {key}.')
            ranges[key] = article
    return ranges


def aligned_signature(article):
    active, historical, references = comparison_signatures(article)
    if active and len(active[1]) == 1 and len(active[1][0]) == 2:
        marker, value = active[1][0]
        if marker.startswith('article:') and value.startswith('status:'):
            active = (active[0], (('article', value),))
    return active, historical, references


def surviving_paragraphs(article):
    return [
        text for paragraph in article['paragraphs']
        if (text := ''.join(run['text'] for run in paragraph['runs'] if not run['deleted']).strip())
    ]


def matches_documented_pair(change, fingerprints):
    return (change['kind'] == 'text_review' and not change['matchedByRange']
            and change['beforeRangeEnd'] is None and change['afterRangeEnd'] is None
            and digest(change['before']) == fingerprints['lexaSha256']
            and digest(change['after']) == fingerprints['camaraSha256'])


def is_historical_annotation(text):
    if ENDED_TERM_NOTE.fullmatch(text):
        return True
    status = STATUS.fullmatch(text)
    return bool(status and status['status'].lower() == 'revogad' and status['reference']
                and STATUS_REFERENCE.fullmatch(status['reference']))


def unmatched_kind(old, new, old_history):
    if new is None and old_history:
        notes = surviving_paragraphs(old)
        if notes and any(ENDED_TERM_NOTE.fullmatch(note) for note in notes) and all(map(is_historical_annotation, notes)):
            return 'retained_history'
    if old is None and 'rangeEnd' not in new:
        paragraphs = surviving_paragraphs(new)
        if len(paragraphs) == 1 and not any(run['deleted'] for p in new['paragraphs'] for run in p['runs']):
            prefix = ARTICLE_PREFIX.match(paragraphs[0])
            note = VETO_NOTE.fullmatch(paragraphs[0][prefix.end():]) if prefix else None
            if note and STATUS_REFERENCE.fullmatch(note['reference']):
                return 'documentary_veto'
    return 'unmatched'


def compare_camara(current, candidate):
    before = {article['id']: article for article in current['articles']}
    after = {article['id']: article for article in candidate['articles']}
    before_ranges, after_ranges = status_ranges(before), status_ranges(after)
    differences = []
    for key in dict.fromkeys([*before, *after]):
        old_article = before.get(key) or before_ranges.get(key)
        new_article = after.get(key) or after_ranges.get(key)
        old, new = article_version(old_article), article_version(new_article)
        old_end = old_article.get('rangeEnd') if old_article else None
        new_end = new_article.get('rangeEnd') if new_article else None
        old_id = old_article['id'] if old_article else None
        new_id = new_article['id'] if new_article else None
        interval = (old_end, old_id) != (new_end, new_id) and (old_end is not None or new_end is not None)
        if not interval and old is not None and new is not None and version_signature(old) == version_signature(new):
            continue

        signature = aligned_signature if interval else comparison_signatures
        old_active, old_history, old_references = signature(old_article)
        new_active, new_history, new_references = signature(new_article)
        conflicting_status_reference = any(
            left != right and left is not None and right is not None
            for index in old_references.keys() & new_references.keys()
            for left, right in zip(old_references[index], new_references[index])
        )
        if old is None or new is None:
            kind = unmatched_kind(old_article, new_article, old_history)
        elif old_active != new_active or conflicting_status_reference:
            kind = 'text_review'
        elif old_history != new_history:
            kind = 'historical_difference'
        elif interval:
            kind = 'range_representation'
        else:
            kind = 'editorial_representation'
        differences.append({
            'articleId': key, 'scope': (new_article or old_article)['scope'], 'kind': kind,
            'beforeArticleId': old_id, 'afterArticleId': new_id,
            'matchedByRange': old_id not in (None, key) or new_id not in (None, key),
            'conflictingStatusReference': conflicting_status_reference,
            'historicalDiffers': bool(old_history or new_history) and old_history != new_history,
            'before': old, 'after': new, 'beforeRangeEnd': old_end, 'afterRangeEnd': new_end,
        })
    return differences
