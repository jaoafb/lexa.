import {escape,codeHref} from './presentation.js';
import {collections,normalize,articleById,articleLabel,searchLibraryReferences} from './data.js';
export function createFavoritesPage({app,getSaved,setSaved,storageWrite,toast,setCleanup}){
const favoritesView={query:'',scroll:0,href:null};
let favoriteUndo=null;
function favoritesPage(params=new URLSearchParams()){
 let saved=getSaved();
 document.title='Meus favoritos — Lexa';
 if(params.has('q'))favoritesView.query=params.get('q');
 app.innerHTML=`<section class="favorites-page"><a class="back" href="#">Biblioteca / sua seleção</a><h1>Meus favoritos</h1><p class="favorites-intro">Artigos e súmulas que você guardou, reunidos por norma.</p><p class="favorites-privacy">As marcações ficam somente neste navegador.</p><div class="favorites-layout"><div class="favorites-main"><div id="favorites-search-field"><label class="field-label" for="favorites-search">Localizar um dispositivo salvo</label><div class="search favorites-search"><span aria-hidden="true">⌕</span><input id="favorites-search" placeholder="Norma, artigo ou palavra…" value="${escape(favoritesView.query)}"></div></div><div class="favorites-totals"><p id="favorites-count" role="status"></p><span>Agrupados por legislação</span></div><div id="favorites-feedback" class="favorites-feedback" hidden><span role="status"></span><button type="button" id="favorites-undo">Desfazer</button></div><div id="favorites-list"></div></div><aside class="favorites-help" aria-label="Sobre os favoritos"><div class="eyebrow">Sua biblioteca pessoal</div><h2>Salve o que importa.</h2><p>Use a estrela junto aos artigos para encontrá-los aqui depois.</p><div class="eyebrow">Privacidade</div><p>Seus favoritos não dependem de conta e não são sincronizados entre dispositivos.</p><p>Ao remover uma marcação, você poderá desfazer a ação.</p></aside></div></section>`;
 const input=document.querySelector('#favorites-search'),feedback=document.querySelector('#favorites-feedback');
 let undoTimer;
 const entries=()=>[...new Set(saved)].map(key=>{
  const separator=key.indexOf('/'),code=collections.find(c=>c.id===key.slice(0,separator));
  const article=code&&articleById(code,key.slice(separator+1));
  return {key,code,article};
 });
 function showUndo(message){
  clearTimeout(undoTimer);
  const available=favoriteUndo&&favoriteUndo.until>Date.now();
  feedback.hidden=!available;
  if(!available)return;
  feedback.querySelector('[role=status]').textContent=message||'Favorito removido. Você pode desfazer esta ação.';
  undoTimer=setTimeout(()=>{if(document.activeElement===document.querySelector('#favorites-undo'))(document.querySelector('[data-remove-favorite]')||document.querySelector('.favorites-empty a')||input).focus({preventScroll:true});feedback.hidden=true;favoriteUndo=null;},favoriteUndo.until-Date.now());
 }
 function draw(){
  const q=normalize(input.value).trim(),all=entries();
  const references=searchLibraryReferences(input.value);
  const matches=all.filter(({key,code,article})=>!q||(references!==null?references.some(result=>result.code.id===code?.id&&result.article.id===article?.id):normalize(code?code.name+' '+code.short+' '+(article?articleLabel(article)+' '+article.text:key):key).includes(q)));
  const groups=collections.map(code=>({code,items:matches.filter(item=>item.code?.id===code.id)}));
  const unknown=matches.filter(item=>!item.code);if(unknown.length)groups.push({code:null,items:unknown});
  document.querySelector('#favorites-search-field').hidden=!all.length;
  document.querySelector('#favorites-count').textContent=`${matches.length} ${matches.length===1?'favorito':'favoritos'}${q?(matches.length===1?' encontrado':' encontrados'):''}`;
  document.querySelector('#favorites-list').innerHTML=matches.length?groups.filter(group=>group.items.length).map(({code,items},groupIndex)=>`<section class="favorite-group"><div class="favorite-group-label">${String(groupIndex+1).padStart(2,'0')} / ${escape(code?.area||'Indisponíveis')}</div><h2>${code?escape(code.name):'Marcações indisponíveis'} <span>${items.length} ${code?.kind==='sumulas'?'súmula(s)':'artigo(s)'}</span></h2><ul>${items.map(({key,article})=>{
   const label=article?articleLabel(article):key;
   const paragraph=article?.paragraphs.find(p=>p.runs.some(run=>!run.deleted&&run.text.trim()));
   const preview=paragraph?.runs.filter(run=>!run.deleted).map(run=>run.text).join('')||article?.text||'';
   return `<li class="favorite-entry"><div>${article?`<a class="favorite-link" href="${codeHref(code,article.id)}"><strong>${escape(label)}</strong><span aria-hidden="true">→</span></a>${['cancelled','pending','suspended'].includes(article.status)?`<small class="favorite-status">${{cancelled:'Cancelada',pending:'Pendente de publicação',suspended:'Suspensa'}[article.status]} — conforme indicado na edição</small>`:''}<p>${escape(preview.slice(0,220))}${preview.length>220?'…':''}</p><a class="favorite-open" href="${codeHref(code,article.id)}" aria-label="Abrir ${escape(label)} de ${escape(code.short)}">Abrir ${escape(code.short)} ↗</a>`:`<strong>${escape(label)}</strong><small class="favorite-status">Indisponível nesta edição</small><p>Esta referência não foi encontrada na edição atual. A marcação foi mantida para sua conferência.</p>`}</div><button data-remove-favorite="${escape(key)}" aria-label="Remover favorito ${escape(label)}${code?' de '+escape(code.short):''}">Remover</button></li>`;
  }).join('')}</ul></section>`).join(''):`<div class="favorites-empty"><span aria-hidden="true">☆</span><h2>${all.length?'Nenhum favorito encontrado':'Nenhum favorito salvo'}</h2><p>${all.length?'Tente o nome da norma, o número ou uma palavra do texto.':'Use a estrela ao lado de um artigo ou súmula para salvá-lo nos favoritos.'}</p><a href="#">Voltar à biblioteca</a></div>`;
  document.querySelectorAll('[data-remove-favorite]').forEach(button=>button.onclick=()=>{
   const key=button.dataset.removeFavorite,position=saved.indexOf(key);
   const buttons=[...document.querySelectorAll('[data-remove-favorite]')],index=buttons.indexOf(button);
   saved=saved.filter(item=>item!==key);setSaved(saved);
   favoriteUndo={key,position,until:Date.now()+8000};
   const persisted=storageWrite('lexa-saved',saved);
   draw();showUndo(persisted?'Favorito removido.':'Remoção temporária: armazenamento indisponível.');
   const remaining=document.querySelectorAll('[data-remove-favorite]');(remaining[Math.min(index,remaining.length-1)]||document.querySelector('#favorites-undo')).focus({preventScroll:true});
  });
 }
 document.querySelector('#favorites-undo').onclick=()=>{
  if(!favoriteUndo||favoriteUndo.until<=Date.now())return;
  const {key,position}=favoriteUndo;
  if(!saved.includes(key))saved.splice(Math.min(position,saved.length),0,key);
  const persisted=storageWrite('lexa-saved',saved);favoriteUndo=null;clearTimeout(undoTimer);feedback.hidden=true;draw();
  ([...document.querySelectorAll('[data-remove-favorite]')].find(button=>button.dataset.removeFavorite===key)||input).focus({preventScroll:true});
  toast(persisted?'Favorito restaurado':'Restauração temporária: armazenamento indisponível');
 };
 input.addEventListener('input',()=>{favoritesView.query=input.value;favoritesView.scroll=0;favoritesView.href=null;const query=new URLSearchParams();if(input.value)query.set('q',input.value);history.replaceState(history.state,'','#/favoritos'+(query.size?'?'+query:''));draw();});
 setCleanup(()=>{clearTimeout(undoTimer);favoritesView.query=input.value;favoritesView.scroll=scrollY;favoritesView.href=document.activeElement?.closest('.favorite-link,.favorite-open')?.getAttribute('href')||null;});
 draw();showUndo();
 requestAnimationFrame(()=>{if(!document.querySelector('.favorites-page'))return;window.scrollTo({top:favoritesView.scroll,behavior:'instant'});if(favoritesView.href)[...document.querySelectorAll('.favorite-link,.favorite-open')].find(link=>link.getAttribute('href')===favoritesView.href)?.focus({preventScroll:true});});
}


return favoritesPage;
}
