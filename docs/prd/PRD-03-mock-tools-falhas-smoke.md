# PRD-03 — Mock tools, operadores de falha e smoke tests

## 1. Objetivo

Especificar a(s) mock tool(s) de catálogo e os **5 operadores de falha**, cada um com o nó de injeção, o mecanismo
(scriptado), exemplo de entrada→saída falha e o ground truth gerado. Inclui um smoke test por falha.

## 2. Mock tool: `ProductCatalogSearch`

Backing: `products.json` (leitura). Duas operações:

- `catalog.search` — args: `product_type`, opcionais `<opção>=<valor>`, `price_min`, `available_only`, `sort`, `op`
  (ex.: `count`). Retorna lista de itens (`item_id`, `price`, `options`) ou agregação.
- `catalog.get_details` — args: `product_id`, `item_id`. Retorna a variante.

Saída **estruturada** (JSON) em caso de sucesso; em caso de erro, objeto `{"ok": false, "error": {...}}`. Saída sempre
registrada no span da tool.

## 3. Mecanismo de injeção

A injeção é **scriptada e determinística**, controlada por `fault_type` no estado. Cada operador atua no nó-alvo, força
o comportamento falho e **não** depende da competência do agente (qualquer que seja o `AGENT_MODEL`). Alternativa
documentada (fora do experimento principal): provocar uma categoria via modificação de prompt — usar só para exploração
pontual, nunca no conjunto principal, pois suja o ground truth.

## 4. Operadores de falha

### 4.1 System Failure — nó Tool

- Mecanismo: a tool levanta exceção/timeout antes de retornar evidência.
- Exemplo: `catalog.search(product_type=Laptop, processor=i7)` →
  `CatalogServiceTimeoutError("... timed out after 30000ms")`; span status ERROR.
- Ground truth: `critical_failure_step` = passo da Tool; categoria System Failure.

### 4.2 Invalid Invocation — nó Researcher

- Mecanismo: o Researcher emite args malformados para uma tool **saudável** (campo obrigatório ausente ou tipo errado).
- Exemplo: esperado `{"product_id": "4760268021", "item_id": "..."}`; injetado `{"product_id": 4760268021}` (sem
  `item_id`, `product_id` como int) → a tool rejeita com erro de schema.
- Ground truth: passo do Researcher; categoria Invalid Invocation.

### 4.3 Misinterpretation of Tool Output — nó Executor

- Mecanismo: a tool retorna output **válido**; o Executor é scriptado a ler errado.
- Exemplo: tool retorna a variante mais barata = item A (US$ 180,02); o Executor afirma que a mais barata é o item B
  (US$ 217,90). Output da tool intacto.
- Ground truth: passo do Executor; categoria Misinterpretation.

### 4.4 Invention of New Information — nó Executor

- Mecanismo: tool retorna vazio/erro; o Executor **fabrica** um resultado.
- Exemplo: `catalog.search(T-Shirt, op=count)` retorna `{"ok": false}` ou lista vazia, mas o Executor responde "Há 10
  opções disponíveis" sem proveniência. (A resposta verdadeira computada é 10 → a fabricação é detectável por não
  derivar do output.)
- Ground truth: passo do Executor; categoria Invention.

### 4.5 Instruction/Plan Adherence Failure — nó Coordinator

- Mecanismo: o Coordinator planeja violando uma restrição explícita da pergunta.
- Exemplo: pergunta pede `processor=i7` e `price_min=2508`; o Coordinator planeja a consulta com `processor=i5` (ou
  descarta `price_min`). Tool intacta.
- Ground truth: passo do Coordinator; categoria Plan Adherence.

## 5. Estrutura no código

- Centralizar os operadores em `faults.py`, um por categoria, com assinatura uniforme `apply(state, logger) -> state'` e
  seleção por `fault_type`.
- O nó correspondente chama o operador antes de produzir sua saída; quando `fault_type` não pertence ao nó, o operador é
  no-op.
- Cada injeção emite um evento OTel `fault.injected` com `category` e `node`.

## 6. Smoke tests (um por falha, em `tests/`)

Para cada categoria, um teste que roda **1 cenário** e verifica:

- O `fault.injected` foi emitido no nó esperado.
- O `ground_truth.json` aponta o passo/categoria corretos.
- O desfecho do run é `FAILED`/`REJECTED` quando deve ser.
- As 2 trajetórias derivadas são geradas sem exceção.
- (4.3/4.4) o output da tool no trace permanece **válido/vazio** conforme o caso, para garantir que a falha está no
  Executor, não na tool.

Critério de aceite: `make smoke` roda os 5 e todos passam **antes** do experimento.

## 7. Critérios de aceite gerais

- Os 5 operadores existem e são selecionáveis por `fault_type`.
- Cada um produz ground truth determinístico e um evento `fault.injected`.
- Nenhum operador depende da saída do LLM para definir o passo crítico.
