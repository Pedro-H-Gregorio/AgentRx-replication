PYTHON ?= uv run python
PYTEST ?= uv run pytest -q
LATEX_MAIN ?= manuscript/paper/main.tex

.PHONY: install check generate simulate derive smoke clean-data \
        validate-benchmark validate-traces validate-trajectories \
        judge smoke-judge smoke-judge-live validate-judge clean-data-judge \
        collect validate-csv clean-data-csv experiment analyze \
        latex-wrap latex-check-wrap latex-lint

# Seleção do passo judge (todos opcionais):
#   make judge SCENARIOS="q01_... q07_..."   FAULT="System Failure"
#   make judge ARM=telemetry REPS=1 ONLY=errors FORCE=1
JUDGE_ARGS = $(if $(SCENARIOS),--scenarios $(SCENARIOS),) \
             $(if $(FAULT),--fault "$(FAULT)",) \
             $(if $(ARM),--arms $(ARM),) \
             $(if $(REPS),--reps $(REPS),) \
             $(if $(filter errors,$(ONLY)),--only-errors,) \
             $(if $(FORCE),--force,)

install:
	./scripts/init.sh

check:
	uv run pre-commit run --all-files
	$(PYTHON) scripts/check_file_size.py

# --- Pipeline segregado (cada passo valida a própria saída) ---

generate:
	$(PYTHON) scripts/generate_benchmark.py
	$(MAKE) validate-benchmark

simulate:
	$(PYTHON) scripts/simulate.py
	$(MAKE) validate-traces

derive:
	$(PYTHON) scripts/derive_trajectories.py
	$(MAKE) validate-trajectories

smoke:
	$(PYTEST) tests/smoke

# --- Julgamento no AgentRx (C6, judge-only, submódulo intocado) ---

# Roda a matriz (backend via JUDGE_BACKEND no .env). Sem args: todas as
# trajetórias, pulando reps já julgadas. Ver JUDGE_ARGS acima para fatias.
judge:
	$(PYTHON) scripts/run_judge.py $(JUDGE_ARGS)
	$(MAKE) validate-judge

# Smoke offline determinístico: 1 cenário por categoria × 2 braços × 1 rep.
smoke-judge:
	JUDGE_BACKEND=stub $(PYTHON) scripts/run_judge.py --smoke --force
	$(MAKE) validate-judge

# Smoke com o juiz real configurado no .env. --preflight aborta cedo se o
# backend não responder (auth quebrada, modelo inválido) antes das reps.
smoke-judge-live:
	$(PYTHON) scripts/run_judge.py --smoke --force --preflight
	$(MAKE) validate-judge

# --- Coleta dos CSVs de resultado (C7, PRD-10) ---

# Transforma os vereditos brutos nos 3 CSVs por experimento. Sem args: todos os
# experimentos em disco. Fatia com EXPERIMENT=<experiment_id>.
COLLECT_ARGS = $(if $(EXPERIMENT),--experiment $(EXPERIMENT),)
collect:
	$(PYTHON) scripts/collect_agentrx.py $(COLLECT_ARGS)
	$(MAKE) validate-csv

# --- Análise A/B posterior ao C7 (C8): tabelas .csv, sem figuras ---

# Resolve o judge_id efetivo (experiment_id derivado do .env), como o collect.
RESOLVE_JUDGE = $(PYTHON) -c "import sys;sys.path.insert(0,'src');from agentrx_otel_poc.judge.config import JudgeConfig;print(JudgeConfig.from_settings().experiment_id())"

# Gera as 6 tabelas de análise (só CSV; nenhuma figura) a partir do metricas.csv
# de um experimento, em data/experiment/analysis/<mas_id>/<judge_id>/. Idempotente.
# Sem args resolve mas_id/judge_id do .env; fatie com METRICS=<caminho/metricas.csv>.
analyze:
	@metrics="$(METRICS)"; \
	if [ -z "$$metrics" ]; then \
	  mas=$$($(RESOLVE_MAS)); judge=$$($(RESOLVE_JUDGE)); \
	  metrics="data/experiment/results/$$mas/$$judge/metricas.csv"; \
	fi; \
	echo "analyze: $$metrics"; \
	Rscript scripts/analysis/c8_run.R "$$metrics"

# --- Orquestração do experimento (composição dos passos segregados) ---

# Encadeia simulate → derive → judge → collect num só comando. NÃO é um "run-all"
# com caminho próprio: apenas compõe os alvos segregados (cada um valida a própria
# saída e é idempotente, então re-executar RETOMA de onde parou). Fail-fast: para
# no primeiro passo que falhar e sinaliza QUAL foi.
experiment:
	@for step in simulate derive judge collect; do \
	  echo "▶ experiment: $$step"; \
	  $(MAKE) --no-print-directory $$step || { \
	    echo "✗ experiment: passo '$$step' FALHOU — corrija e re-execute (retoma daqui)"; \
	    exit 1; \
	  }; \
	  echo "✓ experiment: $$step ok"; \
	done; \
	echo "✓✓ experiment completo: simulate → derive → judge → collect"

# Resolve o mas_id efetivo (MAS_ID ou AGENT_MODEL literal) em tempo de recipe.
RESOLVE_MAS = $(PYTHON) -c "import sys;sys.path.insert(0,'src');from agentrx_otel_poc import paths;from agentrx_otel_poc.settings import Settings;print(paths.resolve_mas_id(Settings()))"

# Reset dos artefatos de run do corpus atual (mantém benchmark + catálogo).
# Mira só data/internal/<mas_id>/ — outros corpora ficam intactos. Idempotente.
clean-data:
	@mas=$$($(RESOLVE_MAS)); \
	rm -f data/internal/$$mas/otel/*.otel.json \
	      data/internal/$$mas/trajectory_telemetry/*.json \
	      data/internal/$$mas/trajectory_agentrx/*.json \
	      data/internal/$$mas/ground_truth/*.ground_truth.json \
	      data/internal/$$mas/logs/*.log \
	      data/internal/$$mas/manifests/*.json; \
	echo "clean-data: limpou data/internal/$$mas/"

clean-data-judge:
	@mas=$$($(RESOLVE_MAS)); \
	find data/internal/$$mas/agentrx -mindepth 1 -not -name .gitkeep -delete 2>/dev/null || true

clean-data-csv:
	@mas=$$($(RESOLVE_MAS)); \
	find data/experiment/results/$$mas -mindepth 1 -not -name .gitkeep -delete 2>/dev/null || true

# --- Validadores isolados ---


validate-benchmark:
	$(PYTEST) tests/test_benchmark.py

validate-traces:
	$(PYTEST) tests/test_traces.py

validate-trajectories:
	$(PYTEST) tests/test_trajectories.py

validate-judge:
	$(PYTEST) tests/test_judge_runs.py

validate-csv:
	$(PYTEST) tests/test_csv_integrity.py

# --- Manuscrito LaTeX ---

# Reflui parágrafos longos para 120 colunas, como o wrap de Markdown do repo.
latex-wrap:
	latexindent -m -l=.latexindent.yaml -wd $(LATEX_MAIN)

# Falha se o LaTeX precisaria ser reformatado por latex-wrap.
latex-check-wrap:
	latexindent -m -l=.latexindent.yaml -k $(LATEX_MAIN)

# Lint sem reescrever o manuscrito.
latex-lint:
	chktex -q $(LATEX_MAIN)
