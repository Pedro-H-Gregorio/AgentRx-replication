# AgentRx OTel Minimal PoC

Caso mínimo para o experimento:

- LangGraph com fluxo multiagente: Coordinator, Researcher, ferramenta configurada por task, Executor, Evaluator.
- Quando `USE_LLM=true`, Coordinator, Researcher, Executor e Evaluator fazem chamadas LLM reais. A ferramenta continua
  sendo o ponto controlado de falha.
- Telemetria baseada em OpenTelemetry Python: `Resource`, `Trace`, `Span`, `Event`, `Attributes`, `Status`.
- A task vem de `TASK_ID` e fica descrita em `src/agentrx_otel_poc/tasks.py`.
- Saídas:
  - `data/otel/<run_id>.otel.json`: fonte de verdade em OTel JSON local.
  - `data/agentrx/<run_id>.trajectory.json`: trajetória textual no estilo aceito pelo AgentRx, sem labels de ground
    truth.
  - `data/text_baseline/<run_id>.txt`: baseline textual derivado da mesma telemetria.
  - `data/metrics/<run_id>.metrics.json`: métricas observacionais por etapa para análise com telemetria.
  - `data/ground_truth/<run_id>.ground_truth.json`: labels separados para avaliação do experimento.
  - `data/logs/<run_id>.log`: log padronizado da execução, espelhado também no terminal.

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Rodar sem LLM

```bash
USE_LLM=false TASK_ID=catalog_dell_price_filter FAULT_TYPE=system_timeout RUN_ID=run_001 python scripts/run_minimal.py
```

Para mais detalhes de execução, aumente o nível de log:

```bash
LOG_LEVEL=DEBUG USE_LLM=false TASK_ID=catalog_dell_price_filter FAULT_TYPE=system_timeout RUN_ID=run_001 python scripts/run_minimal.py
```

## Rodar com LLM OpenAI ou OpenAI-compatible

Configure `.env`:

```env
USE_LLM=true
OPENAI_API_KEY=...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

Para endpoint compatível com OpenAI:

```env
OPENAI_BASE_URL=https://sua-url/v1
OPENAI_API_KEY=...
OPENAI_MODEL=nome-do-modelo
```

Com `USE_LLM=true`, as métricas `input_tokens` e `output_tokens` são preenchidas quando o provedor retorna uso de
tokens. Com `USE_LLM=false`, os agentes usam fallback determinístico e esses campos ficam `0`.

`FAULT_TYPE` controla apenas a simulação experimental. Esse valor não é escrito na trajetória AgentRx nem nas métricas
observacionais; o label fica separado em `data/ground_truth`.

## Rodar o AgentRx com a trajetória textual

Depois de gerar `data/agentrx/run_001.trajectory.json`:

```bash
cd AgentRx
python run.py ../data/agentrx/run_001.trajectory.json \
  --domain flash \
  --endpoint copilot \
  --skip-static \
  --skip-dynamic \
  --run-name run_001_diagnosis
```

## Adicionar AgentRx como submodule

```bash
git init
git submodule add https://github.com/microsoft/AgentRx.git external/AgentRx
git commit -m "Add AgentRx submodule"
```

Para clonar depois com submodule:

```bash
git clone --recurse-submodules <seu-repo>
```

Se alguém já clonou sem submodules:

```bash
git submodule update --init --recursive
```

## Organização do experimento

O experimento gera duas visões da mesma execução:

- `data/agentrx/<run_id>.trajectory.json`: versão textual/não estruturada para o AgentRx seguir o caminho mais próximo
  do artigo original.
- `data/otel/<run_id>.otel.json` e `data/metrics/<run_id>.metrics.json`: versão enriquecida com trace, spans, duração,
  status, erro, tokens, entradas/saídas, resposta da ferramenta e avaliação do agente.
- `data/ground_truth/<run_id>.ground_truth.json`: rótulo usado depois para calcular acurácia, sem contaminar a entrada
  do diagnosticador.
