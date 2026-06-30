# PRD-02 — Gerador de perguntas (benchmark)

## 1. Objetivo

Especificar `scripts/generate_benchmark.py`: um gerador **determinístico, sem IA**
que lê o catálogo do tau-bench e produz `data/benchmark/benchmark_30.json` com 30
perguntas single-turn somente-leitura, com resposta computada do catálogo.

Não é uma biblioteca externa; é código do projeto. O MAS **lê** o JSON pronto;
nunca chama o gerador em tempo de execução.

## 2. Entrada e saída

- Entrada: `data/external/taubench_retail/products.json` (commit fixado).
- Saída: `data/benchmark/benchmark_30.json` (lista de 30 objetos).
- Propriedade: rodar 2× produz arquivos idênticos (determinismo).

## 3. Templates (ancorados em padrões reais de instruções do τ-bench)

| ID | Pergunta | Computação |
|----|----------|-----------|
| T1 | Qual o [tipo] disponível mais barato? | `min(price)` sobre variantes disponíveis |
| T2 | Quantas opções de [tipo] estão disponíveis? | `count` de variantes disponíveis |
| T3 | Quais [tipo] com [opção]=[valor] custam mais que X? | filtro sobre variantes |
| T4 | O item [id] do [tipo] tem [opção]=[valor]? | booleano |
| T5 | Qual o preço do item [id]? | preço da variante |

## 4. Esquema de cada pergunta

```json
{
  "task_id": "q07_t3_laptop",
  "domain": "product_catalog",
  "user_request": "Quais Laptop disponíveis com processor=i7 custam mais que US$ 2508?",
  "tool_name": "ProductCatalogSearch",
  "tool_operation": "catalog.search",
  "default_tool_args": {"product_type": "Laptop", "processor": "i7",
                         "price_min": 2508, "available_only": true},
  "expected_result": "2 itens de Laptop (processor=i7) disponíveis acima de US$ 2508.",
  "expected_answer": {"item_ids": ["..."], "count": 2},
  "success_criteria": ["A resposta deve derivar do output da ferramenta.",
                       "Se a ferramenta falhar, declarar tarefa não concluída."],
  "target_fault_category": "Instruction/Plan Adherence Failure",
  "injection_node": "Coordinator",
  "template_id": "T3_spec_filter"
}
```

`expected_answer` é o ground truth de sucesso (computado). `target_fault_category`
+ `injection_node` ligam a pergunta ao experimento.

## 5. Balanceamento

- 6 perguntas por categoria × 5 categorias = 30.
- Cada categoria usa templates que a hospedam bem (ver PRD-03):
  - System Failure → qualquer template (falha no nó Tool).
  - Invalid Invocation → T3/T4/T5 (args estruturados).
  - Misinterpretation → T1/T3/T4 (há comparação/seleção).
  - Invention → T1/T2/T3 com resposta verdadeira não-vazia (fabricação fica óbvia).
  - Plan Adherence → T1/T3 com restrição explícita a violar.

## 6. Regras de robustez

- Para T3/T4, escolher `opção=valor` que **existe** no catálogo e `price_min` =
  mediana das variantes que casam (garante resultado não trivial).
- Para Invention, garantir `expected_answer` **não-vazio** (senão fabricar e
  "não achar nada" se confundem).
- Falhar com erro claro se um tipo de produto referenciado não existir.

## 7. Critérios de aceite

- `benchmark_30.json` tem 30 itens; `Counter(target_fault_category)` = 6 cada.
- Toda `expected_answer` confere ao recomputar do catálogo.
- Reexecução byte-idêntica.
- O `tasks.py` carrega esse arquivo (substitui o dict hardcoded).
