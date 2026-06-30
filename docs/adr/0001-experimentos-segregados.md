# ADR-0001 — Dois experimentos segregados (MAS simulado + TRAIL)

- **Status**: Accepted
- **Data**: 2026-06-27
- **Relacionado**: PRD-00, PRD-09, AGENTS.md

## Contexto

As RQs (telemetria ajuda o juiz a localizar/classificar a falha?) podem ser respondidas com ground truth limpo mas
artificial (MAS com injeção scriptada) ou com traces reais mas ground truth derivado (dataset TRAIL). Cada fonte tem
força e fraqueza opostas. Tentar unificar os dois sob um mesmo formato de campos forçaria normalização e misturaria as
fontes.

## Decisão

Manter **dois experimentos independentes**, com caminhos de execução separados no repositório, respondendo as mesmas RQs
por ângulos complementares. **Não** há normalização cruzada de campos: o MAS usa seus campos (`gen_ai.*`); o TRAIL usa
os seus (OpenInference). Compartilham apenas o submódulo AgentRx.

## Consequências

- Conclusão robusta quando os dois apontam o mesmo sinal; divergência vira discussão, não defeito.
- Custo: dois pipelines, dois conjuntos de adapters e de saídas (`data/outputs/` separados). Maior superfície de
  manutenção.
- O TRAIL traz validade ecológica; o MAS traz controle. Nenhum sozinho fecha o argumento.

## Alternativas descartadas

- **Normalizar tudo a um vocabulário comum**: agregaria os dois num pipeline, mas confundiria "fonte do dado" com
  "formato" e aumentaria o acoplamento.
- **Só o MAS**: perde validade externa (crítica de ambiente de brinquedo).
- **Só o TRAIL**: perde ground truth limpo do passo crítico (derivado de labels).
