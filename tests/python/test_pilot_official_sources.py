import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from pilot_official_sources import ROOT, combine_documents, load_js, parse_html, probe, write_constitution_review


class OfficialSourcePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = {spec['id']: spec for spec in json.loads((ROOT / 'monitor/sources.json').read_text())}
        cls.current = load_js(ROOT / 'data/official/legislation.js', 'officialImported')

    def check_source(self, key, downloader):
        return probe(self.specs[key], self.current[key], 'novo', '2026-11-18T03:00:00+00:00', downloader)

    def test_complete_reference_preserves_constitution_and_adct(self):
        def downloaded(url, allowed_hosts, *, observe_response):
            self.assertEqual(allowed_hosts, {'portaldalegislacao.presidencia.gov.br'})
            observe_response(url, 200, None)
            return (ROOT / 'HTML/Constituição.html').read_bytes(), None

        result = self.check_source('cf', downloaded)
        self.assertEqual(result['status'], 'compared')
        self.assertEqual(result['articleCounts'], {'main': 250, 'adct': 138})
        self.assertEqual(result['differences'], [])

    def test_incomplete_clt_has_no_comparison(self):
        def downloaded(url, allowed_hosts, *, observe_response):
            observe_response(url, 200, None)
            return (ROOT / 'HTML/Del5452compilado.html').read_bytes(), None

        result = self.check_source('clt', downloaded)
        self.assertEqual(result['status'], 'invalid_document')
        self.assertIn('faltam artigos-base', result['reason'])
        self.assertNotIn('differences', result)

    def test_rejected_redirect_keeps_sanitized_evidence(self):
        def blocked(url, allowed_hosts, *, observe_response):
            observe_response(url, 302, 'https://gov.br/planalto?token=secret')
            raise ValueError('Destino diferente das fontes HTTPS oficiais permitidas')

        result = self.check_source('civil', blocked)
        self.assertEqual(result['status'], 'transfer_failed')
        self.assertEqual(result['resources'][0]['responses'][0]['redirect'], 'https://gov.br/planalto')
        self.assertNotIn('secret', json.dumps(result))
        self.assertNotIn('differences', result)

    def test_camara_adct_keeps_its_own_heading(self):
        constitution = parse_html(b'<h1>Constituicao</h1><p>Art. 1 Texto constitucional.</p>')
        adct = parse_html(('<h1>Câmara dos Deputados</h1>'
                          '<h2>ATO DAS DISPOSIÇÕES CONSTITUCIONAIS TRANSITÓRIAS</h2>'
                          '<p>Art. 1 Texto transitório.</p>').encode())
        combined = combine_documents([constitution, adct])
        self.assertEqual(combined['blocks'], constitution['blocks'] + adct['blocks'][1:])
        with self.assertRaisesRegex(ValueError, 'Cabeçalho do ADCT'):
            combine_documents([constitution, constitution])

    def test_constitution_review_labels_scope_and_preserves_deleted_markers(self):
        before = {'title': None, 'paragraphs': [{'runs': [{'text': 'Redação anterior.', 'deleted': True}]}]}
        after = {'title': None, 'paragraphs': [{'runs': [{'text': 'Texto da Câmara.', 'deleted': False}]}]}
        change = {'scope': 'adct', 'articleId': 'adct-2', 'kind': 'text_review', 'before': before, 'after': after}
        editorial = {**change, 'articleId': 'adct-3', 'kind': 'editorial_representation'}
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'review.md'
            write_constitution_review(path, {'differences': [change, editorial]})
            text = path.read_text(encoding='utf-8')

        self.assertIn('## ADCT · Art. 2', text)
        self.assertIn('    -[RISCADO] Redação anterior. [/RISCADO]', text)
        self.assertIn('    +Texto da Câmara.', text)
        self.assertNotIn('Art. 3', text)
