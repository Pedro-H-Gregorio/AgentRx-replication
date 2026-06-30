# ADR-0006 — Injeção scriptada determinística + renderização de log cega ao gabarito

- **Status**: Accepted
- **Data**: 2026-06-30
- **Relacionado**: PRD-03, PRD-06; change `build-simulated-mas`

## Contexto

A falha precisa de ground truth cristalino (qual passo e qual categoria) e as duas trajetórias derivadas não podem vazar
esse gabarito. Se o texto de log/telemetria de um passo "souber" a categoria mirada, o juiz recebe a resposta de graça e
a comparação entre braços deixa de medir estrutura.

## Decisão

A injeção é **scriptada e determinística** no nó-alvo (não provocada por prompt). O renderizador de passo recebe
**apenas dados do span** — nunca `target_fault_category` nem `injection_node`. O evento `fault.injected` (com `category`
e `node`) é gravado **somente** no OTel bruto e removido das trajetórias pelos adapters (R1/R2). O mesmo template serve
o caminho feliz e o com falha (R5, imparcialidade na fonte).

## Consequências

- (+) Ground truth por construção, independente da competência do agente.
- (+) A diferença entre os braços mede estrutura/telemetria, não conteúdo vazado.
- (−) O teste fraco de R5 (com `USE_LLM` ligado) depende de uma lista de termos proibidos por categoria — adiado; o
  default determinístico usa o teste forte (passos anteriores à injeção idênticos).

## Alternativas descartadas

- Injeção por modificação de prompt: suja o ground truth (a falha passa a depender do LLM), por isso fica só como
  alternativa exploratória.
- Renderizador ciente da categoria para "enriquecer" o texto: vaza o gabarito.
