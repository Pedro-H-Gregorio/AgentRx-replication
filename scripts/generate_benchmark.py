#!/usr/bin/env python3
"""Generate data/benchmark/benchmark_30.json deterministically (no AI, no network).

Thin CLI over agentrx_otel_poc.benchmark; the MAS reads the JSON, never this script.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agentrx_otel_poc.benchmark.generator import write_benchmark  # noqa: E402

CATALOG = ROOT / "data" / "external" / "taubench_retail" / "products.json"
OUT = ROOT / "data" / "benchmark" / "benchmark_30.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--catalog", default=str(CATALOG))
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args()
    scenarios = write_benchmark(args.catalog, args.out, args.seed)
    print(f"generate_benchmark: wrote {len(scenarios)} scenarios -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
