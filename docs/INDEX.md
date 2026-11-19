# Documentação do Lexa

| Preciso de… | Consulte |
| --- | --- |
| Buscar, ler ou instalar o Lexa | [Guia de consulta](GUIA-DE-CONSULTA.md) |
| Encontrar os arquivos da aplicação, do acervo ou do build | [Estrutura do projeto](ESTRUTURA.md) |
| Executar testes, gerar prévias e publicar | [Manutenção](MANUTENCAO.md) e [baseline de desempenho](BASELINE-DESEMPENHO.md) |
| Conferir fontes ou preparar uma atualização | [Monitor das legislações](../monitor/README.md) e [monitor do STF](../monitor/stf/README.md) |
| Manter a biblioteca de Emendas Constitucionais | [Publicação, vínculos e manutenção das emendas](EMENDAS-CONSTITUCIONAIS.md) |
| Trabalhar com redações anteriores | [Fluxo HTML simples](REDACOES-ANTERIORES-SIMPLES.md), [extrator](EXTRATOR-REDACOES-HTML.md) e [decisão de lançamento](REDACOES-ANTERIORES-LANCAMENTO.md) |
| Preparar uma alteração no repositório | [Processo de trabalho](PROCESSO-DE-TRABALHO.md), [instruções para agentes](../AGENTS.md) e [Codex no Windows](CODEX-LOCAL.md) |

## Fontes e evidências

- [PDFs e manifestos](../sources/), [HTMLs locais](../HTML/), [capturas do monitor](../monitor/official/), [dados oficiais](../data/official/) e [dados PDF arquivados](../data/archive/).
- [Distribuição de redações anteriores](../data/previous-wordings/) e [inventário de preservação externa](../experiments/PRESERVACAO.json). A autorização de consulta não altera os estados de homologação.

## Referências e registros anteriores

- [Arquivo de documentação](arquivo/README.md) com estudos de desempenho, entregas de UX, testes de portabilidade e o fluxo anterior de extração por HTML.
- [Histórico legislativo](HISTORICO-LEGISLATIVO.md), [UX e interface](ux-ui/lote-1.md) e [coordenação](coordenacao/INDEX.md).
- Remissões expressas e os fluxos de PDFs/Câmara para redações anteriores estão suspensos. Consulte os registros no histórico do Git.

## Verificações e licença

- [Verificações de PR](../.github/workflows/verify.yml), [publicação](../.github/workflows/deploy-pages.yml) e [conferência diária](../.github/workflows/pilot-official-sources.yml). Consulte o GitHub para o estado de issues, PRs e execuções.
- Código sob a [PolyForm Noncommercial 1.0.0](../LICENSE), com [avisos de licenciamento e fontes](../NOTICE.md).
