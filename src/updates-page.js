import {escape,number,codeHref,collectionDate,diffColumn} from './presentation.js';
import {collections,articleLabel} from './data.js';
import {recordedUpdates} from './history-store.js';
import {filterUpdates,compareVersions,historySummary} from './history.js';
export function updatesPage(app,params) {
 document.title='Atualizações da legislação — Lexa';
 let renderedCount=0;
 let codeId=params.get('codigo')||'',articleId=params.get('artigo')||'',limit=12;
 if(!collections.some(c=>c.id===codeId))codeId='';
 const order=recordedUpdates.map((event,index)=>({event,index})).sort((a,b)=>Date.parse(b.event.capturedAt)-Date.parse(a.event.capturedAt)||b.index-a.index).map(item=>item.event);
 const summary=historySummary(recordedUpdates);
 const kindLabels={baseline:'Referência inicial',text:'Mudanças no texto',source:'Atualização da fonte',processing:'Reprocessamento'};
 const changeLabels={added:'Adicionado ao texto',changed:'Texto alterado',removed:'Ausente nesta versão'};
 app.innerHTML=`<section class="updates-hero"><a class="back" href="#">← Voltar à biblioteca</a><div class="eyebrow">Biblioteca / atualizações / versões coletadas</div><h1>Histórico de versões</h1><p>Compare as versões dos textos incorporados ao Lexa. As datas de coleta não certificam vigência.</p><div class="history-stats">${summary.since?`<span>Acompanhando desde <strong>${collectionDate({capturedAt:summary.since})}</strong></span>`:''}<span><strong>${number(summary.norms)}</strong> ${summary.norms===1?'norma em acompanhamento':'normas em acompanhamento'}</span>${summary.versions?`<span><strong>${number(summary.versions)}</strong> ${summary.versions===1?'nova versão registrada':'novas versões registradas'}</span>`:''}${summary.changes?`<span><strong>${number(summary.changes)}</strong> ${summary.changes===1?'alteração de entrada registrada':'alterações de entradas registradas'}</span>`:''}</div></section><section class="updates-content"><div class="updates-toolbar"><label>Legislação<select id="history-code"><option value="">Todas as legislações</option>${collections.map(c=>`<option value="${escape(c.id)}">${escape(c.name)}</option>`).join('')}</select></label><label>Artigo ou súmula<input id="history-article" placeholder="Ex.: 186, ADCT-1 ou SV 13" value="${escape(articleId)}"></label><button id="history-clear">Limpar filtros</button></div><p class="history-help">Este Histórico de versões compara edições incorporadas ao Lexa; é diferente de Redações anteriores. As datas indicam a coleta da fonte. Os destaques mostram diferenças no texto, sem classificar juridicamente as alterações ou certificar sua vigência.</p><div id="history-results" role="status"></div><div id="history-events"></div><button id="history-more" class="history-more" hidden>Carregar mais versões</button></section>`;
 document.querySelector('#history-code').value=codeId;
 function draw(append=false){
  const events=filterUpdates(order,codeId,articleId);
  document.querySelector('#history-results').textContent=`${events.length} ${events.length===1?'registro encontrado':'registros encontrados'}`;
  const container=document.querySelector('#history-events');
  const markup=events.slice(append?renderedCount:0,limit).map(event=>{
   const code=collections.find(c=>c.id===event.codeId);
   const counts=event.changes.reduce((v,c)=>(v[c.type]++,v),{added:0,changed:0,removed:0});
   return `<details class="update-event" data-history-event="${escape(event.id)}" ${articleId?'open':''}><summary><span class="timeline-dot"></span><div class="event-heading"><div class="event-meta"><time datetime="${escape(event.capturedAt)}">Coleta · ${collectionDate(event)}</time><span class="event-kind kind-${event.kind}">${kindLabels[event.kind]||'Registro de versão'}</span></div><h2>${escape(code.name)}</h2><p>${event.kind==='baseline'?'Ponto de partida para acompanhar as próximas versões.':`${event.changes.length} ${event.changes.length===1?'entrada com diferença':'entradas com diferenças'}${counts.added?' · '+counts.added+' adicionado(s)':''}${counts.removed?' · '+counts.removed+' ausente(s)':''}`}</p></div><span class="event-expand" aria-hidden="true">+</span></summary><div class="event-body">${event.kind==='baseline'?'<div class="baseline-note">Esta é a referência inicial do histórico. A migração entre formatos não é apresentada como mudança na legislação. As próximas versões podem ser comparadas a partir deste registro.</div>':event.changes.length?'':'<p>Foi registrada uma nova versão da fonte, sem diferenças identificadas nos textos das entradas pelo comparador.</p>'}${event.kind==='processing'?'<p class="history-help">Este registro decorre de um ajuste no processamento do mesmo documento, sem indicar uma nova publicação legal.</p>':''}${event.changes.map((change,index)=>`<details class="article-change" data-revision-event="${event.id}" data-revision-index="${index}"><summary><strong>${articleLabel(change)}</strong><span class="change-tag tag-${change.type}">${changeLabels[change.type]}</span><span aria-hidden="true">⌄</span></summary><div class="comparison-container"></div><div class="comparison-footer"><a href="${codeHref(code,change.articleId)}">Abrir entrada na versão atual do Lexa →</a></div></details>`).join('')}<div class="event-footer"><a href="${codeHref(code)}">Consultar edição atual de ${escape(code.short)} →</a><a href="${escape(event.sourceUrl)}" target="_blank" rel="noopener noreferrer">Fonte oficial ↗</a></div></div></details>`;
  }).join('')||`<div class="history-empty"><span>↺</span><h2>${recordedUpdates.length?'Nenhum registro para estes filtros':'O histórico começa aqui.'}</h2><p>${recordedUpdates.length?'Escolha outra legislação ou outro artigo.':'As primeiras versões incorporadas estabelecerão a referência inicial. As mudanças seguintes aparecerão aqui, com comparação entre os textos.'}</p><a href="#">Voltar à biblioteca</a></div>`;
  if(append)container.insertAdjacentHTML('beforeend',markup);else container.innerHTML=markup;
  renderedCount=Math.min(limit,events.length);
  document.querySelector('#history-more').hidden=events.length<=limit;
  document.querySelectorAll('[data-revision-event]:not([data-bound])').forEach(details=>{details.dataset.bound='true';details.addEventListener('toggle',()=>{
   if(!details.open||details.dataset.loaded)return;
   const event=events.find(e=>e.id===details.dataset.revisionEvent);
   const change=event.changes[Number(details.dataset.revisionIndex)];
   const comparison=compareVersions(change.before,change.after);
   details.querySelector('.comparison-container').innerHTML=`<div class="diff-legend"><span class="legend-before">Diferente na versão anterior</span><span class="legend-after">Diferente na versão coletada</span></div><div class="comparison-grid"><section><h3>Versão anterior</h3><p class="comparison-edition">Edição ${escape(event.fromVersion?.slice(0,12)||'não identificada')}</p>${diffColumn(comparison.before,'before')}</section><section><h3>Versão coletada</h3><p class="comparison-edition">Coleta ${collectionDate(event)} · edição ${escape(event.toVersion?.slice(0,12)||'não identificada')}</p>${diffColumn(comparison.after,'after')}</section></div><p class="comparison-caution">Riscados já presentes na fonte são preservados. A ausência de um trecho não determina, por si só, revogação ou início de vigência.</p>`;
   details.dataset.loaded='true';
  });});
 }
 function sync(){
  limit=12;
  const query=new URLSearchParams();if(codeId)query.set('codigo',codeId);if(articleId)query.set('artigo',articleId);
  history.replaceState(history.state,'','#/atualizacoes'+(query.size?'?'+query:''));draw();
 }
 document.querySelector('#history-code').onchange=e=>{codeId=e.target.value;sync();};
 document.querySelector('#history-article').oninput=e=>{articleId=e.target.value;sync();};
 document.querySelector('#history-clear').onclick=()=>{codeId='';articleId='';document.querySelector('#history-code').value='';document.querySelector('#history-article').value='';sync();};
 document.querySelector('#history-more').onclick=event=>{const top=scrollY,previous=renderedCount;limit+=12;draw(true);window.scrollTo({top,behavior:'instant'});if(event.currentTarget.hidden)document.querySelectorAll('.update-event>summary')[previous]?.focus({preventScroll:true});};
 draw();
}
