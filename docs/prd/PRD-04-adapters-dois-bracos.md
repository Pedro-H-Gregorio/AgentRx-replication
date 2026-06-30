# PRD-04 — Artefato OTel, parser e adapters das 2 trajetórias

## 1. Objetivo

Definir o artefato OTel bruto (fonte de verdade) e os adapters que dele derivam as
**2 trajetórias** comparadas no experimento. Separar claramente **parser**
(OTel → estrutura intermediária) de **adapter** (estrutura → formato de saída).

## 2. Artefato bruto: OTel JSON

- Um arquivo `<run_id>.otel.json` por execução base, gerado por `telemetry.py`.
- Contém os spans dos nós (Coordinator, Researcher, Tool, Executor, Evaluator) e
  um span raiz de workflow, com: `experiment.step_index`, `gen_ai.*` (modelo,
  tokens), `duration_ms`, `status`, `events` (incl. `fault.injected`), e o
  conteúdo de entrada/saída de cada passo.
- Regra: **nada é computado fora daqui**; as trajetórias são projeções deste.

## 3. Parser: OTel → IR comum

- `adapters/parser.py`: lê o OTel e produz uma lista ordenada de **passos**
  canônicos, cada um com: `step_index`, `agent_name`, `operation`, `status`,
  `input`, `output`, `tool_name`, `tool_args`, `tool_result`, `events`, e os
  campos de telemetria (`duration_ms`, tokens, `span_id`, `parent_span_id`).
- O parser é único e compartilhado pelos dois adapters → a ordenação e o
  recorte de passos são **idênticos** nos dois braços (evita confundir
  "estrutura" com "ordem diferente").

## 4. Braço A — trajetória com telemetria

- `adapters/trajectory_telemetry.py`: para cada passo, monta o `content` do
  sub-step incluindo o raciocínio/saída **e** as métricas do span
  (`duration_ms`, tokens, `status`, `span_id`, eventos como `fault.injected`).
- Saída: `data/internal/trajectory_telemetry/<run_id>.json`, no schema de entrada
  do AgentRx (ver PRD-05), com as métricas embutidas no campo de conteúdo do passo.

## 5. Braço B — trajetória estilo-AgentRx

- `adapters/trajectory_agentrx.py`: mesmo conjunto de passos, mas o `content`
  descreve o processo em prosa (papel do agente, ação, observação, erro) **sem**
  os campos de telemetria — semelhante às trajetórias sobre as quais o AgentRx
  foi avaliado.
- Saída: `data/internal/trajectory_agentrx/<run_id>.json`.

## 6. Invariante central do experimento

Os dois braços devem carregar a **mesma informação semântica** (mesmos passos,
mesmas ações, mesmos outputs de ferramenta, mesma falha), diferindo **apenas** na
presença/estrutura da telemetria. Caso contrário, mede-se conteúdo, não estrutura.

- Teste de paridade: extrair de A e de B a sequência (agent, operation, status,
  tool_result) e exigir igualdade. Diferença permitida só nos campos de métrica.

## 7. Adapters auxiliares (já existentes, manter)

- `metrics_adapter.py` — tabela por passo (sanidade/observabilidade), não é braço.
- `text_adapter.py` — **redefinir**: o baseline textual de referência é o Braço B
  (prosa fiel), não o `.txt` de 9 linhas atual, que é um espantalho e deve ser
  descontinuado como condição experimental.

## 8. Critérios de aceite

- De 1 `.otel.json` saem A e B sem intervenção manual.
- O teste de paridade (§6) passa para todos os cenários do smoke.
- Ambas as saídas validam contra o schema de entrada do AgentRx (PRD-05).
- O parser é o único ponto que ordena/recorta passos (sem lógica duplicada nos
  adapters).
