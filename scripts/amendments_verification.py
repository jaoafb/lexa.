"""Independent DOM validation of amendment sources; no collection or incorporation."""
import os
import re
import shutil
from pathlib import Path
from amendments_source import clean

DOM='''el=>{const blocks=[];let pieces=[];const boundary=new Set(['P','DIV','BLOCKQUOTE','DIR','TD','TH','TR','LI','H1','H2','H3','H4','BR','HR']);const clean=x=>x.replace(/\\s+/gu,' ').trim();const flush=()=>{if(clean(pieces.join('')))blocks.push(pieces.join(''));pieces=[];};function walk(n){if(n.nodeType===3){pieces.push(n.nodeValue);return;}if(n.nodeType!==1||['SCRIPT','STYLE','HEAD'].includes(n.tagName))return;if(boundary.has(n.tagName))flush();for(const c of n.childNodes)walk(c);if(boundary.has(n.tagName))flush();}walk(el);flush();return blocks;}'''
def browser_executable(playwright):
 """Resolve the Chromium installed by Playwright, preserving an explicit CI override."""
 explicit = os.environ.get('LEXA_CHROMIUM')
 if explicit:
  candidate = Path(explicit).expanduser()
  if not candidate.is_file():
   raise RuntimeError('LEXA_CHROMIUM aponta para um arquivo inexistente: '+str(candidate))
  return str(candidate)
 installed = Path(playwright.chromium.executable_path).expanduser()
 if installed.is_file():
  return str(installed)
 for name in ('chromium','chromium-browser','google-chrome','google-chrome-stable'):
  found = shutil.which(name)
  if found:
   return found
 raise RuntimeError('Chromium não encontrado. Execute python -m playwright install chromium ou defina LEXA_CHROMIUM.')

def verify_browser(html,parsed):
 from playwright.sync_api import sync_playwright
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=browser_executable(p),args=['--no-sandbox']);page=browser.new_page();page.route('**/*',lambda r:r.abort());page.set_content(re.sub(r'<script\b[^>]*>[\s\S]*?</script\s*>','',html,flags=re.I),wait_until='domcontentloaded');blocks=page.locator('.textoNorma').evaluate(DOM);head=page.locator('h1').all_text_contents();browser.close()
 return {'fullTextAndOrder':[clean(x) for x in blocks]==[clean(x['texto']) for x in parsed['linhas']],'identityHeading':parsed['identidade']['cabecalho'] in [clean(x) for x in head],'blocks':len(blocks),'method':'DOM Chromium independente, rede/scripts da fonte bloqueados; apenas espaços normalizados.'}
