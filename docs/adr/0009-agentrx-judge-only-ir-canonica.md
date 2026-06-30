# ADR-0009 — Integração com o AgentRx em modo judge-only com IR canônica

- **Status**: Accepted
- **Data**: 2026-06-30
- **Relacionado**: PRD-05, PRD-06; ADR-0004; change `build-simulated-mas`

## Contexto

A regra corrente do projeto proíbe modificar o submódulo AgentRx. Registrar um domínio `product_catalog` próprio
(ADR-0004) exigiria editar `agentrx/invariants/domain_registry.py` e `agentrx/ir/trajectory_ir.py`. As RQs medem
**localização + categoria do passo crítico**, que é trabalho do estágio `judge` do AgentRx — não dos invariantes
`static`/`dynamic`, que dependem de uma policy de domínio.

## Decisão

Os adapters emitem a **IR canônica** do AgentRx (`trajectory_id`, `instruction`,
`steps[].substeps[]{sub_index, role, content}`) e a integração com o juiz roda em modo **judge-only**
(`--skip-static --skip-dynamic`). O registro do domínio `product_catalog` fica **adiado** enquanto valer a regra de não
tocar no AgentRx. A validade da IR é verificada importando `validate_ir` **apenas nos testes** (o pacote do MAS nunca
importa o AgentRx).

## Consequências

- (+) AgentRx intocado; o pipeline de dados (benchmark → traces → 2 braços) é completo sem editar o submódulo.
- (+) Ambos os braços validam contra `validate_ir` sem converter de domínio.
- (−) Perde-se a checagem de invariantes (`static`/`dynamic`) — diagnóstico extra, fora das RQs. Declarar como ameaça à
  validade.
- (−) A fiação fim-a-fim do `run.py` (invocação do juiz) é trabalho de change futura (C6).

Relaciona-se ao **ADR-0004 sem revogá-lo**: se a regra de não tocar no AgentRx mudar, registrar o domínio
`product_catalog` volta à mesa (novo ADR que o supersede).

## Alternativas descartadas

- Registrar `product_catalog` dentro do AgentRx (ADR-0004): viola a regra atual.
- Reusar `--domain magentic`: injeta uma policy errada e contamina os invariantes.
