"""Each run records an effective-config manifest (reproducibility, PRD-00 §4.1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentrx_otel_poc import paths
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.tasks import load_benchmark

ROOT = Path(__file__).resolve().parent.parent
MAN_DIR = paths.manifests_dir(paths.resolve_mas_id(Settings()))
REQUIRED = {
    "run_id",
    "task_id",
    "use_llm",
    "agent_model",
    "agent_base_url",
    "llm_temperature",
    "otel_service_name",
}

RUN_IDS = sorted(p.stem for p in MAN_DIR.glob("*.json")) if MAN_DIR.exists() else []


def test_manifests_exist() -> None:
    assert RUN_IDS, "no manifests — run `make simulate` first"
    # one manifest per benchmark scenario
    assert set(RUN_IDS) >= set(load_benchmark())


@pytest.mark.parametrize("run_id", RUN_IDS)
def test_manifest_has_required_config(run_id: str) -> None:
    manifest = json.loads((MAN_DIR / f"{run_id}.json").read_text(encoding="utf-8"))
    assert REQUIRED <= set(manifest), f"{run_id}: missing {REQUIRED - set(manifest)}"
    assert manifest["run_id"] == run_id
    assert isinstance(manifest["use_llm"], bool)
