"""Category id ↔ name, from the single source in `judge/scoring.py`.

The CSVs carry categories as the paper's integer taxonomy (PRD-10) plus a
human-readable mirror column. The int↔name table is never duplicated: it is the
same `FAILURE_CASE_TO_CATEGORY` the judge scoring uses.
"""

from __future__ import annotations

from agentrx_otel_poc.judge.scoring import FAILURE_CASE_TO_CATEGORY

CATEGORY_TO_FAILURE_CASE: dict[str, int] = {
    name: case for case, name in FAILURE_CASE_TO_CATEGORY.items()
}


def name_of(case: int | None) -> str:
    """Readable name for a failure-case int, or '' outside the 5 injectable ones."""
    if case is None:
        return ""
    return FAILURE_CASE_TO_CATEGORY.get(case, "")


def case_of(name: str | None) -> int | None:
    """Failure-case int for a category name, or None if not one of the five."""
    if not name:
        return None
    return CATEGORY_TO_FAILURE_CASE.get(name)
