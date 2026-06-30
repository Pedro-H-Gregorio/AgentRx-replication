#!/usr/bin/env python3
"""Fail the build if any tracked source file exceeds the line limit.

Clean-code guard for high-handoff open science: small files stay readable and
reviewable. The limit is enforced in `make check` and mirrored by a pytest test.
"""

from __future__ import annotations

from pathlib import Path

LIMIT = 200
ROOTS = ("src", "scripts", "tests")
SUFFIXES = (".py",)
SKIP_PARTS = {"__pycache__", ".venv", ".ruff_cache"}


def count_lines(path: Path) -> int:
    """Return the number of lines in *path* (why: that is the metric we cap)."""
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def offenders(root_dir: Path, limit: int = LIMIT) -> list[tuple[Path, int]]:
    """Return (path, line_count) for every file above *limit* under the roots."""
    found: list[tuple[Path, int]] = []
    for root in ROOTS:
        base = root_dir / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix not in SUFFIXES:
                continue
            if SKIP_PARTS & set(path.parts):
                continue
            lines = count_lines(path)
            if lines > limit:
                found.append((path, lines))
    return found


def main() -> int:
    root_dir = Path(__file__).resolve().parent.parent
    bad = offenders(root_dir)
    if not bad:
        print(f"check_file_size: OK (all files <= {LIMIT} lines)")
        return 0
    print(f"check_file_size: {len(bad)} file(s) over {LIMIT} lines:")
    for path, lines in bad:
        print(f"  {path.relative_to(root_dir)}: {lines} lines")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
