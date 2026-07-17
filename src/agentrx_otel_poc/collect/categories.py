"""Category id ↔ name, from the single source in `judge/scoring.py`."""

from __future__ import annotations

from agentrx_otel_poc.judge.scoring import (
    FAILURE_CASE_NAMES,
    FAILURE_CASE_TO_CATEGORY,
)

CATEGORY_TO_FAILURE_CASE: dict[str, int] = {
    name: case for case, name in FAILURE_CASE_TO_CATEGORY.items()
}


def name_of(case: int | None) -> str:
    """Full taxonomy name for a failure-case int (0–10), or '' when absent."""
    if case is None:
        return ""
    return FAILURE_CASE_NAMES.get(case, "")


def case_of(name: str | None) -> int | None:
    """Failure-case int for a ground-truth category name (the 5 injectable ones)."""
    if not name:
        return None
    return CATEGORY_TO_FAILURE_CASE.get(name)
