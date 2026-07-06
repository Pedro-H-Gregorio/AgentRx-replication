# ADR-0013 — Corpus do MAS namespaced por modelo em `data/internal/<mas_id>/`

- **Status**: Accepted
- **Data**: 2026-07-06
- **Relacionado**: PRD-00, PRD-01; ADR-0002, ADR-0012; change `namespace-runs-by-mas`

## Contexto

`data/internal/` guardava um único corpus (otel, trajetórias, ground truth, manifestos, saída do juiz). O MAS é
agnóstico de modelo (D2/D31): rodar o agente com um segundo modelo para comparar **sobrescrevia** o corpus do primeiro.
Faltava isolar cada corpus por modelo do MAS.

## Decisão

Todo o corpus de um run do MAS vive sob **`data/internal/<mas_id>/`** (`otel/`, `trajectory_telemetry/`,
`trajectory_agentrx/`, `ground_truth/`, `logs/`, `manifests/`), e a saída do juiz sob
**`data/internal/<mas_id>/agentrx/<judge_id>/`**. Os CSVs de resultado vão a
**`data/experiment/results/<mas_id>/<judge_id>/`** (estende o ADR-0012).

- **`mas_id`** = env `MAS_ID`; default = `AGENT_MODEL`. Usado **literalmente** (case e pontos preservados: `Llama3.1-8B`
  → `data/internal/Llama3.1-8B/`), só dobrando caracteres que quebram um caminho de pasta (`/ \ : espaço` → `-`), para
  nomes de provedor tipo `qwen/qwen-2.5:free` → `qwen-qwen-2.5-free`.
- **Fonte única de caminhos**: `src/agentrx_otel_poc/paths.py`. As constantes de módulo que fixavam paths
  (`planner.ARM_DIRS`/`GT_DIR`, `config.OUTPUT_ROOT`, `runner.DATA`, `derive.INTERNAL`, `collect.DATA_INTERNAL`)
  passaram a **derivar do `mas_id`**.
- A resolução usa a **config efetiva** passada ao run (`paths.resolve_mas_id(settings)`), não uma env global — um run
  programático com outro `AGENT_MODEL`/`MAS_ID` escreve no namespace certo (testes usam um `mas_id` isolado).
- `JudgeConfig` ganha `mas_id`; o manifesto do run (MAS e juiz) registra o `mas_id`.

## Consequências

- Rodar o MAS com outro modelo nunca sobrescreve um corpus anterior; comparar modelos vira colecionar corpora irmãos.
- O par MAS×juiz é a chave natural dos resultados (`results/<mas_id>/<judge_id>/`).
- O `mas_id` literal precisa ser um nome de pasta válido; caracteres de caminho são dobrados. Se `MAS_ID` não estiver
  setado, o default é o `AGENT_MODEL` exato.
- Não altera invariantes: o OTel bruto segue fonte única (ADR-0002), agora sob o namespace; nenhuma lógica de
  scoring/agregação/injeção muda.

## Alternativas descartadas

- **Slugificar o `mas_id`** (minúsculo, só `a-z0-9-`, como o `judge_id`): mais seguro para nomes arbitrários, mas
  ilegível e divergente da intenção do usuário (a pasta migrada é `Llama3.1-8B`, o nome literal do modelo).
- **Namespacear só o lado MAS** (deixar o juiz em `data/internal/agentrx/`): quebraria a correspondência
  corpus↔julgamento; o juiz de um modelo se misturaria com o de outro.
- **Ler `MAS_ID` só no import** (constantes de módulo fixas): um run programático com outro modelo escreveria no lugar
  errado.
