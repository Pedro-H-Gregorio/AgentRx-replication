# PRD-08 — Decisions log

Registro cronológico de decisões de método (open science). Cada entrada: data, decisão, justificativa, alternativas
descartadas. Acrescentar ao final; não reescrever o histórico.

| # | Decisão | Justificativa | Descartado |
| -- | -- | -- | -- |
| D1 | Injeção de falha **scriptada/determinística** | Ground truth de passo/categoria cristalino; não depende da competência do agente | Injeção via prompt no LLM (mantida só como alternativa exploratória) |
| D2 | Agente = **Llama3.1-8B local** | É o que roda na máquina; com injeção scriptada a competência importa pouco | Modelo forte como agente (custo/infra) |
| D3 | Juiz = **gpt-5-mini via Copilot CLI** | É forte o bastante e há cliente pronto no submódulo | 8B como juiz (derrubaria o desempenho) |
| D4 | **2 braços** derivados de 1 OTel bruto | Isola "estrutura" como fator; bruto único garante paridade semântica | 4 representações (excesso de fatores) |
| D5 | Agente roda **1×/cenário**; juiz **3×/trajetória** | Agente determinístico → variância só no juiz; ×3 espelha o AgentRx | ×5 no juiz (sem ganho frente a ×3) |
| D6 | **30 cenários** (6 por categoria) | Balanceamento e poder via categoria×repetição | 5/categoria (25); todas as 9 categorias |
| D7 | **5 categorias** de falha | Injetáveis com ground truth limpo e nativas do AgentRx | Guardrails, Under-specified, Intent Not Supported, Intent-Plan Misalignment |
| D8 | Domínio **`product_catalog` próprio** no AgentRx | Policy/schema corretos; evita contaminação | Reusar domínio `tau` |
| D9 | Catálogo do **tau-bench v1**, commit `6f4b718...` | `products.json` standalone; proveniência limpa; contemporâneo do AgentRx | Catálogo do τ³ (db.json com users/orders embutidos) |
| D10 | Baseline textual = **Braço B (prosa fiel)** | Mesma informação do braço A, difere só na forma | `.txt` de 9 linhas (espantalho) |
| D11 | Perguntas **single-turn somente-leitura, construídas por template** | Tasks do τ-bench são transacionais/multi-turno (0 read-only) | Selecionar tasks do τ-bench; sintetizar dados também |

## Decisões em aberto (resolver antes do M5)

- Quantidade exata de cenários (30 vs 25) — assumido 30.
- Tratamento de runs com erro emergente do 8B além do injetado: descartar ou sinalizar? (relevante só se o agente usar
  LLM em passos não-críticos).
- Métrica primária para reportar nas RQs (acurácia de passo vs distância de passo).
