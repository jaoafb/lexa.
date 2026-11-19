# Conferência das fontes e atualização do acervo

| Fluxo | Resultado |
| --- | --- |
| [Conferência diária com a Câmara](#conferência-diária-com-a-câmara) | Relatório comparado com a edição publicada e evidências para revisão |
| [Preparação manual pela fonte antiga do Planalto](#preparação-de-propostas-pela-fonte-antiga-manual) | Proposta em rascunho com textos, referências, testes e prévia |
| [Publicação no GitHub Pages](../docs/desenvolvimento/MANUTENCAO.md#publicar-no-github-pages) | Site gerado a partir da `main` após a incorporação de mudanças |

As edições já incorporadas ao leitor ficam em [`data/official/`](../data/official/). Consulte também os procedimentos das [súmulas vinculantes](stf/README.md) e das [emendas constitucionais](../docs/EMENDAS-CONSTITUCIONAIS.md).

## Preparação de propostas pela fonte antiga (manual)

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

## Execução manual da preparação antiga

O workflow fica em `.github/workflows/monitor-legislation.yml` e só aceita **Run workflow**. O acesso direto às fontes antigas do Planalto pode redirecionar para fora dos domínios autorizados; por isso, esse fluxo não roda em pushes nem por agendamento. Sua execução é deliberada e serve para preparar uma proposta quando a fonte puder ser validada integralmente.

Em **Settings → Actions → General**, permita os actions utilizados e a criação de PRs pelo `GITHUB_TOKEN`. O GitHub fornece esse token durante o job; não precisa fornecer valores no chat. O job usa `contents: write` e `pull-requests: write`, cria rascunhos e não aprova nem mescla propostas. Monitore falhas em Actions: execução sem sucesso não equivale a “nenhuma mudança na lei”.

## Execução local

### Conferência diária com a Câmara

A conferência diária consulta na Câmara uma fonte oficial para cada uma das 13 legislações do Lexa. Cada resultado é comparado diretamente à edição publicada. Uma falha não apaga as demais evidências, mas a execução só fica verde quando conclui **13/13** comparações. O GitHub Actions programa a consulta para 06:40 em Brasília, tem somente permissão de leitura e guarda por 30 dias o relatório, as tentativas e os HTMLs efetivamente recebidos, identificados por SHA-256.

O resultado diário é documental: não altera `data/`, `sources/`, `monitor/official/`, histórico ou estados de revisão; não cria PR e não publica. Uma diferença pode já existir entre as fontes e não significa necessariamente mudança ocorrida naquele dia. Execuções parciais falham visivelmente, mas preservam toda evidência já obtida no artefato.

```sh
python3 scripts/daily_collection.py --output monitor/run/daily/execucao-local
```

Para diagnóstico isolado, a execução manual ainda aceita `camara`, `planalto`, `classico` ou `novo`. O modo `novo` continua sendo uma sondagem dos caminhos antigos no domínio novo, não uma integração confirmada com a navegação do portal. A conferência resolve os HTMLs de Constituição e ADCT no índice oficial da Câmara e registra a URL e o hash do índice e de cada arquivo. Índice incompleto, links ambíguos ou fontes indisponíveis interrompem apenas a comparação afetada e ficam registrados no relatório.

Na comparação com a Câmara, cada linha mantém o identificador do Lexa e mostra o identificador efetivo em cada edição. Quando um artigo individual está coberto por um intervalo que declara expressamente revogação, supressão ou veto, a linha aponta para esse intervalo. A correspondência usa a mesma numeração e o mesmo escopo e os identificadores com letras são avaliados individualmente. Intervalos reconhecidos e sobrepostos bloqueiam a comparação.

O relatório mantém os textos integrais dos dois lados e registra divergências de redação, redações riscadas e diferenças nas referências de revogação que consegue identificar. A comparação usa uma projeção com marcadores e notas editoriais reconhecidos para indicar diferenças de apresentação. A projeção serve à triagem e os textos brutos, os identificadores publicados e o histórico continuam sendo as referências para a revisão da proposta.

Os dispositivos com redação integralmente riscada e notas documentais de vigência encerrada entram como histórico preservado. Entradas compostas por marcadores explícitos de veto entram como registros documentais. No art. 392-D da CLT, a referência à Lei 15.371/2026 é conferida na publicação original e o relatório registra separadamente o texto publicado, a data da publicação e a cláusula expressa de vigência. Ao chegar à data declarada, a redação permanece pendente de revisão. A conferência entrega evidências para revisão jurídica antes de uma troca de fonte.

### Prévia de Constituição e ADCT

A aplicação das decisões documentais fica em `scripts/constitution_preview.py`, separada da coleta. A suíte essencial testa a prévia sem acesso à rede, em desktop e celular, usando o corpus versionado como fixture (não como captura da Câmara). A conferência ao vivo pode ser solicitada em **Verificar Lexa → Run workflow → camara_live**, sem depender do nome de uma branch. As verificações não homologam escolhas jurídicas.

O modo `novo` é apenas uma sondagem dos caminhos antigos no domínio `portaldalegislacao.presidencia.gov.br`. Não comprova suporte à navegação ou à estrutura do portal novo. Falha de transferência não comprova ausência da lei nem descontinuação da fonte; a migração exige confirmar os endereços dos documentos e sua identidade antes de mudar as fontes de produção.

`npm run preview:camara` gera e serve a prévia em `http://127.0.0.1:3014/#/cf`. Com `-- --build-only`, o comando gera o pacote em `test-results/camara-preview/site`. A candidata usa os dois documentos localizados no índice da Câmara, exige os mesmos identificadores por escopo e informa a fonte de cada documento no leitor e na cópia. O histórico publicado serve de referência na prévia. A comparação constitucional fica no mesmo diretório de teste, ao lado da candidata.

### Preparar uma proposta da fonte antiga no ambiente local

Use Node.js 22+, Python 3.12+ (biblioteca padrão) e curl.

```sh
npm run test:python
python3 scripts/check_official_sources.py
python3 scripts/import_official.py
npm test
npm run build
```

A primeira consulta bem-sucedida estabelece uma referência de monitoramento para revisão. `--only civil` no coletor limita um diagnóstico manual; o workflow completo sempre consulta as fontes cadastradas. O conversor exige todas as referências validadas. Antes de executá-lo localmente, preserve os arquivos gerados que deseja manter: ele prepara os candidatos no checkout atual. Não execute a reimportação dos PDFs como parte da inicialização diária.
