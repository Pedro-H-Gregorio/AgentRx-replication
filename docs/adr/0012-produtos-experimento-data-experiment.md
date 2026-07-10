# ADR-0012 — Produtos do experimento em `data/experiment/`, separados dos intermediários

- **Status**: Accepted
- **Data**: 2026-07-04
- **Relacionado**: PRD-01, PRD-05, PRD-07, PRD-10; ADR-0002; change `collect-metrics-csv`

## Contexto

O pipeline distingue **artefato bruto** (o trace OTel, fonte única de verdade — ADR-0002) de tudo que é **derivado** por
código determinístico. Até o C6, todos os derivados viviam sob `data/internal/` (traces, trajetórias, vereditos brutos
do juiz). O C7 introduz um novo tipo de saída: os **CSVs de resultado** (PRD-10) — não são intermediários do pipeline,
são o **produto final** que alimenta a análise das RQs e a dissertação.

O PRD-01 planejava esses consolidados em `data/outputs/`, mas essa pasta nunca foi materializada. Como o repositório
mira **open science**, o lugar dos resultados precisa ser óbvio para quem chega de fora: "onde estão os números do
experimento?" deve ter resposta imediata, distinta de "onde estão os arquivos de trabalho intermediários?".

## Decisão

Os **produtos do experimento** vivem em `data/experiment/`, separados dos intermediários de `data/internal/`:

```
data/
├── internal/          # intermediários derivados (traces, trajetórias, vereditos brutos)
│   ├── otel/ trajectory_*/ ground_truth/ agentrx/<experiment_id>/
└── experiment/        # PRODUTO do experimento (versionado no git)
    └── results/<experiment_id>/{runs_long,trajectory_index,metricas}.csv
```

- Um conjunto de CSVs **por `experiment_id`** (o mesmo id config-derivado do C6: `judge-<backend>-<modelo>`), de modo
  que rodar um segundo juiz cria um diretório irmão sem quebra nem colisão de chave.
- Os CSVs são **versionados** (são pequenos e são o resultado auditável).
- `data/outputs/` é **abandonado** e removido da documentação (PRD-01, PRD-05, ARCHITECTURE, AGENTS/CLAUDE).
- Espaço reservado para `data/experiment/analysis/<mas_id>/<judge_id>/` (namespaceado como `results/`, ADR-0013, para
  não colidir entre MASes de mesmo juiz). Realizado pelo C8 (`make analyze`): tabelas `.csv` da análise A/B, sem figuras
  por ora.

## Consequências

- Leitor externo localiza os resultados por convenção clara; a fronteira intermediário/produto fica explícita em
  `docs/architecture/architecture.md` e no PRD-01.
- O coletor escreve só em `data/experiment/`; `data/internal/` permanece intocado (nenhum acoplamento novo no C6).
- Documentação que citava `data/outputs/` passa a citar `data/experiment/`; uma varredura garante ausência de
  referências mortas.
- Não altera o invariante do ADR-0002: os CSVs continuam derivados determinísticos do trace bruto (via vereditos), agora
  com casa própria.

## Alternativas descartadas

- **Manter `data/outputs/`**: era o nome planejado, mas nunca materializado e menos legível que a dupla `internal`
  (trabalho) / `experiment` (produto) para um leitor de fora. Trocar agora custa só documentação (a pasta não existia).
- **CSVs sob `data/internal/agentrx/<experiment_id>/`**: misturaria produto final com os vereditos brutos e os
  subprodutos operacionais do juiz, perdendo a distinção que o open science pede.
- **`data/experiment/` sem `results/`**: o subnível deixa espaço nomeado para `analysis/` futura sem reorganizar depois.
