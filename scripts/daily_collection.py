"""Daily read-only comparison against the published corpus, with partial results."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from collection_transport import EvidenceTransport
from pilot_official_sources import ROOT, PILOT_IDS, load_js, probe


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def exit_status(report):
    return int(not report['successfulComparisons'] or any(
        item['status'] == 'internal_error' for item in report['results']))


def run(specs, current, directory, *, compare=probe, transport=None):
    # Never overwrite a previous run. Each directory is an independent evidence set.
    directory.mkdir(parents=True, exist_ok=False)
    transport = transport or EvidenceTransport(directory / 'originals')
    checked = datetime.now(timezone.utc).isoformat(timespec='seconds')
    jobs = [(spec, 'planalto') for spec in specs]
    jobs += [(spec, 'camara') for spec in specs if spec['id'] in PILOT_IDS]
    report = {'schemaVersion': 1, 'checkedAt': checked, 'complete': False,
              'comparisonBasis': 'published_corpus_not_previous_run',
              'expectedComparisons': len(jobs), 'results': []}
    save(directory / 'report.json', report)
    for spec, provider in jobs:
        start = len(transport.attempts)
        try:
            result = compare(spec, current[spec['id']], provider, checked, downloader=transport)
        except Exception as error:
            # Preserve progress while surfacing unexpected programming/parser failures.
            # Do not expose arbitrary exceptions containing response bodies or secrets.
            result = {'id': spec['id'], 'status': 'internal_error', 'errorType': type(error).__name__}
        result.update(provider=provider, attempts=transport.attempts[start:])
        report['results'].append(result)
        save(directory / 'report.json', report)
    report['complete'] = all(item['status'] == 'compared' for item in report['results'])
    report['successfulComparisons'] = sum(item['status'] == 'compared' for item in report['results'])
    report['availabilityFailures'] = sum(item['status'] in {
        'transfer_failed', 'invalid_document', 'conversion_failed', 'comparison_failed', 'evidence_failed'
    } for item in report['results'])
    save(directory / 'report.json', report)
    lines = ['# Conferência diária', '',
             'Diferenças contra a edição do Lexa, não necessariamente alterações surgidas hoje. '
             'Nenhuma fonte é substituída ou homologada automaticamente.', '',
             '| Coleção | Fonte | Resultado | Diferenças |', '| --- | --- | --- | ---: |']
    for item in report['results']:
        count = str(len(item['differences'])) if item['status'] == 'compared' else '—'
        lines.append(f"| {item['id']} | {item['provider']} | {item['status']} | {count} |")
    lines += ['', 'HTMLs recebidos e metadados de tentativas estão no artefato. '
              'Falhas não significam ausência de alterações. Resultados parciais exigem atenção.']
    (directory / 'summary.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Diretório novo para esta execução.')
    parser.add_argument('--summary', type=Path)
    args = parser.parse_args()
    specs = json.loads((ROOT / 'monitor/sources.json').read_text(encoding='utf-8'))
    current = load_js(ROOT / 'data/official/legislation.js', 'officialImported')
    report = run(specs, current, args.output)
    if args.summary:
        with args.summary.open('a', encoding='utf-8') as stream:
            stream.write((args.output / 'summary.md').read_text(encoding='utf-8'))
    print(f"{report['successfulComparisons']}/{report['expectedComparisons']} comparações concluídas.")
    for item in report['results']:
        if item['status'] != 'compared':
            reason = item.get('reason') or item.get('errorType') or 'motivo não registrado'
            print(f"::warning title=Fonte {item['id']} ({item['provider']})::{item['status']}: {reason}")
    # Source outages produce a partial, reviewable artifact. A programming failure
    # or a run without any valid comparison remains a failed automation.
    return exit_status(report)


if __name__ == '__main__':
    raise SystemExit(main())
