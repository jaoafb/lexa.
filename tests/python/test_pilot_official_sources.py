import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from camara_comparison import compare_camara
from import_official import digest
from pilot_official_sources import (
    ROOT, apply_constitution_preview_decisions, combine_documents, load_js, parse_html, probe,
    write_constitution_review,
)
from review_constitution import preview_choice, projection


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

    def test_preview_retains_source_and_versions_only_for_reviewed_pair(self):
        def article(text, section):
            return {'id': '39', 'scope': 'main', 'sectionId': section, 'paragraphs': [
                {'runs': [{'text': text, 'deleted': False}]},
            ]}

        current = {'source': {'url': 'https://example.test/planalto'},
                   'articles': [article('Art. 39 Redação em uso.', 'old')]}
        candidate = {'source': {'url': 'https://example.test/camara'},
                     'articles': [article('Art. 39 Outra redação.', 'new')]}
        changes = compare_camara(current, candidate)
        change = changes[0]
        fingerprints = {'lexaSha256': digest(change['before']), 'camaraSha256': digest(change['after'])}
        decisions = [{'reason': 'Conferência documental', 'sources': [], 'edition': 'planalto',
                      'articles': {'39': fingerprints}}]

        updated = {'articles': [article('Art. 39 Alteração posterior.', 'new')]}
        with self.assertRaisesRegex(ValueError, 'mudou desde a conferência'):
            apply_constitution_preview_decisions(current, updated, compare_camara(current, updated), decisions)
        self.assertEqual(updated['articles'][0], article('Art. 39 Alteração posterior.', 'new'))

        camara = apply_constitution_preview_decisions(current, candidate, changes,
                                                      [{**decisions[0], 'edition': 'camara'}])
        self.assertEqual(camara['39']['edition'], 'camara')
        self.assertEqual(candidate['articles'][0], article('Art. 39 Outra redação.', 'new'))

        held = apply_constitution_preview_decisions(current, candidate, changes, decisions)
        self.assertEqual(list(held), ['39'])
        self.assertEqual(candidate['articles'][0]['paragraphs'], current['articles'][0]['paragraphs'])
        self.assertEqual(candidate['articles'][0]['sectionId'], 'new')
        self.assertEqual(candidate['articles'][0]['documentSource']['url'], current['source']['url'])
        self.assertEqual(current['articles'][0]['sectionId'], 'old')
        self.assertEqual(changes[0]['after']['paragraphs'], article('Art. 39 Outra redação.', 'new')['paragraphs'])

    def test_constitution_projection_keeps_punctuation_and_status(self):
        before = ['Art. 1º Vale, sim.']
        with_note = ['Art. 1° Vale, sim. (Redação dada pela Emenda Constitucional nº 8, de 1995)']
        with_status = ['Art. 1º Vale, sim. (Vide ADI 100, dispositivo declarado inconstitucional)']
        self.assertEqual(projection(before), projection(with_note))
        self.assertNotEqual(projection(before)[0], projection(['Art. 1º Vale sim.'])[0])
        self.assertNotEqual(projection(before), projection(with_status))

    def test_preview_retains_unverified_text_and_context(self):
        def source(text, deleted=False):
            return {'articles': [{'id': '1', 'scope': 'main', 'sectionId': 'a', 'paragraphs': [
                {'runs': [{'text': text, 'deleted': deleted}]},
            ]}], 'source': {'url': 'https://example.test/planalto'}}

        current = source('Art. 1º Vale, sim.')
        candidate = source('Art. 1º Vale sim.')
        differences = compare_camara(current, candidate)
        self.assertEqual(preview_choice(differences[0]), 'keep_pending')
        apply_constitution_preview_decisions(current, candidate, differences, [])
        self.assertEqual(candidate['articles'][0]['paragraphs'], current['articles'][0]['paragraphs'])
        self.assertEqual(candidate['articles'][0]['documentSource']['provider'], 'planalto')

        candidate = source('Art. 1º Vale, sim. (Vide ADI 100)')
        self.assertEqual(preview_choice(compare_camara(current, candidate)[0]), 'keep_pending')
        candidate = source('Art. 1° Vale, sim. (Redação dada pela Emenda Constitucional nº 8, de 1995)')
        self.assertEqual(preview_choice(compare_camara(current, candidate)[0]), 'editorial')
        candidate = source('Art. 1º Vale, sim.', deleted=True)
        self.assertEqual(preview_choice(compare_camara(current, candidate)[0]), 'keep_history')
