#!/usr/bin/env python3
"""Collect judge verdicts into the PRD-10 CSVs (C7). Thin CLI.

Without arguments it collects every experiment under `data/internal/agentrx/`;
`--experiment <id>` restricts to one. Output goes to
`data/experiment/results/<experiment_id>/`.

  python scripts/collect_agentrx.py                        # all experiments
  python scripts/collect_agentrx.py --experiment judge-stub
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agentrx_otel_poc.collect import CollectError, collect  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", help="experiment_id to collect (default: all)")
    args = parser.parse_args()
    try:
        results = collect(args.experiment)
    except (FileNotFoundError, CollectError) as exc:
        print(f"[collect] erro: {exc}", file=sys.stderr)
        return 2
    if not results:
        return 0
    total = sum(r["pairs"] for r in results)
    print(f"[collect] done: {len(results)} experiment(s), {total} trajectory×arm rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
