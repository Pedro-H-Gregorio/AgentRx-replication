# Arquitetura do repositório — Open Science e reprodutibilidade

Documento de arquitetura. Complementa os PRDs (`docs/prd/`): os PRDs dizem *o que* construir; este diz *como o
repositório se organiza* para ser reprodutível e aderente a Open Science. Princípio guia: **um terceiro deve reproduzir
o experimento do zero a partir do repositório, sem informação tácita.**

## 1. Princípios

- **Reprodutibilidade primeiro**: toda saída é função de entradas versionadas + código versionado + ambiente fixado.
  Nada depende de estado de máquina.
- **Fonte única de verdade**: o trace OTel bruto é o único artefato primário; todo o resto é derivado por código
  determinístico.
- **Proveniência explícita**: todo dado de terceiros é fixado por commit e documentado em `NOTICE.md`.
- **FAIR**: dados e código localizáveis, acessíveis, interoperáveis e reusáveis (formatos abertos: JSON, CSV, Markdown).

## 2. Arquitetura de módulos (dependência em sentido único)

```
settings ──▶ telemetry ──▶ graph (nós) ──▶ faults
                                  │
                                  ▼
                              adapters (parser → braços) ──▶ data/internal
scripts/ (generate, run_matrix, collect, analysis) orquestram o acima
AgentRx/ (submódulo) é consumido pelos scripts; NUNCA importado pelo MAS
```

Regras de dependência:

- O pacote do MAS (`src/agentrx_otel_poc/`) **não importa** o AgentRx. A ponte é feita por `scripts/` via arquivos
  (trajetória JSON), não por import.
- `adapters/` depende do `parser` único; nós e adapters não duplicam lógica de ordenação de passos (ver PRD-04).
- `faults.py` é o único lugar que define comportamento falho (ver PRD-03).

## 3. Arquitetura de dados

| Camada | Local | Versionado | Papel |
| -- | -- | -- | -- |
| Externo | `data/external/<fonte>/` | sim (+ NOTICE) | dados de terceiros, fixados por commit |
| Benchmark | `data/benchmark/` | sim | saída do gerador (perguntas) |
| Bruto | `data/internal/otel/` | sim | trace OTel = fonte de verdade |
| Derivado | `data/internal/{trajectory_*,metrics,...}/` | sim | projeções do bruto (regeráveis) |
| Saídas | `data/outputs/` | sim | CSVs e tabelas de métricas |

Invariante: apagar tudo em `data/internal/{trajectory_*,metrics}` e `data/outputs` e rodar `make run` reconstrói os
arquivos idênticos a partir do OTel + scripts.

## 4. Garantias de reprodutibilidade

- **Ambiente fixado**: `.python-version`, `pyproject.toml`/lock, `.env.example` (modelos e endpoints por variável; sem
  segredo no git).
- **Determinismo (default, configurável por `.env`)**: agente em temperatura 0; injeção scriptada; `use_llm` desligado
  nos passos não envolvidos na falha; seeds fixas no gerador. Os modelos do agente e do juiz são parâmetros
  (`AGENT_MODEL`, `JUDGE_MODEL`, `JUDGE_BACKEND`); o invariante é agente ≠ juiz, com juiz capaz.
- **Dados fixados por commit**: catálogo do tau-bench em `6f4b718...`; qualquer outra fonte idem. `main` nunca é usado
  como referência de dados.
- **Pipeline declarativo** (`Makefile`): `install → generate → smoke → run → collect → analyze`, cada alvo reexecutável
  isoladamente e idempotente.
- **Invariantes de integridade** (testados em CI): teste de **não-vazamento** (nenhuma trajetória contém
  `fault.injected` nem caminho de `faults.py`) e teste de **paridade** entre braços (ver PRD-06 §8).

## 5. Open Science — conformidade

- **Licenças**: `LICENSE` do projeto; `NOTICE.md` para terceiros (tau-bench MIT). O TRAIL é *gated* — **não**
  re-hospedar; referenciar por link e commit.
- **Citação**: `CITATION.cff` na raiz (autor, título, versão, ano).
- **Arquivamento**: ao submeter, criar release com tag e depositar no Zenodo para obter DOI; declarar o DOI no
  manuscrito.
- **Declaração de disponibilidade de dados**: o que é público (código, gerador, CSVs, trajetórias próprias) vs. o que é
  referenciado por proveniência (TRAIL).
- **Decisions log** (`docs/prd/PRD-08`): histórico append-only das decisões de método — rastreabilidade das escolhas
  científicas.

## 6. Qualidade e portões de CI

- `pre-commit` (format, lint, type-check) — já configurado.
- Testes unitários + os 5 smoke tests por falha (PRD-03) + paridade/não-vazamento.
- CI falha se: um smoke quebra, a paridade quebra, ou há vazamento de ground truth.

## 7. Verificação por terceiro (checklist de reprodução)

1. `git clone --recurse-submodules` + `make install`.
2. `make generate` → confere `benchmark_30.json` (30 itens, 6/categoria).
3. `make smoke` → 5 falhas passam.
4. `make run && make collect` → CSVs em `data/outputs/`.
5. `make analyze` → tabelas/figuras das RQs.

Se algum passo exigir conhecimento não escrito, é um defeito de reprodutibilidade e deve virar issue.
