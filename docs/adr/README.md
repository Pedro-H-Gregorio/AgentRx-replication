# Architecture Decision Records (ADR)

Memória arquitetural durável. Sessões de chat são apagadas; as decisões estruturais ficam **aqui**, concisas e datadas,
para qualquer pessoa ou agente retomar sem reconstruir o contexto.

## Quando escrever um ADR (e quando não)

- **ADR (aqui)**: decisão **arquitetural/estrutural** com impacto duradouro — fronteiras de módulo, formato de dados,
  fonte de verdade, integração entre sistemas, invariantes de validade.
- **PRD-08 (`docs/prd/PRD-08`)**: decisão de **método/parâmetro** do experimento — número de cenários, modelo default,
  categorias, repetições. Tabela enxuta.
- Regra de bolso: "muda a estrutura do sistema?" → ADR. "ajusta um valor do experimento?" → PRD-08.

## Formato

Um arquivo por decisão, `NNNN-titulo-curto.md`, seguindo `0000-template.md`: Status · Contexto · Decisão · Consequências
· Alternativas descartadas. Status ∈ {Proposed, Accepted, Superseded by ADR-NNNN, Deprecated}. ADRs não são reescritos:
se a decisão muda, crie um novo ADR que **supersede** o anterior.

## Índice (decisões correntes)

| ADR | Título | Status | Detalhe em |
| -- | -- | -- | -- |
| 0001 | Dois experimentos segregados (MAS simulado + TRAIL), sem normalização cruzada de campos | Accepted | PRD-00, PRD-09 |
| 0002 | Trace OTel bruto é a fonte única de verdade; demais artefatos são derivados determinísticos | Accepted | PRD-01, PRD-04 |
| 0003 | Telemetria entra na IR do AgentRx como texto no `content` (IR só tem role/content) | Accepted | PRD-06 |
| 0004 | AgentRx como submódulo, integrado por arquivos; MAS nunca o importa; domínio `product_catalog` próprio | Accepted | PRD-05 |
| 0005 | Dois braços de trajetória (com telemetria vs. "puro") derivados de um trace | Accepted | PRD-04, PRD-06 |
| 0006 | Injeção scriptada determinística + renderização de log cega ao gabarito (imparcialidade) | Accepted | PRD-03, PRD-06 |
| 0007 | Modelos do agente e do juiz parametrizáveis via `.env`; invariante agente ≠ juiz | Accepted | PRD-00, PRD-05 |
| 0008 | Catálogo tau-bench vendorizado (MIT); dataset TRAIL é gated e NÃO versionado | Accepted | PRD-01, PRD-09 |
| 0009 | Integração com o AgentRx em modo judge-only com IR canônica; registro de domínio `product_catalog` adiado | Accepted | PRD-05, PRD-06, ADR-0004 |
| 0010 | Decomposição do MAS em pacotes, limite de 200 linhas por arquivo e pipeline segregado | Accepted | PRD-01, PRD-04 |
| 0011 | Fronteira de integração com o juiz por interposição do binário do Copilot CLI (backend = qualquer shim; submódulo intocado) | Accepted | PRD-05, PRD-08, ADR-0009 |
| 0012 | Produtos do experimento em `data/experiment/` (separados dos intermediários de `data/internal/`); `data/outputs/` abandonado | Accepted | PRD-01, PRD-05, PRD-07, PRD-10, ADR-0002 |

ADRs com arquivo completo: 0006, 0009, 0010, 0011, 0012. Os demais estão registrados acima e detalhados no PRD apontado;
expanda para arquivo próprio ao revisitá-los.

Nota: o ADR-0006 tem dois arquivos históricos; o canônico é `0006-injecao-scriptada-renderizacao-cega.md` (2026-06-30).
O `0006-injecao-scriptada-log-imparcial.md` (2026-06-27) é o rascunho anterior, marcado como Superseded/consolidado.
