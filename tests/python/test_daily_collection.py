from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from collection_transport import EvidenceTransport
from daily_collection import exit_status, run
from official_http import SourceFetchError
from camara_sources import CAMARA_IDS


class DailyCollectionTests(unittest.TestCase):
    def test_evidence_transport_preserves_exact_bytes_by_hash(self):
        responses = [SourceFetchError('temporário', retryable=True), (b'<html>Lei</html>', 'utf-8')]

        def download(url, allowed, *, observe_response):
            value = responses.pop(0)
            observe_response(url, 503 if isinstance(value, Exception) else 200, None)
            if isinstance(value, Exception):
                raise value
            return value

        with TemporaryDirectory() as temporary:
            pauses = []
            transport = EvidenceTransport(Path(temporary), download=download, sleeper=pauses.append)
            raw, encoding = transport('https://example.test/lei', {'example.test'}, observe_response=lambda *_: None)
            self.assertEqual((raw, encoding), (b'<html>Lei</html>', 'utf-8'))
            self.assertEqual([item['status'] for item in transport.attempts], ['failed', 'received'])
            evidence = Path(temporary, transport.attempts[-1]['file'].removeprefix('originals/'))
            self.assertEqual(evidence.read_bytes(), raw)
            self.assertEqual(pauses, [1, 2, 1])

    def test_partial_failure_preserves_other_results_and_never_changes_corpus(self):
        specs = [{'id': 'civil'}, {'id': 'penal'}]
        current = {'civil': {'unchanged': True}, 'penal': {'unchanged': True}}
        snapshot = repr(current)

        class Transport:
            attempts = []

        def compare(spec, corpus, provider, checked, downloader):
            self.assertIs(corpus, current[spec['id']])
            if spec['id'] == 'civil' and provider == 'camara':
                raise RuntimeError('parser failure')
            return {'id': spec['id'], 'status': 'compared', 'differences': []}

        with TemporaryDirectory() as temporary:
            directory = Path(temporary, 'run')
            report = run(specs, current, directory, compare=compare, transport=Transport())
            self.assertFalse(report['complete'])
            self.assertEqual(report['expectedComparisons'], 2)
            self.assertEqual(report['successfulComparisons'], 1)
            self.assertEqual(report['results'][0]['status'], 'internal_error')
            self.assertTrue((directory / 'report.json').is_file())
            self.assertTrue((directory / 'summary.md').is_file())
            self.assertEqual(repr(current), snapshot)

    def test_daily_source_map_covers_every_published_legislation(self):
        import json
        from pilot_official_sources import ROOT

        specs = json.loads((ROOT / 'monitor/sources.json').read_text(encoding='utf-8'))
        self.assertEqual({spec['id'] for spec in specs}, set(CAMARA_IDS))

    def test_existing_run_directory_is_never_overwritten(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary, 'existing')
            directory.mkdir()
            with self.assertRaises(FileExistsError):
                run([], {}, directory)

    def test_only_complete_daily_coverage_has_success_exit_status(self):
        report = {'complete': False, 'successfulComparisons': 1, 'expectedComparisons': 2, 'results': [
            {'id': 'civil', 'provider': 'planalto', 'status': 'transfer_failed'},
            {'id': 'civil', 'provider': 'camara', 'status': 'compared'},
        ]}
        self.assertEqual(exit_status(report), 1)
        report['complete'] = True
        report['successfulComparisons'] = 2
        report['results'][0]['status'] = 'compared'
        self.assertEqual(exit_status(report), 0)


if __name__ == '__main__':
    unittest.main()
