# PRD-10 — Contrato do dicionário de dados dos CSVs

## 1. Objetivo

Definir o contrato dos três CSVs de resultado do experimento. O dicionário campo a campo, co-localizado às saídas para
descoberta imediata, está em [`data/experiment/results/README.md`](../../data/experiment/results/README.md). Ele é
implementado por `csv_writer.py`; este PRD preserva o contrato, as regras de integridade e os critérios de aceite.

## 2. Saídas e granularidade

`make collect` escreve em `data/experiment/results/<mas_id>/<judge_id>/`:

- `runs_long.csv`: uma linha por execução do juiz.
- `trajectory_index.csv`: uma linha por trajetória e braço, ligando-a ao OTel bruto.
- `metricas.csv`: uma linha por trajetória e braço, agregada das repetições.

O braço é uma coluna, nunca arquivo. `scenario_id` + `arm` é a chave de junção. Convenções de tipo, origem, significado,
fórmulas e campos espelho `*_name` estão no dicionário co-localizado.

## 3. Contrato de agregação

O coletor agrega todas as failures de reps com veredito (`ok` e `skipped`) num pool achatado, fiel ao
`compute_stats`/`analysis()` do AgentRx. Reps `error` não entram no pool, mas reduzem `n_judge_runs`; nenhuma linha
desaparece silenciosamente. O coletor é neutro: não executa teste estatístico, não compara braços e não repondera
linhas.

No MAS há exatamente uma falha anotada por cenário. Portanto `cat_acc_any`, `cat_acc_earliest`, `cat_acc_terminal` e
`cat_acc_critical` coincidem. No TRAIL, múltiplos labels podem diferenciá-las.

## 4. Regras de integridade

- `scenario_id` + `arm` une os três CSVs sem linha órfã.
- Campos `bool01` pertencem a `{0,1}`; acurácias por execução pertencem a `[0,1]`.
- `avg_step_distance_norm` usa `trajectory_length`, igual a `n_steps` do índice.
- Cada linha de `metricas.csv` é reconstruível a partir das linhas do mesmo par em `runs_long.csv` e de
  `raw_failures_json`.
- Com insumos idênticos, os três CSVs são byte-idênticos entre execuções.

## 5. Critérios de aceite

- Todo campo emitido pelo coletor tem nome, tipo, origem e significado no dicionário co-localizado.
- Nomes e fórmulas conferem com `csv_writer.py`, `aggregate.py` e o exemplo de referência em
  `docs/examples/metrics-reference.md`.
- `make validate-csv` verifica as regras de integridade; testes golden e de paridade protegem a agregação sem importar o
  submódulo AgentRx.
