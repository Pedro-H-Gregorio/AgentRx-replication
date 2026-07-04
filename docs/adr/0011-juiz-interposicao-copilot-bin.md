# ADR-0011 — Fronteira de integração com o juiz por interposição do binário do Copilot CLI

- **Status**: Accepted
- **Data**: 2026-07-03
- **Relacionado**: PRD-05, PRD-08; ADR-0004, ADR-0009; change `run-judge-experiment`

## Contexto

O experimento precisa julgar as trajetórias variando o modelo do juiz — ora um serviço OpenAI-compatible por `base_url`
(Ollama/vLLM/OpenRouter), ora o CLI do GitHub Copilot. O AgentRx (submódulo intocável, regra 6) só expõe três clientes:
`azure` (exige token Azure AD via `DefaultAzureCredential` — impraticável contra servidor local), `trapi` (interno da
Microsoft) e `copilot`. O cliente `copilot` não chama API alguma: resolve um **binário** por `AGENT_VERIFY_COPILOT_BIN`
e o executa por subprocess com um contrato simples (`-s --no-ask-user --allow-all --output-format text [--model M]`,
prompt via stdin, resposta em texto no stdout, além de responder a `--version`). Não há cliente "OpenAI genérico" onde
encaixar um `base_url`.

## Decisão

A integração com o juiz é uma **fronteira por interposição de binário**: o orquestrador (`scripts/run_judge.py` + pacote
`agentrx_otel_poc.judge`) aponta `AGENT_VERIFY_COPILOT_BIN` para um executável escolhido por `JUDGE_BACKEND`, e sempre
invoca `AgentRx/run.py --endpoint copilot`.

A regra é geral: **um backend é qualquer executável que honre o contrato do Copilot CLI**. `copilot` usa a CLI real;
qualquer outro valor de `JUDGE_BACKEND` resolve para um shim de mesmo nome em `scripts/judge_shims/`. Soltar um shim
novo nesse diretório adiciona um backend **sem tocar no orquestrador** (o código não conhece a lista de backends; só
verifica se o shim existe). Os shims que acompanham o projeto:

- `openai` — encaminha o prompt para `{JUDGE_BASE_URL}/chat/completions` (Ollama/vLLM/OpenRouter), com backoff em
  rate-limit (429/5xx);
- `codex` — dirige a CLI do Codex por `codex exec` (captura só a mensagem final);
- `stub` — devolve um veredito JSON fixo e determinístico, sem rede (smoke offline).

Como camada de robustez da fronteira, `--preflight` sonda o backend com um prompt trivial (mesma invocação real) e
aborta a matriz cedo se ele não responder (auth quebrada, modelo inválido). O orquestrador traduz as vars `JUDGE_*` para
as `AGENT_VERIFY_COPILOT_*` que o submódulo lê; o usuário nunca configura `AGENT_VERIFY_*` diretamente. O pacote do
MAS/orquestrador **nunca importa** `agentrx` — a integração é por subprocess e arquivos, complementando o ADR-0009
(judge-only, IR canônica pré-plantada).

## Consequências

- (+) Troca CLI ↔ `base_url` só por `.env`, sem editar o submódulo.
- (+) O backend `stub` transforma o caminho real do experimento em smoke determinístico e offline (mesma fiação, sem
  juiz).
- (+) A superfície de acoplamento com o AgentRx fica num contrato pequeno e testável (teste de contrato dos shims prende
  a suposição).
- (−) Depende do contrato do `copilot_cli.py` do commit fixado do submódulo; se ele mudar, os shims e o teste de
  contrato precisam acompanhar.
- (−) O `openai` achata as mensagens numa única (como o cliente copilot faz); modelos locais fracos podem devolver JSON
  malformado → `INCONCLUSIVE` (resultado experimental, declarado como ameaça à validade).

## Alternativas descartadas

- **Endpoint `azure` + proxy local**: o cliente exige credencial Azure AD; inviável apontar para servidor local com
  `api_key`.
- **Novo cliente OpenAI dentro do AgentRx**: viola a regra 6 (não tocar no submódulo).
- **Importar `agentrx.judge` direto do Python**: acopla a internals do submódulo e abandona a integração caixa-preta por
  arquivos.
