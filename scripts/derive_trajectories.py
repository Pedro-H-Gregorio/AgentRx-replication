#!/usr/bin/env python3
"""Derive the 2 trajectory arms from every raw OTel trace (PRD-04).

Reads data/internal/otel/*.otel.json → writes data/internal/trajectory_telemetry/
and data/internal/trajectory_agentrx/. Thin CLI over adapters.derive.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agentrx_otel_poc.adapters.derive import derive_to_files  # noqa: E402

INTERNAL = ROOT / "data" / "internal"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--otel-dir", default=str(INTERNAL / "otel"))
    args = parser.parse_args()

    otel_dir = Path(args.otel_dir)
    traces = sorted(otel_dir.glob("*.otel.json"))
    for trace in traces:
        payload = json.loads(trace.read_text(encoding="utf-8"))
        run_id = payload["run_id"]
        derive_to_files(
            payload,
            INTERNAL / "trajectory_telemetry" / f"{run_id}.json",
            INTERNAL / "trajectory_agentrx" / f"{run_id}.json",
        )
    print(f"derive_trajectories: derived 2 arms for {len(traces)} trace(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
