"""Compare three laws from one official portal with the current reader edition."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from check_official_sources import ROOT, fingerprint, parse_html, validate
from import_official import article_version, convert, load_js, version_signature
from official_http import ALLOWED_HOSTS, SourceFetchError, download_once

PILOT_IDS = ('cf', 'civil', 'clt')
PROVIDERS = {
    'planalto': 'www.planalto.gov.br',
    'classico': 'portaldalegislacao-classico.presidencia.gov.br',
    'novo': 'portaldalegislacao.presidencia.gov.br',
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


def probe(spec, current, provider, checked_at, downloader=download_once):
    host = PROVIDERS[provider]
    allowed_hosts = ALLOWED_HOSTS if provider == 'planalto' else {host}
    path = urlsplit(spec['url']).path
    candidate_spec = {**spec, 'url': f'https://{host}{path}'}
    result = {
        'id': spec['id'], 'requestedUrl': candidate_spec['url'], 'responses': [],
        'currentEdition': {key: current['source'][key] for key in ('url', 'capturedAt', 'sha256')},
        'status': 'transfer_failed',
    }

    def observe(url, status, location):
        response = {'url': public_url(url), 'status': status}
        if location:
            try:
                response['redirect'] = public_url(urljoin(url, location))
            except ValueError:
                response['redirect'] = 'inválido'
        result['responses'].append(response)

    try:
        raw, encoding = downloader(candidate_spec['url'], allowed_hosts, observe_response=observe)
    except (SourceFetchError, ValueError) as error:
        return {**result, 'reason': str(error)}

    result.update(rawSha256=sha256(raw).hexdigest(), bytes=len(raw), status='invalid_document')
    try:
        document = parse_html(raw, encoding)
        result['articleCounts'] = validate(document, candidate_spec)
    except ValueError as error:
        return {**result, 'reason': str(error)}

    result['status'] = 'conversion_failed'
    final_url = result['responses'][-1]['url']
    candidate_spec['url'] = final_url
    snapshot = {
        'schema_version': 1, 'id': spec['id'], 'source_url': final_url,
        'captured_at': checked_at, 'raw_sha256': result['rawSha256'],
        'semantic_sha256': fingerprint(document), 'document': document,
    }
    try:
        candidate = convert(candidate_spec, snapshot, allowed_hosts=allowed_hosts)
    except ValueError as error:
        return {**result, 'reason': str(error)}

    return {**result, 'status': 'compared', 'semanticSha256': snapshot['semantic_sha256'],
            'differences': article_differences(current, candidate),
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
    return 0 if complete else 1


if __name__ == '__main__':
    raise SystemExit(main())
