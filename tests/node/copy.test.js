import test from 'node:test';
import assert from 'node:assert/strict';
import {collections,articleById} from '../../src/data.js';
import {articleCopyText} from '../../src/copy.js';

test('cópia mantém todos os parágrafos, identificação, edição e fonte em cada coleção',()=>{
 for(const code of collections){
  const article=code.articles[0],before=JSON.stringify(article),link=`https://example.test/lexa./#/${code.id}/${article.id}`;
  const output=articleCopyText(code,article,link);
  assert.ok(output.startsWith(code.name));assert.ok(output.includes(code.law));assert.ok(output.includes(code.source.edition));assert.ok(output.includes(link));
  for(const paragraph of article.paragraphs)for(const run of paragraph.runs)assert.ok(output.includes(run.text));
  assert.ok(output.includes(article.url||code.source.url||code.url));assert.equal(JSON.stringify(article),before);
 }
});

test('riscados são identificados, sem juntar redações antigas à nova ou eliminar palavras',()=>{
 const code=collections.find(c=>c.id==='cpc');
 const article=code.articles.find(a=>a.paragraphs.some(p=>p.runs.some(r=>r.deleted)));
 const output=articleCopyText(code,article,'https://example.test/#/cpc/'+article.id);
 assert.match(output,/Trecho riscado na fonte:/);
 for(const paragraph of article.paragraphs)for(const run of paragraph.runs){
  assert.ok(output.includes(run.deleted?`[Trecho riscado na fonte: ${run.text}]`:run.text));
 }
});

test('ADCT conserva identidade e revogação agrupada conserva o intervalo',()=>{
 const cf=collections.find(c=>c.id==='cf'),ctn=collections.find(c=>c.id==='ctn');
 assert.match(articleCopyText(cf,articleById(cf,'adct-1'),'https://example.test/#/cf/adct-1'),/ADCT · Art\. 1/);
 const grouped=articleById(ctn,'55');
 assert.match(articleCopyText(ctn,grouped,'https://example.test/#/ctn/'+grouped.id),/Arts\. 52 a 58/);
});

test('cópia de Constituição e ADCT indica o documento da edição correspondente',()=>{
 const cf=collections.find(c=>c.id==='cf');
 const documents={main:{url:'https://example.test/constituicao'},adct:{url:'https://example.test/adct'}};
 const code={...cf,source:{...cf.source,provider:'camara',documents}};
 for(const [id,scope] of [['1','main'],['adct-1','adct']]){
  const output=articleCopyText(code,articleById(code,id),'https://example.test/#/cf/'+id);
  assert.ok(output.includes('Fonte oficial para conferência: '+documents[scope].url));
 }
});

test('cópia constitucional usa a fonte da redação preservada na prévia',()=>{
 const cf=collections.find(c=>c.id==='cf');
 const code={...cf,source:{...cf.source,provider:'camara',edition:'Câmara · Prévia',
  documents:{main:{url:'https://example.test/camara'}}}};
 const article={...articleById(code,'39'),documentSource:{...cf.source,reviewNote:'Redação preservada.'}};
 const copied=articleCopyText(code,article,'https://example.test/#/cf/39');
 assert.ok(copied.includes('Edição consultada no Lexa: '+cf.source.edition));
 assert.ok(copied.includes('Fonte oficial para conferência: '+cf.source.url));
 assert.match(copied,/Redação preservada\./);
 assert.doesNotMatch(copied,/Câmara · Prévia|example\.test\/camara/);
});

test('súmula cancelada informa situação e copia o enunciado separado dos precedentes',()=>{
 const code=collections.find(c=>c.id==='sv'),article=articleById(code,'9');
 const output=articleCopyText(code,article,'https://example.test/#/sv/9');
 assert.match(output,/Situação indicada na edição: Cancelada/);
 assert.match(output,/Súmula Vinculante 9/);
 assert.ok(output.includes(code.source.filename));
 for(const note of article.notes||[]){
  const text=note.runs.map(run=>run.text).join('');
  if(text.length>300)assert.ok(!output.includes(text));
 }
});
