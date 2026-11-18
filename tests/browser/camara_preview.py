"""Exercise the actual Câmara preview in a disposable browser profile."""

import functools
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright
from support import chromium_executable

root = Path(__file__).resolve().parents[2]
preview = root / 'test-results/camara-preview/site'
manifest = json.loads((preview / 'catalog.json').read_text(encoding='utf-8'))
constitution = next(code for code in manifest['collections'] if code['id'] == 'cf')
documents = constitution['source']['documents']


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=preview))
Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=chromium_executable(),
            args=['--no-sandbox', '--disable-dev-shm-usage', '--no-proxy-server'],
        )
        context = browser.new_context(
            service_workers='block', viewport={'width': 390, 'height': 844},
            permissions=['clipboard-read', 'clipboard-write'],
        )
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        base = f'http://127.0.0.1:{server.server_port}/'
        page.goto(base + '#/cf/6')
        expect(page.locator('.camara-preview-notice')).to_be_visible()
        expect(page.locator('#art-6')).to_be_visible()
        expect(page.locator('[data-edition-source]')).to_have_attribute('href', documents['main']['url'])
        expect(page.locator('#art-6 .article-source')).to_contain_text('Câmara dos Deputados')
        page.locator('#art-6 [data-legislative-history]').click()
        expect(page.locator('#legislative-history-panel')).to_be_visible()
        page.keyboard.press('Escape')

        page.locator('[data-scope="adct"]').click()
        expect(page.locator('#art-adct-1')).to_be_visible()
        expect(page.locator('[data-edition-source]')).to_have_attribute('href', documents['adct']['url'])
        page.goto(base + '#/cf/adct-1')
        expect(page.locator('#art-adct-1 .article-source')).to_contain_text('Câmara dos Deputados')
        page.locator('#art-adct-1 .article-copy summary').click()
        page.locator('#art-adct-1 [data-copy-text]').click()
        page.wait_for_function('async link => (await navigator.clipboard.readText()).includes(link)',
                               arg=documents['adct']['url'])

        page.goto(base + '#/cf/39')
        expect(page.locator('#art-39 .legal-unit:not(.deleted-paragraph)').first).to_contain_text('conselho de política')
        expect(page.locator('#art-39 .article-source')).to_contain_text('Planalto')
        planalto = page.locator('#art-39 .article-source a').first.get_attribute('href')
        assert 'planalto.gov.br' in planalto
        page.locator('#art-39 .article-copy summary').click()
        page.locator('#art-39 [data-copy-text]').click()
        page.wait_for_function('async link => (await navigator.clipboard.readText()).includes(link)', arg=planalto)

        page.goto(base + '#/cf/adct-110')
        expect(page.locator('#art-adct-110 .legal-unit:not(.deleted-paragraph)').first).to_contain_text('Revogado')
        expect(page.locator('#art-adct-110 .article-source a').first).to_have_attribute('href', planalto)
        expect(page.locator('#art-adct-110 .legal-unit')).to_have_count(1)

        page.goto(base + '#/cf/adct-120')
        expect(page.locator('#art-adct-120')).to_contain_text('ADI nº 7.212')
        expect(page.locator('#art-adct-120 .article-source a').first).to_have_attribute('href', documents['adct']['url'])

        page.evaluate("localStorage.setItem('lexa-saved', JSON.stringify(['cf/6', 'cf/adct-1']))")
        page.goto(base + '#/favoritos')
        page.reload()
        expect(page.locator('.favorite-link[href="#/cf/6"]')).to_be_visible()
        expect(page.locator('.favorite-link[href="#/cf/adct-1"]')).to_be_visible()
        page.get_by_role('link', name='ADCT · Art. 1', exact=True).click()
        expect(page.locator('#art-adct-1')).to_be_visible()
        page.reload()
        expect(page.locator('#art-adct-1')).to_be_visible()
        page.wait_for_function("JSON.parse(localStorage.getItem('lexa-last-reading'))?.articleId === 'adct-1'")
        page.goto(base)
        expect(page.locator('.resume-reading a[href="#/cf/adct-1"]')).to_be_visible()
        page.locator('.resume-reading a[href="#/cf/adct-1"]').click()
        expect(page.locator('#art-adct-1')).to_be_visible()

        page.goto(base + '#/atualizacoes?codigo=cf')
        expect(page.get_by_role('heading', name='Histórico de versões', exact=True)).to_be_visible()
        expect(page.locator('#history-code')).to_have_value('cf')
        assert not errors, errors
        browser.close()
finally:
    server.shutdown()
    server.server_close()

print('Prévia constitucional validada no Chromium: links, fonte, cópia, favoritos e histórico.')
