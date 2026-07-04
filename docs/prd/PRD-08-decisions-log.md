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
| D21 | Invocar o juiz com **IR pré-plantada + `--stage judge`** (copiar a trajetória como `<run_dir>/trajectory_ir.json` antes de chamar `run.py`) | O estágio IR do AgentRx é pulado quando o arquivo já existe; evita o conversor de domínio `flash`/`llm_ir` re-converter (não-determinístico) a IR canônica | `run.py --skip-static --skip-dynamic` (roda o IR e expõe ao fallback); importar `agentrx.judge` (acopla ao submódulo) |
| D22 | **Juiz cego**: nunca passar `--ground-truth` ao AgentRx; scoring 100% nosso a partir de `data/internal/ground_truth/` | Elimina a classe de risco de vazamento por construção; nosso GT exigiria conversor; scoring único evita divergir do C7 | Passar `--ground-truth` (mesmo sem entrar no prompt no caminho do pipeline) |
| D23 | **3 reps = 3 invocações** do `run.py` com `run_dir` distintos (`rep1/2/3`) | `run_single_iteration` grava sempre `runs/run1.json` (1 iteração/processo); a repetição é responsabilidade do orquestrador | Pedir N iterações internas ao AgentRx (exigiria editar o submódulo) |
| D24 | **Critério de root cause replica o AgentRx**: categoria = moda das failures; passo = `round(média)` dos `step_numbers` | Comparabilidade direta com a métrica nativa (`compute_stats`/`analysis()`); o C7 herda o mesmo critério sem tradução | "Primeira failure" ou "menor passo" (divergiriam da métrica do AgentRx; ficam como métricas secundárias no C8) |
| D25 | **Versionar só** `manifest.json` + `runs_index.jsonl` + `run1.json`; gitignorar o resto dos run dirs | `trajectory_ir.json` é cópia byte-idêntica de arquivo já versionado; `state.json`/plots são operacionais; baseline auditável sem duplicar as 60 trajetórias por experimento | Versionar run dirs inteiros (D19 estrito; incharia o repo) |
| D26 | **`JUDGE_TEMPERATURE`** (default 0) usada pelo shim `openai`; no backend `copilot` a temperatura é `unknown` no manifesto | Determinismo recomendado + parametrizável; o CLI do Copilot não expõe temperatura, então a assimetria é declarada como ameaça à validade (C8) | Hardcode 0 no shim (impede variar); omitir temperatura (perde determinismo) |
| D27 | **Sem retry automático** por rep; retry é explícito (`make judge ONLY=errors`); timeout 600s configurável (`JUDGE_TIMEOUT_SECONDS`) | A idempotência já cobre a retomada; o índice registra fielmente a instabilidade do backend (não a mascara) | Retry automático 1× (esconde falhas transitórias do índice) |
| D28 | **Backoff de transporte no shim `openai`** (429/5xx) é camada distinta do D27: re-tenta *dentro de uma rep* respeitando `Retry-After`/exponencial (`JUDGE_MAX_RETRIES`), enquanto o D27 mantém "sem retry *da rep*" no orquestrador; o `retries` fica no índice | Rate-limit de tier grátis é ruído transitório, não instabilidade a registrar como falha; as retentativas do AgentRx são secas e não aguardam a janela resetar | Deixar o 429 virar `error` (perderia reps por ruído); retry no orquestrador (mascara a instância) |
| D29 | **Veredito vazio = `error`**, nunca `ok` (`has_verdict`: JSON válido E ≥1 failure); `failure_case 0` legítimo conta como veredito | Juiz sem auth/resposta vazia não pode passar por sucesso silencioso; `ONLY=errors` o reexecuta | Aceitar `run1.json` válido-porém-vazio como `ok` (mascara auth quebrada) |
| D30 | **`--preflight`** sonda o backend antes da matriz (mesma invocação real) e aborta cedo | Falha de auth/modelo aparece num probe barato, não após N reps desperdiçadas | Descobrir o problema rep a rep (desperdício em matriz grande) |
| D31 | A matriz roda com **agente-LLM** (`USE_LLM=true`). O **modelo do agente NÃO é fixo**: o MAS é agnóstico de modelo (invariante), escolhido depois via `AGENT_MODEL` e registrado no manifesto de cada run. As trajetórias hoje em `data/internal/` foram geradas com Llama3.1-8B **por acaso** (era o que estava rodando) e são provisórias — podem ser regeneradas com outro modelo | O que é decisão é *usar um LLM* (prosa realista para o juiz), não *qual* LLM; a injeção continua scriptada (gabarito intacto) | Agente determinístico por template (default; descartado); **fixar um modelo específico do agente** (violaria a agnosticidade — o modelo é parâmetro, D2) |

## Consequências de D31 (obrigatórias no C7)

- **Filtro de higiene (D14) deixa de ser YAGNI e vira requisito**: com prosa gerada por LLM, o agente pode errar
  **além** da falha injetada; runs com erro emergente contaminam o gabarito (o juiz pode "acertar" a falha errada). O C7
  SHALL detectar e descartar/sinalizar essas runs. Critério a definir (ex.: divergência do resultado esperado em passos
  não-injetados).
- **Imparcialidade cai para o teste fraco** (R5, ausência de marcadores) — o teste forte de igualdade byte a byte
  pressupõe determinismo. Efeito colateral: o teste forte de imparcialidade **falha** localmente enquanto `USE_LLM=true`
  (deveria gatear em `USE_LLM`; se isso incomodar o `make check`, ajustar o gate do teste é item à parte).
- **Reprodutibilidade**: trajetórias LLM não são byte-idênticas entre execuções; fixar seed e manter o
  modelo/temperatura registrados no manifesto do MAS (já registrados: `use_llm`, `agent_model`, `llm_temperature`).

## Decisões em aberto

- **Critério exato do filtro D14** (como detectar "erro emergente além do injetado") — desenhar no C7.

> Resolvidas desde a redação original: quantidade de cenários (D6 fixou **30**, 6/categoria); métrica primária das RQs
> (o **PRD-07** especifica o conjunto do artigo — 3 de passo + tolerâncias + distância crua/normalizada + 4 de
> categoria; não há "métrica única"); e config do agente na matriz (D31: `USE_LLM=true`).

> Escopo: este log registra decisões de **método/parâmetro**. Decisões **arquiteturais** (estruturais) vivem em
> `docs/adr/` como ADRs. Na dúvida: "muda a estrutura do sistema?" → ADR; "ajusta um valor do experimento?" → aqui.
