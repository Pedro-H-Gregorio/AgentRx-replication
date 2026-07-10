# PRD-07 — Métricas do AgentRx: cálculo e povoamento dos CSVs

## 1. Objetivo

Especificar **como computar as métricas de resultado que o AgentRx propõe** e **como escrevê-las nos CSVs**, espelhando
a seção 4 do artigo (Barke et al., 2026) e o código do submódulo. É um spec de cálculo, desacoplado da análise A/B (essa
vem depois, em cima destes CSVs). Fonte dupla: artigo §4.1/§4.7 (o que reportar) e `agentrx/llm_clients/__init__.py`
(`compute_stats`, `analysis`) + `reports/metrics.py` (como calcular).

## 2. Entradas por trajetória

Para cada trajetória julgada, o AgentRx emite (prompt §G, saída JSON): `failure_case` (int 1–10) e `index` (passo).
Rodamos o juiz **n=3** vezes (default do artigo). Ground truth: `gt_step_number` e `gt_failure_case`. Precisa também de
`trajectory_length` (para normalizar distância).

## 3. Agregação das n execuções (por trajetória) — `compute_stats`

- **Categoria**: `most_common_failure` = moda das n categorias; guardar `modes`, `proportions`, `std_dev`/`variance`
  (estabilidade entre execuções).
- **Passo**: `step_mean` (média), `step_median`, `step_std_dev`/`variance`.
- **Contra GT**: `failure_case_accuracy` = fração das n execuções com categoria == GT; `step_mae` = média de
  `|passo − gt|`; `step_error_distribution`.

## 4. Métricas de resultado do artigo (o que povoar)

### 4.1 Step Localization (artigo §4.1)

- **Critical Step-index Accuracy**: `round(step_mean) == gt_step` (fração exata).
- **Step-index Accuracy@±r**, r∈{1,3,5}: `|round(step_mean) − gt_step| ≤ r`. (o código também computa r=2,4; reportar ao
  menos 1,3,5 como o artigo.)
- **Average Step Distance** (↓): `|step_mean − gt_step|`, e a versão **normalizada** por `trajectory_length`. Reportar
  separada para categoria certa/errada e geral.

### 4.2 Failure Category (artigo §4.1) — QUATRO variantes

- **Critical Category Accuracy**: predita == categoria GT do passo crítico.
- **Any-failure Category Accuracy**: predita == qualquer categoria entre os passos de falha da trajetória.
- **Earliest Category Accuracy**: predita == categoria do **primeiro** passo de falha.
- **Terminal Category Accuracy**: predita == categoria do **último** passo de falha.

As três últimas exigem o **conjunto de falhas anotadas** da trajetória, não só a crítica. Ver §6 (ground truth
estendido).

## 5. Esquema do CSV (uma linha por trajetória)

O significado, tipo e origem de cada campo são **canônicos no PRD-10 (dicionário de dados)**; exemplo de mesa em
`docs/examples/metrics-reference.md`. Resumo das colunas (ver PRD-10 para tipos/faixas e as colunas-espelho `*_name`):

`scenario_id, arm, n_judge_runs, trajectory_length, gt_step, gt_category,`
`gt_failures_json, gt_earliest_category, gt_terminal_category,` `most_common_category, step_mean, step_median,`
`step_acc_exact, step_acc_tol1, step_acc_tol3, step_acc_tol5,` `avg_step_distance, avg_step_distance_norm,`
`cat_acc_critical, cat_acc_any, cat_acc_earliest, cat_acc_terminal,`
`failure_case_accuracy_perrun, step_mae, category_std, step_std,` `judge_model, agentrx_run_name`

- `gt_failures_json`: lista `[{step, category}]` das falhas anotadas (habilita Any/Earliest/Terminal).
- Um segundo CSV `runs_long.csv` guarda **uma linha por execução do juiz**
  (`scenario_id, arm, judge_idx, pred_step, pred_category`) — matéria-prima da agregação e da análise de variância.

## 6. Ground truth estendido (necessário para §4.2)

O AgentRx anota **todas** as falhas da trajetória mais a crítica (paper §2.1, Apêndice B/D). No MAS: como injetamos
**uma** falha por cenário, o conjunto de falhas anotadas = {a injetada}; então Any/Earliest/Terminal coincidem com a
crítica (documentar isso — não é limitação, é consequência do desenho). No braço TRAIL: usar os múltiplos erros dos
`labels` (PRD-09) para popular as quatro.

## 7. Mapeamento de categoria (pré-requisito)

`failure_case` é int 1–10 (paper §G): 1 Instruction/Plan Adherence … 9 System Failure, 10 Inconclusive. As 5 categorias
do estudo devem mapear para esses **inteiros** (o código compara `str(value)`). Versionar a tabela `categoria → id`. A
métrica de passo independe disso.

## 8. Runner e coleta (scripts)

- **Runner**: `scripts/run_judge.py` (C6) — cenário × braço × rep, sequencial e idempotente; grava
  `data/internal/<mas_id>/agentrx/<judge_id>/` com manifesto + `runs_index.jsonl` (insumo da coleta). Não há
  `run_matrix.py` (planejado, mas o `run_judge.py` já é a matriz).
- `scripts/collect_agentrx.py` (C7): agrega os vereditos brutos → os 3 CSVs (§5 / PRD-10) em
  `data/experiment/results/<mas_id>/<judge_id>/`. A agregação **reimplementa** o critério do
  `compute_stats`/`analysis()` (pooling achatado das failures das reps `ok`; PRD-08 D32) e **passa no teste de paridade
  numérica** contra fixtures versionadas geradas uma vez do submódulo — **não importa `agentrx`** (regra 6; PRD-08 D33).
  O coletor é **neutro**: nenhuma estatística, nenhuma comparação A/B, nenhuma linha descartada.
- **Análise (C8)**: consome os CSVs de `data/experiment/results/` — o agregado `metricas.csv` **e** a matéria-prima
  por-rep `runs_long.csv` (a tabela de frequência/MAE por categoria exige o por-rep) — e emite as **tabelas** da seção
  de Resultados do artigo em `data/experiment/analysis/<mas_id>/<judge_id>/` (`make analyze`). É leitura pura: não
  recomputa a métrica (é do C7) nem importa `agentrx`. Por ora **só tabelas**; figuras ficam para change futura. A
  comparação A vs B / TRAIL é artefato **posterior**, sobre estes números (fora do escopo do C7).

### 8.1 Auditoria de higiene (manual, pareada) — PRD-08 D35

Com `USE_LLM=true` (D31) o agente pode, em tese, narrar uma prosa desancorada além da falha injetada. Em vez de um
filtro automático (descartado — D35: superfície pequena com injeção scriptada, e a contaminação é ~simétrica entre
braços), o protocolo é **manual e documentado**: candidato a erro emergente = cenário em que **os dois braços, nas 3
reps, apontam consistentemente um passo ≠ do injetado**. Esses (poucos) casos são auditados lendo a trajetória e
decididos caso a caso, com a decisão registrada no PRD-08. A exclusão, se houver, é **pareada** (sai dos dois braços,
senão quebra o A/B). É ameaça à validade declarada, não requisito de código do C7.

## 9. Baselines de referência do artigo (preenchidos)

Tabela 6 (n=3), para ancorar plausibilidade. τ-bench (AgentRx): Step 54.0, @±1 59.8, @±3 72.4, @±5 83.9, Dist 2.4,
Critical Cat 40.2, Any 41.4, Earliest 35.6, Terminal 34.5. Flash (AgentRx): Step 83.3, Critical Cat 60.3. Magentic
(AgentRx): Step 31.8, Critical Cat 37.1. Ver Tabela 5 para ablações one-shot vs step-by-step. **Não** comparar nossos
absolutos com estes (setup diferente) — âncora metodológica.

## 10. Critérios de aceite

- CSV da §5 gerado com as **10** métricas (3 de passo + tolerâncias, distância crua e normalizada, e as **4** de
  categoria).
- `runs_long.csv` existe e reconstrói a agregação.
- Cálculo **reimplementa** o critério e passa no teste de paridade numérica contra fixtures do submódulo (não importa
  `agentrx`; PRD-08 D33).
- Tabela `categoria → id (1–10)` versionada (fonte única em `judge/scoring.py`).
- MAS e TRAIL produzem o mesmo esquema, em saídas separadas.
