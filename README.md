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
make smoke
make check
```

## Próximos comandos

| Objetivo | Comando |
| -- | -- |
| Smoke offline do juiz | `make smoke-judge` |
| Matriz completa do juiz | `make judge` |
| Coletar resultados | `make collect` |
| Gerar seis tabelas de análise | `make analyze` |
| Compor simulação, derivação, juiz e coleta | `make experiment` |

Configuração de LLM, backends do juiz, filtros, retomada e limpeza estão no [guia operacional](docs/operacao.md).

## Documentações

- [Guia operacional](docs/operacao.md): configuração, matriz completa e análise.
- [Testes](tests/README.md): escopo de cada suíte e comandos de validação.
- [Artefatos internos](data/internal/README.md): traces, trajetórias, manifestos e vereditos.
- [Resultados CSV](data/experiment/results/README.md): dicionário completo de `runs_long`, `trajectory_index` e
  `metricas`.
- [Tabelas de análise](data/experiment/analysis/README.md): dicionário das seis saídas de `make analyze`.
- [Arquitetura](docs/architecture/architecture.md), [PRDs](docs/prd/PRD-INDEX.md) e [ADRs](docs/adr/README.md): contrato
  experimental e decisões duráveis.
