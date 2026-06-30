# ADR-0010 — Decomposição do MAS em pacotes, limite de 200 linhas e pipeline segregado

- **Status**: Accepted
- **Data**: 2026-06-30
- **Relacionado**: PRD-01, PRD-03, PRD-04; change `build-simulated-mas`

## Contexto

O esqueleto concentrava o MAS num `graph.py` de 715 linhas. O repositório é de ciência aberta e mira **handoff alto**:
qualquer pessoa ou agente novo precisa retomar sem reconstruir contexto — o que exige legibilidade, módulos pequenos e
etapas testáveis isoladamente.

## Decisão

1. **Limite de 200 linhas** por arquivo em `src/`, `scripts/`, `tests/`, imposto em `make check`
   (`scripts/check_file_size.py` + `tests/test_file_size.py`).
2. **Decomposição em pacotes coesos**: `faults/` (operadores), `graph/` (`context`, `spans`, `nodes/`, `builder`,
   `runner`), `adapters/` (`parser`, `sanitize`, `content_lines`, `ir`, dois braços), `benchmark/` (`catalog`,
   `templates`, `generator`).
3. **Pipeline segregado** em passos idempotentes do Makefile — `generate`, `simulate`, `derive` — cada um com seu
   validador (`validate-benchmark`, `validate-traces`, `validate-trajectories`), **sem** um alvo "run-all", documentado
   como tutorial no `README.md`.

## Consequências

- (+) Diffs pequenos e revisáveis; etapas testáveis em isolamento; onboarding rápido.
- (+) A regra de 200 linhas impede o monólito reaparecer.
- (−) Mais arquivos para navegar e mais imports entre módulos.

## Alternativas descartadas

- Manter `graph.py` monolítico com exceção ao limite: fere a própria regra.
- Um único `make run` orquestrando tudo: mais difícil de testar etapa a etapa.
