# PRD — Índice geral

Replicação do AgentRx com extensão de telemetria OpenTelemetry sobre um MAS simulado (LangGraph). Conjunto de PRDs
incrementais; cada arquivo é mantido **abaixo de 200 linhas** para facilitar a validação.

## Ordem de leitura

| # | Arquivo | Escopo | Status |
| -- | -- | -- | -- |
| 0 | `PRD-00-objetivos-criterios-aceite.md` | RQs, hipóteses, desenho experimental, critérios de aceite, glossário | base |
| 1 | `PRD-01-estrutura-repo-dados-scripts.md` | Estrutura de pastas, gestão de dados, pasta `scripts/`, open science | base |
| 2 | `PRD-02-gerador-de-perguntas.md` | Script gerador do benchmark de 30 perguntas (determinístico, sem IA) | base |
| 3 | `PRD-03-mock-tools-falhas-smoke.md` | Mock tools, 5 operadores de falha, smoke test por falha | base |
| 4 | `PRD-04-adapters-dois-bracos.md` | Artefato OTel bruto, parser, adapters das 2 trajetórias | base |
| 5 | `PRD-05-integracao-agentrx-coleta-csv.md` | Domínio próprio no AgentRx, invocação do juiz, coleta e CSV | base |
| 6 | `PRD-06-contrato-dados-otel-ir.md` | Campos da versão OTel e mapeamento OTel→IR dos 2 braços (telemetria e AgentRx puro) | base |
| 7 | `PRD-07-runner-metricas-analise.md` | Runner de matriz, métricas, scripts de análise | próximo incremento |
| 9 | `PRD-09-experimento-trail.md` | Experimento TRAIL (segregado): campos do dataset, extração, adapters, avaliação | base |

## Dois experimentos segregados

O repositório executa **dois experimentos independentes** que respondem as mesmas RQs por ângulos complementares, com
caminhos de execução separados:

- **MAS simulado** (PRD-00..06): ground truth limpo por injeção scriptada.
- **TRAIL** (PRD-09): traces reais, ground truth derivado dos labels. Não há normalização cruzada de campos;
  compartilham só o submódulo AgentRx.

## Decisões consolidadas (ver `PRD-08-decisions-log.md` para histórico)

- Injeção de falha: **scriptada / determinística** (prompt-based só como alternativa documentada).
- Modelos do agente e do juiz **parametrizáveis via `.env`** (`AGENT_MODEL`, `JUDGE_MODEL`, `JUDGE_BACKEND`); invariante
  = agente ≠ juiz, juiz capaz, modelos registrados por run. Defaults: agente Llama3.1-8B local; juiz gpt-5-mini via
  Copilot CLI.
- **2 braços**: trajetória com telemetria vs. trajetória estilo-AgentRx, ambas derivadas de 1 artefato OTel bruto.
- Agente roda **1×/cenário** (determinístico); juiz roda **3×/trajetória**.
- **30 cenários** (6 por categoria × 5 categorias). 30 traces × 2 braços × 3 julgamentos = 180 execuções do juiz.
- Domínio do AgentRx: **registrar `product_catalog` próprio** (não reusar `tau`).
- 5 categorias: System Failure, Invalid Invocation, Misinterpretation of Tool Output, Invention of New Information,
  Instruction/Plan Adherence Failure.

## Convenções

- Idioma dos PRDs: pt-BR. Identificadores de código e nomes de campo: inglês.
- Identificador de run = id do cenário, no formato `qNN_<template>_<produto>`.
- Todo artefato de dados versionado carrega proveniência (ver `NOTICE.md`).
- "Critério de aceite" = condição verificável (idealmente por teste automatizado).

## Registro de decisões

- Decisões **arquiteturais** (estruturais, duradouras): `docs/adr/` (ADRs numerados; índice em `docs/adr/README.md`).
- Decisões de **método/parâmetro**: `docs/prd/PRD-08-decisions-log.md`.
