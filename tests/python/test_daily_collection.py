from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from collection_transport import EvidenceTransport
from daily_collection import exit_status, run
from official_http import SourceFetchError


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
            if spec['id'] == 'civil' and provider == 'planalto':
                raise RuntimeError('parser failure')
            return {'id': spec['id'], 'status': 'compared', 'differences': []}

        with TemporaryDirectory() as temporary:
            directory = Path(temporary, 'run')
            report = run(specs, current, directory, compare=compare, transport=Transport())
            self.assertFalse(report['complete'])
            self.assertEqual(report['expectedComparisons'], 3)
            self.assertEqual(report['successfulComparisons'], 2)
            self.assertEqual(report['results'][0]['status'], 'internal_error')
            self.assertTrue((directory / 'report.json').is_file())
            self.assertTrue((directory / 'summary.md').is_file())
            self.assertEqual(repr(current), snapshot)

    def test_existing_run_directory_is_never_overwritten(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary, 'existing')
            directory.mkdir()
            with self.assertRaises(FileExistsError):
                run([], {}, directory)

    def test_partial_source_outage_is_reported_without_discarding_successes(self):
        report = {'successfulComparisons': 1, 'expectedComparisons': 2, 'results': [
            {'id': 'civil', 'provider': 'planalto', 'status': 'transfer_failed'},
            {'id': 'civil', 'provider': 'camara', 'status': 'compared'},
        ]}
        self.assertEqual(exit_status(report), 0)
        report['results'][0]['status'] = 'internal_error'
        self.assertEqual(exit_status(report), 1)
        report['successfulComparisons'] = 0
        self.assertEqual(exit_status(report), 1)


if __name__ == '__main__':
    unittest.main()
