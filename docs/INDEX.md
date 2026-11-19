# Documentação do Lexa

| Preciso de… | Consulte |
| --- | --- |
| Buscar, ler ou instalar o Lexa | [Guia de consulta](consulta/GUIA-DE-CONSULTA.md) |
| Encontrar os arquivos da aplicação, do acervo ou do build | [Estrutura do projeto](desenvolvimento/ESTRUTURA.md) |
| Executar testes, gerar prévias e publicar | [Manutenção](desenvolvimento/MANUTENCAO.md) e [baseline de desempenho](desenvolvimento/BASELINE-DESEMPENHO.md) |
| Conferir fontes ou preparar uma atualização | [Monitor das legislações](../monitor/README.md) e [monitor do STF](../monitor/stf/README.md) |
| Manter a biblioteca de Emendas Constitucionais | [Vínculos e manutenção das emendas](EMENDAS-CONSTITUCIONAIS.md) |
| Trabalhar com redações anteriores | [Fluxo HTML simples](redacoes-anteriores/REDACOES-ANTERIORES-SIMPLES.md), [extrator](redacoes-anteriores/EXTRATOR-REDACOES-HTML.md) e [referência de compatibilidade](redacoes-anteriores/HISTORICO-LEGISLATIVO.md) |
| Preparar uma alteração no repositório | [Processo de trabalho](coordenacao/PROCESSO-DE-TRABALHO.md), [instruções para agentes](../AGENTS.md) e [Codex no Windows](desenvolvimento/CODEX-LOCAL.md) |

## Autorizações de publicação

Os registros abaixo ficam na raiz de `docs/` porque os arquivos de liberação apontam para seus caminhos e seções.

- [Emendas Constitucionais](EMENDAS-CONSTITUCIONAIS.md#publicação-direta-autorizada-pelo-mantenedor)
- [Redações anteriores](REDACOES-ANTERIORES-LANCAMENTO.md#autorizacao-de-publicacao)

## Fontes e evidências

- [PDFs e manifestos](../sources/), [HTMLs locais](../HTML/), [capturas do monitor](../monitor/official/), [dados oficiais](../data/official/) e [dados PDF arquivados](../data/archive/).
- [Distribuição de redações anteriores](../data/previous-wordings/) e [inventário de preservação externa](../experiments/PRESERVACAO.json). A autorização de consulta não altera os estados de homologação.

## Referências e registros anteriores

- [Arquivo de documentação](arquivo/README.md) com estudos de desempenho, entregas de UX, testes de portabilidade e o fluxo anterior de extração por HTML.
- [UX e interface](ux-ui/lote-1.md) e [coordenação](coordenacao/INDEX.md).
- Remissões expressas e os fluxos de PDFs/Câmara para redações anteriores estão suspensos. Consulte os registros no histórico do Git.

## Verificações e licença

- [Verificações de PR](../.github/workflows/verify.yml), [publicação](../.github/workflows/deploy-pages.yml) e [conferência diária](../.github/workflows/pilot-official-sources.yml). Consulte o GitHub para o estado de issues, PRs e execuções.
- Código sob a [PolyForm Noncommercial 1.0.0](../LICENSE), com [avisos de licenciamento e fontes](../NOTICE.md).
