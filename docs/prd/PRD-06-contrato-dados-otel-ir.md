# PRD-06 — Contrato de dados: OTel → IR (braços telemetria e AgentRx "puro")

## 1. Objetivo

Especificar, campo a campo: (a) quais dados existem na versão OTel; (b) o mapeamento OTel → IR do AgentRx para o **braço
telemetria**; (c) o mapeamento para o **braço AgentRx "puro"** (formato descrito no artigo). É o contrato que o parser e
os adapters (PRD-04) devem cumprir.

## 2. Restrição central (ler antes de tudo)

A IR canônica do AgentRx por sub-step tem **apenas** `sub_index`, `role`, `content` (string). Não há campo estruturado
para telemetria. Logo, **a telemetria só entra no AgentRx como texto dentro de `content`** — no braço A, como string
JSON (a IR segue com só `role`/`content`; invariante #6). Com o braço A estruturado (JSON, telemetria enriquecida) e o B
em prosa (baseline do artigo), o experimento testa **"o pacote de telemetria estruturada e enriquecida ajuda o juiz vs.
a baseline do artigo?"**. Ameaça à validade de construto: formato e conteúdo mudam juntos no braço A → um eventual
efeito não se decompõe em "formato" vs. "conteúdo" (ADR-0014, PRD-08 D40). Declarar no manuscrito.

IR alvo (de `agentrx/ir/trajectory_ir.py`):

```
{ "trajectory_id": str, "instruction": str,
  "steps": [ {"index": int, "substeps": [ {"sub_index": int, "role": str, "content": str} ]} ] }
```

Entrada aceita pelo loader: `{trajectory_id, instruction, events:[...]}` (um converter de domínio mapeia `events` →
`steps/substeps`).

## 3. Inventário da versão OTel (campos disponíveis por span)

- Identidade/estrutura: `trace_id`, `span_id`, `parent_span_id`, `kind`, `name`, `experiment.step_index`.
- Tempo/custo: `duration_ms`, `gen_ai.usage.{input,output,total}_tokens`, `gen_ai.request.model`.
- Estado: `status.status_code`, `status.description`, `error.type`, `error.message`.
- Semântica do passo: `gen_ai.agent.name`, `gen_ai.operation.name`, `agent.role`, `agent.input_message`,
  `agent.output_message`, `tool.name`, `gen_ai.tool.parameters`, `tool.args_json`, `tool.result_json`,
  `plan.query_json`, `plan.text`, `validation.status`, `validation.reason`, `constraint.violations_json`.
- Infra: `peer.service`, `server.address`, `rpc.system`, `http.request.method`.
- Eventos: `events[].{name, timestamp_unix_ns, attributes}` — inclui `task_delegated`, `tool_call_planned`,
  `dependency_call_failed`, `exception`, `artifact_created`, `validation_failed` e **`fault.injected`**.

## 4. Regras de prevenção de vazamento (ambos os braços)

Estas regras valem para A **e** B; violá-las invalida a comparação.

- **R1 — Remover o ground truth do trace.** O evento `fault.injected` e qualquer atributo `experiment.*` que nomeie a
  categoria/nó injetados **não** podem entrar na trajetória. Eles vivem só no `ground_truth.json`. Caso contrário, o
  braço que os contiver "ganha" por receber a resposta.
- **R2 — Stacktrace limpo na origem, mantido só em A.** A falha de System Failure é levantada na **borda do tool** (fora
  do pacote `faults`), então o `exception.stacktrace` bruto já nomeia só frames de aplicação — nunca `faults.py`/
  `_system_failure`/a categoria (2A, ADR-0014). Ele é surfaceado no bloco `telemetry` do braço A e scrubado
  defensivamente (todo valor com token de injeção — incluindo o pontilhado `faults.` — é descartado). O braço B nunca
  carrega stacktrace.
- **R3 — Telemetria só no braço A** (ver §6).
- **R4 — Paridade semântica.** Os fatos semânticos (§5) devem ser **idênticos** em A e B. As diferenças permitidas são
  (a) o bloco `telemetry`, exclusivo de A, e (b) o **formato** de serialização — A é JSON, B é prosa (baseline do
  artigo; o formato de A faz parte do tratamento, ADR-0014). Verificação: os fatos de A, renderizados como prosa,
  reproduzem B.
- **R5 — Imparcialidade de log.** A redação de cada passo depende só dos dados do passo, nunca do ground truth
  (categoria/nó) nem de o run ser de falha. O renderizador **não recebe** a categoria; o mesmo template gera o caminho
  feliz e o com falha. Sem palavras-chave que denunciem a falha mirada.

## 5. Mapeamento comum (A e B) — vai para `content` nos dois braços

| IR | Origem OTel |
| -- | -- |
| `trajectory_id` | `run_id` |
| `instruction` | `task` / `user_request` |
| `steps[].index` | `experiment.step_index` |
| `substeps[].role` | `gen_ai.agent.name` (ou `agent.role`) |
| `content`: Agent/Operation | `gen_ai.agent.name`, `gen_ai.operation.name` |
| `content`: Status/Observation | derivado de `status` + `error.*` (prosa) |
| `content`: Tool / Contract / Args / Result | `tool.name`, `gen_ai.tool.parameters`, `tool.args_json`, `tool.result_json` (sanitizado por R2) |
| `content`: Plan | `plan.query_json`, `plan.text` |
| `content`: Error | `error.type`, `error.message` |
| `content`: Answer | `agent.output_message` |
| `content`: Validation | `validation.status`, `validation.reason`, `constraint.violations_json` |

Observação: `tool.result_json` e a verdade do Evaluator são **semânticos** — entram nos dois braços (são o que o sistema
observou de fato).

## 6. Mapeamento exclusivo do braço A (telemetria) — bloco `telemetry` no `content` (JSON)

O `content` do braço A é uma **string JSON**: os fatos da §5 mais um objeto `telemetry`:

| Chave em `telemetry` | Origem OTel |
| -- | -- |
| `duration_ms` | `duration_ms` |
| `tokens{input,output,total}` | `gen_ai.usage.*_tokens` |
| `model` | `gen_ai.request.model` |
| `span{span_id,parent_span_id,trace_id}` | ids do span |
| `otel_status`, `kind` | `status.status_code`, `kind` |
| `events[]{name,attributes}` (sem `fault.injected`) | eventos **com atributos** (não só o nome), após R1/R2 |
| `infra{peer_service,rpc_system,http_method}` | atributos de infra |
| `stacktrace` (só em passos de erro) | `exception.stacktrace` limpo na origem (R2) |

A telemetria vive **dentro** da string `content` (JSON), nunca como campo estruturado da IR (invariante #6). O braço B
não tem `telemetry`. AgentRx exige só que `content` seja `str`, sem impor forma — o JSON é uma string válida que o juiz
lê.

## 7. Braço B (AgentRx "puro") — o que NÃO entra

`content` de B contém apenas as linhas da §5 (formato do artigo: papel, operação, observação, tool/args/result, erro,
raciocínio, validação). **Excluídos**: todas as linhas da §6 (duração, tokens, ids de span, status OTel, eventos com
timing, infra). É o baseline textual fiel — substitui o `.txt` de 9 linhas.

## 8. Critérios de aceite

- De 1 `.otel.json` saem A e B; ambos validam contra `validate_ir` do AgentRx.
- **Teste de não-vazamento**: nenhuma trajetória (A ou B) contém `fault.injected`, `experiment.fault`, `faults.py` nem o
  caminho pontilhado `faults.`; `exception.type` aparece só com o nome simples da classe.
- **Teste de paridade semântica**: os fatos de A (JSON, descontado `telemetry`), renderizados como prosa, são idênticos
  ao `content` de B, por passo.
- A diferença A−B é exatamente o bloco `telemetry` e o formato (JSON vs prosa); o conteúdo semântico é o mesmo.
- **Teste de imparcialidade (R5)**: para a mesma pergunta, os passos não-afetados das trajetórias do run sem falha e do
  run com falha são **idênticos** (default, determinístico); com `USE_LLM` on, nenhuma linha contém marcadores da
  categoria. Por estática: o renderizador/adapter não importa nem recebe `target_fault_category`.
