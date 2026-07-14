# Dicionário dos CSVs de resultado

`make collect` transforma vereditos em `data/experiment/results/<mas_id>/<judge_id>/`. Ele lê o índice e os `run1.json`
em `data/internal/<mas_id>/agentrx/<judge_id>/`, o ground truth e as trajetórias. Não executa testes estatísticos nem
compara braços. Rode `make validate-csv` para verificar chaves, faixas, normalização e reagregação.

Os três arquivos usam `scenario_id` + `arm` como chave de junção. O braço é uma coluna (`telemetry` ou `agentrx`), nunca
um arquivo. O esquema é escrito por `src/agentrx_otel_poc/collect/csv_writer.py`; este README é seu dicionário canônico
exigido pelo PRD-10.

## Convenções

| Tipo | Representação |
| -- | -- |
| `int` | Inteiro decimal. |
| `float` | Número decimal; métricas do coletor usam precisão fixa. |
| `str` | Texto UTF-8. |
| `bool01` | `0` ou `1`. |
| `enum` | Um dos valores enumerados no campo. |
| `json` | JSON serializado numa célula CSV, com chaves ordenadas. |
| `iso8601` | Data/hora ISO 8601 com fuso. |

Categorias de ground truth pertencem às cinco injetáveis. Predições usam a taxonomia completa do AgentRx: uma previsão
fora de escopo mantém código e nome, mas conta como erro de categoria.

## `runs_long.csv`

Granularidade: uma linha por execução do juiz. É a matéria-prima por repetição; não agrega julgamentos.

| Campo | Tipo | Origem | Significado | | -- | -- | -- | | `scenario_id` | `str` | meta | Identificador do cenário e
chave de junção. | | `arm` | `enum{telemetry,agentrx}` | meta | Representação enviada ao juiz. | | `judge_idx` | `int` |
meta | Índice da repetição do juiz, começando em 1. | | `pred_step` | `int` | veredito | Passo previsto na repetição:
média dos steps das failures, arredondada. | | `pred_category` | `int (0..10)` | veredito | Categoria prevista na
repetição; 0 e 10 continuam sendo miss. | | `pred_category_name` | `str` | veredito | Nome completo correspondente a
`pred_category`. | | `raw_failures_json` | `json` | veredito | Lista bruta `[{case,step}]` usada para reconstruir a
agregação. | | `agentrx_run_name` | `str` | meta | Caminho relativo `<arm>/<run_id>/rep<k>` para rastrear a repetição. |

## `trajectory_index.csv`

Granularidade: uma linha por trajetória e braço. Liga a trajetória enviada ao trace OTel que a originou; o trace não é
copiado para os CSVs.

| Campo | Tipo | Origem | Significado | | -- | -- | -- | | `run_id` | `str` | meta | Execução do MAS que originou o
trace. | | `scenario_id` | `str` | meta | Chave de junção com os outros CSVs. | | `arm` | `enum{telemetry,agentrx}` |
meta | Braço da trajetória. | | `trajectory_path` | `str (path)` | meta | Caminho da IR enviada ao AgentRx. | |
`otel_path` | `str (path)` | meta | Caminho do trace OTel bruto, fonte de verdade. | | `n_steps` | `int` | meta | Número
de passos da trajetória; denominador da distância normalizada. | | `sent_at` | `iso8601` | meta | Mtime do `run1.json`
da repetição mais antiga do par. |

## `metricas.csv`

Granularidade: uma linha por trajetória e braço. Cada linha agrega todas as reps com veredito (`ok` e `skipped`); reps
`error` não entram no pool e reduzem `n_judge_runs`. O pooling é fiel ao `compute_stats` do AgentRx.

### Identificação e ground truth

| Campo | Tipo | Origem | Significado | | -- | -- | -- | | `scenario_id` | `str` | meta | Chave de junção. | | `arm` |
`enum{telemetry,agentrx}` | meta | Braço; os dois valores do cenário formam o par A/B. | | `n_judge_runs` | `int` | meta
| Número de reps com veredito usadas no pool. | | `trajectory_length` | `int` | meta | Passos da trajetória; normaliza a
distância. | | `gt_step` | `int` | GT | Passo crítico verdadeiro. | | `gt_category` | `int (1..10)` | GT | Categoria
crítica verdadeira. | | `gt_category_name` | `str` | GT | Nome legível de `gt_category`. | | `gt_failures_json` | `json`
| GT | Lista `[{step,category}]` de todas as falhas anotadas. | | `gt_earliest_category` | `int` | GT | Categoria da
falha de menor passo. | | `gt_terminal_category` | `int` | GT | Categoria da falha de maior passo. |

### Agregados das repetições

| Campo | Tipo | Origem | Significado | | -- | -- | -- | | `most_common_category` | `int (0..10)` | agregado | Moda das
categorias no pool de failures. | | `most_common_category_name` | `str` | agregado | Nome legível da moda. | |
`step_mean` | `float` | agregado | Média dos steps no pool. | | `step_median` | `float` | agregado | Mediana dos steps
no pool. | | `category_std` | `float` | agregado | Desvio-padrão dos inteiros de categoria no pool. | | `step_std` |
`float` | agregado | Desvio-padrão dos steps no pool. | | `failure_case_accuracy_perrun` | `float [0,1]` | agregado × GT
| Fração das failures do pool cuja categoria bate com o GT. | | `step_mae` | `float` | agregado × GT | Média de
`abs(step - gt_step)` no pool. |

### Métricas de localização e categoria

| Campo | Tipo | Fórmula | Significado |
| -- | -- | -- | -- |
| `step_acc_exact` | `bool01` | `round(step_mean) == gt_step` | Critical Step-index Accuracy. |
| `step_acc_tol1` | `bool01` | `abs(round(step_mean)-gt_step) <= 1` | Acc@±1. |
| `step_acc_tol3` | `bool01` | `abs(round(step_mean)-gt_step) <= 3` | Acc@±3. |
| `step_acc_tol5` | `bool01` | `abs(round(step_mean)-gt_step) <= 5` | Acc@±5. |
| `avg_step_distance` | `float` | `abs(step_mean-gt_step)` | Distância de passo; menor é melhor. |
| `avg_step_distance_norm` | `float` | `avg_step_distance/trajectory_length` | Distância normalizada. |
| `cat_acc_critical` | `bool01` | moda = GT crítico | Acurácia de categoria crítica. |
| `cat_acc_any` | `bool01` | moda ∈ GT anotado | Acurácia para qualquer falha. |
| `cat_acc_earliest` | `bool01` | moda = GT mais cedo | Acurácia para primeira falha. |
| `cat_acc_terminal` | `bool01` | moda = GT mais tarde | Acurácia para última falha. |

No MAS há uma falha injetada por cenário; por isso as quatro métricas de categoria coincidem. No TRAIL, múltiplos labels
podem diferenciá-las.

### Metadados

| Campo | Tipo | Origem | Significado | | -- | -- | -- | | `judge_model` | `str` | meta | `effective_model` uniforme das
reps, ou fallback do manifesto. | | `agentrx_run_name` | `str` | meta | Base dos diretórios de rep, `<arm>/<run_id>`. |

## Regras de integridade

- Cada par `scenario_id` + `arm` existe nos três CSVs, sem órfãos.
- `bool01` pertence a `{0,1}`; acurácias pertencem a `[0,1]`.
- `avg_step_distance_norm` usa `trajectory_length`, igual a `n_steps` do índice.
- `metricas.csv` é reconstruível das linhas correspondentes de `runs_long.csv`.
- A rerun com os mesmos insumos produz bytes idênticos.

O [exemplo de referência](../../../docs/examples/metrics-reference.md) mostra o pooling e as fórmulas com um cenário
pequeno calculado à mão.
