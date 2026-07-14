# Testes

A suíte protege os invariantes experimentais e também os contratos de produção dos artefatos. Execute `uv run pytest`
para a suíte completa ou escolha a menor fatia que cobre a alteração.

## Grupos de teste

| Área | Arquivos principais | O que garantem |
| -- | -- | -- |
| Benchmark e tarefas | `test_benchmark.py`, `test_tasks.py` | 30 cenários balanceados, schema, respostas determinísticas e labels coerentes. |
| Falhas e traces | `test_faults.py`, `test_traces.py`, `smoke/test_smoke_faults.py` | Operadores atingem somente o nó-alvo, trace e ground truth são coerentes, uma smoke por categoria. |
| Trajetórias e imparcialidade | `test_trajectories.py`, `test_impartiality.py`, `test_r5_weak.py`, `test_execution_context.py` | Não-vazamento, paridade semântica, IR válida e logs cegos ao gabarito. |
| Agente e namespace | `test_agent_backoff.py`, `test_agent_resilience.py`, `test_manifest.py`, `test_paths_namespace.py` | Retry, modo estrito, manifesto reprodutível e isolamento por `mas_id`. |
| Juiz | `test_judge_scoring.py`, `test_judge_shims.py`, `test_judge_runs.py`, `test_run_judge_cli.py` | Scoring local, shims, matriz retomável, índice e CLI. |
| Coleta e resultados | `test_collect_csv.py`, `test_collect_parity.py`, `test_csv_integrity.py` | CSVs estáveis, paridade com fixtures do AgentRx, chaves e fórmulas. |
| Documentação | `test_documentation.py` | Guias existem e dicionários cobrem schemas declarados. |

## Comandos

```bash
uv run pytest
uv run pytest tests/test_trajectories.py tests/test_impartiality.py
uv run pytest tests/test_collect_csv.py tests/test_collect_parity.py
make validate-benchmark
make validate-traces
make validate-trajectories
make validate-judge
make validate-csv
make smoke
make smoke-judge
make check
```

`make smoke-judge` força backend `stub`, sem rede. `make smoke-judge-live` usa o backend configurado e é uma verificação
de integração, não requisito para CI local.

## Fixtures

- `fixtures/golden/`: entrada de juiz e CSVs esperados para o coletor.
- `fixtures/parity/`: casos congelados a partir do `compute_stats` do AgentRx; os testes não importam o submódulo para
  recomputá-los.
- Trajetórias e traces do corpus versionado: usados pelos validadores de artefato.

## Escolha por alteração

- Benchmark, templates ou catálogo: `test_benchmark.py` e `test_tasks.py`.
- Falhas, nós, OTel ou adapters: `make smoke`, `test_traces.py`, `test_trajectories.py`, `test_impartiality.py`.
- Configuração do agente ou namespace: testes de agente, manifesto e paths.
- Juiz ou shims: testes de scoring, shims, CLI e `make smoke-judge`.
- Coletor, schema ou análise: testes de coleta, integridade e documentação.

Não reduza guardas de não-vazamento, paridade ou imparcialidade para acomodar uma mudança: elas validam o desenho
experimental, não detalhes de implementação.
