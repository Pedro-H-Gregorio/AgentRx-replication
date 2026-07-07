# ADR-0015 — Contexto de execução no passo da causa

- **Status**: Accepted
- **Data**: 2026-07-06
- **Relacionado**: PRD-03, PRD-06, PRD-08 (D42); ADR-0002, ADR-0005, ADR-0006, ADR-0014; change
  `complete-execution-context`

## Contexto

A auditoria dos resultados mostrou que duas categorias não eram localizáveis no próprio passo da causa:

- em **Invalid Invocation**, o Researcher gravava os args planejados, mas não o contrato da operação da tool; a
  invalidez só aparecia quando a Tool rejeitava a chamada no passo seguinte;
- em **Instruction/Plan Adherence Failure**, o Coordinator decidia uma query violada, mas o span não carregava essa
  query; a violação só aparecia nos args que o Researcher consumia depois.

O trace OTel bruto é a fonte única de verdade, e as duas trajetórias derivadas precisam carregar os mesmos fatos
semânticos. Logo, contexto necessário para julgar um passo não pode ser inventado no adapter nem restrito ao braço de
telemetria.

## Decisão

Todo passo que toma uma decisão passível de julgamento deve registrar, no próprio span, o contrato/contexto contra o
qual essa decisão será avaliada:

- o Researcher grava `gen_ai.tool.parameters` como JSON do contrato estático da operação (`catalog.search` ou
  `catalog.get_details`);
- o Coordinator grava `plan.query_json` e `plan.text` depois de decidir a query/plan, incluindo a mutação causada por
  uma injeção no próprio Coordinator.

Esses atributos são tratados como fatos semânticos comuns: o parser os extrai para `ParsedStep`, `semantic_fields`
alimenta tanto o braço A (JSON + telemetria) quanto o braço B (prosa). O contrato é estático e idêntico entre happy e
fault; a query só difere do caminho feliz quando o Coordinator é o nó injetado.

## Consequências

- Invalid Invocation e Plan Adherence passam a ter contexto observável no passo da causa, sem depender do sintoma no
  passo seguinte.
- A baseline também recebe os novos fatos, preservando paridade semântica; a diferença A/B continua sendo formato +
  bloco `telemetry`.
- O corpus derivado muda ao regenerar trajetórias; os vereditos antigos não medem essa instrumentação.
- A mistura `gen_ai.tool.parameters` com `tool.*` custom é temporária e será resolvida em um passe futuro de
  conformidade OTel GenAI.
- O campo morto `agent.reasoning_summary=""` é removido; raciocínio fabricado não vira fato de execução.

## Alternativas descartadas

- **Gravar o contrato/query só no braço A:** tornaria a melhoria uma vantagem exclusiva da telemetria, mas a falha era
  falta de contexto semântico que também afetava a baseline.
- **Derivar contrato/query no adapter:** violaria a fonte única de fatos; o adapter deve apenas transformar o trace.
- **Renomear todos os atributos `tool.*` agora:** escopo maior, sem necessidade para localizar as duas falhas.
- **Consertar Invention nesta change:** mudaria o operador e o desenho experimental; fica como ameaça à validade
  documentada no PRD-08.
