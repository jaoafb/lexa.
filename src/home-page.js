import {escape,number,codeHref,highlight} from './presentation.js';
import {collections,normalize,articleById,articleLabel,parseReference,searchLibraryReferences} from './data.js';
import {initialCatalog} from './collections.js';
import {loadSearchIndexes,loadSearchIndex} from './loading.js';
import {loadFailureText} from './interface-copy.js';
import {searchLibraryText,libraryExcerpt} from './library-search.js';
export function createHomePage({app,lastReading,setCleanup}){
const total=collections.filter(c=>c.kind!=='sumulas').reduce((n,c)=>n+c.articleCount,0);
let category='Todas as áreas',libraryQuery='';
function recentUpdatesSection(){
 // This build projection contains only incorporated textual changes, not baselines or processing events.
 const events=(initialCatalog?.recentUpdates||[]).filter(event=>event.totalChanges>0&&collections.some(code=>code.id===event.codeId));
 return events.length?'<a class="legislative-indicator" href="#/atualizacoes" aria-label="Consultar alterações legislativas registradas">Alterações<span class="indicator-full"> registradas</span> ↗</a>':'';
}

function home() {
 const resume=lastReading();
 let homeActive=true,searchSequence=0;
 document.title='Lexa — Consulta à legislação brasileira';
 app.innerHTML=`<section class="hero editorial-hero"><div class="hero-copy"><div class="eyebrow">Consulte a legislação</div><h1>O que você deseja consultar?</h1><p>Pesquise normas, artigos e súmulas na biblioteca do Lexa.</p><label class="field-label" for="library-search">Buscar norma, artigo ou palavra</label><div class="search hero-search"><span aria-hidden="true">⌕</span><input id="library-search" placeholder="Ex.: art. 5 CF, SV 13, dignidade"><kbd aria-hidden="true">/</kbd></div><div class="search-examples" role="group" aria-label="Exemplos de busca"><span>Exemplos</span>${['Art. 5 CF','SV 13','dignidade'].map(query=>`<button type="button" data-example="${escape(query)}">${escape(query)}</button>`).join('')}</div><div class="quick-reference" id="quick-reference" aria-label="Resultados por referência" hidden></div></div><aside class="consultation-guide" aria-label="Como consultar"><div class="eyebrow">Como consultar</div><p><b>01</b><span>Referência exata<small>Art. 5 CF ou SV 13</small></span></p><p><b>02</b><span>Expressão no texto<small>Ex.: dignidade</small></span></p></aside><div class="hero-note"><span><strong>${collections.filter(c=>c.kind!=='sumulas').length}</strong> legislações <i aria-hidden="true"></i> <strong>${number(total)}</strong> entradas <i aria-hidden="true"></i> <strong>${collections.find(c=>c.id==='sv').articleCount}</strong> súmulas</span>${recentUpdatesSection()}</div></section>${resume?`<section class="resume-reading" aria-label="Continuar leitura"><a class="resume-link" href="${codeHref(resume.code,resume.article.id)}"><span class="eyebrow">Continuar leitura</span><p><strong>${escape(resume.code.name)}</strong> · ${articleLabel(resume.article)}</p></a><button id="forget-reading" aria-label="Remover esta consulta da página inicial">×</button></section>`:''}<section class="library"><div class="section-heading"><div class="eyebrow">Biblioteca / acervo</div><h2>Explore a biblioteca</h2><p>Navegue pelas legislações e refine a consulta por área do Direito.</p></div><div class="filters" aria-label="Filtrar por área">${['Todas as áreas','Constitucional','Civil','Penal','Processual','Consumidor','Tributário','Trabalho','Infância e Juventude','Mulher','Administrativo','Súmulas'].map(x=>`<button class="${x===category?'active':''}" data-category="${x}" aria-pressed="${x===category}">${x}</button>`).join('')}</div><p id="library-results" class="library-results" role="status"></p><div class="catalog-heading"><span>Legislações e súmulas disponíveis</span><span>${collections.length} no acervo</span></div><div class="cards" id="cards"></div><div id="text-results" class="text-results"></div></section>`;
 document.querySelector('#library-search').value=libraryQuery;
 document.querySelector('#forget-reading')?.addEventListener('click',()=>{try{localStorage.removeItem('lexa-last-reading');}catch{}document.querySelector('.resume-reading').remove();});
 const findReferences=query=>{
  const results=searchLibraryReferences(query);
  return results===null?null:results.filter(({code})=>parseReference(query).codeId||category==='Todas as áreas'||code.area.includes(category));
 };
 let textGroups=[],visibleCounts=new Map(),currentQuery='';
 const draw=async()=>{
  const sequence=++searchSequence;
  currentQuery=document.querySelector('#library-search').value.trim();libraryQuery=document.querySelector('#library-search').value;
  const q=normalize(currentQuery);
  document.querySelector('#text-results').innerHTML='';
  visibleCounts=new Map();
  const ref=parseReference(currentQuery);
  const selected=collections.filter(code=>(!ref?.codeId||code.id===ref.codeId)&&(ref?.codeId||category==='Todas as áreas'||code.area.includes(category)));
  if((ref||q.length>=2)&&selected.some(code=>!code.searchIndex)){
   document.querySelector('#quick-reference').hidden=true;
   const status=document.querySelector('#library-results');
   status.textContent=ref?'Carregando referências…':'Carregando índice…';
   try{await loadSearchIndexes(selected);}catch(error){
    if(homeActive&&sequence===searchSequence){status.textContent=loadFailureText(error);document.querySelector('#text-results').innerHTML='<button class="text-more" id="retry-search">Tentar novamente</button>';document.querySelector('#retry-search').onclick=draw;}
    return;
   }
   if(!homeActive||sequence!==searchSequence)return;
  }
  const references=findReferences(q);
  const quick=document.querySelector('#quick-reference');
  quick.hidden=references===null;
  quick.innerHTML='';
  if(references!==null){
   quick.innerHTML=references.length?references.map(({code,article})=>`<a href="${codeHref(code,article.id)}"><span><strong>${articleLabel(article)}</strong><small>${escape(code.name)}</small></span><b aria-hidden="true">→</b></a>`).join(''):'<p>Referência não encontrada. Confira o número e a sigla.</p>';
   if(parseReference(q).codeId){category='Todas as áreas';document.querySelectorAll('[data-category]').forEach(button=>{button.classList.toggle('active',button.dataset.category===category);button.setAttribute('aria-pressed',String(button.dataset.category===category));});}
   document.querySelector('#library-results').textContent=`${references.length} ${references.length===1?'referência encontrada':'referências encontradas'}`;
   document.querySelector('#cards').innerHTML='';
   return;
  }
  document.querySelector('#library-results').textContent='';
  const filtered=collections.filter(c=>(category==='Todas as áreas'||c.area.includes(category))&&normalize(c.name+' '+c.short+' '+c.area+' '+c.description).includes(q));
  document.querySelector('#cards').innerHTML=filtered.map(c=>c.id==='cf'&&initialCatalog.amendments?`<div class="code-card constitution-card"><a class="constitution-main" href="${codeHref(c)}"><div class="card-top"><span class="code-short">${escape(c.short)} / Legislação</span><span class="catalog-number">${String(collections.indexOf(c)+1).padStart(2,'0')}</span></div><h3>${escape(c.name)}</h3><p>${escape(c.description)}</p></a><a class="constitution-amendments" href="#/emendas">Emendas Constitucionais →</a></div>`:`<a class="code-card" href="${codeHref(c)}"><div class="card-top"><span class="code-short">${escape(c.short)} / ${c.kind==='sumulas'?'súmulas':'legislação'}</span><span class="catalog-number">${String(collections.indexOf(c)+1).padStart(2,'0')}</span></div><h3>${escape(c.name)}</h3><p>${escape(c.description)}</p></a>`).join('');
  textGroups=q.length>=2?searchLibraryText(currentQuery,category):[];
  const count=textGroups.reduce((sum,group)=>sum+group.matches.length,0);
  if(q){
   document.querySelector('#library-results').textContent=q.length<2?'Digite pelo menos 2 caracteres para buscar nos textos.':`${number(count)} ${count===1?'entrada encontrada':'entradas encontradas'} nos textos · ${textGroups.length} ${textGroups.length===1?'coleção':'coleções'}${filtered.length?' · '+filtered.length+' coleção(ões) pelo nome ou descrição':''}`;
   drawTextResults();
  }
 };
 function drawTextResults(){
  const results=document.querySelector('#text-results');
  if(normalize(currentQuery).length<2){results.innerHTML='';return;}
  results.innerHTML=textGroups.length?`<div class="text-search-heading"><h2>Ocorrências nos textos</h2><p>Resultados por coleção, na ordem dos dispositivos. Redações riscadas e notas de aplicação também podem aparecer, com identificação.</p></div>`+textGroups.map(({code,matches})=>{
   const limit=visibleCounts.get(code.id)||4;
   return `<section class="text-result-group" aria-labelledby="search-group-${escape(code.id)}"><div class="text-group-heading"><h3 id="search-group-${escape(code.id)}">${escape(code.name)}</h3><span>${number(matches.length)} ${matches.length===1?'entrada':'entradas'}</span></div><ul>${matches.slice(0,limit).map(({article,match})=>{
    const excerpt=libraryExcerpt(match),riscado=excerpt.runs.some(run=>run.deleted);
    const status={cancelled:'Cancelada',pending:'Pendente de publicação',suspended:'Suspensa'}[article.status];
    return `<li><a class="text-result" href="${codeHref(code,article.id)}?q=${encodeURIComponent(currentQuery)}"><div class="text-result-title"><strong>${articleLabel(article)}</strong><span aria-hidden="true">→</span></div>${status?`<span class="search-badge">${status} — conforme a edição</span>`:''}${match.kind==='notes'?'<span class="search-badge">Ocorrência em precedentes, jurisprudência ou observações</span>':match.kind==='title'?'<span class="search-badge">Ocorrência no título do artigo</span>':''}${match.deleted?'<span class="search-badge">Ocorrência em trecho riscado na fonte</span>':riscado?'<span class="search-badge">Contém trecho riscado na fonte</span>':''}<p>${excerpt.leading?'…':''}${excerpt.runs.map(run=>run.deleted?`<del>${highlight(run.text,currentQuery)}</del>`:highlight(run.text,currentQuery)).join('')}${excerpt.trailing?'…':''}</p><small>${escape(article.section||'')}</small></a></li>`;
   }).join('')}</ul>${matches.length>limit?`<button class="text-more" data-more-code="${escape(code.id)}">Mostrar mais de ${escape(code.short)} · ${number(matches.length-limit)} restantes</button>`:''}</section>`;
  }).join(''):'<div class="empty"><h3>Nenhuma ocorrência nos textos</h3><p>Tente uma expressão mais curta ou selecione outra área. A busca procura o texto digitado, sem distinção de acentos.</p></div>';
  results.querySelectorAll('[data-more-code]').forEach(button=>button.onclick=()=>{
   const id=button.dataset.moreCode,previous=visibleCounts.get(id)||4;
   visibleCounts.set(id,previous+6);drawTextResults();
   document.querySelector(`#search-group-${id}`)?.closest('section').querySelectorAll('.text-result')[previous]?.focus({preventScroll:true});
  });
 }
 let searchTimer;
 setCleanup(()=>{clearTimeout(searchTimer);homeActive=false;searchSequence++;});
 document.querySelector('#library-search').addEventListener('input',()=>{clearTimeout(searchTimer);libraryQuery=document.querySelector('#library-search').value;if(searchLibraryReferences(document.querySelector('#library-search').value)!==null)draw();else searchTimer=setTimeout(draw,150);});
 document.querySelector('#library-search').addEventListener('keydown',async event=>{if(event.key==='Enter'){clearTimeout(searchTimer);const submitted=event.target.value;await draw();if(!homeActive||event.target.value!==submitted)return;const results=findReferences(submitted);if(results?.length===1){location.hash=codeHref(results[0].code,results[0].article.id);}else if(results===null){const heading=document.querySelector('.text-search-heading h2');if(heading){heading.tabIndex=-1;heading.scrollIntoView({block:'start'});heading.focus({preventScroll:true});}}}});
 document.querySelectorAll('[data-example]').forEach(button=>button.onclick=()=>{clearTimeout(searchTimer);const input=document.querySelector('#library-search');input.value=button.dataset.example;libraryQuery=input.value;draw();input.focus({preventScroll:true});});
 document.querySelectorAll('[data-category]').forEach(b=>b.onclick=()=>{category=b.dataset.category;document.querySelectorAll('[data-category]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});draw();});
 draw();
 if(resume&&!resume.code.loaded)loadSearchIndex(resume.code).then(()=>{
  if(homeActive&&!articleById(resume.code,resume.article.id))document.querySelector('.resume-reading')?.remove();
 }).catch(()=>{});
}


return home;
}
