# PRD-06 — Contrato de dados: OTel → IR (braços telemetria e AgentRx "puro")

## 1. Objetivo

Especificar, campo a campo: (a) quais dados existem na versão OTel; (b) o
mapeamento OTel → IR do AgentRx para o **braço telemetria**; (c) o mapeamento para
o **braço AgentRx "puro"** (formato descrito no artigo). É o contrato que o parser
e os adapters (PRD-04) devem cumprir.

## 2. Restrição central (ler antes de tudo)

A IR canônica do AgentRx por sub-step tem **apenas** `sub_index`, `role`,
`content` (string). Não há campo estruturado para telemetria. Logo, **a telemetria
só entra no AgentRx como texto dentro de `content`**. O experimento, portanto,
testa "incluir telemetria-como-texto no conteúdo do passo ajuda o juiz?", não
"formato estruturado vs. não estruturado". Declarar isso como ameaça à validade de
construto no manuscrito.

IR alvo (de `agentrx/ir/trajectory_ir.py`):
```
{ "trajectory_id": str, "instruction": str,
  "steps": [ {"index": int, "substeps": [ {"sub_index": int, "role": str, "content": str} ]} ] }
```
Entrada aceita pelo loader: `{trajectory_id, instruction, events:[...]}` (um
converter de domínio mapeia `events` → `steps/substeps`).

## 3. Inventário da versão OTel (campos disponíveis por span)

- Identidade/estrutura: `trace_id`, `span_id`, `parent_span_id`, `kind`,
  `name`, `experiment.step_index`.
- Tempo/custo: `duration_ms`, `gen_ai.usage.{input,output,total}_tokens`,
  `gen_ai.request.model`.
- Estado: `status.status_code`, `status.description`, `error.type`, `error.message`.
- Semântica do passo: `gen_ai.agent.name`, `gen_ai.operation.name`,
  `agent.role`, `agent.input_message`, `agent.output_message`,
  `agent.reasoning_summary`, `tool.name`, `tool.args_json`, `tool.result_json`,
  `validation.status`, `validation.reason`, `constraint.violations_json`.
- Infra: `peer.service`, `server.address`, `rpc.system`, `http.request.method`.
- Eventos: `events[].{name, timestamp_unix_ns, attributes}` — inclui
  `task_delegated`, `tool_call_planned`, `dependency_call_failed`, `exception`,
  `artifact_created`, `validation_failed` e **`fault.injected`**.

## 4. Regras de prevenção de vazamento (ambos os braços)

Estas regras valem para A **e** B; violá-las invalida a comparação.

- **R1 — Remover o ground truth do trace.** O evento `fault.injected` e qualquer
  atributo `experiment.*` que nomeie a categoria/nó injetados **não** podem entrar
  na trajetória. Eles vivem só no `ground_truth.json`. Caso contrário, o braço que
  os contiver "ganha" por receber a resposta.
- **R2 — Sanitizar stacktrace.** O `exception.stacktrace` aponta para
  `faults.py`/`maybe_raise_*`, revelando que a falha é injetada. Remover o
  stacktrace ou apagar caminhos de arquivo que citem o código de injeção.
- **R3 — Telemetria só no braço A** (ver §6).
- **R4 — Paridade semântica.** Os campos da categoria "semântica" (§5) devem ser
  **idênticos** em A e B. Diferença permitida apenas nos campos de telemetria.
- **R5 — Imparcialidade de log.** A redação de cada passo depende só dos dados do
  passo, nunca do ground truth (categoria/nó) nem de o run ser de falha. O
  renderizador **não recebe** a categoria; o mesmo template gera o caminho feliz e
  o com falha. Sem palavras-chave que denunciem a falha mirada.

## 5. Mapeamento comum (A e B) — vai para `content` nos dois braços

| IR | Origem OTel |
|----|-------------|
| `trajectory_id` | `run_id` |
| `instruction` | `task` / `user_request` |
| `steps[].index` | `experiment.step_index` |
| `substeps[].role` | `gen_ai.agent.name` (ou `agent.role`) |
| `content`: Agent/Operation | `gen_ai.agent.name`, `gen_ai.operation.name` |
| `content`: Status/Observation | derivado de `status` + `error.*` (prosa) |
| `content`: Tool / Args / Result | `tool.name`, `tool.args_json`, `tool.result_json` (sanitizado por R2) |
| `content`: Error | `error.type`, `error.message` |
| `content`: Reasoning/Answer | `agent.reasoning_summary`, `agent.output_message` |
| `content`: Validation | `validation.status`, `validation.reason`, `constraint.violations_json` |

Observação: `tool.result_json` e a verdade do Evaluator são **semânticos** — entram
nos dois braços (são o que o sistema observou de fato).

## 6. Mapeamento exclusivo do braço A (telemetria) — só em `content` de A

| Linha de `content` (A) | Origem OTel |
|------------------------|-------------|
| `duration_ms=...` | `duration_ms` |
| `tokens in/out/total=...` | `gen_ai.usage.*_tokens` |
| `model=...` | `gen_ai.request.model` |
| `span_id / parent_span_id / trace_id` | ids do span |
| `otel_status / kind` | `status.status_code`, `kind` |
| `events=[...]` (sem `fault.injected`) | `events[].name` (+ timing), após R1/R2 |
| `peer.service / rpc / http.method` | atributos de infra |

O braço A também pode carregar um bloco `otel{}` paralelo ao `content`, desde que
o conversor de domínio o ignore (a IR só lê `content`). Recomendado: manter tudo
em `content`, pois é o que o juiz efetivamente lê.

## 7. Braço B (AgentRx "puro") — o que NÃO entra

`content` de B contém apenas as linhas da §5 (formato do artigo: papel, operação,
observação, tool/args/result, erro, raciocínio, validação). **Excluídos**: todas
as linhas da §6 (duração, tokens, ids de span, status OTel, eventos com timing,
infra). É o baseline textual fiel — substitui o `.txt` de 9 linhas.

## 8. Critérios de aceite

- De 1 `.otel.json` saem A e B; ambos validam contra `validate_ir` do AgentRx.
- **Teste de não-vazamento**: nenhuma trajetória (A ou B) contém a string
  `fault.injected`, `experiment.fault`, nem caminhos de `faults.py`.
- **Teste de paridade** (liga ao PRD-04 §6): removendo de A as linhas da §6, o
  `content` de A e B fica idêntico por passo.
- A diferença A−B é exatamente o conjunto de campos da §6 (auditável por diff).
- **Teste de imparcialidade (R5)**: para a mesma pergunta, os passos não-afetados
  das trajetórias do run sem falha e do run com falha são **idênticos** (default,
  determinístico); com `USE_LLM` on, nenhuma linha contém marcadores da categoria.
  Por estática: o renderizador/adapter não importa nem recebe `target_fault_category`.