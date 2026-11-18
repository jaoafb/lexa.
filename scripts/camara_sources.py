"""Source-specific discovery and documentary evidence for the Câmara monitor."""

from datetime import date, datetime
import re
from urllib.parse import unquote, urljoin, urlsplit
from zoneinfo import ZoneInfo

from amendments_source import Parser, clean, date_iso, decode
from check_official_sources import parse_html
from official_http import check_url

CAMARA_HOST = 'www2.camara.leg.br'
CONSTITUTION_INDEX = f'https://{CAMARA_HOST}/atividade-legislativa/legislacao/constituicao1988'
CAMARA_PATHS = {
    'civil': ('/legin/fed/lei/2002/lei-10406-10-janeiro-2002-432893-normaatualizada-pl.html',),
    'penal': ('/legin/fed/declei/1940-1949/decreto-lei-2848-7-dezembro-1940-412868-normaatualizada-pe.html',),
    'cpc': ('/legin/fed/lei/2015/lei-13105-16-marco-2015-780273-normaatualizada-pl.html',),
    'cdc': ('/legin/fed/lei/1990/lei-8078-11-setembro-1990-365086-normaatualizada-pl.html',),
    'ctn': ('/legin/fed/lei/1960-1969/lei-5172-25-outubro-1966-358971-normaatualizada-pl.html',),
    'cpp': ('/legin/fed/declei/1940-1949/decreto-lei-3689-3-outubro-1941-322206-normaatualizada-pe.html',),
    'eca': ('/legin/fed/lei/1990/lei-8069-13-julho-1990-372211-normaatualizada-pl.html',),
    'lep': ('/legin/fed/lei/1980-1987/lei-7210-11-julho-1984-356938-normaatualizada-pl.html',),
    'maria-penha': ('/legin/fed/lei/2006/lei-11340-7-agosto-2006-545133-normaatualizada-pl.html',),
    'improbidade': ('/legin/fed/lei/1992/lei-8429-2-junho-1992-357452-normaatualizada-pl.html',),
    'licitacoes': ('/legin/fed/lei/2021/lei-14133-1-abril-2021-791222-normaatualizada-pl.html',),
    'clt': ('/legin/fed/declei/1940-1949/decreto-lei-5452-1-maio-1943-415500-normaatualizada-pe.html',),
}
CAMARA_IDS = ('cf', *CAMARA_PATHS)
CONSTITUTION_FILES = urlsplit(CONSTITUTION_INDEX).path + '/arquivos/'
CONSTITUTION_NAMES = {
    'cf': re.compile(r'ConstituicaoTextoAtualizado[_ -]EC[_ -]+[0-9]+\.html?', re.I),
    'adct': re.compile(r'constituicao-adct-de-1988[_ -]ec[_ -]+[0-9]+\.html?', re.I),
}
LAW_15371_URL = (
    f'https://{CAMARA_HOST}/legin/fed/lei/2026/'
    'lei-15371-31-marco-2026-798908-publicacaooriginal-178711-pl.html'
)
ARTICLE_392_D = re.compile(
    r"""['‘“]((?:Art\. 392-D\.)\s+.+?)['’”](?=\s+(?:\(NR\)\s+)?['‘“]Art\.\s+[0-9])"""
)
EFFECTIVE_CLAUSE = re.compile(
    r'Art\. 14\. Esta Lei entra em vigor no dia [0-9]{1,2}º? de [a-zç]+ de [0-9]{4}\.', re.I
)
DOU_NOTICE = re.compile(
    r'Este texto não substitui o original publicado no Diário Oficial da União - Seção 1 de [0-9]{1,2}/[0-9]{1,2}/[0-9]{4}\.?'
)
CONSOLIDATION_REFERENCE = re.compile(
    r'Art\. 392-D\.\s+\(Vide Lei nº 15\.371, de 31/3/2026\)', re.I
)


def constitution_links(raw, encoding):
    html, details = decode(raw, 'charset=' + encoding if encoding else '')
    if details.get('alerta'):
        raise ValueError('Codificação do índice de Constituição e ADCT não reconhecida.')
    links = {key: set() for key in CONSTITUTION_NAMES}
    for anchor in Parser(html).root.all('a'):
        if clean(anchor.text()).casefold() != 'formato html':
            continue
        url = urljoin(CONSTITUTION_INDEX + '/', anchor.attrs.get('href', ''))
        path = unquote(urlsplit(url).path)
        if not path.startswith(CONSTITUTION_FILES):
            continue
        filename = path.removeprefix(CONSTITUTION_FILES)
        for key, pattern in CONSTITUTION_NAMES.items():
            if pattern.fullmatch(filename):
                check_url(url, {CAMARA_HOST})
                links[key].add(url)
    if any(len(found) != 1 for found in links.values()):
        raise ValueError('O índice da Câmara não apresenta um único HTML identificado para Constituição e ADCT.')
    return [next(iter(links[key])) for key in ('cf', 'adct')]


def publication_392_d(raw, encoding):
    blocks = parse_html(raw, encoding)['blocks']
    text = [''.join(run['text'] for run in block) for block in blocks if not any(run['deleted'] for run in block)]
    if text.count('LEI Nº 15.371, DE 31 DE MARÇO DE 2026') != 1:
        raise ValueError('Identidade da publicação original da Lei 15.371/2026 não confirmada.')

    provisions = [match[1] for block in text for match in ARTICLE_392_D.finditer(block)]
    clauses = [block for block in text if EFFECTIVE_CLAUSE.fullmatch(block)]
    notices = [block for block in text if DOU_NOTICE.fullmatch(block)]
    if len(provisions) != 1 or len(clauses) != 1 or len(notices) != 1:
        raise ValueError('Redação do art. 392-D, cláusula de vigência ou data de publicação não identificada.')
    published = date.fromisoformat(date_iso(notices[0]) or '')
    effective = date.fromisoformat(date_iso(clauses[0]) or '')
    if effective < published:
        raise ValueError('A cláusula de vigência antecede a data declarada de publicação.')
    return {
        'publishedOn': published.isoformat(),
        'declaredEffectiveOn': effective.isoformat(),
        'effectiveClause': clauses[0],
        'text': provisions[0],
    }


def references_392_d(difference):
    if (difference['kind'] != 'unmatched' or difference['articleId'] != '392-D'
            or difference['scope'] != 'main' or difference['before'] is not None):
        return False
    paragraphs = difference['after']['paragraphs']
    return len(paragraphs) == 1 and not any(run['deleted'] for run in paragraphs[0]['runs']) and bool(
        CONSOLIDATION_REFERENCE.fullmatch(''.join(run['text'] for run in paragraphs[0]['runs']))
    )


def publication_kind(evidence, checked_at):
    day = datetime.fromisoformat(checked_at).astimezone(ZoneInfo('America/Sao_Paulo')).date()
    return (
        'published_future_effect' if day < date.fromisoformat(evidence['declaredEffectiveOn'])
        else 'published_text_pending_review'
    )
