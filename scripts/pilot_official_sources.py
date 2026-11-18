"""Compare three laws from one official portal with the current reader edition."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from difflib import unified_diff
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from camara_comparison import compare_camara
from camara_sources import (
    CAMARA_HOST, CONSTITUTION_INDEX, LAW_15371_URL, constitution_links,
    publication_392_d, publication_kind, references_392_d,
)
from check_official_sources import ADCT, ROOT, fingerprint, parse_html, validate
from import_official import article_version, convert, load_js, version_signature
from official_http import ALLOWED_HOSTS, SourceFetchError, download_once

PILOT_IDS = ('cf', 'civil', 'clt')
PROVIDERS = {
    'planalto': 'www.planalto.gov.br',
    'classico': 'portaldalegislacao-classico.presidencia.gov.br',
    'novo': 'portaldalegislacao.presidencia.gov.br',
    'camara': CAMARA_HOST,
}
CAMARA_PATHS = {
    'civil': ('/legin/fed/lei/2002/lei-10406-10-janeiro-2002-432893-normaatualizada-pl.html',),
    'clt': ('/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-normaatualizada-pe.html',),
}


def public_url(url):
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.hostname or '', parts.path, '', ''))


def article_differences(current, candidate):
    before = {article['id']: article for article in current['articles']}
    after = {article['id']: article for article in candidate['articles']}
    differences = []
    for key in dict.fromkeys([*before, *after]):
        old_article, new_article = before.get(key), after.get(key)
        old, new = article_version(old_article), article_version(new_article)
        old_end = old_article.get('rangeEnd') if old_article else None
        new_end = new_article.get('rangeEnd') if new_article else None
        if old_end == new_end and version_signature(old) == version_signature(new):
            continue
        differences.append({
            'articleId': key, 'scope': (new_article or old_article)['scope'],
            'before': old, 'after': new, 'beforeRangeEnd': old_end, 'afterRangeEnd': new_end,
        })
    return differences


def download_document(url, allowed_hosts, downloader, *, parse=parse_html):
    result = {'requestedUrl': url, 'responses': [], 'status': 'transfer_failed'}

    def observe(url, status, location):
        response = {'url': public_url(url), 'status': status}
        if location:
            try:
                response['redirect'] = public_url(urljoin(url, location))
            except ValueError:
                response['redirect'] = 'inválido'
        result['responses'].append(response)

    try:
        raw, encoding = downloader(url, allowed_hosts, observe_response=observe)
    except (SourceFetchError, ValueError) as error:
        return {**result, 'reason': str(error)}, None
    except OSError as error:
        return {**result, 'reason': f'Falha de transferência ou leitura ({type(error).__name__}).'}, None

    result.update(rawSha256=sha256(raw).hexdigest(), bytes=len(raw), status='invalid_document')
    try:
        document = parse(raw, encoding)
    except ValueError as error:
        return {**result, 'reason': str(error)}, None
    return {**result, 'status': 'parsed'}, document


def combine_documents(documents):
    if len(documents) == 1:
        return documents[0]
    constitution, adct = documents
    headings = [index for index, block in enumerate(adct['blocks'])
                if ''.join(run['text'] for run in block).upper() == ADCT]
    if len(headings) != 1:
        raise ValueError('Cabeçalho do ADCT ausente ou repetido no arquivo da Câmara.')
    return {
        'blocks': constitution['blocks'] + adct['blocks'][headings[0]:],
        'deletion_styles': sorted(set(constitution['deletion_styles'] + adct['deletion_styles'])),
    }


def probe(spec, current, provider, checked_at, downloader=download_once):
    host = PROVIDERS[provider]
    allowed_hosts = ALLOWED_HOSTS if provider == 'planalto' else {host}
    result = {
        'id': spec['id'],
        'currentEdition': {key: current['source'][key] for key in ('url', 'capturedAt', 'sha256')},
    }
    if provider == 'camara' and spec['id'] == 'cf':
        index, urls = download_document(CONSTITUTION_INDEX, allowed_hosts, downloader, parse=constitution_links)
        result['index'] = index
        if urls is None:
            return {**result, 'status': index['status'], 'reason': index['reason']}
    else:
        paths = CAMARA_PATHS[spec['id']] if provider == 'camara' else (urlsplit(spec['url']).path,)
        urls = [f'https://{host}{path}' for path in paths]
    captures = [download_document(url, allowed_hosts, downloader) for url in urls]
    resources, documents = zip(*captures)
    result['resources'] = resources
    for resource, document in captures:
        if document is None:
            return {**result, 'status': resource['status'], 'reason': resource['reason']}

    final_url = resources[0]['responses'][-1]['url']
    candidate_spec = {**spec, 'url': final_url}
    try:
        document = combine_documents(documents)
        result['articleCounts'] = validate(document, candidate_spec)
    except ValueError as error:
        return {**result, 'status': 'invalid_document', 'reason': str(error)}

    snapshot = {
        'schema_version': 1, 'id': spec['id'], 'source_url': final_url,
        'captured_at': checked_at, 'raw_sha256': resources[0]['rawSha256'] if len(resources) == 1 else None,
        'semantic_sha256': fingerprint(document), 'document': document,
    }
    try:
        candidate = convert(candidate_spec, snapshot, allowed_hosts=allowed_hosts)
    except ValueError as error:
        return {**result, 'status': 'conversion_failed', 'reason': str(error)}

    compare = compare_camara if provider == 'camara' else article_differences
    try:
        differences = compare(current, candidate)
    except ValueError as error:
        return {**result, 'status': 'comparison_failed', 'reason': str(error)}
    if provider == 'camara':
        if spec['id'] == 'clt':
            for difference in differences:
                if references_392_d(difference):
                    source, evidence = download_document(LAW_15371_URL, allowed_hosts, downloader, parse=publication_392_d)
                    difference['relatedPublication'] = {**source, **(evidence or {})}
                    if evidence is None:
                        result['evidenceFailure'] = source['reason']
                    else:
                        difference['kind'] = publication_kind(evidence, checked_at)
        result['differenceKinds'] = dict(Counter(item['kind'] for item in differences))
        result['idsMatchedByRange'] = sum(item['matchedByRange'] for item in differences)

    status = 'evidence_failed' if 'evidenceFailure' in result else 'compared'
    return {**result, 'status': status, 'semanticSha256': snapshot['semantic_sha256'],
            'differences': differences,
            'structureDiffers': any(current[key] != candidate[key] for key in ('sections', 'introductions'))}


def write_summary(path, provider, results):
    lines = [f'### Conferência de legislação — {provider}', '',
             '| Coleção | Resultado | Texto para revisar | Histórico preservado | Vetos documentais | Publicações pendentes | Sem correspondência |',
             '| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for result in results:
        kinds = result.get('differenceKinds')
        totals = [str(sum(kinds.get(key, 0) for key in keys)) if kinds is not None else '—' for keys in (
            ('text_review',), ('retained_history',), ('documentary_veto',),
            ('published_future_effect', 'published_text_pending_review'), ('unmatched',),
        )]
        lines.append('| ' + ' | '.join([result['id'], result['status'], *totals]) + ' |')
    lines.extend(['', 'O artefato JSON registra as fontes, os hashes, os textos e as diferenças para revisão.'])
    with path.open('a', encoding='utf-8') as summary:
        summary.write('\n'.join(lines) + '\n')


def review_lines(version):
    lines = [version['title']] if version['title'] else []
    lines.extend(''.join(f"[RISCADO] {run['text']} [/RISCADO]" if run['deleted'] else run['text']
                         for run in paragraph['runs']) for paragraph in version['paragraphs'])
    return lines


def write_constitution_review(path, comparison):
    lines = ['# Constituição e ADCT — divergências de texto', '',
             'Comparação para revisão. A linha removida mostra a edição do Lexa e a linha adicionada mostra a Câmara.', '']
    for difference in comparison['differences']:
        if difference['kind'] != 'text_review':
            continue
        scope = 'ADCT' if difference['scope'] == 'adct' else 'Constituição'
        lines.extend([f"## {scope} · Art. {difference['articleId'].removeprefix('adct-')}", ''])
        delta = unified_diff(review_lines(difference['before']), review_lines(difference['after']),
                             fromfile='Lexa', tofile='Câmara', n=1, lineterm='')
        lines.extend('    ' + line for line in delta)
        lines.append('')
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=PROVIDERS, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()
    specs = {spec['id']: spec for spec in json.loads((ROOT / 'monitor/sources.json').read_text(encoding='utf-8'))}
    current = load_js(ROOT / 'data/official/legislation.js', 'officialImported')
    checked_at = datetime.now(timezone.utc).isoformat(timespec='seconds')
    results = [probe(specs[key], current[key], args.provider, checked_at) for key in PILOT_IDS]
    complete = all(result['status'] == 'compared' for result in results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({
        'provider': args.provider, 'checkedAt': checked_at, 'complete': complete, 'results': results,
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.provider == 'camara':
        review_path = args.output.with_name(args.output.stem + '-revisao-constitucional.md')
        if results[0]['status'] == 'compared':
            write_constitution_review(review_path, results[0])
        else:
            review_path.unlink(missing_ok=True)
    if args.summary:
        write_summary(args.summary, args.provider, results)
    for result in results:
        detail = result.get('reason') or result.get('evidenceFailure') or f"{len(result['differences'])} artigos com diferenças para revisão"
        print(f"{result['id']}: {result['status']} — {detail}")
        if 'differenceKinds' in result:
            print(f"  {result['idsMatchedByRange']} identificadores associados a intervalos; "
                  + json.dumps(result['differenceKinds'], sort_keys=True))
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
