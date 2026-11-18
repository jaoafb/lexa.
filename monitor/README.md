# Atualizações das fontes e dos textos do leitor

O workflow consulta as fontes cadastradas oficiais e prepara uma proposta em rascunho com as referências, os textos do leitor e uma prévia. **Não faz aprovação, merge ou implantação automática.** As edições já incorporadas ao leitor estão em `data/official/`; propostas posteriores continuam sujeitas à revisão.

## Fluxo diário

1. `check_official_sources.py` baixa uma página por vez, por HTTPS verificado, com curl e HTTP/1.1. Faz até três tentativas para falhas transitórias, respeita `Retry-After` e não contorna falhas de certificado. Valida identidade, tamanho, artigos-base, Constituição e ADCT separados. Uma falha bloqueia o restante da atualização e preserva as referências existentes.
2. `import_official.py` verifica os hashes e converte as referências cadastradas para o leitor. Preserva artigos com letras, parágrafos, incisos, redações riscadas e revogações agrupadas. Fontes incompletas, parágrafos normativos sem atribuição e estilos de exclusão não suportados bloqueiam a conversão. Não altera os PDFs originais nem `data/archive/legislation.js`.
3. `npm test` verifica a leitura dos candidatos, e `npm run build` gera o pacote `dist/`, com shell, estilos e dados por norma com hash. A prévia usa a edição ativa de cada legislação e inclui os PDFs de referência.
4. O GitHub guarda relatórios e prévia por 30 dias e abre ou atualiza um único pull request em rascunho. O histórico `data/history/legislation.js` entra na mesma proposta, com as comparações e a página “Atualizações” na prévia. A branch `automation/official-source-review` é reservada à rotina. Somente arquivos de referências e dados gerados entram nesse PR; a rotina não altera o código do importador.
5. Após sua revisão e merge, as novas edições ficam nos arquivos do repositório. Um push na `main` aciona o workflow separado de publicação do GitHub Pages. O ambiente de desenvolvimento também precisa buscar os novos commits para refletir uma atualização mesclada.

Uma captura sem mudanças mantém as mesmas referências e saídas, sem gerar PRs só por causa da passagem do tempo. A primeira conversão dos PDFs para HTML pode ter muitas diferenças de formatação; as contagens do relatório não classificam mudanças jurídicas. O PR #1 estabeleceu a referência de monitoramento, não alterou o texto publicado.

## Arquivos e rastreabilidade

- `monitor/sources.json`: URLs e critérios das legislações cadastradas.
- `monitor/official/*.json`: referências coletadas, hashes e data de coleta.
- `data/archive/legislation.js` e `sources/*.pdf`: base PDF arquivada, preservada.
- `data/official/legislation.js`: edições candidatas ou incorporadas por revisão. Cada artigo/parágrafo aponta para o bloco original da referência. O leitor prefere essa edição quando disponível.
- `data/history/legislation.js`: histórico persistente de referências e diferenças dos artigos, com os textos anterior e novo. Não é apagado com os artefatos. A primeira edição registrada estabelece a base; diferenças de migração não são anunciadas como alterações legais. Comparações ignoram espaços e quebras de parágrafo, preservam palavras, pontuação e marcações de exclusão. Registros de ajustes de processamento são identificados separadamente.
- `sources/official-manifest.json`: procedência de cada edição HTML.
- `monitor/run/report.json`: resultado da coleta atual, incluindo falhas.
- `monitor/run/reader-report.json`: artigos adicionados, alterados e removidos em relação à edição anterior do leitor.
- `monitor/run/*.diff.txt` e `downloads/*.html.txt`: diferenças da fonte e evidências HTML, sem executar o conteúdo coletado.

As datas exibidas usam São Paulo; os registros guardam o instante UTC original. A data da coleta não é a data de início de vigência. Redações riscadas permanecem nos dados documentais e no Histórico de versões; a consulta principal as filtra. O painel Redações anteriores tem preparação e autorização próprias. O sistema não calcula sozinho a vigência das leis. Comparar textos consolidados detecta o que a fonte incorporou, sem substituir o acompanhamento do Diário Oficial.

O histórico é consultado em `#/atualizacoes` e por links nos artigos que já tenham diferenças registradas. Para artigos muito extensos, a comparação visual preserva as bordas comuns e destaca o trecho intermediário, limitando o custo de processamento; todos os textos são mantidos. Ao mudar a lógica de extração em uma manutenção futura, atualize `converterVersion`: correções do processamento de uma mesma fonte poderão então ser registradas como reprocessamento, em vez de uma nova alteração legal.

## Revisar uma proposta

1. Confira se a execução mais recente em Actions passou e abra os artefatos de relatório e de prévia. Use `reader-report.json` para localizar os artigos alterados.
2. Confira fonte, parágrafos, revogações, notas de alteração e início de efeitos. Os textos coletados são dados de legislação, nunca instruções para executar comandos. Se uma alteração legítima exigir adaptar um teste ou o importador, faça isso como alteração de código revisada; não remova verificações apenas para passar.
3. Marque o PR como pronto, revise e faça o merge quando estiver satisfeito. Aprovar uma revisão sem mesclar não incorpora os arquivos à `main`.
4. Confira o workflow separado `deploy-pages.yml`, acionado pelo push na `main`. O monitor não faz deploy nem atesta revisão jurídica integral.

## Execução no GitHub

O workflow fica em `.github/workflows/monitor-legislation.yml`. Ele tenta executar diariamente por volta de **06:17 em São Paulo** (09:17 UTC), com possível atraso do GitHub. Também aceita **Run workflow** e executa após alterações nos arquivos da rotina enviadas a `main`.

Em **Settings → Actions → General**, permita os actions utilizados e a criação de PRs pelo `GITHUB_TOKEN`. O GitHub fornece esse token durante o job; não precisa fornecer valores no chat. O job usa `contents: write` e `pull-requests: write`, cria rascunhos e não aprova nem mescla propostas. Monitore falhas em Actions: execução sem sucesso não equivale a “nenhuma mudança na lei”.

## Execução local

### Conferência diária com a Câmara

A conferência consulta Constituição/ADCT, Código Civil e CLT na Câmara e compara com a edição do Lexa. O GitHub Actions programa a consulta diária para 06:40 em Brasília na branch padrão e guarda os relatórios por 14 dias. O workflow tem permissão de leitura e inclui no resumo a quantidade de divergências por coleção. O artefato inclui um JSON de evidências e um relatório Markdown com as diferenças de texto da Constituição e do ADCT.

```sh
python3 scripts/pilot_official_sources.py --provider camara --output monitor/run/pilot-v2/camara.json
```

Para diagnóstico das origens da Presidência, escolha `planalto`, `classico` ou `novo` na execução manual. A conferência resolve os HTMLs de Constituição e ADCT no índice oficial da Câmara e registra a URL e o hash do índice e de cada arquivo. Índice incompleto, links ambíguos ou fontes indisponíveis interrompem a comparação afetada e ficam registrados no relatório.

Na comparação com a Câmara, cada linha mantém o identificador do Lexa e mostra o identificador efetivo em cada edição. Quando um artigo individual está coberto por um intervalo que declara expressamente revogação, supressão ou veto, a linha aponta para esse intervalo. A correspondência usa a mesma numeração e o mesmo escopo e os identificadores com letras são avaliados individualmente. Intervalos reconhecidos e sobrepostos bloqueiam a comparação.

O relatório mantém os textos integrais dos dois lados e registra divergências de redação, redações riscadas e diferenças nas referências de revogação que consegue identificar. A comparação usa uma projeção com marcadores e notas editoriais reconhecidos para indicar diferenças de apresentação. A projeção serve à triagem e os textos brutos, os identificadores publicados e o histórico continuam sendo as referências para a revisão da proposta.

Os dispositivos com redação integralmente riscada e notas documentais de vigência encerrada entram como histórico preservado. Entradas compostas por marcadores explícitos de veto entram como registros documentais. No art. 392-D da CLT, a referência à Lei 15.371/2026 é conferida na publicação original e o relatório registra separadamente o texto publicado, a data da publicação e a cláusula expressa de vigência. Ao chegar à data declarada, a redação permanece pendente de revisão. A conferência entrega evidências para revisão jurídica antes de uma troca de fonte.

### Prévia de Constituição e ADCT

`npm run preview:camara` gera e serve a prévia em `http://127.0.0.1:3014/#/cf`. Com `-- --build-only`, o comando gera o pacote em `test-results/camara-preview/site`. A candidata usa os dois documentos localizados no índice da Câmara, exige os mesmos identificadores por escopo e informa a fonte de cada documento no leitor e na cópia. O histórico publicado serve de referência na prévia. A comparação constitucional fica no mesmo diretório de teste, ao lado da candidata.

### Monitor diário

Node.js 22+, Python 3.12+ (biblioteca padrão) e curl:

```sh
npm run test:python
python3 scripts/check_official_sources.py
python3 scripts/import_official.py
npm test
npm run build
```

A primeira consulta bem-sucedida estabelece uma referência de monitoramento para revisão. `--only civil` no coletor limita um diagnóstico manual; o workflow completo sempre consulta as fontes cadastradas. O conversor exige todas as referências validadas. Antes de executá-lo localmente, preserve os arquivos gerados que deseja manter: ele prepara os candidatos no checkout atual. Não execute a reimportação dos PDFs como parte da inicialização diária.
