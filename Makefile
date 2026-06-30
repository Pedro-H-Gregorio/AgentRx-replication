PYTHON ?= uv run python
PYTEST ?= uv run pytest -q

.PHONY: install check generate simulate derive smoke \
        validate-benchmark validate-traces validate-trajectories

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

# --- Validadores isolados ---

validate-benchmark:
	$(PYTEST) tests/test_benchmark.py

validate-traces:
	$(PYTEST) tests/test_traces.py

validate-trajectories:
	$(PYTEST) tests/test_trajectories.py
