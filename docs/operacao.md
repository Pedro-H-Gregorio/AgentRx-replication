# Guia operacional

Use este guia depois do [início rápido](../README.md). Ele reúne configuração e operação do experimento sem esconder o
caminho determinístico de primeira execução.

## Configuração

Copie o arquivo de exemplo e edite apenas o grupo necessário:

```bash
cp example.env .env
```

### MAS e agente

| Variável | Exemplo padrão | Uso e quando mudar |
| -- | -- | -- |
| `USE_LLM` | `false` | Ative para o agente narrar passos com LLM; desligado mantém o corpus offline e determinístico. |
| `USE_LLM_STRICT` | `false` | Ative no corpus final com LLM; uma resposta ausente ou erro depois das tentativas aborta o cenário, sem fallback de template. |
| `AGENT_MODEL` | `Gemma3:27b` | Nome enviado ao endpoint do agente. Escolha um modelo disponível no provedor. |
| `AGENT_BASE_URL` | `http://localhost:11434/v1` | Endpoint OpenAI-compatible do agente. Declare explicitamente para registrar o endpoint efetivo. |
| `AGENT_API_KEY` | `ollama` | Credencial do endpoint; nunca versione uma chave real. |
| `MAS_ID` | vazio | Nome opcional do corpus. Vazio usa `AGENT_MODEL` literalmente, preservando corpora de modelos distintos. |
| `LLM_TEMPERATURE` | `0` | Temperatura do agente; mantenha zero para reprodutibilidade. |
| `LLM_TIMEOUT_SECONDS` | `30` | Limite de espera de uma chamada do agente. |
| `AGENT_MAX_RETRIES` | `5` | Tentativas extras para 429, 5xx e timeout do agente. |
| `AGENT_RETRY_BASE_SECONDS` | `5` | Espera inicial do backoff do agente. |
| `AGENT_RETRY_MAX_SECONDS` | `120` | Teto de cada espera do backoff do agente. |
| `OTEL_SERVICE_NAME` | `agentrx-otel-poc` | Nome do serviço gravado no trace OTel. |

Com `USE_LLM=true`, a injeção de falha continua scriptada. O manifesto registra o modelo, endpoint, temperatura e
quantos passos usaram fallback. Para corpus final, use `USE_LLM_STRICT=true` e verifique que `fallback_steps` é zero nos
manifestos.

### Juiz AgentRx

| Variável | Exemplo padrão | Uso e quando mudar |
| -- | -- | -- |
| `JUDGE_BACKEND` | `stub` | `stub` é offline; `openai`, `copilot` e `codex` usam seus respectivos shims/CLI. |
| `JUDGE_MODEL` | vazio | Modelo do juiz. Deixe vazio no backend `codex` para o default do plano. |
| `JUDGE_BASE_URL` | vazio | Endpoint OpenAI-compatible; obrigatório no backend `openai`. |
| `JUDGE_API_KEY` | vazio | Credencial do endpoint OpenAI-compatible. |
| `JUDGE_TIMEOUT_SECONDS` | `600` | Limite por execução do juiz. |
| `JUDGE_TEMPERATURE` | `0` | Temperatura usada pelo shim `openai`; Copilot não a expõe. |
| `JUDGE_REPS` | `10` | Repetições por trajetória; `REPS=` na linha de comando a substitui. |
| `JUDGE_MAX_RETRIES` | `5` | Tentativas extras do shim `openai` para 429 e 5xx. |
| `JUDGE_RETRY_BASE_SECONDS` | `5` | Espera inicial de retry do juiz. |
| `JUDGE_RETRY_MAX_SECONDS` | `120` | Teto de espera de retry do juiz. |
| `JUDGE_CODEX_BIN` | `codex` | Override opcional do binário Codex. Deixe a linha comentada se não precisar. |
| `JUDGE_CODEX_ARGS` | vazio | Flags opcionais para `codex exec`. |
| `JUDGE_VERBOSE` | ausente | Defina `1` apenas para imprimir todo `agentrx.log` de cada repetição. |

`copilot` exige `copilot login`; `codex` exige `codex login`. O juiz deve ser distinto do agente e capaz o suficiente
para a tarefa. O modelo efetivamente usado fica no manifesto e no índice de reps.

## Executar e verificar

### Caminho determinístico

```bash
make generate
make simulate
make derive
make smoke
make check
```

`make simulate` cria o corpus e valida traces; `make derive` valida não-vazamento, paridade e IR. Consulte o
[dicionário interno](../data/internal/README.md) para os caminhos produzidos.

### Juiz, coleta e análise

```bash
make smoke-judge       #opcional        # 5 cenários × 2 braços × 1 rep, stub offline
make smoke-judge-live  #opcional        # mesmo recorte com backend configurado
make judge             # 30 cenários × 2 braços × JUDGE_REPS
make collect
make analyze
```

`make collect` escreve três CSVs e executa `make validate-csv`. `make analyze` precisa de `Rscript`, Pandoc e dos
pacotes R diretos listados em `scripts/analysis/requirements.R` (versões fixadas em `renv.lock`); ele só lê CSVs, não
importa AgentRx nem recalcula as métricas. Além das seis tabelas, produz `analysis_report.md` e PNGs relativos em
`analysis_report_files/figure-gfm/`, sob `data/experiment/analysis/<mas_id>/<judge_id>/`. A saída é Markdown GFM; o
fluxo não gera HTML. Veja os dicionários de [resultados](../data/experiment/results/README.md) e
[análise](../data/experiment/analysis/README.md).

## Escolha como executar a análise

Após `make collect`, escolha **uma** das alternativas abaixo. Ambas leem o mesmo `metricas.csv` e `runs_long.csv`,
escrevem os seis CSVs, o Markdown e os PNGs em `data/experiment/analysis/<mas_id>/<judge_id>/` e não geram HTML.

Sem `METRICS`, os alvos resolvem a execução padrão a partir da configuração do MAS e do juiz. Para analisar um resultado
específico, informe sempre `METRICS=data/experiment/results/<mas_id>/<judge_id>/metricas.csv`.

### Opção A — R local

Use se já tiver R 4.1.2 instalado. Na primeira vez (ou após alterar `renv.lock`), restaure o ambiente isolado do
projeto:

```bash
make r-restore
```

Depois, gere a análise padrão:

```bash
make analyze
```

`make r-restore` é o único passo que instala ou baixa pacotes. A biblioteca `renv/library/` e o cache `.renv/` ficam
fora do versionamento; `make analyze` não acessa a rede e indica como restaurar o ambiente se ele estiver ausente.

### Opção B — Docker (sem R local)

Use se não tiver R instalado, mas tiver Docker. O alvo `make analyze-container` constrói a imagem com R 4.1.2, Pandoc e
o `renv.lock`; depois roda a mesma análise no repositório montado, preservando o UID:GID do usuário anfitrião.

```bash
make analyze-container
```

Esse caminho requer Docker, mas não `Rscript` no anfitrião. A primeira execução baixa e constrói a imagem; as
posteriores reutilizam suas camadas enquanto o lockfile não mudar.

As células são valores de apresentação para as tabelas do artigo. Percentuais, contagens e estatísticas são serializados
como texto para preservar formatação; células não aplicáveis são escritas vazias, não como `NA`. Requer `Rscript`, os
pacotes R de `scripts/analysis/requirements.R` e Pandoc. A geração não instala dependências nem acessa a rede.

### Fatiar ou retomar a matriz

```bash
make judge FAULT="System Failure" ARM=telemetry REPS=1
make judge SCENARIOS="q01_t1_electric_kettle q07_t3_electric_kettle"
make judge ONLY=errors
make judge FORCE=1
make collect EXPERIMENT=judge-stub
make analyze METRICS=data/experiment/results/<mas_id>/<judge_id>/metricas.csv
```

Sem `FORCE=1`, reps com veredito válido são puladas. `ONLY=errors` refaz apenas reps sem veredito. O manifesto descreve
a última invocação, enquanto `runs_index.jsonl` é reconstruído ao fim da sessão.

### Corpus final com agente LLM

Configure um endpoint do agente e então execute:

```bash
USE_LLM=true USE_LLM_STRICT=true make simulate
make derive
make judge
make collect
make analyze
```

Antes de publicar o corpus, confirme `fallback_steps: 0` em cada manifesto. O modo estrito evita misturar prosa LLM e
template depois de uma falha de transporte.

### Limpar dados de um corpus

Os comandos abaixo removem somente artefatos do `<mas_id>` resolvido pelo `.env`. Eles não alteram benchmark nem
catálogo, mas apagam resultados gerados; confira o namespace antes de executar.

```bash
make clean-data
make clean-data-judge
make clean-data-csv
```

`make experiment` compõe `simulate → derive → judge → collect → analyze`, para no primeiro erro e pode ser reexecutado.
Prefira passos individuais para investigar falhas.
