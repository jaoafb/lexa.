"""Apply explicitly recorded decisions to an isolated constitutional preview."""
from camara_comparison import STATUS, matches_documented_pair
from review_constitution import preview_choice


def apply_constitution_preview_decisions(current, candidate, differences, decisions):
    """Apply evidence to reviewed pairs and preserve text and history on unclear changes."""
    previous = {article['id']: article for article in current['articles']}
    incoming = {article['id']: article for article in candidate['articles']}
    changes = {item['articleId']: item for item in differences}
    applied = {}
    sources = {}
    annotations = {}
    for decision in decisions:
        for key, fingerprints in decision['articles'].items():
            if key not in previous:
                raise ValueError(f'Artigo ausente na base de revisão: {key}.')
            change = changes.get(key)
            if change is None:
                continue
            if not matches_documented_pair(change, fingerprints):
                raise ValueError(f'A divergência do art. {key} mudou desde a conferência documental.')
            if decision['edition'] not in ('planalto', 'camara') or key in applied:
                raise ValueError(f'Decisão documental inválida ou duplicada para o art. {key}.')
            applied[key] = {field: decision[field] for field in ('edition', 'reason', 'sources')}
            if note := decision.get('readerNote'):
                selected = previous[key] if decision['edition'] == 'planalto' else incoming[key]
                inactive = []
                for prefix in decision.get('inactivePrefixes', ()):
                    indices = [i for i, paragraph in enumerate(selected['paragraphs'])
                               if ''.join(run['text'] for run in paragraph['runs'] if not run['deleted']).strip().startswith(prefix)]
                    if len(indices) != 1:
                        raise ValueError(f'Dispositivo afastado não localizado de forma inequívoca para o art. {key}.')
                    inactive.extend(indices)
                annotations[key] = (note, set(inactive))
            if decision['edition'] != 'planalto':
                continue
            source = {
                **current['source'], 'provider': 'planalto',
                'reviewNote': 'Redação do Planalto mantida após conferência documental para esta prévia.',
            }
            if decision.get('revoked'):
                notes = []
                for index, paragraph in enumerate(previous[key]['paragraphs']):
                    text = ''.join(run['text'] for run in paragraph['runs'] if not run['deleted']).strip()
                    if (status := STATUS.fullmatch(text)) and status['status'].lower() == 'revogad':
                        notes.append(index)
                if len(notes) != 1:
                    raise ValueError(f'Nota de revogação não localizada de forma inequívoca para o art. {key}.')
                source['revocationParagraph'] = notes[0]
            sources[key] = source

    for item in differences:
        key = item['articleId']
        choice = preview_choice(item, applied.get(key))
        if choice in ('keep_history', 'keep_pending'):
            sources[key] = {
                **current['source'], 'provider': 'planalto',
                'reviewNote': ('A prévia mantém os trechos riscados da edição do Lexa.' if choice == 'keep_history'
                               else 'A prévia mantém a edição do Lexa enquanto a diferença entre fontes é conferida.'),
            }

    for index, article in enumerate(candidate['articles']):
        key = article['id']
        if key in sources:
            article = {
                **previous[key], 'sectionId': article['sectionId'],
                'documentSource': sources[key],
            }
        if key in annotations:
            note, inactive = annotations[key]
            article = {**article, 'documentaryReview': note, 'paragraphs': [
                paragraph for index, paragraph in enumerate(article['paragraphs']) if index not in inactive
            ]}
        candidate['articles'][index] = article
    return applied
