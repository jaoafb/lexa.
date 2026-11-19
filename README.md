<div align="center">
  <img src="public/favicon.svg" width="64" height="64" alt="" />
  <h1>Lexa</h1>
  <p><strong>A lei, mais perto. A consulta, mais simples.</strong></p>
  <p>Biblioteca gratuita de legislação brasileira, com leitura no navegador e acesso offline.</p>
  <p><a href="https://jaoafb.github.io/lexa./"><strong>Abrir o Lexa</strong></a> · <a href="https://jaoafb.github.io/lexa./#/atualizacoes">Atualizações</a> · <a href="https://github.com/jaoafb/lexa./issues">Relatar um problema</a></p>
  <a href="https://github.com/jaoafb/lexa./actions/workflows/deploy-pages.yml"><img src="https://github.com/jaoafb/lexa./actions/workflows/deploy-pages.yml/badge.svg?branch=main" alt="Publicação no GitHub Pages" /></a>
</div>

## Consulte a legislação

Busque por uma referência como `Art. 186 CC`, `ADCT art. 1` ou `SV 13`, ou pesquise uma expressão em toda a biblioteca. No leitor, você pode abrir o índice, salvar favoritos, ajustar a leitura e copiar um artigo com a referência e o link.

- [Constituição Federal](https://jaoafb.github.io/lexa./#/cf) e [ADCT](https://jaoafb.github.io/lexa./#/cf/adct-1)
- [Códigos e leis federais](docs/GUIA-DE-CONSULTA.md#acervo)
- [Súmulas Vinculantes do STF](https://jaoafb.github.io/lexa./#/sv) e [Emendas Constitucionais nº 1–141](https://jaoafb.github.io/lexa./#/emendas)

O [guia de consulta](docs/GUIA-DE-CONSULTA.md) reúne o acervo completo, exemplos de busca, instruções para usar offline e informações de privacidade.

## Fontes e atualizações

Cada coleção informa a edição e a origem dos textos. A conferência diária compara as 13 legislações com a Câmara dos Deputados e registra diferenças para revisão. A incorporação ao acervo depende de revisão e merge. O GitHub Pages publica a partir da `main`. As súmulas têm atualização manual. Veja os [procedimentos de conferência e atualização](monitor/README.md).

Para uso jurídico, confira a redação e a vigência nas fontes oficiais. A biblioteca das ECs 1–141 reúne publicações originais da Câmara, disponibilizadas por autorização do mantenedor e ainda pendentes de homologação jurídica humana independente. Veja o [registro da publicação das emendas](docs/EMENDAS-CONSTITUCIONAIS.md#publicação-direta-autorizada-pelo-mantenedor).

## Desenvolva localmente

Na raiz do repositório, com Node.js 22 ou superior, execute `npm start` e abra [localhost:3000](http://localhost:3000). A aplicação usa JavaScript nativo e dispensa a instalação de dependências npm.

```sh
npm test              # Gera o pacote e executa os testes JavaScript
npm run test:python   # Testa os importadores e monitores com Python 3.12+
```

| Pasta | Conteúdo |
| --- | --- |
| [`src/`](src/) e [`public/`](public/) | Interface, busca, leitor e recursos da PWA |
| [`data/`](data/), [`sources/`](sources/) e [`HTML/`](HTML/) | Dados do acervo, originais e registros de procedência |
| [`scripts/`](scripts/), [`monitor/`](monitor/) e [`tests/`](tests/) | Build, coleta, importação e verificações |
| [`docs/`](docs/INDEX.md) | Guias de consulta, desenvolvimento e manutenção |

Consulte a [estrutura do projeto](docs/ESTRUTURA.md) antes de editar e o [guia de manutenção](docs/MANUTENCAO.md) para gerar prévias ou publicar. Para abrir uma issue de conteúdo, indique a norma, o dispositivo e a fonte oficial, se disponível.

## Licença

O código do Lexa é licenciado para uso não comercial sob a [PolyForm Noncommercial 1.0.0](LICENSE). Consulte os [avisos sobre código e fontes](NOTICE.md).
