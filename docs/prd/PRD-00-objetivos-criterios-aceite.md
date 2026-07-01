# PRD-00 — Objetivos e critérios de aceite

## 1. Contexto

Replicação parcial do AgentRx (diagnóstico de falhas em sistemas multiagente) estendida com **telemetria
OpenTelemetry**. Avalia-se se uma trajetória que carrega telemetria estruturada melhora o diagnóstico do AgentRx frente
a uma trajetória textual mais descritiva, semelhante à que o AgentRx foi avaliado.

O ambiente é um MAS simulado em LangGraph (Coordinator → Researcher → Tool → Executor → Evaluator) com **injeção
controlada de falhas**, o que dá ground truth determinístico de qual passo falhou e de qual categoria.

## 2. Perguntas de pesquisa e hipóteses

- **RQ1 — Localização.** A trajetória com telemetria estruturada aumenta a acurácia de localização do passo crítico do
  AgentRx frente à trajetória textual?
- **RQ2 — Categorização.** A telemetria estruturada aumenta a acurácia de classificação da categoria de falha?
- **H1/H2**: a telemetria ajuda mais nas falhas semânticas (Misinterpretation, Invention, Plan Adherence) do que nas de
  superfície (System Failure). Resultado nulo é um achado válido — não se assume vantagem a priori.

## 3. Escopo (categorias de falha)

1. System Failure — injeção no nó **Tool**.
2. Invalid Invocation — injeção no nó **Researcher**.
3. Misinterpretation of Tool Output — injeção no nó **Executor**.
4. Invention of New Information — injeção no nó **Executor**.
5. Instruction/Plan Adherence Failure — injeção no nó **Coordinator**.

Categorias do AgentRx fora de escopo (não injetáveis de forma honesta no MAS): Intent-Plan Misalignment, Under-specified
User Intent, Intent Not Supported, Guardrails Triggered. Declarar como ameaça à validade (cobertura parcial).

## 4. Desenho experimental

- **Fator independente**: representação da trajetória (braço A = com telemetria; braço B = estilo-AgentRx).
- **Variáveis dependentes**: acurácia de localização do passo crítico; acurácia de categoria; distância média de passo.
- **Controladas**: injeção **scriptada**; modo do agente **determinístico** por default (configurável); mesmo conteúdo
  semântico nos dois braços (diferem só na forma). Os modelos do agente e do juiz são parâmetros de `.env` (ver §4.1); o
  invariante é agente ≠ juiz, com juiz capaz, e ambos registrados por run.
- **Unidade**: cenário = pergunta + categoria de falha.

### 4.1 Modelos e determinismo (parametrizáveis via `.env`)

As escolhas de modelo são configuração, não premissa do estudo. `.env`: `AGENT_MODEL`, `AGENT_BASE_URL`, `JUDGE_MODEL`,
`JUDGE_BACKEND`, `USE_LLM`, `LLM_TEMPERATURE`. Invariante: agente ≠ juiz; juiz é um modelo capaz; os modelos
efetivamente usados são gravados no manifesto de cada run. Defaults sugeridos (não obrigatórios): agente = Llama3.1-8B
local; juiz = gpt-5-mini via Copilot CLI. Determinismo é o default recomendado (temperatura 0; `USE_LLM` off nos passos
não-críticos; seeds fixas) e também é configurável.

Dimensionamento: 30 cenários (6 por categoria) × 2 braços × 3 julgamentos do juiz = 180 execuções do AgentRx, a partir
de 30 traces base.

## 5. Glossário

- **Cenário**: par (pergunta de leitura, categoria de falha a injetar).
- **Execução base**: 1 rodada do MAS para um cenário → 1 trace OTel bruto.
- **Braço / representação**: uma das 2 trajetórias derivadas do trace bruto.
- **Julgamento**: 1 execução do AgentRx sobre 1 trajetória.
- **Ground truth de localização**: o nó/passo onde a falha foi injetada.
- **Ground truth de sucesso**: a resposta correta computada do catálogo.

## 6. Dois ground truths (manter separados)

- *Sucesso da tarefa* (`expected_answer`): valida que, sem injeção, o MAS resolve a pergunta — controle de sanidade.
- *Localização da falha* (`injection_node` / `critical_failure_step`): o que as RQs medem. Um run só entra na análise
  das RQs se este estiver limpo.

## 7. Critérios de aceite por marco

- **M1 — Dados e perguntas**: catálogo vendorizado com proveniência; gerador produz `benchmark_30.json` com 30 itens, 6
  por categoria, respostas computadas e reprodutíveis (mesma saída em 2 execuções).
- **M2 — MAS e falhas**: os 5 operadores de falha implementados; cada smoke test por falha passa (comportamento e ground
  truth conforme esperado).
- **M3 — Adapters**: de 1 trace OTel saem as 2 trajetórias; verificável que ambas carregam a mesma informação semântica
  e diferem só na estrutura.
- **M4 — AgentRx**: juiz roda em modo **judge-only** sobre uma trajetória de exemplo e devolve passo + categoria
  preditos, sem tocar o submódulo. O registro do domínio `product_catalog` fica **adiado** (ADR-0009); a perda das
  checagens de invariantes de policy é ameaça à validade declarada, não requisito de aceite do M4.
- **M5 — Experimento**: matriz completa executada; CSV consolidado (pergunta + trajetória + predição) gerado; scripts de
  análise produzem as métricas das RQs.

## 8. Não-objetivos

- Não há objetivo de publicação imediata (entrega é de mestrado).
- Não se reproduz o comportamento transacional/multi-turno do τ-bench.
- Não se busca um MAS de alto desempenho; o modelo do agente é configurável e até um modelo fraco como default é
  aceitável, porque a injeção é scriptada e o ground truth não depende da competência do agente.
