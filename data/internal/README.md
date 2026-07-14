# Artefatos internos

Este diretório guarda o corpus intermediário por modelo do MAS. `make simulate` cria o trace OTel, labels, logs e
manifestos; `make derive` cria as trajetórias; `make judge` acrescenta vereditos do AgentRx. O namespace evita que
modelos ou configurações diferentes se sobrescrevam.

```text
data/internal/<mas_id>/
├── otel/<run_id>.otel.json
├── ground_truth/<run_id>.ground_truth.json
├── trajectory_telemetry/<run_id>.json
├── trajectory_agentrx/<run_id>.json
├── logs/<run_id>.log
├── manifests/<run_id>.json
└── agentrx/<judge_id>/
    ├── manifest.json
    ├── runs_index.jsonl
    └── <arm>/<run_id>/rep<k>/
```

`<mas_id>` é `MAS_ID`, quando definido, ou `AGENT_MODEL`; `<judge_id>` deriva da configuração do juiz. O trace OTel
bruto é a fonte de verdade para trajetórias. Ground truth serve ao scoring local e nunca é enviado nas trajetórias ao
juiz.

| Etapa | Produtor | Validação |
| -- | -- | -- |
| Corpus MAS | `make simulate` | `make validate-traces` |
| Trajetórias A/B | `make derive` | `make validate-trajectories` |
| Matriz do juiz | `make judge` | `make validate-judge` |

## Manifesto do run do MAS

`manifests/<run_id>.json` é escrito por `make simulate`, um por cenário. Registra configuração efetiva para reprodução e
não contém ground truth.

| Campo | Significado |
| -- | -- |
| `run_id` / `task_id` | Identificador do cenário. |
| `mas_id` | Namespace do corpus. |
| `use_llm` | Se a prosa dos passos veio de LLM. |
| `use_llm_strict` | Se o run aborta em vez de usar fallback. |
| `fallback_steps` | Passos que caíram para template; deve ser zero no corpus LLM final. |
| `agent_model` / `agent_base_url` | Modelo e endpoint efetivamente configurados. |
| `llm_temperature` | Temperatura do agente. |
| `otel_service_name` | Nome do serviço no trace. |

## Manifesto do experimento de julgamento

`agentrx/<judge_id>/manifest.json` é reescrito no início de cada invocação de `make judge`; descreve a última sessão. A
história de reps válidas está no índice.

| Campo | Significado |
| -- | -- |
| `experiment_id` | ID derivado da configuração do juiz, sem timestamp. |
| `mas_id` | Corpus avaliado pelo juiz. |
| `started_at` | Início da última sessão. |
| `repo_git_sha` / `agentrx_git_sha` | Versões que produziram a sessão. |
| `selection` | Filtros da matriz. |
| `judge_backend` / `judge_model` / `judge_base_url` | Configuração solicitada ao juiz. |
| `judge_temperature` | Temperatura, ou `unknown` quando o backend não a expõe. |

Em `selection`, `null` significa sem filtro: `arms`, `scenarios` e `fault` usam todo o conjunto; `reps` usa o padrão.
`only_errors` e `force` correspondem a `ONLY=errors` e `FORCE=1`.

## Índice de repetições

`agentrx/<judge_id>/runs_index.jsonl` tem uma linha por rep e é reconstruído do disco ao final da sessão. `ok` e
`skipped` têm veredito aproveitável; `error` não tem e pode ser refeito com `ONLY=errors`.

| Campo | Significado |
| -- | -- |
| `run_id` / `arm` / `rep` | Coordenada da repetição na matriz. |
| `status` | `ok`, `skipped` ou `error`. |
| `run_dir` | Caminho relativo da rep. |
| `effective_model` | Modelo de fato servido pelo backend. |
| `retries` | Retentativas de transporte da rep. |
| `predicted_category` / `predicted_in_scope` | Categoria relatada e se está nas cinco injetáveis. |
| `predicted_step` / `raw_failure_cases` | Predição e failures brutas do juiz. |
| `gt_category` / `gt_step` / `hit_category` / `hit_step` | GT e acertos calculados localmente; o juiz é cego ao GT. |

## Arquivos de uma repetição

Cada `agentrx/<judge_id>/<arm>/<run_id>/rep<k>/` contém:

| Arquivo | Versionado | Significado |
| -- | -- | -- |
| `judge_output/runs/run1.json` | sim | Veredito bruto do AgentRx. |
| `trajectory_ir.json` | não | Cópia da trajetória enviada antes do plantio da IR. |
| `agentrx.log` | não | Saída e erro do processo do juiz. |
| `judge_meta.json` | não | Metadados do shim, como modelo efetivo e retries. |

Somente manifestos, índice e `run1.json` são versionados do experimento. Os CSVs derivados deste conteúdo estão em
[resultados](../experiment/results/README.md).
