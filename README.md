# Replicação AgentRx + OpenTelemetry — MAS simulado

Replicação parcial do **AgentRx** (diagnóstico de falhas em sistemas multiagente) estendida com **telemetria
OpenTelemetry**. Um MAS simulado em LangGraph (Coordinator → Researcher → Tool → Executor → Evaluator) roda perguntas de
catálogo somente-leitura com **injeção scriptada de falha**, gerando um trace OTel bruto por execução. De cada trace
derivam duas trajetórias — uma **com telemetria** (braço A) e outra **estilo-AgentRx** (braço B, prosa fiel) — para
perguntar: a telemetria ajuda o juiz a localizar/classificar a falha?

Leia `AGENTS.md` primeiro, depois `docs/prd/PRD-INDEX.md` e `docs/adr/README.md`.

## Invariantes (não-negociáveis)

- O `.otel.json` bruto é a **única fonte de verdade**; todo o resto é derivado.
- As trajetórias **nunca** vazam o ground truth (`fault.injected`, `experiment.fault*`, caminhos de `faults.py`).
- Os dois braços carregam a **mesma semântica**; diferem só nos campos de telemetria.
- A injeção é **scriptada/determinística**; o renderizador de log é **cego ao gabarito**.

## Instalação

```bash
make install        # ou: uv sync
cp example.env .env
```

Determinismo é o default: `USE_LLM=false`, temperatura 0, sem rede no caminho de geração de dados. O modelo do agente é
parametrizável via `.env` (`AGENT_MODEL`).

Com `USE_LLM=true`, os nós-agente (Coordinator, Researcher, Executor, Evaluator) chamam o modelo do agente em
`AGENT_BASE_URL` (ex.: Ollama em `http://localhost:11434/v1`, com o modelo já baixado). O agente usa **só** as vars
`AGENT_MODEL`/`AGENT_BASE_URL`/`AGENT_API_KEY` — setar `AGENT_BASE_URL` explicitamente (não confiar em `OPENAI_*`, que o
SDK da openai poderia ler do ambiente sem registrar no manifesto). A **injeção de falha continua scriptada** — o LLM só
gera a prosa do passo e a telemetria de tokens. Se o endpoint não responder, o passo cai em fallback determinístico e
registra `agent.llm.failed` no log. **Checagem prática:** `total_tokens > 0` no manifesto/telemetria confirma que o LLM
real foi usado; tokens 0 com `USE_LLM=true` = fallback silencioso por config errada.

## Tutorial — pipeline segregado

Cada passo é idempotente e **valida a própria saída**; não há um alvo "run-all".

| Passo | Comando | Produz | Validador |
| -- | -- | -- | -- |
| 1. Benchmark | `make generate` | `data/benchmark/benchmark_30.json` (6×5 categorias) | `validate-benchmark` |
| 2. Simular MAS | `make simulate` | `data/internal/otel/<id>.otel.json` + `ground_truth/<id>...` | `validate-traces` |
| 3. Derivar braços | `make derive` | `data/internal/trajectory_telemetry/` e `trajectory_agentrx/` | `validate-trajectories` |
| 4. Smoke | `make smoke` | — (5 testes, 1 por falha) | — |
| 5. Qualidade | `make check` | — (format/lint + limite de 200 linhas) | — |

```bash
make generate   # → wrote 30 scenarios
make simulate   # → 30 traces (6 spans cada) + ground truth
make derive     # → 2 trajetórias por trace, sem vazamento, em paridade
make smoke      # → 5 passed (System/Invalid/Misinterpretation/Invention/Plan)
make check      # → ruff + check_file_size OK
```

Os validadores também rodam isolados: `make validate-benchmark`, `make validate-traces`, `make validate-trajectories`.

### Reset antes do experimento

Para começar o experimento do zero (limpar traces/trajetórias/ground truth/logs/manifests de runs de teste):

```bash
make clean-data   # apaga data/internal/{otel,trajectory_*,ground_truth,logs,manifests}
make generate simulate derive   # regenera a baseline determinística
```

`make clean-data` é idempotente e não toca no benchmark nem no catálogo vendorizado. Os artefatos de run seguem
versionados (commite a baseline nova após regenerar).

## Juiz do AgentRx (próxima etapa)

A invocação do juiz é trabalho de uma change seguinte. Pela regra de **não tocar no submódulo AgentRx**, a integração
será em modo **judge-only** sobre a IR canônica que os adapters já emitem (ver `docs/adr/0009-...`). O pacote do MAS
nunca importa o AgentRx; a integração é por arquivos.

## Onde as coisas vivem

- `src/agentrx_otel_poc/` — `benchmark/`, `faults/`, `graph/` (nós + runner), `adapters/` (parser + sanitize + 2
  braços), `telemetry.py`, `tasks.py`.
- `scripts/` — `generate_benchmark.py`, `simulate.py`, `derive_trajectories.py`, `check_file_size.py`.
- `data/external/` (catálogo vendorizado), `data/benchmark/`, `data/internal/` (artefatos por run).
- `docs/prd/` (specs) · `docs/adr/` (decisões arquiteturais) · `tests/` (+ `tests/smoke/`).
