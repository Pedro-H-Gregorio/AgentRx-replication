# Dicionário dos artefatos de dados (manifestos, índice e run dirs)

O que cada arquivo intermediário significa, campo a campo — para replicar ou depurar o experimento sem ler o código. Os
**CSVs de resultado** têm dicionário próprio (PRD-10 + `docs/examples/metrics-reference.md`); aqui ficam os artefatos de
`data/internal/`.

## 1. Manifesto do run do MAS — `data/internal/<mas_id>/manifests/<run_id>.json`

Escrito por `make simulate`, **um por cenário**. Registra a config efetiva do run (reprodutibilidade, PRD-00 §4.1).
Nunca contém ground truth.

| Campo | Significado |
| -- | -- |
| `run_id` / `task_id` | Identificador do run (= id do cenário, PRD-INDEX). |
| `mas_id` | Namespace do corpus (`MAS_ID` ou `AGENT_MODEL` literal; ADR-0013) — a pasta sob `data/internal/`. |
| `use_llm` | O agente narrou com LLM (`true`) ou com template determinístico. |
| `use_llm_strict` | Modo estrito ativo (falha alto em vez de degradar; corpus final). |
| `fallback_steps` | Nº de passos que degradaram de prosa-LLM para template (0 = corpus puro; 0 também com `use_llm=false`). Auditoria: `grep -L '"fallback_steps": 0' data/internal/<mas_id>/manifests/*.json` deve sair vazio na matriz final. |
| `agent_model` / `agent_base_url` | Modelo do agente efetivamente configurado (o MAS é agnóstico de modelo). |
| `llm_temperature` | Temperatura do agente (0 = default determinístico). |
| `otel_service_name` | Nome do serviço no trace OTel. |

## 2. Manifesto do experimento de julgamento — `data/internal/<mas_id>/agentrx/<experiment_id>/manifest.json`

Escrito por `make judge` **no início de cada invocação** — ele reflete a **última sessão**, não a história acumulada (a
história do que existe julgado é o índice + os run dirs).

| Campo | Significado |
| -- | -- |
| `experiment_id` | Derivado da config (`judge-<backend>-<modelo>`), não de timestamp — reexecuções retomam a mesma árvore. |
| `mas_id` | Corpus do MAS que este juiz julgou (ADR-0013). |
| `started_at` | Início da última sessão. |
| `repo_git_sha` / `agentrx_git_sha` | Versões do repo e do submódulo que produziram a sessão. |
| `selection` | A fatia da matriz pedida na CLI (abaixo). |
| `judge_backend` / `judge_model` / `judge_base_url` | Config do juiz (`.env`). O modelo **de fato usado** por rep fica no índice (`effective_model`). |
| `judge_temperature` | Temperatura, ou `"unknown"` quando o backend não a expõe (ex.: Copilot CLI — ameaça declarada, PRD-08 D26). |

### O bloco `selection` (fatia da matriz)

`null`/default = **sem filtro**, não "dado faltando". Tudo `null` + `reps: 3` é exatamente `make judge` sem parâmetros
(matriz completa 30 × 2 × 3).

| Campo | Flag na CLI | `null`/default significa |
| -- | -- | -- |
| `arms` | `--arms` / `ARM=` | ambos os braços |
| `scenarios` | `--scenarios` / `SCENARIOS=` | todos os 30 cenários |
| `fault` | `--fault` / `FAULT=` | todas as 5 categorias |
| `reps` | `--reps` / `REPS=` | 3 (default do artigo, D5) |
| `only_errors` | `ONLY=errors` | rodada normal |
| `force` | `FORCE=1` | pula reps que já têm veredito |

## 3. Índice de reps — `data/internal/<mas_id>/agentrx/<experiment_id>/runs_index.jsonl`

Uma linha por rep, **reconstruído do disco ao final da sessão** (o disco é a verdade; o índice nunca diverge dele).
Consequência prática: uma sessão **interrompida** ainda não tem índice — basta reexecutar `make judge` (a retomada checa
o `run1.json` em disco, não o índice) e, ao final, o índice cobre tudo. `make collect` exige o índice.

| Campo | Significado |
| -- | -- |
| `run_id` / `arm` / `rep` | Coordenada da rep na matriz. |
| `status` | `ok` = julgada nesta sessão; `skipped` = **veredito válido de sessão anterior** (tão bom quanto `ok`; o coletor agrega os dois); `error` = sem veredito (timeout, auth, veredito vazio) — reexecutável com `ONLY=errors`. |
| `run_dir` | Caminho relativo da rep. |
| `effective_model` | Modelo que o backend **de fato** usou (capturado pelo shim; pode diferir do configurado — ex.: `JUDGE_MODEL` vazio no codex). |
| `retries` | Retentativas de transporte do shim (rate-limit) nesta rep. |
| `predicted_category` | Nome completo da categoria dita pelo juiz (taxonomia 0–10) — **nunca nulo quando há veredito**; nulo só significa "sem predição". Fora do escopo (ex.: "Intent-Plan Misalignment") aparece nomeado, e ainda conta como miss. |
| `predicted_in_scope` | `true` se a categoria predita é uma das 5 injetáveis; `false` para vereditos fora do escopo (distingue-os de ausência de predição). |
| `predicted_step`/`raw_failure_cases` | Passo predito (critério per-rep D24) + failures brutas. |
| `gt_category`/`gt_step`/`hit_category`/`hit_step` | Ground truth e acerto — scoring **nosso**, o juiz é cego (D22). Fora do escopo = miss por construção (foge do GT). |

## 4. Run dir de uma rep — `.../<arm>/<run_id>/rep<k>/`

| Arquivo | Versionado? | Significado |
| -- | -- | -- |
| `judge_output/runs/run1.json` | sim | O veredito bruto do AgentRx (fonte das failures). |
| `trajectory_ir.json` | não | Cópia byte-idêntica da trajetória (pré-plantio da IR, D21). |
| `agentrx.log` | não | stdout+stderr do `run.py` (observabilidade da rep). |
| `judge_meta.json` | não | Metadados do shim (`effective_model`, `retries`) propagados ao índice. |

Política de versionamento (D25): do experimento, só `manifest.json`, `runs_index.jsonl` e os `run1.json` vão ao git.
