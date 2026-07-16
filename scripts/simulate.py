#!/usr/bin/env python3
"""Run the MAS over every benchmark scenario → raw OTel trace + ground truth."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from agentrx_otel_poc.graph.agent_llm import AgentLLMError
from agentrx_otel_poc.graph.runner import run_scenario
from agentrx_otel_poc.tasks import load_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default=None, help="run a single scenario")
    args = parser.parse_args()

    task_ids = [args.task_id] if args.task_id else list(load_benchmark())
    for task_id in task_ids:
        try:
            payload = run_scenario(task_id, run_id=task_id)
        except AgentLLMError as exc:
            # Strict mode (USE_LLM_STRICT): fail fast so no mixed corpus is written.
            print(f"simulate: ABORTED at {task_id} -> {exc}", file=sys.stderr)
            return 3
        print(
            f"simulate: {task_id} -> {len(payload['spans'])} spans, {payload['status']}"
        )
    print(f"simulate: completed {len(task_ids)} scenario(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
