# pep#

Especificacao de linguagem para automacao, pipelines de dados e execucao distribuida transparente.

## 1. Identidade

Nome: pep#

Categoria:

- Linguagem moderna de proposito geral
- Orientada a fluxo de dados
- Focada em automacao, processamento de dados e sistemas distribuidos
- Otimizada para simplicidade, desempenho e paralelismo automatico

Frase conceitual:

pep# e uma linguagem onde um script simples pode automaticamente se tornar um sistema paralelo e distribuido.

## 2. Objetivo

pep# foi desenhada para que o modelo principal de programacao seja um pipeline de dados. O programador descreve o que deve acontecer com os dados. O runtime decide como executar localmente, em paralelo e, quando habilitado, de forma distribuida. O mesmo programa deve escalar do notebook ao cluster sem mudanca de codigo-fonte.

## 3. Filosofia

### Pipeline First

O fluxo de dados e a principal abstracao da linguagem. Quase tudo pode produzir, consumir ou transformar um pipeline.

### Menos codigo intermediario

pep# privilegia transformacoes encadeadas, bindings curtos e composicao direta. Variaveis existem, mas nao sao o centro da modelagem.

### Paralelismo automatico

O programador descreve dependencias. O runtime infere particionamento, fan-out, fan-in, backpressure e uso de multiplos nucleos.

### Observabilidade nativa

Pipelines, tarefas e servidores expoem estado em tempo real. O comportamento operacional nao e um extra do ecossistema; faz parte da linguagem.

### Erros explicitos

Erros sao valores tipados. Operacoes faliveis nunca falham silenciosamente.

### Simplicidade sintatica

A superficie sintatica deve ser pequena, legivel e previsivel. pep# prefere poucas formas fortes a muitas variacoes.

## 4. Modelo mental

Um programa pep# e uma composicao de:

- Valores
- Funcoes
- Pipelines
- Tarefas
- Servicos

O eixo central e o pipeline:

```pep
transactions :=
    file "transactions.json"
    -> parse json
    -> validate schema Transaction
    -> group by customer_id
    -> reduce total = sum(amount)
    -> store "out/totals.parquet"
```

Cada etapa recebe um fluxo de itens, lotes ou eventos e produz um novo fluxo. O runtime pode materializar, particionar ou distribuir esse fluxo sem alterar a semantica do programa.

## 5. Caracteristicas centrais

- Sintaxe enxuta inspirada em linguagens de script modernas
- Tipagem gradual com inferencia local
- Operador de pipeline `->` como operador principal
- I/O nativo para JSON, CSV, Parquet, HTTP e streams
- Scheduler orientado a DAG de dados
- Auto-paralelizacao baseada em custo e pureza das etapas
- Distribuicao transparente por workers e cluster
- Observabilidade embutida com `watch`, `trace` e `explain`
- Servidor web embutido
- CLI e pacote padrao para automacao e DevOps

## 6. Sintaxe essencial

### 6.1 Comentarios

```pep
# comentario de linha

## comentario de bloco curto
## ainda no bloco
```

### 6.2 Declaracao e binding

`:=` cria um binding local. Bindings sao imutaveis por padrao.

```pep
name := "Lucas"
age := 21
enabled := true
```

Mutacao e explicita:

```pep
mut count := 0
set count = count + 1
```

### 6.3 Estruturas literais

```pep
numbers := [1, 2, 3]
user := {
    name: "Lucas",
    age: 21,
    tags: ["admin", "ops"]
}
```

### 6.4 Funcoes

```pep
fn soma(a: number, b: number) -> number:
    return a + b

fn is_adult(user) -> boolean:
    return user.age >= 18
```

Funcoes de uma linha:

```pep
fn double(x) => x * 2
```

Closures:

```pep
fn make_adder(base):
    return fn (x) => x + base
```

### 6.5 Condicionais

```pep
if age >= 18:
    print "adult"
elif age >= 13:
    print "teen"
else:
    print "child"
```

### 6.6 Loops

```pep
for item in list:
    print item

repeat 10:
    print "running"

while connected:
    sync()
```

### 6.7 Match

```pep
match status:
    200 => print "ok"
    404 => print "not found"
    _ => print "unexpected"
```

## 7. Pipelines

### 7.1 Operador central

`->` significa passagem de fluxo entre etapas.

```pep
logs
-> filter status == 500
-> count
-> print
```

### 7.2 Fontes nativas

```pep
users := json "users.json"
logs := csv "logs.csv"
images := files "images/"
events := stream kafka "orders"
payload := http get "https://api.example.com/users"
```

### 7.3 Etapas padrao

- `filter <expr>`
- `map <expr>`
- `flatmap <expr>`
- `reduce <expr>`
- `group by <expr>`
- `sort by <expr>`
- `take <n>`
- `drop <n>`
- `window tumbling <duration>`
- `window sliding <duration> every <duration>`
- `join <pipeline> on <expr>`
- `merge <pipeline>`
- `branch <expr>`
- `sink <target>`

### 7.4 Pipeline com blocos nomeados

```pep
users :=
    file "users.json"
    -> parse json
    -> step adults:
        filter age >= 18
    -> step names:
        map { id: id, name: name }
    -> save "out/users.json"
```

Etapas nomeadas aparecem em `watch`, logs, traces e metricas.

### 7.5 Semantica operacional

- Cada etapa declara se e pura, stateful ou side-effecting.
- Etapas puras podem ser reordenadas, fundidas e paralelizadas.
- Etapas stateful usam chaves de particionamento ou afinidade.
- Etapas com efeito externo sao pontos de barreira e checkpoint.

## 8. Sistema de tipos

pep# usa tipagem gradual.

### 8.1 Tipos primitivos

- `number`
- `string`
- `boolean`
- `list<T>`
- `map<K, V>`
- `record`
- `pipeline<T>`
- `bytes`
- `time`
- `duration`
- `error`
- `result<T>`
- `option<T>`

### 8.2 Records e schemas

```pep
type User:
    id: string
    name: string
    age: number
    country?: string

type Transaction:
    id: string
    customer_id: string
    amount: number
    created_at: time
```

### 8.3 Inferencia

```pep
age := 21              # number
name := "Lucas"       # string
users := json "u.json" # pipeline<map<string, any>>
```

### 8.4 Contratos em pipeline

```pep
users: pipeline<User> :=
    json "users.json"
    -> validate schema User
```

## 9. Erros e confiabilidade

pep# nao usa falha silenciosa. Toda operacao falivel pode ser:

- propagada automaticamente como `result<T>`
- tratada explicitamente
- transformada em erro terminal do pipeline

### 9.1 Operador `?`

`?` tenta extrair o valor. Em caso de erro, retorna um objeto `error` no contexto atual.

```pep
config := file "config.json" ?

if config is error:
    print config.message
    exit 1
```

### 9.2 Tratamento explicito

```pep
result := parse json text

match result:
    ok data => print data
    err e => log e.message
```

### 9.3 Politicas de falha em pipeline

```pep
events
-> decode json on_error skip
-> validate schema Event on_error route invalid_events
-> store "good.parquet"
```

Politicas suportadas:

- `fail`
- `skip`
- `retry <n>`
- `route <pipeline>`
- `default <value>`

## 10. Concorrencia declarativa

pep# trata concorrencia como composicao de tarefas e dependencias, nao como threads explicitas.

```pep
task ingest:
    process file1

task enrich:
    process file2

await ingest, enrich
```

### 10.1 Grupos de tarefa

```pep
taskgroup daily:
    task extract:
        run extract_data

    task transform:
        run transform_data

    task publish:
        run publish_data

    after extract -> transform -> publish
```

### 10.2 Canais e sinais

```pep
signal shutdown

task server:
    run api.start()

on shutdown:
    api.stop()
```

## 11. Paralelismo automatico

pep# expande paralelismo em tres niveis:

- Vetorizacao e batching local
- Execucao multi-core no mesmo host
- Distribuicao entre workers

### 11.1 Heuristicas do runtime

O runtime considera:

- Pureza da etapa
- Tamanho estimado do dataset
- Custo de serializacao
- Cardinalidade e skew de chaves
- Latencia versus throughput desejados
- Restricoes de memoria

### 11.2 Controle declarativo opcional

O usuario pode orientar, sem codificar threads ou processos:

```pep
images
-> load "images/"
-> parallel max 8
-> resize 1024
-> compress quality 80
-> upload bucket "assets"
```

Outras diretivas:

- `partition by <expr>`
- `affinity <expr>`
- `batch <n>`
- `buffer <n>`
- `ordered`
- `unordered`

## 12. Execucao distribuida transparente

O mesmo programa pode rodar em `local`, `hosted` ou `cluster`.

```pep
transactions
-> load "transactions.json"
-> validate schema Transaction
-> compute totals
-> store "daily_totals.parquet"
```

Sem alterar o codigo, o runtime pode:

- fragmentar leitura por particao
- enviar etapas puras para workers remotos
- fazer shuffle por chave
- executar reducers proximos do armazenamento
- reexecutar particoes falhadas

### 12.1 Modos de execucao

```pep
runtime mode local
runtime mode cluster
runtime workers 32
runtime checkpoint every 30s
```

### 12.2 Garantias

O runtime oferece politicas configuraveis:

- `best_effort`
- `at_least_once`
- `exactly_once` para sinks compativeis

## 13. Observabilidade nativa

### 13.1 Comando `watch`

```pep
watch transactions
```

Saida esperada:

```text
load transactions     ok 20000 items
validate              ok 19920 items
compute totals        running 14832 items/s
store                 waiting
```

### 13.2 Comando `trace`

```pep
trace transactions
```

Mostra latencia por etapa, retries, shuffles, backpressure e uso de memoria.

### 13.3 Comando `explain`

```pep
explain transactions
```

Mostra o plano logico e o plano fisico:

- fusao de operadores
- limites de paralelismo
- pontos de checkpoint
- trocas de formato
- distribuicao entre workers

## 14. Arquivos e I/O nativos

Arquivos sao objetos de primeira classe.

```pep
users := json "users.json"
logs := csv "logs.csv"
table := parquet "warehouse/events.parquet"
blob := file "notes.txt"
```

Escrita:

```pep
data -> save "out/data.json"
data -> csv.write "out/data.csv"
data -> parquet.write "out/data.parquet"
```

## 15. Web server embutido

```pep
users := json "users.json"

server 8080:
    route "/":
        return "Hello"

    route "/health":
        return { status: "ok" }

    route "/users":
        return users -> take 100 -> collect
```

### 15.1 Recursos HTTP nativos

- `route`
- `middleware`
- `request`
- `response`
- `cookie`
- `stream`
- `websocket`

Exemplo com middleware:

```pep
server 8080:
    middleware logger
    middleware cors

    route "/events":
        return stream events
```

## 16. Modulos e pacotes

### 16.1 Importacao

```pep
use http
use json
use crypto
use dataframe@1.2
```

### 16.2 Alias

```pep
use crypto as c
token := c.sha256 "abc"
```

### 16.3 Estrutura de pacote

```text
pep.toml
src/main.pep
src/etl/normalize.pep
tests/normalize_test.pep
```

`pep.toml`:

```toml
[package]
name = "sales-pipeline"
version = "0.1.0"
entry = "src/main.pep"

[runtime]
mode = "local"
observability = true
```

## 17. CLI integrada

Comandos principais:

- `pep run script.pep`
- `pep watch script.pep`
- `pep test`
- `pep fmt`
- `pep plan script.pep`
- `pep publish`
- `pep repl`

Exemplo:

```bash
pep run etl.pep
pep watch etl.pep
pep plan etl.pep --mode cluster
```

## 18. Gramatica resumida

EBNF simplificada:

```ebnf
program         = { statement } ;

statement       = use_stmt
                | type_stmt
                | let_stmt
                | mut_stmt
                | set_stmt
                | fn_stmt
                | if_stmt
                | for_stmt
                | repeat_stmt
                | while_stmt
                | match_stmt
                | task_stmt
                | taskgroup_stmt
                | server_stmt
                | expr_stmt ;

use_stmt        = "use" ident [ "@" version ] [ "as" ident ] ;
type_stmt       = "type" ident ":" NEWLINE INDENT { field_decl } DEDENT ;
field_decl      = ident [ "?" ] ":" type_expr NEWLINE ;

let_stmt        = ident ":=" expr ;
mut_stmt        = "mut" ident ":=" expr ;
set_stmt        = "set" ident "=" expr ;

fn_stmt         = "fn" ident "(" [ params ] ")" [ "->" type_expr ] ":" block
                | "fn" ident "(" [ params ] ")" "=>" expr ;

if_stmt         = "if" expr ":" block
                  { "elif" expr ":" block }
                  [ "else" ":" block ] ;

for_stmt        = "for" ident "in" expr ":" block ;
repeat_stmt     = "repeat" expr ":" block ;
while_stmt      = "while" expr ":" block ;

match_stmt      = "match" expr ":" NEWLINE INDENT { match_arm } DEDENT ;
match_arm       = pattern "=>" expr NEWLINE ;

task_stmt       = "task" [ ident ] ":" block ;
taskgroup_stmt  = "taskgroup" ident ":" block ;
server_stmt     = "server" number ":" block ;

expr            = pipeline_expr ;
pipeline_expr   = logical_expr { "->" pipeline_stage } ;
pipeline_stage  = ident [ args ]
                | "step" ident ":" block
                | "filter" expr
                | "map" expr
                | "reduce" expr
                | "group" "by" expr
                | "join" expr "on" expr ;

logical_expr    = equality_expr { ( "and" | "or" ) equality_expr } ;
equality_expr   = additive_expr { ( "==" | "!=" | ">" | ">=" | "<" | "<=" ) additive_expr } ;
additive_expr   = term { ( "+" | "-" ) term } ;
term            = factor { ( "*" | "/" | "%" ) factor } ;
factor          = literal | ident | call_expr | list_expr | map_expr | "(" expr ")" ;
```

## 19. Semantica de execucao

pep# possui duas representacoes principais:

- AST sintatica para analise e erros de compilacao
- Flow IR para pipelines, tarefas e distribuicao

### 19.1 Regras de avaliacao

- Expressoes simples seguem avaliacao eager.
- Pipelines seguem avaliacao lazy ate o primeiro sink, `collect`, `watch`, `print` ou retorno observavel.
- Um pipeline vira DAG executavel no momento da materializacao.

### 19.2 Pureza e efeitos

Funcoes podem ser anotadas para otimizar planejamento:

```pep
fn normalize(user) pure => {
    id: user.id,
    name: upper(user.name)
}

fn publish(item) effect("network"):
    http post "https://api" body item
```

## 20. Arquitetura do compilador e do runtime

### 20.1 Front-end

Camadas:

1. Lexer sensivel a indentacao
2. Parser LL com recuperacao de erro amigavel
3. Analise semantica
4. Inferencia de tipos
5. Lowering para Flow IR

### 20.2 IRs

#### AST

Representa a forma original do codigo, comentarios de documentacao e spans de erro.

#### Flow IR

Representa:

- DAG de operadores
- fronteiras de task
- hints de paralelismo
- contratos de schema
- efeitos e checkpoints

#### Bytecode IR

Usado para funcoes escalares, expressoes e logica de controle. Pipelines continuam descritos por operadores especializados.

### 20.3 Backend de execucao

O runtime contem:

- Scheduler cooperativo de tarefas
- Motor de pipelines com backpressure
- Pool multi-core com work-stealing
- Planejador de distribuicao
- Monitor de execucao
- Gerenciador de memoria orientado a arena e buffers reutilizaveis

## 21. Scheduler

O scheduler do pep# trabalha em dois niveis.

### 21.1 Scheduler local

Gerencia:

- futures leves
- filas lock-light
- timers
- sinais
- rede e I/O assincronos

### 21.2 Scheduler de pipeline

Gerencia:

- consumo de fontes
- fan-out de particoes
- fusao de operadores
- checkpoint
- retries
- commit de sink

## 22. Motor de pipeline

Cada pipeline e transformado em uma DAG fisica com nodos de:

- `SourceNode`
- `MapNode`
- `FilterNode`
- `WindowNode`
- `ShuffleNode`
- `ReduceNode`
- `SinkNode`

Otimizacoes principais:

- fusao de `map` e `filter`
- predicate pushdown para fontes compativeis
- leitura vetorizada de JSON, CSV e Parquet
- prefetch adaptativo
- compactacao de lotes pequenos
- reducao parcial antes de shuffle

## 23. Modelo distribuido

### 23.1 Componentes

- `Coordinator`: recebe o plano, faz scheduling global e rastreia workers
- `Worker`: executa particoes e envia metricas
- `Artifact Store`: guarda pacotes, schemas e checkpoints
- `Control Plane`: heartbeats, discovery e politicas
- `Data Plane`: transporte de lotes e shuffle

### 23.2 Processo de execucao

1. O compilador gera Flow IR.
2. O planner cria o plano logico.
3. O planner fisico decide particoes e localidade.
4. O coordinator distribui fragments aos workers.
5. Workers executam etapas, reportam metricas e checkpoints.
6. Sinks realizam commit conforme a garantia configurada.

### 23.3 Tolerancia a falhas

- retries por particao
- replay a partir de checkpoints
- isolamento de operador falho
- detecao de worker indisponivel por heartbeat

## 24. Memoria e desempenho

Decisoes de design:

- buffers em lote para reduzir overhead por item
- reuse de memoria para operadores quentes
- representacao colunar opcional para analytics
- representacao orientada a linhas para eventos e APIs
- zero-copy quando fonte e sink permitirem

pep# privilegia throughput previsivel sem sacrificar ergonomia.

## 25. Modelo de compilacao

pep# suporta dois modos.

### 25.1 Interpretado

Ideal para scripts pequenos, REPL, automacao e desenvolvimento rapido.

Fluxo:

- parse
- type-check parcial
- lowering para bytecode
- execucao imediata

### 25.2 Compilado para bytecode

Ideal para servicos, jobs agendados e distribuicao.

Fluxo:

- parse
- inferencia e validacao completas
- geracao de pacote `.pepc`
- cache e assinatura de artefatos

### 25.3 Otimizacao adaptativa

O runtime pode recompilar hot paths com perfis reais de execucao, especialmente em etapas `map`, `filter` e serializacao.

## 26. Biblioteca padrao sugerida

Namespaces padrao:

- `io`
- `fs`
- `json`
- `csv`
- `parquet`
- `http`
- `time`
- `math`
- `crypto`
- `proc`
- `cloud`
- `test`
- `observe`

## 27. Seguranca e sandbox

pep# pode rodar em modo sandbox com permissoes declarativas:

```pep
permit fs.read "data/"
permit fs.write "out/"
permit net.connect "api.example.com:443"
```

Isso torna scripts automacao mais seguros em CI, jobs agendados e execucao remota.

## 28. Testes

```pep
test "sum totals":
    input := [1, 2, 3]
    result := input -> reduce sum
    expect result == 6
```

Testes de pipeline:

```pep
test "adult filter":
    users := [
        { name: "Ana", age: 17 },
        { name: "Leo", age: 22 }
    ]

    result :=
        users
        -> filter age >= 18
        -> map name
        -> collect

    expect result == ["Leo"]
```

## 29. Exemplo completo de ETL

```pep
use json
use parquet

type Sale:
    id: string
    region: string
    amount: number
    created_at: time

sales: pipeline<Sale> :=
    json "data/sales.json"
    -> validate schema Sale
    -> filter amount > 0

daily :=
    sales
    -> group by region
    -> reduce {
        region: key,
        total: sum(amount),
        count: count()
    }

daily -> parquet.write "warehouse/daily_sales.parquet"

watch daily
```

## 30. Exemplo completo de automacao operacional

```pep
use http
use json

servers := json "infra/servers.json"

results :=
    servers
    -> parallel max 20
    -> map {
        host: host,
        health: http get "https://{host}/health" ?
    }
    -> map {
        host: host,
        ok: health.status == 200,
        body: health.body
    }

results
-> filter ok == false
-> save "out/incidents.json"
```

## 31. Exemplo completo de backend simples

```pep
use json

users := json "data/users.json"

server 8080:
    route "/users":
        return users -> take 100 -> collect

    route "/adults":
        return users -> filter age >= 18 -> collect

    route "/stats":
        return {
            total: users -> count,
            adults: users -> filter age >= 18 -> count
        }
```

## 32. Comparacao conceitual

pep# combina:

- simplicidade de linguagens de script modernas
- modelo declarativo de ferramentas de dados
- observabilidade nativa comum em plataformas operacionais
- paralelismo automatico inspirado em motores de processamento distribuido

Ela nao exige que o desenvolvedor pense primeiro em threads, filas, workers ou orquestradores. Essas decisoes ficam no runtime, com controles declarativos apenas quando realmente necessarios.

## 33. Posicionamento profissional

pep# e adequada para:

- automacao operacional
- ETL e ELT
- ingestao de eventos
- jobs agendados
- ferramentas CLI
- APIs simples
- processamento analitico em media escala
- workloads distribuidos previsiveis

Nao pretende substituir linguagens de baixo nivel ou sistemas que exigem controle absoluto de memoria e latencia sub-milisegundo. O foco e produtividade com escala operacional.

## 34. Roadmap de implementacao realista

### Fase 1

- Lexer e parser
- AST e erros amigaveis
- Bytecode simples
- Pipelines locais
- JSON, CSV, file, HTTP
- `watch` local

### Fase 2

- Type checker gradual
- Flow IR
- Scheduler multi-core
- Parquet
- servidor web
- testes e formatter

### Fase 3

- Coordinator e workers
- checkpointing
- shuffle distribuido
- `explain` e `trace`
- garantias `at_least_once`

### Fase 4

- exactly-once para sinks suportados
- perfilamento adaptativo
- pacote e registry oficial
- politicas de seguranca e sandbox completas

## 35. Resumo executivo

pep# e uma linguagem moderna, realista e implementavel cujo modelo central e o pipeline de dados. Sua proposta principal e permitir que um mesmo codigo comece como script e cresca para execucao paralela e distribuida sem reescrita estrutural. A combinacao de sintaxe simples, runtime inteligente, erros explicitos e observabilidade nativa a posiciona como uma linguagem forte para automacao, dados e sistemas operacionais modernos.