import copy
import unittest

from camara_comparison import compare_camara


def article(number, text, *, scope='main', range_end=None, struck=None):
    key = ('adct-' if scope == 'adct' else '') + str(number)
    entry = {'id': key, 'number': str(number), 'scope': scope, 'paragraphs': [
        {'runs': [{'text': text, 'deleted': False}]},
    ]}
    if range_end is not None:
        entry['rangeEnd'] = range_end
    if struck is not None:
        entry['paragraphs'].insert(0, {'runs': [{'text': struck, 'deleted': True}]})
    return entry


def compare(*, before, after):
    return compare_camara({'articles': before}, {'articles': after})


class CamaraComparisonTests(unittest.TestCase):
    def test_civil_revocation_range_matches_existing_ids_and_retains_source_text(self):
        citation = 'Lei nº 15.040, de 2024'
        before = [article(n, f'Art. {n}. (Revogado pela {citation}) Vigência') for n in (757, 758)]
        text = ('Arts. 757 a 777. (Revogados pela Lei nº 15.040, de 9/12/2024, '
                'publicada no DOU de 10/12/2024, em vigor 1 ano após a publicação)')
        after = [article(757, text, range_end=777)]
        originals = copy.deepcopy((before, after))

        first, second = compare(before=before, after=after)

        self.assertEqual([first['kind'], second['kind']], ['range_representation', 'range_representation'])
        self.assertEqual(second['beforeArticleId'], '758')
        self.assertEqual(second['afterArticleId'], '757')
        self.assertTrue(second['matchedByRange'])
        self.assertEqual(second['after']['paragraphs'][0]['runs'][0]['text'], text)
        self.assertEqual((before, after), originals)

    def test_range_and_individual_article_with_different_revocation_acts_need_review(self):
        before = [article(23, 'Art. 23. (Revogado pela Lei nº 10.000, de 2000)')]
        after = [article(22, 'Arts. 22 a 24. (Revogados pelo Decreto-Lei nº 926, de 10/10/1969)', range_end=24)]

        existing = compare(before=before, after=after)[0]

        self.assertEqual(existing['afterArticleId'], '22')
        self.assertTrue(existing['conflictingStatusReference'])
        self.assertEqual(existing['kind'], 'text_review')

    def test_different_declared_delays_for_the_same_act_need_review(self):
        before = [article(2, 'Art. 2º (Revogado pela Lei nº 1, de 2000, em vigor 30 dias após a publicação)')]
        after = [article(2, 'Art. 2º (Revogado pela Lei nº 1, de 2000, em vigor após 60 dias da publicação)')]

        row = compare(before=before, after=after)[0]

        self.assertTrue(row['conflictingStatusReference'])
        self.assertEqual(row['kind'], 'text_review')

    def test_status_range_cannot_match_suffixed_articles_or_the_other_scope(self):
        before = [article('2-A', 'Art. 2-A. (Revogado)'), article(2, 'Art. 2º (Revogado)', scope='adct')]
        after = [article(1, 'Arts. 1 a 3. (Revogados)', range_end=3)]

        differences = compare(before=before, after=after)

        self.assertEqual([row['kind'] for row in differences], ['unmatched'] * 3)
        self.assertTrue(all(row['afterArticleId'] is None for row in differences[:2]))

    def test_range_mapping_works_when_the_earlier_edition_groups_articles(self):
        before = [article(1, 'Arts. 1 a 3. (Revogados)', scope='adct', range_end=3)]
        after = [article(2, 'Art. 2º (Revogado)', scope='adct')]

        row = next(row for row in compare(before=before, after=after) if row['articleId'] == 'adct-2')

        self.assertEqual((row['beforeArticleId'], row['afterArticleId']), ('adct-1', 'adct-2'))
        self.assertEqual(row['kind'], 'range_representation')

    def test_overlapping_intervals_are_rejected(self):
        before = [article(1, 'Arts. 1 a 3. (Revogados)', range_end=3)]
        after = [*before, article(2, 'Art. 2º (Revogado)')]

        with self.assertRaisesRegex(ValueError, 'Intervalos sobrepostos'):
            compare(before=before, after=after)

    def test_unrecognized_range_qualifier_stays_visible_without_mapping(self):
        before = [article(2, 'Art. 2º Foi mantida esta redação.')]
        after = [article(1, 'Arts. 1 a 3. (Revogados pela Lei nº 1, de 2000, exceto o art. 2º)', range_end=3)]

        row = compare(before=before, after=after)[0]

        self.assertEqual(row['kind'], 'unmatched')
        self.assertIsNone(row['afterArticleId'])

    def test_recognized_editorial_note_and_article_marker_stay_in_the_evidence(self):
        before = [article(1, 'Art. 1 o Vale a mesma redação. (Vigência)')]
        text = 'Art. 1º Vale a mesma redação. (Artigo com redação dada pela Lei nº 1, de 2000 (DOU))'
        after = [article(1, text)]

        row = compare(before=before, after=after)[0]

        self.assertEqual(row['kind'], 'editorial_representation')
        self.assertEqual(row['after']['paragraphs'][0]['runs'][0]['text'], text)

    def test_operative_parentheses_and_punctuation_require_text_review(self):
        before = [article(1, 'Art. 1º O prazo será de 3 (três) anos.')]
        after = [article(1, 'Art. 1º O prazo será de 3 (quatro) anos. (Vigência)')]

        self.assertEqual(compare(before=before, after=after)[0]['kind'], 'text_review')
        after = [article(1, 'Art. 1º O prazo será de 3 (três) anos:')]
        self.assertEqual(compare(before=before, after=after)[0]['kind'], 'text_review')

    def test_historical_wording_is_preserved_when_the_current_text_matches(self):
        before = [article(1, 'Art. 1º Redação atual.', struck='Art. 1º Redação anterior.')]
        after = [article(1, 'Art. 1º Redação atual. (Vigência)')]

        row = compare(before=before, after=after)[0]

        self.assertEqual(row['kind'], 'historical_difference')
        self.assertTrue(row['historicalDiffers'])
        self.assertTrue(row['before']['paragraphs'][0]['runs'][0]['deleted'])

    def test_only_struck_wording_with_historical_notes_is_retained_in_history(self):
        historical = article('12-A', '(Vigência encerrada)', struck='Art. 12-A. Redação anterior.')
        paragraphs = historical['paragraphs']
        paragraphs.append({'runs': [{'text': '(Revogado pela Medida Provisória n. 955, de 2020)', 'deleted': False}]})

        row = compare(before=[historical], after=[])[0]

        self.assertEqual((row['kind'], row['beforeArticleId']), ('retained_history', '12-A'))
        self.assertEqual(row['before']['paragraphs'][0]['runs'][0], {'text': 'Art. 12-A. Redação anterior.', 'deleted': True})

        historical['paragraphs'].append({'runs': [{'text': 'Parágrafo único. Redação adicional.', 'deleted': False}]})
        self.assertEqual(compare(before=[historical], after=[])[0]['kind'], 'unmatched')

    def test_only_veto_placeholders_are_documentary_entries(self):
        veto = article('401-A', 'Art. 401-A. (VETADO na Lei nº 9.799, de 26/5/1999)')
        row = compare(before=[], after=[veto])[0]
        self.assertEqual((row['kind'], row['afterArticleId']), ('documentary_veto', '401-A'))

        veto['paragraphs'].append({'runs': [{'text': '§ 1º Redação adicional.', 'deleted': False}]})
        self.assertEqual(compare(before=[], after=[veto])[0]['kind'], 'unmatched')
