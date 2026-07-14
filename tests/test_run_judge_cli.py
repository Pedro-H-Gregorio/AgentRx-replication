"""CLI defaults for the judge runner."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import os
from pathlib import Path

import pytest

import agentrx_otel_poc.settings as settings_module
from agentrx_otel_poc.settings import Settings

ROOT = Path(__file__).resolve().parent.parent
RUN_JUDGE_PATH = ROOT / "scripts" / "run_judge.py"


def _load_run_judge():
    spec = importlib.util.spec_from_file_location("run_judge_cli", RUN_JUDGE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _args(*, smoke: bool = False, reps: int | None = None) -> argparse.Namespace:
    return argparse.Namespace(smoke=smoke, reps=reps)


def test_smoke_forces_one_rep() -> None:
    run_judge = _load_run_judge()
    settings = Settings(judge_reps=10)

    assert run_judge._resolve_reps(_args(smoke=True, reps=7), settings) == 1


def test_explicit_reps_override_settings() -> None:
    run_judge = _load_run_judge()
    settings = Settings(judge_reps=10)

    assert run_judge._resolve_reps(_args(reps=2), settings) == 2


def test_settings_reps_used_when_cli_omits_reps() -> None:
    run_judge = _load_run_judge()
    settings = Settings(judge_reps=6)

    assert run_judge._resolve_reps(_args(), settings) == 6


def test_settings_reads_judge_reps_from_environment(monkeypatch) -> None:
    previous = os.environ.get("JUDGE_REPS")
    monkeypatch.setenv("JUDGE_REPS", "8")
    reloaded = importlib.reload(settings_module)
    try:
        assert reloaded.Settings().judge_reps == 8
    finally:
        if previous is None:
            monkeypatch.delenv("JUDGE_REPS", raising=False)
        else:
            monkeypatch.setenv("JUDGE_REPS", previous)
        importlib.reload(settings_module)


def test_default_reps_remains_three(monkeypatch) -> None:
    """Shipped default is 3 reps when nothing in the environment overrides it."""
    import dotenv

    monkeypatch.delenv("JUDGE_REPS", raising=False)
    original_load = dotenv.load_dotenv
    dotenv.load_dotenv = lambda *args, **kwargs: None
    try:
        reloaded = importlib.reload(settings_module)
        run_judge = _load_run_judge()
        assert run_judge._resolve_reps(_args(), reloaded.Settings()) == 3
    finally:
        dotenv.load_dotenv = original_load
        importlib.reload(settings_module)


@pytest.mark.parametrize("value", [0, -1])
def test_explicit_reps_must_be_positive(value: int) -> None:
    run_judge = _load_run_judge()

    with pytest.raises(SystemExit, match="reps deve ser >= 1"):
        run_judge._resolve_reps(_args(reps=value), Settings(judge_reps=3))


@pytest.mark.parametrize("value", [0, -1])
def test_settings_reps_must_be_positive(value: int) -> None:
    run_judge = _load_run_judge()

    with pytest.raises(SystemExit, match="reps deve ser >= 1"):
        run_judge._resolve_reps(_args(), Settings(judge_reps=value))


def test_smoke_ignores_invalid_reps_values() -> None:
    run_judge = _load_run_judge()

    assert (
        run_judge._resolve_reps(_args(smoke=True, reps=0), Settings(judge_reps=0)) == 1
    )
