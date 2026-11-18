"""Exercise the preview boundary without fetching sources or approving legal text."""
import functools
import http.server
import subprocess
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from support import chromium_executable

ROOT = Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory(prefix='lexa-preview-') as directory:
    # Reuse the versioned corpus only as a test fixture, never as a Câmara capture.
    script = """import {stagePages} from './scripts/build-pages.mjs';
import {officialImported} from './data/official/legislation.js';
const cf=structuredClone(officialImported.cf);
cf.source={...cf.source,provider:'camara',documents:{
 main:{url:'https://example.test/cf'},adct:{url:'https://example.test/adct'}}};
cf.articles.find(a=>a.id==='6').documentSource={...officialImported.cf.source,reviewNote:'Fixture: edição preservada.'};
await stagePages(process.argv[1],{constitutionPreview:cf});
"""
    subprocess.run(['node', '--input-type=module', '-e', script, directory], cwd=ROOT, check=True)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *_):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=directory))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=chromium_executable())
            for width in (390, 1440):
                page = browser.new_page(viewport={'width': width, 'height': 900})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                base = f'http://127.0.0.1:{server.server_port}/'
                page.route('**/*', lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
                page.goto(base + '#/cf/6')
                expect(page.locator('.camara-preview-notice')).to_be_visible()
                expect(page.locator('[data-edition-source]')).to_have_attribute('href', 'https://example.test/cf')
                expect(page.locator('#art-6 .article-source')).to_contain_text('Planalto')
                page.locator('#art-6 [data-legislative-history]').click()
                expect(page.locator('#legislative-history-panel')).to_be_visible()
                page.keyboard.press('Escape')
                page.goto(base + '#/cf/adct-1')
                expect(page.locator('#art-adct-1')).to_be_visible()
                expect(page.locator('[data-edition-source]')).to_have_attribute('href', 'https://example.test/adct')
                expect(page.locator('#art-adct-1 .article-source')).to_contain_text('Câmara dos Deputados')
                assert not errors, errors
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
print('Prévia sem rede: desktop/celular, fontes por artigo/escopo, histórico e navegação.')
