import {createHomePage} from './home-page.js';
import {createFavoritesPage} from './favorites-page.js';
import {updatesPage} from './updates-page.js';
import {loadFailureText} from './interface-copy.js';
import {reader} from './reader.js';
import {initialCatalog} from './collections.js';
import {copyContent} from './clipboard.js';
import {escape} from './presentation.js';
import {recordedUpdates} from './history-store.js';
import {loadCollection,loadHistory,loadSearchIndexes,activateCollection} from './loading.js';
import { setupPwa } from './pwa.js';
import {collections,articleById} from './data.js';

const app = document.querySelector('#app');
let saved = [];
try { const value=JSON.parse(localStorage.getItem('lexa-saved') || '[]'); if(Array.isArray(value))saved=value.filter(x=>typeof x==='string'); } catch {}
// Preferences and reading position belong only to this browser.
const storageRead=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback;}catch{return fallback;}};
const storageWrite=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{return false;}};
const storedPreferences=storageRead('lexa-reading',{});
const readingPreferences={
 size:Number.isInteger(storedPreferences?.size)&&storedPreferences.size>=16&&storedPreferences.size<=26?storedPreferences.size:19,
 spacing:['standard','comfortable','wide'].includes(storedPreferences?.spacing)?storedPreferences.spacing:'standard'
};
function lastReading(){
 const value=storageRead('lexa-last-reading',null);
 const code=collections.find(c=>c.id===value?.codeId);
 let article=code&&typeof value.articleId==='string'?articleById(code,value.articleId):null;
 if(code&&!code.loaded&&/^(?:adct-)?\d+(?:-[A-Z]+)*$/.test(value.articleId))article={id:value.articleId,number:value.articleId.replace('adct-',''),scope:value.articleId.startsWith('adct-')?'adct':'main',kind:code.kind==='sumulas'?'vinculante':undefined};
 return article?{code,article}:null;
}
let cleanupReader=()=>{};
let toastTimer;
function toast(message,duration=2500) { const el=document.querySelector('#toast'); clearTimeout(toastTimer); el.textContent=message; el.classList.add('visible'); toastTimer=setTimeout(()=>el.classList.remove('visible'),duration); }
document.addEventListener('click',event=>{
 if(navigator.onLine!==false||!event.target.closest('.feedback-link,.article-feedback,.privacy-contact'))return;
 event.preventDefault();
 toast('O formulário precisa de internet. Conecte-se e tente novamente. Sua leitura continua disponível.',8000);
});
document.querySelector('.skip-link').addEventListener('click',event=>{event.preventDefault();const target=document.querySelector('#settings-page').hidden?app:document.querySelector('#settings-title');target.focus();target.scrollIntoView({block:'start'});});
const historyArticleIds=new Set([...recordedUpdates.flatMap(event=>event.changes.map(change=>event.codeId+'/'+change.articleId)),...collections.flatMap(code=>(code.changedArticleIds||[]).map(id=>code.id+'/'+id))]);

function readerServices(){
 return {app,readingPreferences,storageWrite,historyArticleIds,toast,
  copyContent:(text,button,message)=>copyContent(text,button,message,toast),
  state:{get saved(){return saved;},set saved(value){saved=value;},
   get cleanupReader(){return cleanupReader;},set cleanupReader(value){cleanupReader=value;}}
 };
}

const setCleanup=cleanup=>{cleanupReader=cleanup;};
const home=createHomePage({app,lastReading,setCleanup});
const favoritesPage=createFavoritesPage({app,getSaved:()=>saved,setSaved:value=>{saved=value;},storageWrite,toast,setCleanup});
let routeGeneration=0;
async function route(){
 const generation=++routeGeneration;
 const copyDialog=document.querySelector('#copy-dialog');if(copyDialog.open)copyDialog.close();
 cleanupReader();cleanupReader=()=>{};app.classList.remove('amendment-reader','amendment-full');
 const [path,query='']=location.hash.slice(1).split('?');
 const [,id,article]=path.split('/');
 const leavingSettings=!document.querySelector('#settings-page').hidden;
 const settings=id==='privacidade'||id==='sobre-e-ajustes'||id==='sobre-lexa'||path==='sobre-lexa';
 document.querySelector('#settings-page').hidden=!settings;app.hidden=settings;
 document.body.classList.toggle('settings-view',settings);
 const activeNav=settings?'#/sobre-e-ajustes':id==='favoritos'?'#/favoritos':id==='atualizacoes'?'#/atualizacoes':'#';
 document.querySelectorAll('header nav>a').forEach(link=>{
  if(link.getAttribute('href')===activeNav)link.setAttribute('aria-current','page');
  else link.removeAttribute('aria-current');
 });
 const code=collections.find(c=>c.id===id);
 activateCollection(code?.id||null);
 const needsData=code&&!code.loaded||id==='favoritos'||id==='atualizacoes';
 if(needsData)app.innerHTML=`<section class="loading-panel"><p role="status">${code?'Carregando '+escape(code.name)+'…':id==='favoritos'?'Carregando favoritos…':'Carregando histórico…'}</p></section>`;
 try{
  if(id==='emendas'){
   if(!initialCatalog.amendments)throw new Error('Biblioteca de Emendas não habilitada nesta edição.');
   app.innerHTML='<p class="loading-panel" role="status">Carregando Emendas Constitucionais…</p>';
   const amendments=await import('./amendments.js');
   if(!article){await amendments.amendmentLibrary(app,new URLSearchParams(query),()=>generation===routeGeneration);return;}
   const {document,entry}=await amendments.loadAmendment(article),links=await amendments.loadAmendmentLinks();if(generation!==routeGeneration)return;
   const collection=amendments.amendmentCollection(document,entry),services=readerServices();services.renderParagraphs=amendments.amendmentParagraphs;services.storageWrite=(key,value)=>key==='lexa-last-reading'?true:storageWrite(key,value);
   reader(collection,path.split('/')[3],new URLSearchParams(query),services);amendments.enhanceAmendmentReader(app,document,links,new URLSearchParams(query));return;
  }
  if(settings){document.title=id==='privacidade'?'Privacidade — Lexa':'Sobre e ajustes — Lexa';app.innerHTML='';const heading=document.querySelector(id==='privacidade'?'#privacy-title':'#settings-title');heading.focus({preventScroll:true});if(id==='privacidade')heading.scrollIntoView({block:'start'});else window.scrollTo(0,0);return;}
  if(id==='favoritos'){
   await loadSearchIndexes(collections.filter(code=>saved.some(key=>key.startsWith(code.id+'/'))));
   if(generation!==routeGeneration)return;
   favoritesPage(new URLSearchParams(query));return;
  }
  if(id==='atualizacoes'){
   const history=await loadHistory();if(generation!==routeGeneration)return;
   recordedUpdates.splice(0,recordedUpdates.length,...history);
   updatesPage(app,new URLSearchParams(query));window.scrollTo(0,0);return;
  }
  if(code){await loadCollection(code);const services=readerServices();let amendments,links;
   if(code.id==='cf'&&initialCatalog.amendments){amendments=await import('./amendments.js');links=await amendments.loadAmendmentLinks();services.amendmentNotes={records:links.records,decorate:amendments.decorateAmendmentNotes};}
   if(generation!==routeGeneration)return;reader(code,article,new URLSearchParams(query),services);
   const ec=new URLSearchParams(query).get('emenda');if(ec&&links?.records.some(x=>String(x.ec)===ec&&x.articleId===article)){const back=document.createElement('a');back.className='back';back.href='#/emendas/'+ec;back.textContent='← Voltar à EC '+ec;app.querySelector('.reader-top').prepend(back);}
  }
  else{home();if(leavingSettings)app.focus({preventScroll:true});}
  if(!article)window.scrollTo(0,0);
 }catch(error){
  if(generation!==routeGeneration)return;
  app.innerHTML=`<section class="loading-panel"><h1>Não foi possível abrir esta edição</h1><p role="status">${escape(loadFailureText(error))}</p><button id="retry-load">Tentar novamente</button><a href="#">Voltar à biblioteca</a></section>`;
  document.querySelector('#retry-load').onclick=route;
 }
}
let dark=false;try{dark=localStorage.getItem('lexa-theme')==='dark';}catch{}
document.documentElement.classList.toggle('dark',dark);
function setTheme(value){
 dark=value;document.documentElement.classList.toggle('dark',dark);
 document.querySelectorAll('[data-theme]').forEach(button=>button.setAttribute('aria-pressed',String((button.dataset.theme==='dark')===dark)));
 try{localStorage.setItem('lexa-theme',dark?'dark':'light');}catch{}
}
document.querySelector('#theme').onclick=()=>setTheme(!dark);
document.querySelectorAll('[data-theme]').forEach(button=>button.onclick=()=>setTheme(button.dataset.theme==='dark'));
setTheme(dark);
document.addEventListener('keydown',e=>{
 if(e.key==='Escape'&&!document.querySelector('#copy-dialog').open){const menu=document.querySelector('.article-copy[open]');if(menu){menu.open=false;menu.querySelector('summary').focus({preventScroll:true});e.stopImmediatePropagation();return;}}
 if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();document.querySelector('input')?.focus();}});
document.addEventListener('pointerdown',event=>{if(!document.querySelector('#copy-dialog').open&&!event.target.closest('.article-copy'))document.querySelectorAll('.article-copy[open]').forEach(menu=>menu.open=false);});
document.querySelector('#copy-select').onclick=()=>{const field=document.querySelector('#copy-content');field.focus();field.select();};
window.addEventListener('hashchange',route);route();

setupPwa();
