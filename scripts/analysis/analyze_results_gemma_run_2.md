Análise de Resultados e Discussão — Telemetria (A) vs AgentRx (B)
================
07/07/2026

  - [1. Resumo executivo](#1-resumo-executivo)
  - [2. Estatística descritiva](#2-estatística-descritiva)
      - [2.1 Acurácias por braço](#21-acurácias-por-braço)
      - [2.2 Dispersão das amostras (o quanto os números
        variam)](#22-dispersão-das-amostras-o-quanto-os-números-variam)
      - [2.3 Distância de passo — descritivo completo (menor é
        melhor)](#23-distância-de-passo--descritivo-completo-menor-é-melhor)
  - [3. Visualização e leitura](#3-visualização-e-leitura)
      - [3.1 Passos acertados por tipo de
        falha](#31-passos-acertados-por-tipo-de-falha)
      - [3.2 Comparação A × B nas métricas-chave
        (dumbbell)](#32-comparação-a--b-nas-métricas-chave-dumbbell)
      - [3.3 Distância pareada por cenário (\>0 = telemetria
        pior)](#33-distância-pareada-por-cenário-0--telemetria-pior)
      - [3.4 Categoria por tipo de falha (H1/H2: semânticas vs
        superfície)](#34-categoria-por-tipo-de-falha-h1h2-semânticas-vs-superfície)
      - [3.5 Placar completo por cenário (A vs B vs
        gabarito)](#35-placar-completo-por-cenário-a-vs-b-vs-gabarito)
  - [4. Inferência estatística](#4-inferência-estatística)
      - [4.1 Margem de erro por t-Student (média ± MoE,
        95%)](#41-margem-de-erro-por-t-student-média--moe-95)
      - [4.2 IC bootstrap (percentil, 5000
        reamostragens)](#42-ic-bootstrap-percentil-5000-reamostragens)
      - [4.3 Testes de hipótese
        pareados](#43-testes-de-hipótese-pareados)
      - [4.4 Vitórias pareadas](#44-vitórias-pareadas)
  - [5. Discussão](#5-discussão)
  - [6. Ameaças à validade](#6-ameaças-à-validade)
  - [7. Conclusão](#7-conclusão)

**MAS:** Gemma3-27B-RUN-2 | **Juiz:** judge-codex-gpt-5-5 | **n = 30
cenários pareados** | **reps por trajetória:** 3.

As métricas já vêm **agregadas sobre as reps** pelo coletor (PRD-07):
cada linha da `metricas.csv` é um par (cenário × braço), com a
média/mediana/desvio das reps embutidos. O braço **A (telemetria)**
carrega os mesmos fatos semânticos do **B (AgentRx, baseline do
artigo)** mais o bloco de telemetria e o formato JSON; a comparação é
**pareada por cenário**. A pergunta de pesquisa é dupla: a telemetria
estruturada **(RQ1)** melhora a **localização** do passo crítico e
**(RQ2)** a **classificação** da categoria da falha? Resultado nulo é
achado válido (PRD-00 §2).

-----

# 1\. Resumo executivo

Sobre 30 cenários (3 reps/trajetória), a telemetria (A) registrou
**categoria crítica** média de 86.7% contra 80.0% da baseline (B) —
diferença de **+6.7 p.p.**, a favor da telemetria (A), não distinguível
(p = 0.480) pelo McNemar. Na **localização exata** do passo, A acertou
83.3% contra 86.7% de B (**-3.3 p.p.**, a favor da baseline (B)). Na
**distância média de passo** (menor é melhor), A ficou em 0.267 e B em
0.222 (Δ A−B = +0.044, a favor da baseline (B); Wilcoxon não
distinguível (p = 0.588)).

A leitura detalhada nas seções seguintes mostra que **as diferenças A×B
são pequenas e, na maioria das métricas, dentro do intervalo de
confiança que inclui zero** — ou seja, ainda sem evidência de que a
telemetria supere a baseline neste juiz. O padrão de **dispersão**
(§2.2) indica que boa parte da variação vem da instabilidade do juiz
**entre reps** em alguns cenários, o que motiva diretamente a
re-execução com mais reps.

-----

# 2\. Estatística descritiva

## 2.1 Acurácias por braço

| Métrica           | Telemetria (A) | AgentRx (B) | Δ (A−B) p.p. |
| :---------------- | -------------: | ----------: | -----------: |
| Passo exato (±0)  |          83.3% |       86.7% |        \-3.3 |
| Passo ±1          |          96.7% |       93.3% |        \+3.3 |
| Passo ±3          |         100.0% |      100.0% |        \+0.0 |
| Passo ±5          |         100.0% |      100.0% |        \+0.0 |
| Categoria crítica |          86.7% |       80.0% |        \+6.7 |
| Categoria (any)   |          86.7% |       80.0% |        \+6.7 |

A tabela contrasta as duas RQs. Na **classificação** (categoria
crítica), a telemetria marca 86.7% e a baseline 80.0% (Δ = +6.7 p.p.);
em *categoria (any)*, que relaxa a fronteira de scoring, o comportamento
tende a acompanhar. Na **localização exata**, A fica em 83.3% e B em
86.7% (Δ = -3.3 p.p.). As tolerâncias ±k contam acerto quando |passo
predito − gabarito| ≤ k; como as trajetórias têm 5 passos, **±3/±5
saturam em \~100% (efeito-teto)** e não discriminam — quem separa os
braços é o **passo exato**. Portanto, o eixo informativo de localização
é a coluna “passo exato” e a **distância de passo** (§2.3), não as
tolerâncias largas.

## 2.2 Dispersão das amostras (o quanto os números variam)

| Braço          | DP passo-exato | DP cat-crítica | DP distância | Instab. passo (média step\_std) | Instab. categoria (média category\_std) | Cenários c/ passo instável |
| :------------- | -------------: | -------------: | -----------: | ------------------------------: | --------------------------------------: | -------------------------: |
| Telemetria (A) |          0.379 |          0.346 |        0.634 |                           0.269 |                                   0.189 |                          7 |
| AgentRx (B)    |          0.346 |          0.407 |        0.657 |                           0.058 |                                   0.038 |                          3 |

Há **dois níveis de dispersão** e eles contam histórias diferentes:

  - **Entre cenários** (o `DP` das colunas de acurácia): mede o quão
    heterogêneo é o conjunto de 30 cenários. Um `DP` alto no passo-exato
    ou na distância (A: 0.634; B: 0.657 na distância) indica que
    **poucos cenários difíceis concentram o erro**, enquanto a maioria é
    acerto limpo — não um erro espalhado por igual. Isso é coerente com
    o efeito-teto: System Failure e Misinterpretation são quase sempre
    acertados, e a variância vem de Invalid Invocation e Plan Adherence.
  - **Intra-cenário, entre reps** (`step_std`, `category_std` médios):
    mede a **instabilidade do próprio juiz** — quando as 3 reps do
    *mesmo* cenário discordam do passo ou da categoria. A telemetria
    apresenta `step_std` médio de 0.269 e a baseline 0.058; em
    categoria, 0.189 (A) vs 0.038 (B). 7 cenários no braço A e 3 no B
    têm `step_std > 0`, isto é, o juiz **mudou de passo predito entre
    reps**.

Essa segunda dispersão é o argumento metodológico central: parte da
diferença A×B observada pode ser **ruído de Monte Carlo do juiz**, não
sinal de tratamento. Com poucas reps, a binarização “acertou/errou”
(moda/`round` das reps) fica sujeita a virar por uma única rep
divergente. **Aumentar o número de reps reduz `step_std`/`category_std`
esperados por cenário e estabiliza a estimativa** — é exatamente o
experimento em curso.

## 2.3 Distância de passo — descritivo completo (menor é melhor)

| Braço          | Média |    DP | Mediana | Mín | Máx | Norm. média | MAE passo |
| :------------- | ----: | ----: | ------: | --: | --: | ----------: | --------: |
| Telemetria (A) | 0.267 | 0.634 |       0 |   0 |   3 |       0.053 |     0.333 |
| AgentRx (B)    | 0.222 | 0.657 |       0 |   0 |   3 |       0.044 |     0.222 |

A distância de passo é a métrica de localização **contínua** (não
binária), logo a mais sensível. A média de A é 0.267 e a de B 0.222;
note que a **mediana** costuma ser bem menor que a média nos dois braços
— sinal de distribuição **assimétrica à direita**: a maioria dos
cenários tem distância 0 (acerto no passo) e um punhado de outliers
(cenários de Plan Adherence, onde o juiz vai para passos tardios) puxa a
média para cima. Por isso o desvio-padrão (`DP`) é da ordem da própria
média: a variação não é gaussiana em torno de um centro, é uma massa em
zero mais uma cauda. Essa forma justifica usar **Wilcoxon**
(não-paramétrico) na inferência de distância (§4.3), além do
t/bootstrap.

-----

# 3\. Visualização e leitura

## 3.1 Passos acertados por tipo de falha

Quantos cenários cada braço **localizou no passo exato**, por tipo de
falha (6 por tipo).

<img src="analyze_results_gemma_run_2_files/figure-gfm/fig_hits-1.png" alt="" style="display: block; margin: auto;" />

| Braço          | Acertos exatos | de |  Taxa |
| :------------- | -------------: | -: | ----: |
| Telemetria (A) |             25 | 30 | 83.3% |
| AgentRx (B)    |             26 | 30 | 86.7% |

O gráfico decompõe a localização por categoria. A leitura típica:
**System Failure** e **Misinterpretation** ficam saturados (perto de 6/6
nos dois braços) — falhas de superfície, o passo é óbvio. A
discriminação entre A e B se concentra em **Invalid Invocation** e
**Plan Adherence**, as categorias onde o passo da causa é sutil. É aí
que qualquer efeito da telemetria — positivo ou negativo — aparece; nas
demais, o teto impede diferença. A tabela consolida os totais por braço
para ancorar a taxa global de acerto exato citada em §2.1.

## 3.2 Comparação A × B nas métricas-chave (dumbbell)

<img src="analyze_results_gemma_run_2_files/figure-gfm/fig_dumbbell-1.png" alt="" style="display: block; margin: auto;" />

Cada haste liga o ponto da baseline (laranja) ao da telemetria (azul);
**o comprimento da haste é a vantagem de um braço**. Em *categoria
crítica* a haste aponta a favor da telemetria (A) (+6.7 p.p.); em
*passo exato*, a favor da baseline (B) (-3.3 p.p.). Hastes **curtas** —
como as aqui — são o retrato visual de um efeito pequeno: os dois braços
quase se sobrepõem. *Passo ±1* aparece só como referência de teto
(satura), não como evidência.

## 3.3 Distância pareada por cenário (\>0 = telemetria pior)

<img src="analyze_results_gemma_run_2_files/figure-gfm/fig_diverging-1.png" alt="" style="display: block; margin: auto;" />

Este gráfico é a **evidência pareada crua**: cada barra é um cenário, à
esquerda de zero a telemetria localizou melhor, à direita pior. A
maioria das barras está **em zero (empate)** — 25 de 30 cenários —, com
1 cenário(s) favorecendo a baseline e 4 favorecendo a telemetria. O
predomínio de empates é o que esvazia o poder dos testes pareados: a
diferença vive numa minoria de cenários, e nesses ela tende a favorecer
a telemetria.

## 3.4 Categoria por tipo de falha (H1/H2: semânticas vs superfície)

<img src="analyze_results_gemma_run_2_files/figure-gfm/fig_cat-1.png" alt="" style="display: block; margin: auto;" />

| Categoria          | Braço          | Cat. crítica | Passo exato (de 6) | Dist. média |
| :----------------- | :------------- | -----------: | -----------------: | ----------: |
| System Failure     | Telemetria (A) |       100.0% |                  6 |       0.000 |
| System Failure     | AgentRx (B)    |       100.0% |                  6 |       0.000 |
| Invalid Invocation | Telemetria (A) |       100.0% |                  4 |       0.333 |
| Invalid Invocation | AgentRx (B)    |       100.0% |                  5 |       0.111 |
| Misinterpretation  | Telemetria (A) |       100.0% |                  6 |       0.000 |
| Misinterpretation  | AgentRx (B)    |       100.0% |                  6 |       0.000 |
| Invention          | Telemetria (A) |       100.0% |                  6 |       0.000 |
| Invention          | AgentRx (B)    |        83.3% |                  6 |       0.000 |
| Plan Adherence     | Telemetria (A) |        33.3% |                  3 |       1.000 |
| Plan Adherence     | AgentRx (B)    |        16.7% |                  3 |       1.000 |

A classificação por tipo separa **falhas de superfície** (System
Failure, Invalid Invocation) de **falhas semânticas**
(Misinterpretation, Invention, Plan Adherence). As semânticas são as
difíceis: exigem que o juiz entenda *o conteúdo* da resposta, não só
que “deu erro”. É onde a categoria crítica costuma cair abaixo de 100% e
onde as duas categorias vizinhas — **Invention** e **Misinterpretation**
— se confundem (ambas são falhas no Executor; ver ameaça à validade em
§6). A tabela alinha, por categoria, a acurácia de categoria, os
acertos de passo e a distância média, permitindo cruzar RQ1 e RQ2 no
mesmo tipo de falha.

## 3.5 Placar completo por cenário (A vs B vs gabarito)

Categoria e passo preditos por cada braço; `✓`/`✗` = acertou/errou vs o
gabarito.

| Cenário                       | GT categoria       | GT passo |        A categoria         | A passo |        B categoria         | B passo |
| :---------------------------- | :----------------- | :------: | :------------------------: | :-----: | :------------------------: | :-----: |
| q01\_t1\_electric\_kettle     | System Failure     |    3     |      System Failure ✓      |   3 ✓   |      System Failure ✓      |   3 ✓   |
| q02\_t2\_mechanical\_keyboard | System Failure     |    3     |      System Failure ✓      |   3 ✓   |      System Failure ✓      |   3 ✓   |
| q03\_t3\_vacuum\_cleaner      | System Failure     |    3     |      System Failure ✓      |   3 ✓   |      System Failure ✓      |   3 ✓   |
| q04\_t4\_smartphone           | System Failure     |    3     |      System Failure ✓      |   3 ✓   |      System Failure ✓      |   3 ✓   |
| q05\_t5\_jigsaw\_puzzle       | System Failure     |    3     |      System Failure ✓      |   3 ✓   |      System Failure ✓      |   3 ✓   |
| q06\_t1\_skateboard           | System Failure     |    3     |      System Failure ✓      |   3 ✓   |      System Failure ✓      |   3 ✓   |
| q07\_t3\_electric\_kettle     | Invalid Invocation |    2     |    Invalid Invocation ✓    |   3 ✗   |    Invalid Invocation ✓    |   3 ✗   |
| q08\_t4\_mechanical\_keyboard | Invalid Invocation |    2     |    Invalid Invocation ✓    |   2 ✓   |    Invalid Invocation ✓    |   2 ✓   |
| q09\_t5\_vacuum\_cleaner      | Invalid Invocation |    2     |    Invalid Invocation ✓    |   2 ✓   |    Invalid Invocation ✓    |   2 ✓   |
| q10\_t3\_smartphone           | Invalid Invocation |    2     |    Invalid Invocation ✓    |   3 ✗   |    Invalid Invocation ✓    |   2 ✓   |
| q11\_t4\_jigsaw\_puzzle       | Invalid Invocation |    2     |    Invalid Invocation ✓    |   2 ✓   |    Invalid Invocation ✓    |   2 ✓   |
| q12\_t5\_skateboard           | Invalid Invocation |    2     |    Invalid Invocation ✓    |   2 ✓   |    Invalid Invocation ✓    |   2 ✓   |
| q13\_t1\_electric\_kettle     | Misinterpretation  |    4     |    Misinterpretation ✓     |   4 ✓   |    Misinterpretation ✓     |   4 ✓   |
| q14\_t3\_mechanical\_keyboard | Misinterpretation  |    4     |    Misinterpretation ✓     |   4 ✓   |    Misinterpretation ✓     |   4 ✓   |
| q15\_t4\_vacuum\_cleaner      | Misinterpretation  |    4     |    Misinterpretation ✓     |   4 ✓   |    Misinterpretation ✓     |   4 ✓   |
| q16\_t1\_smartphone           | Misinterpretation  |    4     |    Misinterpretation ✓     |   4 ✓   |    Misinterpretation ✓     |   4 ✓   |
| q17\_t3\_jigsaw\_puzzle       | Misinterpretation  |    4     |    Misinterpretation ✓     |   4 ✓   |    Misinterpretation ✓     |   4 ✓   |
| q18\_t4\_skateboard           | Misinterpretation  |    4     |    Misinterpretation ✓     |   4 ✓   |    Misinterpretation ✓     |   4 ✓   |
| q19\_t1\_electric\_kettle     | Invention          |    4     |        Invention ✓         |   4 ✓   |        Invention ✓         |   4 ✓   |
| q20\_t2\_mechanical\_keyboard | Invention          |    4     |        Invention ✓         |   4 ✓   |        Invention ✓         |   4 ✓   |
| q21\_t3\_vacuum\_cleaner      | Invention          |    4     |        Invention ✓         |   4 ✓   |    Misinterpretation ✗     |   4 ✓   |
| q22\_t1\_smartphone           | Invention          |    4     |        Invention ✓         |   4 ✓   |        Invention ✓         |   4 ✓   |
| q23\_t2\_jigsaw\_puzzle       | Invention          |    4     |        Invention ✓         |   4 ✓   |        Invention ✓         |   4 ✓   |
| q24\_t3\_skateboard           | Invention          |    4     |        Invention ✓         |   4 ✓   |        Invention ✓         |   4 ✓   |
| q25\_t1\_electric\_kettle     | Plan Adherence     |    1     |      Plan Adherence ✓      |   2 ✗   | Intent-Plan Misalignment ✗ |   1 ✓   |
| q26\_t3\_mechanical\_keyboard | Plan Adherence     |    1     |       Inconclusive ✗       |   1 ✓   |       Inconclusive ✗       |  \-1 ✗  |
| q27\_t1\_vacuum\_cleaner      | Plan Adherence     |    1     | Intent-Plan Misalignment ✗ |   1 ✓   | Intent-Plan Misalignment ✗ |   1 ✓   |
| q28\_t3\_smartphone           | Plan Adherence     |    1     |       Inconclusive ✗       |   0 ✗   |       Inconclusive ✗       |   0 ✗   |
| q29\_t1\_jigsaw\_puzzle       | Plan Adherence     |    1     |      Plan Adherence ✓      |   1 ✓   |      Plan Adherence ✓      |   1 ✓   |
| q30\_t3\_skateboard           | Plan Adherence     |    1     |    Misinterpretation ✗     |   4 ✗   |    Misinterpretation ✗     |   4 ✗   |

Esta tabela é a auditoria cenário-a-cenário: permite localizar
exatamente **onde** os braços divergem e conferir se o erro é de
categoria, de passo, ou de ambos. É a fonte para investigar manualmente
qualquer caso discordante (por ex., um cenário de Plan Adherence em que
a categoria predita cai fora do escopo, contando como *miss* nomeado —
PRD-08 D39).

-----

# 4\. Inferência estatística

Todos os testes são **pareados** (o mesmo cenário nos dois braços), n =
30.

## 4.1 Margem de erro por t-Student (média ± MoE, 95%)

Para uma métrica com média
![\\bar{x}](https://latex.codecogs.com/png.image?%5Cdpi%7B110%7D&space;%5Cbg_white&space;%5Cbar%7Bx%7D
"\\bar{x}"), desvio
![s](https://latex.codecogs.com/png.image?%5Cdpi%7B110%7D&space;%5Cbg_white&space;s
"s") e
![n](https://latex.codecogs.com/png.image?%5Cdpi%7B110%7D&space;%5Cbg_white&space;n
"n") cenários, a margem de erro é ![\\text{MoE} =
t\_{n-1,\\,0.975}\\cdot
s/\\sqrt{n}](https://latex.codecogs.com/png.image?%5Cdpi%7B110%7D&space;%5Cbg_white&space;%5Ctext%7BMoE%7D%20%3D%20t_%7Bn-1%2C%5C%2C0.975%7D%5Ccdot%20s%2F%5Csqrt%7Bn%7D
"\\text{MoE} = t_{n-1,\\,0.975}\\cdot s/\\sqrt{n}"), e o IC95% é
![\\bar{x} \\pm
\\text{MoE}](https://latex.codecogs.com/png.image?%5Cdpi%7B110%7D&space;%5Cbg_white&space;%5Cbar%7Bx%7D%20%5Cpm%20%5Ctext%7BMoE%7D
"\\bar{x} \\pm \\text{MoE}"). Aplicada à **diferença pareada**
![A-B](https://latex.codecogs.com/png.image?%5Cdpi%7B110%7D&space;%5Cbg_white&space;A-B
"A-B") de cada cenário, é o intervalo de confiança do efeito médio do
tratamento (equivalente ao teste-t pareado). *Ressalva:* nas métricas
binárias (acerto/erro) a normalidade é aproximada — por isso reportamos
também o bootstrap (§4.2) e, na distância, o Wilcoxon (§4.3).

| Métrica (A−B)      |      Δ média | DP dos pares | Erro-padrão | MoE (t95) |           IC95% (t) |
| :----------------- | -----------: | -----------: | ----------: | --------: | ------------------: |
| Categoria crítica  | \+6.667 p.p. |       25.371 |       4.632 |     9.474 | \[-2.807, +16.140\] |
| Passo exato        | \-3.333 p.p. |       31.984 |       5.839 |    11.943 | \[-15.276, +8.610\] |
| Distância de passo |      \+0.044 |        0.379 |       0.069 |     0.141 |  \[-0.097, +0.186\] |

Interpretação: se o **IC95% (t) inclui zero**, não há efeito médio
distinguível na métrica. Na categoria, o efeito médio é +6.7 p.p. com IC
\[-2.8, +16.1\] p.p. (inclui zero). No passo exato, -3.3 p.p., IC
\[-15.3, +8.6\] p.p.. Na distância, Δ = +0.044, IC \[-0.097, +0.186\]. A
**magnitude do efeito** (Cohen d pareado) é 0.26 (categoria), -0.10
(passo) e 0.12 (distância) — valores próximos de zero indicam efeito
trivial mesmo quando o sinal aponta para um lado.

## 4.2 IC bootstrap (percentil, 5000 reamostragens)

O bootstrap não assume normalidade: reamostra os 30 pares com reposição
e lê os percentis 2,5% e 97,5% da distribuição da diferença média. É o
contraponto robusto ao t da §4.1 — quando os dois concordam, a conclusão
não depende da suposição gaussiana.

| Métrica (A−B)            | Δ média |     IC95% bootstrap | Inclui zero? |
| :----------------------- | ------: | ------------------: | -----------: |
| Categoria crítica (p.p.) | \+6.667 | \[+0.000, +16.667\] |          sim |
| Passo exato (p.p.)       | \-3.333 | \[-13.333, +6.667\] |          sim |
| Distância de passo       | \+0.044 |  \[-0.100, +0.178\] |          sim |

Comparando com a §4.1: o IC bootstrap da distância é \[-0.100, +0.178\]
e o IC-t é \[-0.097, +0.186\] — os dois métodos concordam sobre
incluir/excluir zero, o que reforça a conclusão.

## 4.3 Testes de hipótese pareados

| Teste                                            | Resultado | Leitura                      |
| :----------------------------------------------- | :-------- | :--------------------------- |
| McNemar — categoria crítica (binário)            | p = 0.480 | não distinguível (p = 0.480) |
| McNemar — passo exato (binário)                  | p = 1.000 | não distinguível (p = 1.000) |
| Wilcoxon pareado — distância de passo (contínuo) | p = 0.588 | não distinguível (p = 0.588) |
| teste-t pareado — distância de passo             | p = 0.526 | não distinguível (p = 0.526) |

O **McNemar** é o teste correto para as métricas binárias pareadas: ele
olha só os pares **discordantes** (um braço acerta, o outro erra) e
ignora os empates — que aqui são a maioria. Com poucos discordantes, o
teste tem pouco poder e o p tende a ser alto por **falta de amostra
discordante**, não por igualdade comprovada. O **Wilcoxon** trata a
distância como contínua e não-paramétrica (adequado à assimetria de
§2.3); o **teste-t pareado** é o correlato paramétrico, reportado ao
lado para transparência. Quando todos apontam “não distinguível”, a
leitura conjunta é de **ausência de efeito detectável**, não de
equivalência provada.

## 4.4 Vitórias pareadas

| Métrica             | A vence | B vence | Empate |
| :------------------ | ------: | ------: | -----: |
| cat\_acc\_critical  |       2 |       0 |     28 |
| step\_acc\_exact    |       1 |       2 |     27 |
| avg\_step\_distance |       4 |       1 |     25 |

Vitórias pareadas (de 30 cenários)

A contagem de vitórias é a evidência mais direta e sem suposição: em
quantos cenários A supera B, o inverso, ou empatam. O predomínio de
**empates** em todas as métricas é a assinatura de dois braços que
carregam os mesmos fatos semânticos — a paridade por construção —
diferindo só onde a telemetria/formato pesa. É essa escassez de
discordâncias que limita o poder estatístico com n = 30.

-----

# 5\. Discussão

**RQ1 (localização).** A telemetria estruturada a favor da baseline (B)
no passo exato (Δ = -3.3 p.p.) e, na distância contínua, a favor da
baseline (B) (Δ = +0.044; Wilcoxon não distinguível (p = 0.588)). Como o
IC da distância inclui zero, não há evidência de que a telemetria
melhore a localização fina. A hipótese de trabalho é que o bloco de
telemetria e o formato JSON adicionam contexto **mas também ruído** ao
redor do passo da causa, o que explicaria a leve desvantagem quando ela
aparece.

**RQ2 (classificação).** Em categoria crítica, A a favor da telemetria
(A) (Δ = +6.7 p.p.), efeito não distinguível (p = 0.480). A vantagem,
quando existe, concentra-se nas categorias semânticas ambíguas
(Invention/Plan Adherence), que são justamente as de maior
`category_std` — ou seja, onde o juiz mais **oscila entre reps**. Isso
enfraquece a atribuição do ganho ao tratamento: pode ser deslocamento de
ruído, não sinal.

**Síntese.** O conjunto de evidências é consistente com resultado nulo:
nenhuma métrica-manchete exclui zero. A dispersão intra-cenário (§2.2)
indica que uma fração relevante da variação é instabilidade do juiz
entre reps — motivo pelo qual **mais reps** devem apertar os IC e dar
uma leitura mais estável do sinal (ou confirmar sua ausência com mais
confiança). Resultado nulo aqui é achado legítimo e informativo:
telemetria-como-texto, mesmo estruturada e enriquecida, **não
demonstra** ajudar este juiz nesta escala.

-----

# 6\. Ameaças à validade

  - **Amostra e poder.** 1 juiz, 1 MAS, n = 30 cenários; muitos empates
    estruturais → pouco poder discordante. Os testes são **sugestivos,
    não confirmatórios**.
  - **Efeito-teto.** Passo ±3/±5 saturam; só passo-exato e distância
    discriminam.
  - **Instabilidade do juiz.** `step_std`/`category_std` \> 0 em vários
    cenários: parte do sinal A×B pode ser ruído de reps (mitigado por
    mais reps — experimento em curso).
  - **Fronteira semântica.** Invention ↔ Misinterpretation são
    adjacentes (ambas no Executor); a confusão entre elas contamina a
    acurácia de categoria dessas classes (PRD-08).
  - **Tratamento acoplado.** Em A, formato (JSON) e conteúdo
    (telemetria) mudam juntos; um eventual efeito não se decompõe entre
    os dois (ADR-0014).
  - **Normalidade aproximada.** Os IC-t sobre métricas binárias são
    aproximações; por isso o bootstrap e o Wilcoxon acompanham cada
    conclusão.

-----

# 7\. Conclusão

Nesta segunda execução (3 reps, n = 30), a telemetria (A) não supera a
baseline (B) em nenhuma métrica-manchete de forma distinguível:
categoria Δ = +6.7 p.p. (não distinguível (p = 0.480)), passo exato Δ =
-3.3 p.p., distância Δ = +0.044 (não distinguível (p = 0.588)). A
evidência é compatível com **resultado nulo**, com a ressalva de que a
instabilidade do juiz entre reps é uma fonte de ruído endereçável: a
re-execução com mais repetições deve **estreitar os intervalos de
confiança** e permitir afirmar o nulo — ou um efeito pequeno — com mais
segurança. Um segundo juiz sobre o mesmo corpus daria robustez adicional
à conclusão.
