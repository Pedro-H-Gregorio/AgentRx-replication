PYTHON ?= uv run python
PYTEST ?= uv run pytest -q

.PHONY: install check generate simulate derive smoke clean-data \
        validate-benchmark validate-traces validate-trajectories \
        judge smoke-judge smoke-judge-live validate-judge clean-data-judge

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

# Reset dos artefatos de run (mantém benchmark + catálogo). Idempotente.
clean-data:
	rm -f data/internal/otel/*.otel.json \
	      data/internal/trajectory_telemetry/*.json \
	      data/internal/trajectory_agentrx/*.json \
	      data/internal/ground_truth/*.ground_truth.json \
	      data/internal/logs/*.log \
	      data/internal/manifests/*.json

clean-data-judge:
		find data/internal/agentrx -mindepth 1 -not -name .gitkeep -delete 2>/dev/null || true

# --- Validadores isolados ---


validate-benchmark:
	$(PYTEST) tests/test_benchmark.py

validate-traces:
	$(PYTEST) tests/test_traces.py

validate-trajectories:
	$(PYTEST) tests/test_trajectories.py

validate-judge:
	$(PYTEST) tests/test_judge_runs.py
