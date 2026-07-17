# PRD-01 — Estrutura de repositório, dados e scripts

## 1. Objetivo

Definir o layout do repositório, a gestão de dados (bruto vs. derivado), a pasta `scripts/` e as práticas de open
science que tornam o experimento reprodutível.

## 2. Árvore de pastas (alvo)

```
repo/
├── src/agentrx_otel_poc/        # pacote do MAS (já existe)
│   ├── graph.py state.py llm.py settings.py
│   ├── tasks.py                 # passa a carregar benchmark_30.json
│   ├── mock_tools.py faults.py  # ver PRD-03
│   ├── telemetry.py             # artefato OTel bruto (ver PRD-04)
│   └── adapters/                # parser + 2 trajetórias (ver PRD-04)
├── AgentRx/                     # submódulo microsoft/AgentRx (não editar a fundo)
├── scripts/
│   ├── generate_benchmark.py    # gerador de perguntas (PRD-02)
│   ├── run_matrix.py            # runner do experimento (PRD-06)
│   ├── collect_agentrx.py       # coleta saída do AgentRx → CSV (PRD-05)
│   └── analysis/                # scripts de análise de dados
├── data/
│   ├── external/taubench_retail/products.json   # catálogo (com NOTICE)
│   ├── benchmark/benchmark_30.json              # saída do gerador (versionado)
│   ├── internal/                # artefatos por run (ver §4)
│   └── experiment/results/<mas_id>/<judge_id>/  # PRODUTO: CSVs de resultado (ADR-0012)
├── tests/                       # smoke tests por falha (PRD-03)
├── manuscript/                  # paper ACM (já existe)
├── docs/prd/                    # estes PRDs
├── NOTICE.md LICENSE Makefile example.env
```

## 3. Dados externos (proveniência)

- Todo dado de terceiros vive em `data/external/<fonte>/` e tem entrada no `NOTICE.md` com: fonte, caminho original,
  **commit fixado**, licença, uso.
- O catálogo é o `products.json` do tau-bench, commit `6f4b718037db619539b8b692060e6686f3f0dcc9` (MIT). Não modificar o
  arquivo.

## 4. Artefatos por run (`data/internal/`)

Um run produz um conjunto nomeado por `run_id`, sob o namespace do modelo do MAS (`<mas_id>` = `MAS_ID` ou `AGENT_MODEL`
literal; ADR-0013):

```
data/internal/<mas_id>/
├── otel/<run_id>.otel.json              # ARTEFATO BRUTO (fonte de verdade)
├── trajectory_telemetry/<run_id>.json   # braço A (derivado)
├── trajectory_agentrx/<run_id>.json     # braço B (derivado)
├── ground_truth/<run_id>.ground_truth.json
├── logs/<run_id>.log · manifests/<run_id>.json
└── agentrx/<judge_id>/                  # saída do juiz sobre ESTE corpus (C6)
```

Rodar o MAS com outro modelo cria `data/internal/<outro_mas_id>/` sem sobrescrever.

Regra: **o OTel é o único artefato primário; tudo mais é derivado dele** por adapters determinísticos. Derivados podem
ser regenerados e, em princípio, não precisariam ser versionados — mas serão versionados para auditabilidade.

## 5. Pasta `scripts/`

- `generate_benchmark.py` — entrada `products.json`, saída `benchmark_30.json`.
- `run_judge.py` — orquestra a matriz cenário × braço × rep do juiz (C6). (Não há `run_matrix.py`.)
- `collect_agentrx.py` — agrega os vereditos de `data/internal/<mas_id>/agentrx/<judge_id>/` nos 3 CSVs (C7).
- `analysis/` — um script por figura/tabela do paper; entrada = CSVs de `data/experiment/results/`, saída =
  `manuscript/paper/figures/` ou tabelas.

Todo script é **idempotente** e aceita `--seed` quando houver qualquer escolha não trivial; sem IA no caminho de geração
de dados de entrada.

## 6. Open science e reprodutibilidade

- **Licença e atribuição**: `LICENSE` do projeto + `NOTICE.md` para terceiros.
- **Decisions log**: `PRD-08-decisions-log.md` registra cada decisão com data e justificativa (rastreabilidade das
  escolhas de método).
- **Ambiente**: `.python-version`, `pyproject.toml`/`requirements`, `example.env` (sem segredos). Modelos e endpoints
  declarados via env.
- **Determinismo**: temperatura 0 no agente; `use_llm` desligado nos passos não envolvidos na falha; seeds fixas onde
  aplicável.
- **Makefile**: alvos `install`, `check`, `generate`, `smoke`, `run`, `collect`, `analyze` — cada etapa reexecutável
  isoladamente.
- **Versionado vs. ignorado**: versiona-se `benchmark_30.json`, `data/internal/**` (só manifesto/índice/`run1.json` em
  `data/internal/<mas_id>/agentrx/**`) e `data/experiment/**`; ignora-se `.venv`, caches, `AgentRx/runs/**`
  (regeráveis).

## 7. Critérios de aceite

- A árvore acima existe e `make install` configura o ambiente do zero.
- `NOTICE.md` cobre todo arquivo em `data/external/`.
- Qualquer artefato derivado é regenerável a partir do `.otel.json` + scripts.
