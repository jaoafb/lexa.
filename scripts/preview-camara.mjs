import {execFileSync} from 'node:child_process';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {stagePages} from './build-pages.mjs';

const root=fileURLToPath(new URL('../',import.meta.url));
const preview=resolve(root,'test-results/camara-preview');
const candidate=resolve(preview,'constitution.json');
const report=resolve(preview,'camara.json');
const site=resolve(preview,'site');

execFileSync('python3',['scripts/pilot_official_sources.py','--provider','camara','--output',report,'--constitution-preview',candidate],{cwd:root,stdio:'inherit'});
const constitutionPreview=JSON.parse(await readFile(candidate,'utf8'));
await stagePages(site,{constitutionPreview});

if(!process.argv.includes('--build-only')){
 process.env.LEXA_SERVE_DIR=site;
 process.env.LEXA_LOCAL_PREVIEW='1';
 process.env.PORT||='3014';
 await import('./server.mjs');
}
