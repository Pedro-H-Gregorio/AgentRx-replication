"""Mirror of scripts/check_file_size.py so the 200-line limit fails in pytest/CI."""

from __future__ import annotations

from pathlib import Path

from scripts.check_file_size import LIMIT, offenders

ROOT = Path(__file__).resolve().parent.parent


def test_no_source_file_exceeds_limit() -> None:
    bad = offenders(ROOT)
    assert not bad, "Files over %d lines: %s" % (
        LIMIT,
        ", ".join(f"{p.relative_to(ROOT)} ({n})" for p, n in bad),
    )
