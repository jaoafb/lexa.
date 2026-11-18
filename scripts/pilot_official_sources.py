"""Compare three laws from one official portal with the current reader edition."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from camara_comparison import compare_camara
from check_official_sources import ADCT, ROOT, fingerprint, parse_html, validate
from import_official import article_version, convert, load_js, version_signature
from official_http import ALLOWED_HOSTS, SourceFetchError, download_once

PILOT_IDS = ('cf', 'civil', 'clt')
PROVIDERS = {
    'planalto': 'www.planalto.gov.br',
    'classico': 'portaldalegislacao-classico.presidencia.gov.br',
    'novo': 'portaldalegislacao.presidencia.gov.br',
    'camara': 'www2.camara.leg.br',
}
CAMARA_CONSTITUTION = '/atividade-legislativa/legislacao/constituicao1988/arquivos/'
CAMARA_PATHS = {
    'cf': (CAMARA_CONSTITUTION + 'ConstituicaoTextoAtualizado_EC%20141.html',
           CAMARA_CONSTITUTION + 'constituicao-adct-de-1988_ec-136.html'),
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


def download_document(url, allowed_hosts, downloader):
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
        document = parse_html(raw, encoding)
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
    paths = CAMARA_PATHS[spec['id']] if provider == 'camara' else (urlsplit(spec['url']).path,)
    captures = [download_document(f'https://{host}{path}', allowed_hosts, downloader) for path in paths]
    resources, documents = zip(*captures)
    result = {
        'id': spec['id'], 'resources': resources,
        'currentEdition': {key: current['source'][key] for key in ('url', 'capturedAt', 'sha256')},
    }
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
        result['differenceKinds'] = dict(Counter(item['kind'] for item in differences))
        result['idsMatchedByRange'] = sum(item['matchedByRange'] for item in differences)

    return {**result, 'status': 'compared', 'semanticSha256': snapshot['semantic_sha256'],
            'differences': differences,
            'structureDiffers': any(current[key] != candidate[key] for key in ('sections', 'introductions'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provider', choices=PROVIDERS, required=True)
    parser.add_argument('--output', type=Path, required=True)
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
    for result in results:
        detail = result.get('reason') or f"{len(result['differences'])} artigos com diferenças para revisão"
        print(f"{result['id']}: {result['status']} — {detail}")
        if 'differenceKinds' in result:
            print(f"  {result['idsMatchedByRange']} identificadores associados a intervalos; "
                  + json.dumps(result['differenceKinds'], sort_keys=True))
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
