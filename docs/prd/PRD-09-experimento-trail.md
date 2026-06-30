# PRD-09 — Experimento TRAIL (braço de validade ecológica)

## 1. Objetivo e segregação

Segundo experimento, **independente** do MAS simulado. Avalia as mesmas RQs
(telemetria ajuda o juiz a localizar/classificar a falha?) sobre **traces reais**
do dataset TRAIL. Os dois experimentos **não compartilham normalização**: o TRAIL
usa seus próprios campos nativos (OpenInference); o MAS usa os seus (`gen_ai.*`).
Cada um tem seu caminho de execução. Compartilham apenas o submódulo AgentRx.

Por que vale: o MAS dá ground truth limpo mas artificial; o TRAIL dá traces reais
com telemetria real, ao custo de ground truth derivado. Conclusão robusta = mesmo
sinal nos dois; divergência vira discussão (ver PRD-00).

## 2. Fonte, proveniência e LICENÇA (atenção)

- Dataset: `PatronusAI/TRAIL` (Hugging Face), arquivos `.parquet` brutos.
- Local no repo: `data/external/TRAIL/*.parquet` (como baixado, sem modificar).
- **TRAIL é GATED.** Termos: não re-hospedar fora de repo gated/privado; uso só
  para avaliação/benchmark. Logo: **os `.parquet` NÃO são versionados** num repo
  público — entram no `.gitignore`. Versiona-se apenas: `scripts/trail/fetch.py`
  (instruções/identificador de versão), o `NOTICE.md` e as saídas derivadas que
  não reproduzam o dataset (métricas/CSVs agregados). Registrar a versão/revisão
  do dataset usada.

## 3. Estrutura do dataset (verificada)

Dois parquet (GAIA ~117, SWE ~31). Cada linha: `trace` (str JSON) e `labels` (str JSON).

`trace` = `{trace_id, spans:[...]}`. Cada span é uma **árvore** (`child_spans`),
com: `span_id`, `parent_span_id`, `trace_id`, `timestamp`, `span_name`,
`span_kind`, `service_name`, `duration`, `status_code`, `status_message`,
`events`, `logs`, `links`, `resource_attributes`, `span_attributes`.

`span_attributes` (OpenInference): `openinference.span.kind` (LLM/TOOL/CHAIN/AGENT),
`input.value`, `output.value`, `llm.model_name`, `llm.token_count.{prompt,completion,total}`,
`llm.invocation_parameters`, `llm.input_messages.N.message.{role,content}`,
`llm.output_messages.N.message.{role,content}`.

`labels` = `{trace_id, errors:[{category, location, evidence, description, impact}], scores:{...}}`.
`location` é um **span_id**; `impact` ∈ {LOW,MEDIUM,HIGH}; **não há** "erro crítico"
eleito (multi-erro); taxonomia própria do TRAIL.

## 4. Telemetria e custo (presentes)

Confirmado por inspeção: `duration` e `status_code` em todos os spans; tokens
(`llm.token_count.*`) e `llm.model_name` nos spans de LLM; hierarquia via
`parent_span_id`; `events`/`logs` (esparsos). **Custo** não é campo explícito, mas
é **derivável** de tokens + modelo. Isso atende ao alvo do experimento.
Observação: TRAIL não tem evento de falha injetada — a regra de não-vazamento do
PRD-06 não se aplica aqui (a falha é anotada, não injetada).

## 5. Pipeline do experimento TRAIL (caminho próprio)

```
data/external/TRAIL/*.parquet
  └─ scripts/trail/extract.py    → por-trace: {trace_id, tree, errors, scores}
       └─ src/trail_experiment/parser.py  → árvore → lista plana de passos
            ├─ adapter_telemetry → trajetória COM telemetria (campos TRAIL nativos)
            └─ adapter_pure      → trajetória SEM telemetria (estilo-AgentRx)
                 └─ AgentRx (juiz) ×3  → collect_trail.py → data/outputs/trail/
```

Mantém o mesmo conceito de **2 braços** do MAS, mas com adapters próprios e campos
nativos do TRAIL. Sem normalização cruzada.

## 6. Decisões fixadas (parametrizáveis)

- **Achatamento árvore→passos**: DFS por `timestamp` de início (default). Cada span
  vira um passo; `index` = ordem do DFS. Configurável (ex.: só folhas).
- **Erro crítico** a partir do multi-erro: primeiro erro `HIGH` em ordem temporal
  (default). Declarar como heurística e ameaça à validade (PRD-00 §6).
- **Mapa de taxonomia** TRAIL→AgentRx: tabela explícita versionada; categorias sem
  correspondência limpa marcadas como tal. Métrica de localização (por passo)
  reportada à parte, pois independe da taxonomia.

## 7. AgentRx para o TRAIL (difere do MAS)

Traces do TRAIL (GAIA/SWE) **não têm policy de domínio** como o `product_catalog`.
Default: rodar o AgentRx em modo **judge-only** (pular static/dynamic invariants)
para classificar passo/categoria sem sintetizar invariantes de policy inexistente.
Alternativa: domínio genérico mínimo. Registrar a escolha no decisions log.

## 8. Localização e ground truth

- `location` (span_id) → `step_index` pelo mesmo mapa do parser (§6).
- Sucesso/erro vem dos `labels`; não há resposta computável como no MAS.
- A métrica de passo crítico depende da regra do §6 → é acurácia-relativa-à-regra,
  não ao TRAIL. Declarar. A métrica "localizou algum erro real?" é limpa.

## 9. Critérios de aceite

- `scripts/trail/extract.py` lê os parquet e emite um registro por trace.
- De cada trace saem as 2 trajetórias; ambas validam contra `validate_ir`.
- Teste de paridade: removendo a telemetria do braço com telemetria, o `content`
  iguala o do braço puro (mesma diff auditável do PRD-06, com campos TRAIL).
- `.parquet` não aparece no git; `NOTICE.md` + `fetch.py` presentes.
- `collect_trail.py` gera CSVs em `data/outputs/trail/`, separados do MAS.
- O mapa de taxonomia TRAIL→AgentRx está versionado e é auditável.
