"""Category id ↔ name, from the single source in `judge/scoring.py`.

The CSVs carry categories as the paper's integer taxonomy (PRD-10) plus a
human-readable mirror column. Names are never duplicated here: predictions use
the full display table (`FAILURE_CASE_NAMES`, 0–10) so an out-of-scope verdict
carries its real name instead of blank; ground truth uses the scope table (it is
always one of the 5 injectable categories by construction).
"""

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
