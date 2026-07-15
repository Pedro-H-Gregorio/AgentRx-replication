# Dicionário dos artefatos de análise

`make analyze` executa `scripts/analysis/c8_run.R` e `scripts/analysis/c8_render_report.R` sobre
`data/experiment/results/<mas_id>/<judge_id>/metricas.csv` e o `runs_long.csv` vizinho. Ele escreve seis CSVs, um
relatório Markdown GFM e figuras PNG em `data/experiment/analysis/<mas_id>/<judge_id>/`. A análise é leitura pura: não
importa AgentRx nem recalcula métricas do coletor.

As células são valores de apresentação para as tabelas do artigo. Percentuais, contagens e estatísticas são serializados
como texto para preservar formatação; células não aplicáveis são escritas vazias, não como `NA`. Requer `Rscript` e os
pacotes `readr`, `dplyr`, `tidyr`, `scales`, `boot`, `broom`, `rmarkdown`, `knitr` e `ggplot2`, além de Pandoc. A
geração não instala dependências nem acessa a rede.

## Relatório Markdown e figuras

`analysis_report.md` é renderizado a partir do template canônico `scripts/analysis/analysis_report.Rmd`, consumindo o
mesmo contexto C8 das tabelas. As três figuras vivem em `analysis_report_files/figure-gfm/`, com links relativos no
Markdown. O relatório traz o resumo descritivo, resultados por categoria, frequências por repetição, comparação pareada,
IC bootstrap BCa e placar por cenário. O fluxo não gera HTML, PDF, dashboard ou visualização interativa.

## `tab_acuracias.csv`

Entrada: `metricas.csv`. Uma linha por métrica de acurácia.

| Campo | Tipo serializado | Significado |
| -- | -- | -- |
| `Métrica` | `str` | Nome da métrica do artigo. |
| `Telemetria (A)` | `str percent` | Média da métrica no braço A. |
| `Log textual (B)` | `str percent` | Média da métrica no braço B. |
| `Δ (A−B) p.p.` | `str signed decimal` | Diferença A menos B em pontos percentuais. |

## `tab_distancia_passo.csv`

Entrada: `metricas.csv`. Uma linha por braço.

| Campo | Tipo serializado | Significado |
| -- | -- | -- |
| `Braço` | `enum` | `Telemetria (A)` ou `Log textual (B)`. |
| `Média` | `str decimal` | Média de `avg_step_distance`. |
| `DP` | `str decimal` | Desvio-padrão da distância. |
| `Med.` | `int` | Mediana da distância. |
| `Mín.` | `int` | Menor distância. |
| `Máx.` | `int` | Maior distância. |
| `Norm.` | `str decimal` | Média da distância normalizada. |
| `MAE` | `str decimal` | Média de `step_mae`. |

## `tab_por_categoria.csv`

Entrada: `metricas.csv`. Uma linha por categoria e braço.

| Campo | Tipo serializado | Significado |
| -- | -- | -- |
| `Categoria` | `str` | Nome completo da categoria injetável. |
| `Braço` | `enum` | Braço de comparação. |
| `Failure Category Accuracy` | `str percent` | Média de `cat_acc_critical`. |
| `Critical Step Accuracy` | `str ratio` | Acertos exatos de passo sobre cenários da categoria. |
| `Average Step Distance` | `str decimal` | Média de `avg_step_distance`. |

## `tab_frequencia_mae_categoria.csv`

Entrada: `runs_long.csv` + GT trazido de `metricas.csv`. Uma linha por categoria; é a única tabela construída a partir
de predições por repetição.

| Campo | Tipo serializado | Significado |
| -- | -- | -- |
| `Categoria` | `str` | Nome completo da categoria injetável. |
| `Cat. A` | `str ratio` | Acertos/erros de categoria das reps do braço A. |
| `Cat. B` | `str ratio` | Acertos/erros de categoria das reps do braço B. |
| `Passo A` | `str ratio` | Acertos/erros de passo das reps do braço A. |
| `Passo B` | `str ratio` | Acertos/erros de passo das reps do braço B. |
| `MAE A` | `str decimal` | Erro absoluto médio por rep do braço A. |
| `MAE B` | `str decimal` | Erro absoluto médio por rep do braço B. |

## `tab_inferencial.csv`

Entrada: `metricas.csv`. Uma linha por teste pareado.

| Campo | Tipo serializado | Significado |
| -- | -- | -- |
| `Teste` | `str` | McNemar, Wilcoxon ou bootstrap reportado. |
| `Ambos` | `int or empty` | Cenários acertados pelos dois braços; só McNemar. |
| `Só A` | `int or empty` | Cenários acertados somente por A; só McNemar. |
| `Só B` | `int or empty` | Cenários acertados somente por B; só McNemar. |
| `Nenhum` | `int or empty` | Cenários errados pelos dois braços; só McNemar. |
| `Resultado` | `str` | Valor-p ou intervalo bootstrap. |
| `Leitura` | `str` | Interpretação textual do resultado. |

O IC bootstrap BCa usa seed 42 e 5.000 reamostragens de linhas da tabela larga, preservando juntos os dois braços de
cada cenário. A diferença de distância é A menos B; intervalo positivo indica A pior nessa métrica.

## `tab_estimativas_por_cenario.csv`

Entrada: `metricas.csv`. Uma linha por cenário; confronta GT e predição agregada dos dois braços.

| Campo | Tipo serializado | Significado |
| -- | -- | -- |
| `Cenário` | `str` | Identificador do cenário. |
| `GT categoria` | `str` | Nome da categoria verdadeira. |
| `GT passo` | `int` | Passo crítico verdadeiro. |
| `A categoria` | `str` | Categoria agregada de A seguida de `✓` ou `✗`. |
| `A passo` | `str` | Passo agregado de A seguido de `✓` ou `✗`. |
| `B categoria` | `str` | Categoria agregada de B seguida de `✓` ou `✗`. |
| `B passo` | `str` | Passo agregado de B seguido de `✓` ou `✗`. |

As saídas são idempotentes e byte-estáveis. Para o schema de entrada, consulte o
[dicionário de resultados](../results/README.md); para operação, o [guia operacional](../../../docs/operacao.md).
