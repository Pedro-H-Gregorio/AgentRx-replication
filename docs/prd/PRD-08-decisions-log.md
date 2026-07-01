# PRD-08 — Decisions log

Registro cronológico de decisões de método (open science). Cada entrada: data, decisão, justificativa, alternativas
descartadas. Acrescentar ao final; não reescrever o histórico.

| # | Decisão | Justificativa | Descartado |
| -- | -- | -- | -- |
| D1 | Injeção de falha **scriptada/determinística** | Ground truth de passo/categoria cristalino; não depende da competência do agente | Injeção via prompt no LLM (mantida só como alternativa exploratória) |
| D2 | Modelo do agente **parametrizável** (`AGENT_MODEL`); default Llama3.1-8B local | É o que roda na máquina; com injeção scriptada a competência importa pouco; trocável por `.env` | Fixar um único modelo no código |
| D3 | Modelo do juiz **parametrizável** (`JUDGE_MODEL`/`JUDGE_BACKEND`); default gpt-5-mini via Copilot CLI | Há cliente pronto; invariante é juiz capaz e ≠ agente, não um modelo específico | Hardcode do juiz; 8B como juiz |
| D4 | **2 braços** derivados de 1 OTel bruto | Isola "estrutura" como fator; bruto único garante paridade semântica | 4 representações (excesso de fatores) |
| D5 | Agente roda **1×/cenário**; juiz **3×/trajetória** | Agente determinístico → variância só no juiz; ×3 espelha o AgentRx | ×5 no juiz (sem ganho frente a ×3) |
| D6 | **30 cenários** (6 por categoria) | Balanceamento e poder via categoria×repetição | 5/categoria (25); todas as 9 categorias |
| D7 | **5 categorias** de falha | Injetáveis com ground truth limpo e nativas do AgentRx | Guardrails, Under-specified, Intent Not Supported, Intent-Plan Misalignment |
| D8 | Domínio **`product_catalog` próprio** no AgentRx | Policy/schema corretos; evita contaminação | Reusar domínio `tau` |
| D9 | Catálogo do **tau-bench v1**, commit `6f4b718...` | `products.json` standalone; proveniência limpa; contemporâneo do AgentRx | Catálogo do τ³ (db.json com users/orders embutidos) |
| D10 | Baseline textual = **Braço B (prosa fiel)** | Mesma informação do braço A, difere só na forma | `.txt` de 9 linhas (espantalho) |
| D11 | Perguntas **single-turn somente-leitura, construídas por template** | Tasks do τ-bench são transacionais/multi-turno (0 read-only) | Selecionar tasks do τ-bench; sintetizar dados também |
| D12 | **Imparcialidade de log** + teste (forte: igualdade de passos não-afetados, default determinístico; fraco: ausência de marcadores se `USE_LLM` on) | Evita vazamento estilístico que faria juiz/telemetria acertar por viés, não por mérito; renderizador não vê o gabarito | Renderizador que recebe a categoria-alvo para "enfeitar" o log |
| D13 | `user_request` e logs **em inglês**; tipos/opções/preços derivados do catálogo tau-bench (unidade do próprio catálogo) | Casa com o catálogo vendorizado e com o juiz; evita "Dell/BRL" inventado do esqueleto antigo | pt-BR/BRL do `run_001` antigo (descartado) |
| D14 | Filtro de **higiene de erro emergente** do agente **adiado** (YAGNI); declarado como ameaça à validade | Só importa com `USE_LLM` on no agente; default é determinístico; investigar com o AgentRx em C6 | Implementar o filtro já agora (código morto no default) |
| D15 | **Evaluator fraco**: valida só a presença de evidência da tool, não a corretude da resposta | Modela um avaliador realista que não pega erros semânticos; faltas de superfície (System/Invalid) → `FAILED`, mas Misinterpretation/Invention/Plan **propagam** com a resposta errada visível na trajetória (cabe ao **juiz** localizá-las, não ao MAS). Ameaça à validade declarada | Evaluator "onisciente" comparando contra `expected_answer` (marcaria quase tudo `FAILED`, irreal e enfraqueceria o sinal das RQs) |
| D16 | **Invention** operacionalizada como fabricação ungrounded (a resposta cita um registro inexistente, `item 0000000000`), distinta de **Misinterpretation** (mis-seleção de um item **real** da evidência) | A tool **não** é forçada a retornar vazio porque isso exigiria o nó Tool conhecer a categoria-alvo (viola R5/Regra #7) ou mover a injeção para fora do Executor (viola o nó de injeção do PRD-00 §3). A distinção fica testável: Invention referencia item ausente da evidência; Misinterpretation referencia item presente | Tornar a tool vazia/erro para Invention (exemplo literal do PRD-03 §4.4) — incompatível com R5 |
| D17 | Remover **já** o scaffold do juiz de `llm.py` (`invoke_llm`/`summarize_with_llm`/`build_llm`/`parse_json_object`) e os campos `openai_*` de `Settings` | Código morto (0 chamadores) deixado pelo refactor; será reintroduzido limpo no C6 junto do juiz | Manter como placeholder (confunde a config e cria risco de "funcionar por acaso" via env da openai) |
| D18 | Remover `adapters/metrics_adapter.py` | 143 linhas mortas (0 referências); parser + 2 braços já cobrem a derivação | Ligá-lo como "tabela de sanidade" do PRD-04 §7 (uso não demandado, YAGNI) |
| D19 | `make clean-data` para reset + **seguir versionando** os artefatos de run | Reset idempotente antes do experimento; baseline auditável fica no git | Gitignorar os artefatos de run (perderia a baseline versionada) |
| D20 | Corrigir a reprodutibilidade da config do agente **só via `.env`/docs** (usar `AGENT_*` explícito; `example.env` sem `OPENAI_*`) | Endurecer o código (gravar base_url efetivo no manifesto / falhar alto no fallback) cabe melhor quando o juiz entrar (C6); docs bastam agora | Endurecer `agent_llm`/manifesto já agora (fora do escopo desta limpeza) |

## Decisões em aberto (resolver antes do M5)

- Quantidade exata de cenários (30 vs 25) — assumido 30.
- Tratamento de runs com erro emergente do 8B além do injetado: descartar ou sinalizar? (relevante só se o agente usar
  LLM em passos não-críticos).
- Métrica primária para reportar nas RQs (acurácia de passo vs distância de passo).

> Escopo: este log registra decisões de **método/parâmetro**. Decisões **arquiteturais** (estruturais) vivem em
> `docs/adr/` como ADRs. Na dúvida: "muda a estrutura do sistema?" → ADR; "ajusta um valor do experimento?" → aqui.
