# PRD-05 — Integração com o AgentRx e coleta (CSV)

## 1. Objetivo

Definir como registrar o domínio próprio no AgentRx, invocar o pipeline com o juiz
o juiz configurado (`JUDGE_MODEL`/`JUDGE_BACKEND`; default gpt-5-mini via Copilot
CLI), e coletar os outputs em CSVs que unam **pergunta + trajetória enviada
+ resultado do juiz**.

## 2. Registro de domínio próprio

- O AgentRx sintetiza invariantes a partir de **policy + schema de tool** de um
  domínio registrado (`agentrx/invariants/domain_registry.py`). Não reusar `tau`.
- Registrar `product_catalog` com:
  - **policy** = derivada dos `success_criteria` das perguntas (regras gerais:
    resposta deve derivar do output da tool; declarar falha quando a tool falha).
  - **schema** da `ProductCatalogSearch` (operações, args, formato de retorno).
- Justificativa: reusar a política do `tau` injetaria restrições erradas e
  contaminaria a checagem de invariantes.

## 3. Invocação do pipeline

- Entrada: uma das trajetórias (`trajectory_telemetry` ou `trajectory_agentrx`).
- Comando base (push-button runner do submódulo):
  `python AgentRx/run.py <trajetoria.json> --domain product_catalog`
- Estágios: ir → static → dynamic → check → judge → report. Saída em
  `AgentRx/runs/<run_name>/`.
- **Juiz**: definido por `.env` (`JUDGE_MODEL`, `JUDGE_BACKEND`). Default sugerido:
  gpt-5-mini via Copilot CLI (cliente já presente em
  `agentrx/llm_clients/copilot_cli.py`); outros backends (azure, trapi) são
  suportados. O modelo/versão usado é gravado no manifesto do run e no decisions
  log. Invariante: juiz ≠ agente e juiz é um modelo capaz.
- **Repetições do juiz**: 3 por trajetória. Convém fixar `run_name` por
  (cenário, braço, julgamento) para rastreio, ex.: `q07_t3_laptop__telemetry__j2`.

## 4. O que coletar de `runs/<run_name>/`

- A classificação do juiz: passo crítico predito + categoria predita (+ justificativa).
- Opcional para diagnóstico: invariantes violados (saída do estágio `check`).
- `collect_agentrx.py` percorre os `run_name`, lê a saída do juiz e cruza com o
  `ground_truth.json` do cenário correspondente.

## 5. CSVs de saída (`data/outputs/`)

### 5.1 `judgements.csv` (linha por julgamento)
Colunas:
`run_id, scenario_id, user_request, arm, judge_idx, gt_step, gt_category,
pred_step, pred_category, step_correct, category_correct, step_distance,
judge_model, agentrx_run_name`

- `arm` ∈ {telemetry, agentrx}; `judge_idx` ∈ {1,2,3}.
- `step_correct` = `pred_step == gt_step`; `category_correct` análogo;
  `step_distance` = |pred_step − gt_step| no espaço de passos do parser.

### 5.2 `trajectory_index.csv` (linha por trajetória enviada)
`run_id, scenario_id, arm, trajectory_path, otel_path, n_steps, sent_at`

- Liga cada julgamento à trajetória bruta que o originou (rastreabilidade).

### 5.3 `scenarios.csv` (linha por cenário)
`scenario_id, user_request, template_id, target_fault_category, injection_node,
expected_answer`

## 6. Agregação para as RQs

- A análise (PRD-06) parte de `judgements.csv`; agrega por `arm` × categoria com
  os 3 julgamentos como repetições, reportando média + IC e testes pareados
  (telemetry vs agentrx) por cenário.

## 7. Critérios de aceite

- Domínio `product_catalog` registrado e `run.py` completa os estágios numa
  trajetória de exemplo, devolvendo passo + categoria.
- `collect_agentrx.py` gera os 3 CSVs sem linhas órfãs (todo julgamento liga a um
  cenário e a uma trajetória).
- Para 1 cenário de teste, é possível rastrear pergunta → trajetória → predição
  ponta a ponta.