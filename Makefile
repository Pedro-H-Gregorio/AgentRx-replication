PYTHON ?= uv run python
PYTEST ?= uv run pytest -q
LATEX_MAIN ?= manuscript/paper/main.tex

.PHONY: install check generate simulate derive smoke clean-data \
        validate-benchmark validate-traces validate-trajectories \
        judge smoke-judge smoke-judge-live validate-judge clean-data-judge \
        collect validate-csv clean-data-csv experiment analyze r-restore \
        analyze-container \
        latex-wrap latex-check-wrap latex-lint

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

judge:
	$(PYTHON) scripts/run_judge.py $(JUDGE_ARGS)
	$(MAKE) validate-judge

smoke-judge:
	JUDGE_BACKEND=stub $(PYTHON) scripts/run_judge.py --smoke --force
	$(MAKE) validate-judge

smoke-judge-live:
	$(PYTHON) scripts/run_judge.py --smoke --force --preflight
	$(MAKE) validate-judge

COLLECT_ARGS = $(if $(EXPERIMENT),--experiment $(EXPERIMENT),)
collect:
	$(PYTHON) scripts/collect_agentrx.py $(COLLECT_ARGS)
	$(MAKE) validate-csv

RESOLVE_JUDGE = $(PYTHON) -c "import sys;sys.path.insert(0,'src');from agentrx_otel_poc.judge.config import JudgeConfig;print(JudgeConfig.from_settings().experiment_id())"
R_ANALYSIS_IMAGE ?= agentrx-otel-analysis:local
R_ANALYSIS_PACKAGES = readr,dplyr,tidyr,scales,boot,broom,rmarkdown,knitr,ggplot2

r-restore:
	Rscript scripts/analysis/restore_renv.R

analyze:
	@metrics="$(METRICS)"; \
	if [ -z "$$metrics" ]; then \
	  mas=$$($(RESOLVE_MAS)); judge=$$($(RESOLVE_JUDGE)); \
	  metrics="data/experiment/results/$$mas/$$judge/metricas.csv"; \
	fi; \
	r_library=$$(Rscript --vanilla -e 'cat(file.path("renv", "library", paste0("R-", R.version$$major, ".", sub("[.].*", "", R.version$$minor)), R.version$$platform))'); \
	if [ ! -d "$$r_library" ]; then \
	  echo "Ambiente R ausente. Execute 'make r-restore' ou use 'make analyze-container'."; \
	  exit 1; \
	fi; \
	R_ANALYSIS_LIBRARY="$$r_library" R_LIBS="$$r_library$${R_LIBS:+:$$R_LIBS}" Rscript --vanilla -e 'packages <- strsplit("$(R_ANALYSIS_PACKAGES)", ",")[[1]]; missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]; if (length(missing)) stop("Ambiente R incompleto: ", paste(missing, collapse = ", "), ". Execute make r-restore.", call. = FALSE)'; \
	echo "analyze: $$metrics"; \
	R_ANALYSIS_LIBRARY="$$r_library" R_LIBS="$$r_library$${R_LIBS:+:$$R_LIBS}" Rscript scripts/analysis/c8_run.R "$$metrics" && \
	R_ANALYSIS_LIBRARY="$$r_library" R_LIBS="$$r_library$${R_LIBS:+:$$R_LIBS}" Rscript scripts/analysis/c8_render_report.R "$$metrics"

analyze-container:
	@metrics="$(METRICS)"; \
	if [ -z "$$metrics" ]; then \
	  mas=$$($(RESOLVE_MAS)); judge=$$($(RESOLVE_JUDGE)); \
	  metrics="data/experiment/results/$$mas/$$judge/metricas.csv"; \
	fi; \
	echo "analyze-container: $$metrics"; \
	docker build --quiet --tag "$(R_ANALYSIS_IMAGE)" --file docker/analysis/Dockerfile . && \
	docker run --rm --user "$$(id -u):$$(id -g)" -e HOME=/tmp \
	  --volume "$(CURDIR):/workspace" --workdir /workspace "$(R_ANALYSIS_IMAGE)" \
	  /bin/sh -ceu 'Rscript scripts/analysis/c8_run.R "$$1"; Rscript scripts/analysis/c8_render_report.R "$$1"' -- "$$metrics"

# Composition only: each target retains validation and idempotence.
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

RESOLVE_MAS = $(PYTHON) -c "import sys;sys.path.insert(0,'src');from agentrx_otel_poc import paths;from agentrx_otel_poc.settings import Settings;print(paths.resolve_mas_id(Settings()))"

# Only the current corpus namespace is removed; benchmark and catalog remain.
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

latex-wrap:
	latexindent -m -l=.latexindent.yaml -wd $(LATEX_MAIN)

latex-check-wrap:
	latexindent -m -l=.latexindent.yaml -k $(LATEX_MAIN)

latex-lint:
	chktex -q $(LATEX_MAIN)
