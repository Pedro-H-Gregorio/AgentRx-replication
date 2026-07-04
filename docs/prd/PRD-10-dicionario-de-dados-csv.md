# PRD-10 — Dicionário de dados dos CSVs

## 1. Objetivo

Definir o significado, o tipo e a origem de **cada campo** dos CSVs de resultado, para validar o esquema antes de codar.
Três CSVs, granularidades diferentes; o **braço é coluna**, nunca arquivo. Complementa o PRD-05 (coleta) e o PRD-07
(cálculo).

Convenções de tipo: `int`, `float`, `str`, `bool01` (0/1), `enum`, `json` (string JSON), `iso8601`. "Origem": de onde o
valor vem (bruto do juiz, agregado, GT, meta).

## 2. `runs_long.csv` — granularidade: 1 linha por execução do juiz

Matéria-prima; guarda a variância entre as n execuções. Nada agregado aqui.

| Campo | Tipo | Origem | Significado |
| -- | -- | -- | -- |
| `scenario_id` | str | meta | Pergunta + categoria alvo (ex.: `q07_t3_laptop`). Chave de junção. |
| `arm` | enum{telemetry,agentrx} | meta | Representação da trajetória enviada ao juiz. |
| `judge_idx` | int (1..n) | meta | Índice da execução do juiz (default n=3). |
| `pred_step` | int | bruto do juiz | Passo crítico previsto (`index` da saída do AgentRx). |
| `pred_category` | int (1..10) | bruto do juiz | Categoria prevista (`failure_case`, taxonomia do paper). |
| `agentrx_run_name` | str | meta | Nome do run do AgentRx (`runs/<name>/`), para rastreio. |

## 3. `trajectory_index.csv` — granularidade: 1 linha por trajetória×braço

Liga cada trajetória enviada ao trace bruto que a originou. O trace **não** entra nos CSVs; aqui vão os ponteiros.

| Campo | Tipo | Origem | Significado |
| -- | -- | -- | -- |
| `run_id` | str | meta | Execução base do MAS que gerou o trace (ex.: `run_007`). |
| `scenario_id` | str | meta | Chave de junção com os outros CSVs. |
| `arm` | enum | meta | Braço desta trajetória. |
| `trajectory_path` | str (path) | meta | Caminho da trajetória enviada ao AgentRx. |
| `otel_path` | str (path) | meta | Caminho do trace OTel bruto (fonte de verdade). |
| `n_steps` | int | meta | Nº de passos da trajetória (denominador da distância normalizada). |
| `sent_at` | iso8601 | meta | Quando foi submetida ao juiz. |

## 4. `metricas.csv` — granularidade: 1 linha por trajetória×braço (agregado de n)

O CSV que alimenta a análise. Cada linha resume as n execuções de um braço.

### 4.1 Identificação e ground truth

| Campo | Tipo | Origem | Significado |
| -- | -- | -- | -- |
| `scenario_id` | str | meta | Chave de junção. |
| `arm` | enum | meta | Braço. Par (telemetry, agentrx) do mesmo `scenario_id` = comparação A/B. |
| `n_judge_runs` | int | meta | Nº de execuções agregadas (default 3). |
| `trajectory_length` | int | meta | Passos da trajetória; normaliza a distância. |
| `gt_step` | int | GT | Passo crítico verdadeiro (ponto de injeção no MAS; derivado nos labels do TRAIL). |
| `gt_category` | int (1..10) | GT | Categoria crítica verdadeira. |
| `gt_failures_json` | json | GT | Lista `[{step,category}]` de TODAS as falhas anotadas. No MAS: 1 item. No TRAIL: vários. Habilita any/earliest/terminal. |
| `gt_earliest_category` | int | GT | Categoria da falha de menor `step` em `gt_failures_json`. |
| `gt_terminal_category` | int | GT | Categoria da falha de maior `step` em `gt_failures_json`. |

### 4.2 Agregados das n execuções

| Campo | Tipo | Origem | Significado |
| -- | -- | -- | -- |
| `most_common_category` | int | agregado | Moda de `pred_category` nas n execuções (`most_common_failure`). |
| `step_mean` | float | agregado | Média de `pred_step` nas n execuções. |
| `step_median` | float | agregado | Mediana de `pred_step`. |
| `category_std` | float | agregado | Desvio-padrão da categoria entre execuções (estabilidade). |
| `step_std` | float | agregado | Desvio-padrão do passo entre execuções. |
| `failure_case_accuracy_perrun` | float [0,1] | agregado×GT | Fração das n execuções com `pred_category == gt_category`. |
| `step_mae` | float | agregado×GT | Média de \` |

### 4.3 Métricas do artigo (localização de passo — §4.1)

| Campo | Tipo | Fórmula | Significado |
| -- | -- | -- | -- |
| `step_acc_exact` | bool01 | `round(step_mean)==gt_step` | Critical Step-index Accuracy. |
| `step_acc_tol1` | bool01 | `\|round(step_mean)−gt_step\|<=1` | Acc@±1. |
| `step_acc_tol3` | bool01 | `<=3` | Acc@±3. |
| `step_acc_tol5` | bool01 | `<=5` | Acc@±5. |
| `avg_step_distance` | float | `\|step_mean−gt_step\|` | Distância de passo (↓ melhor). |
| `avg_step_distance_norm` | float | `avg_step_distance/trajectory_length` | Distância normalizada. |

### 4.4 Métricas do artigo (categoria — §4.1, 4 variantes)

| Campo | Tipo | Fórmula | Significado |
| -- | -- | -- | -- |
| `cat_acc_critical` | bool01 | `most_common_category==gt_category` | Critical Category Accuracy. |
| `cat_acc_any` | bool01 | moda ∈ categorias de `gt_failures_json` | Any-failure Category Accuracy. |
| `cat_acc_earliest` | bool01 | `most_common_category==gt_earliest_category` | Earliest Category Accuracy. |
| `cat_acc_terminal` | bool01 | `most_common_category==gt_terminal_category` | Terminal Category Accuracy. |

### 4.5 Metadados

| Campo | Tipo | Origem | Significado |
| -- | -- | -- | -- |
| `judge_model` | str | meta | Modelo/versão do juiz (do manifesto do run). |
| `agentrx_run_name` | str | meta | Base do nome dos runs agregados. |

## 5. Regras de integridade (validáveis)

- Chave de junção: `scenario_id` (+ `arm`) liga os três CSVs sem linha órfã.
- `bool01` ∈ {0,1}; acurácias por execução ∈ [0,1]; `gt_category`,`pred_category` ∈ [1,10].
- No MAS, `gt_failures_json` tem 1 item ⇒ `cat_acc_any=cat_acc_earliest=cat_acc_terminal=cat_acc_critical`.
- `avg_step_distance_norm` usa `trajectory_length` = `n_steps` do índice.
- Toda linha de `metricas.csv` reconstrói-se a partir das linhas de `runs_long.csv` do mesmo (`scenario_id`,`arm`) —
  teste de reprodutibilidade da agregação.

## 6. Critérios de aceite

- Cada campo dos três CSVs tem entrada aqui (tipo, origem, significado).
- Os nomes batem exatamente com PRD-05 (§5) e PRD-07 (§5). Divergência = corrigir.
- As fórmulas de §4.3/§4.4 conferem com o exemplo de referência (docs/examples/).
