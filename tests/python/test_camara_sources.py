from textwrap import dedent
import unittest

from camara_sources import (
    CAMARA_HOST, CONSTITUTION_FILES, constitution_links, publication_392_d,
    publication_kind, references_392_d,
)


def html(source):
    return ('<html lang="pt-br"><meta charset="utf-8"><body>' + dedent(source) + '</body></html>').encode()


class CamaraSourcesTests(unittest.TestCase):
    def test_constitution_index_uses_labelled_html_links_and_ignores_stale_image_link(self):
        page = html(f'''
            <a href="{CONSTITUTION_FILES}ConstituicaoTextoAtualizado_EC%20139.html"><img alt="Baixar"></a>
            <a href="{CONSTITUTION_FILES}ConstituicaoTextoAtualizado_EC%20142.html">formato HTML</a>
            <a href="{CONSTITUTION_FILES}constituicao-adct-de-1988_ec-140.html"><img alt="Baixar"> formato html</a>
        ''')

        self.assertEqual(constitution_links(page, None), [
            f'https://{CAMARA_HOST}{CONSTITUTION_FILES}ConstituicaoTextoAtualizado_EC%20142.html',
            f'https://{CAMARA_HOST}{CONSTITUTION_FILES}constituicao-adct-de-1988_ec-140.html',
        ])

    def test_constitution_index_rejects_incomplete_ambiguous_or_untrusted_links(self):
        cf = f'<a href="{CONSTITUTION_FILES}ConstituicaoTextoAtualizado_EC%20142.html">formato html</a>'
        adct = f'<a href="{CONSTITUTION_FILES}constituicao-adct-de-1988_ec-140.html">formato html</a>'
        for page in (cf, cf + cf.replace('142', '143') + adct,
                     cf.replace('href="', 'href="https://example.org') + adct):
            with self.subTest(page=page), self.assertRaises(ValueError):
                constitution_links(html(page), None)

    def test_original_publication_supplies_text_and_declared_effective_date(self):
        page = html("""
            <h1>LEI Nº 15.371, DE 31 DE MARÇO DE 2026</h1>
            <div>'Art. 392-D. Redação publicada.' 'Art. 393. Redação seguinte.'</div>
            <p>Art. 14. Esta Lei entra em vigor no dia 1º de janeiro de 2027.</p>
            <p>Este texto não substitui o original publicado no Diário Oficial da União - Seção 1 de 01/04/2026</p>
        """)

        evidence = publication_392_d(page, None)

        self.assertEqual(evidence['publishedOn'], '2026-04-01')
        self.assertEqual(evidence['declaredEffectiveOn'], '2027-01-01')
        self.assertEqual(evidence['text'], 'Art. 392-D. Redação publicada.')
        self.assertEqual(publication_kind(evidence, '2027-01-01T02:59:59+00:00'), 'published_future_effect')
        self.assertEqual(publication_kind(evidence, '2027-01-01T03:00:00+00:00'), 'published_text_pending_review')

        for missing in (b'15.371', b'392-D', b'2027', b'01/04/2026'):
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                publication_392_d(page.replace(missing, b'---'), None)

    def test_only_the_known_cross_reference_triggers_the_supplement(self):
        difference = {'kind': 'unmatched', 'articleId': '392-D', 'scope': 'main', 'before': None,
                      'after': {'paragraphs': [{'runs': [
                          {'text': 'Art. 392-D. (Vide Lei nº 15.371, de 31/3/2026)', 'deleted': False},
                      ]}]}}

        self.assertTrue(references_392_d(difference))
        self.assertFalse(references_392_d({**difference, 'scope': 'adct'}))
        difference['after']['paragraphs'][0]['runs'][0]['text'] += ' Redação consolidada.'
        self.assertFalse(references_392_d(difference))
