# ADR-0006 — Injeção scriptada + log cego ao gabarito (imparcialidade)

- **Status**: Superseded — consolidado em
  [`0006-injecao-scriptada-renderizacao-cega.md`](0006-injecao-scriptada-renderizacao-cega.md) (mesmo número ADR-0006,
  versão canônica de 2026-06-30). Este é o rascunho anterior (2026-06-27), mantido só por proveniência; a decisão
  vigente e o texto completo estão no arquivo canônico.
- **Data**: 2026-06-27
- **Relacionado**: PRD-03, PRD-06, AGENTS.md (regra 7)

## Contexto

A falha é injetada de forma scriptada no nó-alvo, o que dá ground truth limpo. Mas surge um viés sutil: se o código que
gera os logs "souber" qual é a categoria-alvo do cenário, pode escrever os logs do caminho com falha de um jeito que os
denuncia (palavras-chave, estrutura diferente). Aí o juiz e a telemetria acertam por **vazamento estilístico**, não por
mérito — o resultado fica inflado e inválido.

## Decisão

A injeção é scriptada e determinística no nó. A **redação de log/telemetria de um passo depende só dos dados daquele
passo** — nunca da `target_fault_category`, do `injection_node` nem de o run ser de falha. O renderizador **não recebe**
a categoria como argumento; o mesmo template gera o caminho feliz e o com falha.

## Consequências

- O viés fica estruturalmente impossível: sem acesso ao gabarito, o renderizador não tem como escrever para ele.
- Cobrança por teste: igualdade dos passos não-afetados entre run sem falha e com falha (default, agente
  determinístico); por estática, o renderizador não importa a categoria. Com `USE_LLM` ligado, cair para o teste fraco
  (ausência de marcadores).
- Limita "embelezar" logs por categoria — intencional.

## Alternativas descartadas

- **Confiar na instrução textual de imparcialidade** sem teste: regra não testada não é regra; o viés voltaria
  silenciosamente.
- **Só o teste fraco (lista de termos proibidos)**: tem ponto cego (só pega o que está na lista). O teste forte de
  igualdade é preferível quando o determinismo permite, por não depender de adivinhar marcadores.
