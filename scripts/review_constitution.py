"""Corroborate a recorded Constituição/ADCT comparison with the Senado EC 141 ePub."""

import argparse
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
import unicodedata
from xml.etree import ElementTree
from zipfile import ZipFile

from camara_comparison import (
    ARTICLE_PREFIX, STATUS_CHANGE, matches_documented_pair, strip_editorial_tail, surviving_paragraphs,
)
from check_official_sources import ROOT

SENATE_URL = 'https://www2.senado.leg.br/jspui/bitstream/id/962911/6/CF88_EC141_ebook.epub'
SENATE_SHA256 = '7b0daa4f848282b62062bdd8686e2865f4119e2cb09de774e2efd74f136651e6'
SENATE_DOCUMENTS = [*(f'OEBPS/0{i}_titulo_{i}.xhtml' for i in range(1, 10)), 'OEBPS/10_adct.xhtml']
TYPOGRAPHY = str.maketrans({
    '–': '-', '—': '-', '“': '"', '”': '"', '‘': "'", '’': "'", '\u00ad': None, '\u200b': None,
})
AMENDMENT_NOTE = re.compile(
    r'^(?:(?:["“”]caput["“”]|caput) d[oa] (?:artigo|parágrafo|inciso)|'
    r'artigo|parágrafo|inciso|alínea|item) (?:com (?:nova )?redação dada|acrescid[oa]|incluíd[oa]|'
    r'renumerad[oa]) pel[oa] Emenda Constitucional\b[^()]*$', re.I,
)
CAVEAT = re.compile(r'\b(?:inconstitucion\w*|vigência encerrada|suspens\w*|modula\w*)\b', re.I)
LEGAL_CONTEXT = re.compile(
    r'\b(?:ADIs?|ADPFs?|ADINs?|ADCs?|regulamento|vigência|produção de efeitos?|revogad[oa]s?|'
    r'vetad[oa]s?|suprimid[oa]s?)\b', re.I,
)
PLAIN_NOTE = re.compile(r'^\((?:Regulamento|Produção de efeitos?|Vigência)\)$', re.I)
TOKENS = re.compile(r'\w+|[^\s\w]')
WORDS = re.compile(r'\w+')
LABELS = {
    'documentary_planalto': ('Decisão documental · Planalto', 'O dispositivo conferido sustenta manter a edição do Lexa na prévia'),
    'documentary_camara': ('Decisão documental · Câmara', 'O dispositivo conferido sustenta a escolha da Câmara na prévia'),
    'same_normalized': ('Mesmo texto', 'Mesmo texto após remover notas reconhecidas e normalizar tipografia'),
    'senate_matches_lexa': ('Senado e Lexa', 'Texto do Senado coincide com o Lexa nessa comparação'),
    'senate_matches_camara': ('Senado e Câmara', 'Texto do Senado coincide com a Câmara nessa comparação'),
    'same_words': ('Mesmas palavras', 'Mesmas palavras na mesma ordem, com diferença gráfica ou de pontuação'),
    'further_review': ('Em aberto', 'Diferença de texto, de estrutura ou de marcação ainda aberta'),
}
PREVIEW_CHOICES = {
    'documentary': 'Decisão documental aplicada',
    'editorial': 'Câmara · diferença editorial conferida',
    'keep_history': 'Planalto · mantém trechos riscados da edição em uso',
    'keep_pending': 'Planalto · seleção da redação ainda pendente',
}


def element_text(element):
    if element.get('role') == 'doc-noteref':
        return ''
    if 'Ordinal' in element.get('class', '').split() and element.text in ('o', 'a') and not len(element):
        return {'o': 'º', 'a': 'ª'}[element.text]
    return (element.text or '') + ''.join(element_text(child) + (child.tail or '') for child in element)


def senate_articles(path):
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != SENATE_SHA256:
        raise ValueError('O EPUB não corresponde à edição do Senado registrada para a conferência.')
    articles = {}
    with ZipFile(BytesIO(raw)) as archive:
        for name in SENATE_DOCUMENTS:
            prefix = 'adct-' if name.endswith('10_adct.xhtml') else ''
            current = None
            for paragraph in ElementTree.fromstring(archive.read(name)).findall('.//{*}p'):
                style = paragraph.get('class')
                if style == 'Texto_Tx-artigo':
                    line = ' '.join(element_text(paragraph).split())
                    match = ARTICLE_PREFIX.match(line)
                    if not match:
                        raise ValueError(f'Identificador não reconhecido na edição do Senado: {line}')
                    current = prefix + match['number'].replace('–', '-')
                    if current in articles:
                        raise ValueError(f'Identificador repetido na edição do Senado: {current}')
                    articles[current] = (name, paragraph.get('id'), [line])
                elif style == 'Texto_Tx-PIA------I--a-' and current:
                    articles[current][2].append(element_text(paragraph))
    return articles


def strip_notes(text):
    text = ' '.join(text.split())
    if PLAIN_NOTE.fullmatch(text):
        return ''
    # Keep explicit judicial/status caveats, including those embedded in editorial notes.
    if CAVEAT.search(text) or STATUS_CHANGE.search(text):
        return text
    while text:
        before = text
        note = re.search(r'\s+\(([^()]*)\)$', text)
        if note and AMENDMENT_NOTE.fullmatch(note[1]):
            text = text[:note.start()]
        else:
            text = strip_editorial_tail(text)
        if before == text:
            return text
    return text


def projection(paragraphs):
    content = ' '.join(strip_notes(line) for line in paragraphs)
    content = unicodedata.normalize('NFC', content).translate(TYPOGRAPHY)
    content = re.sub(r'(?<=\d)\s*[º°](?!\w)', 'º', content)
    content = re.sub(r'\bn\s*[º°](?=\s*\d)', 'nº ', content)
    return tuple(TOKENS.findall(content)), tuple(WORDS.findall(content.lower()))


def classify(change, senate, documented):
    if documented:
        return 'documentary_' + documented
    if change['matchedByRange'] or change['conflictingStatusReference']:
        return 'further_review'
    left, right = (change[side] for side in ('before', 'after'))
    if left['title'] != right['title']:
        return 'further_review'
    lexa, lexa_words = projection(surviving_paragraphs(left))
    camara, camara_words = projection(surviving_paragraphs(right))
    independent = projection(senate[2])[0] if senate else None
    if lexa == camara:
        return 'same_normalized'
    if lexa == independent:
        return 'senate_matches_lexa'
    if camara == independent:
        return 'senate_matches_camara'
    if lexa_words == camara_words:
        return 'same_words'
    return 'further_review'


def preview_choice(change, document=None):
    """Choose a preview disposition for each compared article without judging legal effect."""
    if document:
        return 'documentary'
    if change['historicalDiffers']:
        return 'keep_history'
    if change['matchedByRange'] or change['conflictingStatusReference']:
        return 'keep_pending'
    left, right = change['before'], change['after']
    if left is None or right is None or left['title'] != right['title']:
        return 'keep_pending'
    before, after = map(surviving_paragraphs, (left, right))
    # Compare by paragraph, keeping markers and legal punctuation. Do not promote
    # a variant on a text-only match when it adds or removes legal-status context.
    if ([projection([line])[0] for line in before if strip_notes(line)] ==
            [projection([line])[0] for line in after if strip_notes(line)] and
            [line for line in before if LEGAL_CONTEXT.search(line) or CAVEAT.search(line)] ==
            [line for line in after if LEGAL_CONTEXT.search(line) or CAVEAT.search(line)]):
        return 'editorial'
    return 'keep_pending'


def document_decisions(comparison):
    decisions = json.loads((ROOT / 'monitor/constitution-preview-decisions.json').read_text(encoding='utf-8'))
    changes = {item['articleId']: item for item in comparison['differences']}
    for decision in decisions:
        matched = []
        for key, pair in decision['articles'].items():
            item = changes.get(key)
            if item and matches_documented_pair(item, pair):
                matched.append(key)
        if matched:
            yield decision, matched


def write_review(path, comparison, senate):
    groups = list(document_decisions(comparison))
    documented = {key: group for group, keys in groups for key in keys}
    rows = []
    counts = Counter()
    choices = Counter()
    history_count = 0
    for change in comparison['differences']:
        key = change['articleId']
        decision = documented.get(key)
        choice = preview_choice(change, decision)
        choices[choice] += 1
        if change['kind'] == 'text_review':
            evidence = decision['edition'] if decision else None
            classification = classify(change, senate.get(key), evidence)
            counts[classification] += 1
            finding = LABELS[classification][0]
        else:
            finding = {'historical_difference': 'Variação nas redações riscadas',
                       'editorial_representation': 'Representação editorial'}.get(change['kind'], change['kind'])
        scope = 'ADCT' if change['scope'] == 'adct' else 'CF'
        source_file, anchor, _ = senate.get(key, (None, None, None))
        locator = source_file.removeprefix('OEBPS/') if source_file else '—'
        if anchor:
            locator += '#' + anchor
        history_count += change['historicalDiffers']
        history = 'Sim' if change['historicalDiffers'] else '—'
        rows.append(f'| {scope} · {key.removeprefix("adct-")} | {finding} | '
                    f'{PREVIEW_CHOICES[choice]} | {history} | {locator} |')

    lines = [
        '# Conferência das divergências constitucionais', '',
        f'{len(rows)} divergências da comparação completa, das quais {sum(counts.values())} foram sinalizadas para revisão textual. '
        'As decisões documentais indicam a edição escolhida para a divergência específica. '
        'A revisão do restante do artigo e do histórico é independente. '
        'As coincidências são indícios para revisão jurídica e se referem ao texto sem riscos, '
        'com notas editoriais reconhecidas e chamadas de rodapé retiradas da comparação. '
        'A pontuação é mantida na comparação de texto. '
        f'Em {history_count} artigos há também diferenças nos trechos riscados das fontes, indicadas na tabela. '
        'O relatório bruto mantém ambas as versões integrais. '
        'O texto de base é preservado sempre que a substituição possa perder redações históricas ou contexto sem evidência suficiente.', '',
        f'- Lexa (Planalto), SHA-256 semântico {comparison["currentEdition"]["sha256"]}.',
        f'- Câmara, SHA-256 semântico {comparison["semanticSha256"]}.',
        f'- Senado, [ePub compilado até a EC 141]({SENATE_URL}), SHA-256 {SENATE_SHA256}.', '',
        '| Resultado | Critério | Artigos |', '| --- | --- | ---: |',
        *(f'| {label} | {criterion} | {counts[key]} |' for key, (label, criterion) in LABELS.items()), '',
        '## Decisões na prévia', '',
        '| Ação | Artigos |', '| --- | ---: |',
        *(f'| {label} | {choices[key]} |' for key, label in PREVIEW_CHOICES.items()), '',
        '## Decisões documentais aplicadas à prévia', '',
    ]
    for decision, keys in groups:
        ids = ', '.join(keys)
        edition = {'planalto': 'Planalto', 'camara': 'Câmara'}[decision['edition']]
        links = ' · '.join(f'[{s["label"]}]({s["url"]})' for s in decision['sources'])
        lines.extend([f'- **{ids} · {edition}** — {decision["reason"]} {links}', ''])
    lines.extend(['## Resultado por artigo', '',
                  '| Artigo | Evidência textual | Decisão na prévia | Diferença em trecho riscado | Localizador no EPUB do Senado |',
                  '| --- | --- | --- | --- | --- |', *rows, '',
                  '## Reprodução', '',
                  'Use o JSON original da comparação da Câmara e o EPUB identificado acima.', '',
                  '```sh',
                  'python scripts/review_constitution.py camara.json CF88_EC141_ebook.epub revisao.md',
                  '```', ''])
    path.write_text('\n'.join(lines), encoding='utf-8')
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('comparison', type=Path)
    parser.add_argument('senate_epub', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = json.loads(args.comparison.read_text(encoding='utf-8'))
    comparison = next(result for result in report['results'] if result['id'] == 'cf')
    if report['provider'] != 'camara' or comparison['status'] != 'compared':
        parser.error('É necessária uma comparação constitucional concluída com a Câmara.')
    print(dict(write_review(args.output, comparison, senate_articles(args.senate_epub))))


if __name__ == '__main__':
    main()
