# Replicação AgentRx + OpenTelemetry

Experimento para avaliar se telemetria OpenTelemetry ajuda o juiz do AgentRx a localizar e classificar falhas em um
sistema multiagente simulado. O MAS executa perguntas de catálogo somente-leitura com injeção de falha scriptada e gera
um trace OTel bruto; dele surgem duas trajetórias semanticamente equivalentes: telemetria (A) e log textual (B).

```text
benchmark → simulação MAS → trace OTel → duas trajetórias → juiz → CSVs → análise
```

O trace OTel é a fonte de verdade. Trajetórias não recebem ground truth, e os dois braços só diferem pela telemetria e
pelo formato de apresentação.

## Sumário

- [Primeira execução](#primeira-execu%C3%A7%C3%A3o)
- [Próximos comandos](#pr%C3%B3ximos-comandos)
- [Estrutura do repositório](#estrutura-do-reposit%C3%B3rio)
- [Documentações](#documenta%C3%A7%C3%B5es)

## Primeira execução

Pré-requisitos: Git, Make, Python 3.13 e `uv`. Clone com o submódulo:

```bash
git clone --recurse-submodules <url-do-repo>
cd replicacao-agentrx
make install
cp example.env .env
```

`example.env` inicia no modo determinístico e offline (`USE_LLM=false`, juiz `stub`). Execute o pipeline básico nesta
ordem:

| Comando | Produz ou verifica |
| -- | -- |
| `make generate` | 30 cenários determinísticos em `data/benchmark/` |
| `make simulate` | traces OTel, labels e manifestos em `data/internal/<mas_id>/` |
| `make derive` | trajetórias A e B, com paridade e não-vazamento validados |
| `make smoke` | uma execução por categoria de falha |
| `make check` | formatação, lint e limite de tamanho dos arquivos de código |

```bash
make generate
make simulate
make derive
make smoke # opicional, apenas se quiser rodar uma versão de teste de fumaça
make check # opicional, apenas se quiser fazer um check para os testes de resultados
```

## Próximos comandos

| Objetivo | Comando |
| -- | -- |
| Smoke offline do juiz | `make smoke-judge` |
| Matriz completa do juiz | `make judge` |
| Coletar resultados | `make collect` |
| Gerar seis tabelas, relatório Markdown e figuras PNG com R | `make analyze` |
| Compor simulação, derivação, juiz e coleta | `make experiment` |

Configuração de LLM, backends do juiz, filtros, retomada e limpeza estão no [guia operacional](docs/operacao.md).

## Estrutura do repositório

O fluxo de dados é linear e cada pasta guarda um estágio dele: dados externos fixos → benchmark gerado → artefatos
intermediários por execução → produtos finais para o artigo. O padrão de nomes `<mas_id>/<judge_id>` (ex.:
`Gemma3-27B-RUN-3/judge-codex-gpt-5-5`) segrega execuções por modelo do MAS e por juiz, de modo que rodar com outro
modelo nunca sobrescreve resultados anteriores.

```text
replicacao-agentrx/
├── src/agentrx_otel_poc/    # Código do MAS e do pipeline (o AgentRx nunca é importado daqui)
│   ├── benchmark/           #   gerador determinístico das 30 perguntas de catálogo (templates, sem IA)
│   ├── graph/               #   grafo LangGraph: nós Coordinator→Researcher→Tool→Executor→Evaluator
│   ├── faults/              #   os 5 operadores de injeção scriptada de falha
│   ├── mock_tools.py        #   ferramentas de leitura mockadas (backing = catálogo tau-bench)
│   ├── telemetry.py         #   emissão do trace OTel bruto (a fonte de verdade)
│   ├── adapters/            #   parser do trace + derivação das 2 trajetórias (A telemetria, B log textual)
│   ├── judge/               #   orquestração do AgentRx em modo judge-only (planner/executor/scoring)
│   └── collect/             #   coletor neutro que agrega os vereditos em CSV (nunca importa o agentrx)
├── scripts/                 # Entradas de linha de comando de cada estágio (chamadas pelo Makefile)
│   ├── generate_benchmark.py · simulate.py · derive_trajectories.py · run_judge.py · collect_agentrx.py
│   ├── analysis/            #   scripts R: tabelas C8 e relatório GFM (`analysis_report.md`)
│   └── judge_shims/         #   shims dos backends do juiz (stub offline, openai, codex)
│
├── data/                    # Todos os dados, do externo ao experimento final
│   ├── external/            #   DADOS EXTERNOS fixados por commit — nunca gerados aqui
│   │   ├── taubench_retail/ #     products.json: catálogo de 50 produtos do tau-bench (MIT, ver NOTICE.md);
│   │   │                    #     é o backing somente-leitura das mock tools do MAS
│   │   └── TRAIL/           #     benchmark TRAIL (gaia/swe) — dataset GATED; usado só como referência de
│   │                        #     taxonomia (PRD-09).
│   ├── benchmark/           #   benchmark_30.json: as 30 perguntas geradas por `make generate`
│   ├── internal/            #   INTERMEDIÁRIOS por execução (`<mas_id>/`): 1 arquivo por cenário em cada
│   │                        #     otel/ ground_truth/ logs/ manifests/ trajectory_telemetry/ trajectory_agentrx/
│   │                        #     e agentrx/<judge_id>/ com os vereditos brutos por repetição
│   └── experiment/          #   PRODUTOS FINAIS do experimento (`<mas_id>/<judge_id>/`)
│       ├── results/         #     CSVs: runs_long (600 julgamentos brutos), metricas, trajectory_index
│       └── analysis/        #     6 tabelas, relatório Markdown e PNGs de `make analyze`
│
├── manuscript/paper/        # Artigo (LaTeX ACM): main.tex, refs.bib, figures/
├── docs/                    # Contrato experimental e decisões duráveis
│   ├── prd/                 #   PRDs (comece por PRD-INDEX.md): requisitos e dicionário de dados
│   ├── adr/                 #   Architecture Decision Records (decisões estruturais)
│   └── architecture/        #   desenho de repo e reprodutibilidade
├── tests/                   # Unitários + 5 smoke por falha + testes de paridade/não-vazamento
├── AgentRx/                 # Submódulo (fixado) no commit SHA: f228165bfec60a801fd5fedd9d8ffe0f9de0c69d 
└── Makefile · example.env · pyproject.toml · uv.lock · NOTICE.md   # execução, config e procedência
```

Regra de leitura dos dados: o **trace OTel** (`data/internal/<mas_id>/otel/`) é a única fonte de verdade; tudo em
`benchmark/`, `internal/` (exceto o OTel) e `experiment/` é derivado dele por código determinístico e pode ser
regenerado. Nunca editar à mão um arquivo derivado. A procedência dos insumos de `data/external/` está em
[NOTICE.md](NOTICE.md).

## Documentações

- [Guia operacional](docs/operacao.md): configuração, matriz completa e análise.
- [Testes](tests/README.md): escopo de cada suíte e comandos de validação.
- [Artefatos internos](data/internal/README.md): traces, trajetórias, manifestos e vereditos.
- [Resultados CSV](data/experiment/results/README.md): dicionário completo de `runs_long`, `trajectory_index` e
  `metricas`.
- [Artefatos de análise](data/experiment/analysis/README.md): dicionário das seis tabelas, do relatório Markdown e das
  figuras PNG de `make analyze`.
- [Arquitetura](docs/architecture/architecture.md), [PRDs](docs/prd/PRD-INDEX.md) e [ADRs](docs/adr/README.md): contrato
  experimental e decisões duráveis.
- [Artigo do experimento](manuscript/paper/build/main.pdf): Replicação AgentRx: Diagnóstico em Falhas de Sistemas
  Multiagentes utilizando Telemetria Estruturada
