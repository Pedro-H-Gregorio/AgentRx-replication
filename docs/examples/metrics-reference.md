# Exemplo de referência — cálculo dos CSVs (PRD-07/PRD-10)

Oráculo de mesa do coletor (C7): um cenário fictício **`gold01`**, com as fórmulas do PRD-10 §4 aplicadas à mão. As
linhas esperadas aqui são exatamente as que o coletor produz sobre o fixture `tests/fixtures/golden/` — o teste golden
(`tests/test_collect_csv.py`) trava essa igualdade. Se uma fórmula divergir, o golden falha exibindo o campo.

## Cenário

- **Ground truth**: falha injetada no Researcher → `Invalid Invocation` (int 3), `critical_failure_step = 2`. Trajetória
  com **5 passos** (`trajectory_length`).
- **3 execuções do juiz** (reps), braço `telemetry`, todas `ok`. A rep 3 traz **duas failures** (multi-failure) — o caso
  que separa "pooling" de "moda das predições per-rep".

| rep | failures (case, step) | pred_category (moda) | pred_step (round média) |
| -- | -- | -- | -- |
| 1 | (3, 2) | 3 | 2 |
| 2 | (3, 2) | 3 | 2 |
| 3 | (3, 3), (9, 4) | 3 (empate 3 vs 9 → 1º inserido) | round(3.5) = 4 |

## `runs_long.csv` (1 linha por rep)

Cada linha = uma execução do juiz; `raw_failures_json` guarda as failures brutas da rep (matéria-prima da reagregação do
PRD-10 §5).

```
gold01,telemetry,1,2,3,Invalid Invocation,"[{""case"":3,""step"":2}]",telemetry/gold01/rep1
gold01,telemetry,2,2,3,Invalid Invocation,"[{""case"":3,""step"":2}]",telemetry/gold01/rep2
gold01,telemetry,3,4,3,Invalid Invocation,"[{""case"":3,""step"":3},{""case"":9,""step"":4}]",telemetry/gold01/rep3
```

## Pooling (réplica do `compute_stats`)

Achatam-se as failures das 3 reps num único conjunto:

- **cases** = [3, 3, 3, 9] → `most_common_category` = **3** (moda)
- **steps** = [2, 2, 3, 4] → `step_mean` = (2+2+3+4)/4 = **2.75**

## `metricas.csv` — fórmulas aplicadas

| Campo | Fórmula | Valor |
| -- | -- | -- |
| `n_judge_runs` | reps `ok` agregadas | 3 |
| `trajectory_length` | passos da trajetória | 5 |
| `gt_step` / `gt_category` | do ground truth | 2 / 3 |
| `gt_failures_json` | 1 falha no MAS | `[{category:3, step:2}]` |
| `most_common_category` | moda de cases | 3 |
| `step_mean` | média de steps | 2.75 |
| `step_median` | mediana de [2,2,3,4] = (2+3)/2 | 2.5 |
| `category_std` | desvio-padrão amostral de cases [3,3,3,9]\* | 3.0 |
| `step_std` | desvio-padrão amostral de steps [2,2,3,4] | 0.957427 |
| `failure_case_accuracy_perrun` | frac. de cases == gt (3/4) | 0.75 |
| `step_mae` | média de \|step−gt\| = média[0,0,1,2] | 0.75 |
| `step_acc_exact` | round(2.75)=3 == 2 ? | 0 |
| `step_acc_tol1` | \|3−2\| ≤ 1 ? | 1 |
| `step_acc_tol3` / `tol5` | ≤ 3 / ≤ 5 ? | 1 / 1 |
| `avg_step_distance` | \|2.75 − 2\| | 0.75 |
| `avg_step_distance_norm` | 0.75 / 5 | 0.15 |
| `cat_acc_critical` | 3 == 3 ? | 1 |
| `cat_acc_any` | 3 ∈ {3} ? | 1 |
| `cat_acc_earliest` / `terminal` | = crítica (1 falha no MAS) | 1 / 1 |
| `judge_model` | do manifesto (fallback) | golden-judge |

\* `category_std` é o desvio-padrão dos **inteiros** de `failure_case` — fiel ao `compute_stats` do AgentRx, ainda que
estatisticamente estranho para uma variável categórica (ressalva registrada no PRD-10). Métrica de passo independe
disso.

Linha esperada:

```
gold01,telemetry,3,5,2,3,Invalid Invocation,"[{""category"":3,""step"":2}]",3,3,3,Invalid Invocation,2.75,2.5,3.0,0.957427,0.75,0.75,0,1,1,1,0.75,0.15,1,1,1,1,golden-judge,telemetry/gold01
```

## Nota sobre a rep multi-failure

Se toda rep trouxesse **1** failure, o pooling coincidiria com a moda das predições per-rep (D24). A rep 3 (duas
failures) mostra a diferença: o pool [3,3,3,9] pondera as 4 failures, não as 3 reps — é o critério do AgentRx.
