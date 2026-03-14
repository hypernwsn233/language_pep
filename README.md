# pep# language runtime

Implementacao profissional inicial da linguagem pep#, com foco em pipelines de dados, observabilidade e CLI.

## Recursos disponiveis na v0.1

- Declaracao de variaveis com `:=`
- Expressoes seguras
- Pipelines com operador `->`
- Etapas: `filter`, `map`, `count`, `take`, `collect`, `save`, `print`, `parse json`
- Fontes nativas: `file`, `json`, `csv`
- Controle de fluxo: `if`, `for`, `repeat`
- Funcoes com `fn` e `return`
- Erros explicitos com operador `?`
- Observabilidade com `watch <pipeline>`
- CLI com `pep run`, `pep watch` e `pep repl`
- Concorrencia declarativa com `task` e `await`
- Servidor web embutido com `server` e `route`
- Planner de execucao com `pep plan`
- Compilacao para artefato `.pepc` com `pep compile`
- Otimizacoes de performance: cache de expressao e `parallel max N` real em map/filter

## Execucao local

```bash
python -m pip install -e .
pep run examples/etl.pep
pep watch examples/etl.pep --pipeline sales
pep plan examples/etl.pep --mode cluster
pep compile examples/etl.pep
```

## Estrutura

- `pep_lang/ast_nodes.py`: AST da linguagem
- `pep_lang/parser.py`: parser indent-sensitive
- `pep_lang/runtime.py`: interpretador e contexto
- `pep_lang/pipeline.py`: motor de pipeline e metricas
- `pep_lang/server.py`: servidor HTTP embutido
- `pep_lang/planner.py`: plano logico/fisico inicial
- `pep_lang/bytecode.py`: compilacao para artefato `.pepc`
- `pep_lang/cli.py`: interface de linha de comando
- `tests/`: testes unitarios

## Status

Projeto funcional para uso real em scripts de automacao e pipelines locais. O modo distribuido esta preparado no design e sera evoluido em fases seguintes.
