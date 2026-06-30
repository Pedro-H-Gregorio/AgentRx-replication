"""Load benchmark scenarios as `TaskSpec`s; build the success/localization labels.

The MAS reads `benchmark_30.json` (produced offline by scripts/generate_benchmark.py)
— there is no hardcoded task list. The fault localization ground truth is, by
construction, the scenario's own injection node + target category.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from agentrx_otel_poc.faults import CATEGORY_TO_FAULT
from agentrx_otel_poc.runtime_logging import RunLogger

_DEFAULT_BENCHMARK = (
    Path(__file__).resolve().parents[2] / "data" / "benchmark" / "benchmark_30.json"
)
_DEFAULT_FAILURE_RESPONSE = "The product catalog search could not be completed."

# MAS step order (matches experiment.step_index emitted by the graph).
NODE_STEP = {
    "Coordinator": 1,
    "Researcher": 2,
    "Tool": 3,
    "Executor": 4,
    "Evaluator": 5,
}


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    user_request: str
    domain: str
    tool_name: str
    tool_operation: str
    default_tool_args: dict[str, Any]
    expected_result: str
    expected_answer: dict[str, Any]
    success_criteria: list[str]
    target_fault_category: str
    injection_node: str
    template_id: str
    failure_response: str = _DEFAULT_FAILURE_RESPONSE

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _from_scenario(scenario: dict[str, Any]) -> TaskSpec:
    return TaskSpec(
        task_id=scenario["task_id"],
        user_request=scenario["user_request"],
        domain=scenario["domain"],
        tool_name=scenario["tool_name"],
        tool_operation=scenario["tool_operation"],
        default_tool_args=dict(scenario["default_tool_args"]),
        expected_result=scenario["expected_result"],
        expected_answer=dict(scenario["expected_answer"]),
        success_criteria=list(scenario["success_criteria"]),
        target_fault_category=scenario["target_fault_category"],
        injection_node=scenario["injection_node"],
        template_id=scenario["template_id"],
        failure_response=scenario.get("failure_response", _DEFAULT_FAILURE_RESPONSE),
    )


@lru_cache(maxsize=4)
def _load(path: str) -> dict[str, TaskSpec]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return {s["task_id"]: _from_scenario(s) for s in raw}


def load_benchmark(path: str | Path | None = None) -> dict[str, TaskSpec]:
    """Return all scenarios keyed by task_id (cached per path)."""
    return _load(str(path or _DEFAULT_BENCHMARK))


def get_task_spec(task_id: str, path: str | Path | None = None) -> TaskSpec:
    tasks = load_benchmark(path)
    try:
        return tasks[task_id]
    except KeyError as exc:
        available = ", ".join(sorted(tasks))
        raise ValueError(
            f"Unknown TASK_ID={task_id!r}. Available tasks: {available}"
        ) from exc


def build_ground_truth(task: TaskSpec) -> dict[str, Any]:
    """Localization ground truth = the scenario's injection node + category.

    `fault_mode` is derived from the target category (single source of truth), so it
    can never disagree with `failure_category`.
    """
    node = task.injection_node
    return {
        "run_task_id": task.task_id,
        "critical_failure_step": NODE_STEP[node],
        "failure_category": task.target_fault_category,
        "failed_component": task.tool_name if node == "Tool" else node,
        "fault_mode": CATEGORY_TO_FAULT[task.target_fault_category],
        "reason": f"Fault injected at the {node} step ({task.target_fault_category}).",
    }


def write_ground_truth_json(
    ground_truth: dict[str, Any] | None,
    output_path: Path,
    *,
    logger: RunLogger | None = None,
) -> dict[str, Any] | None:
    if not ground_truth:
        return None
    if logger:
        logger.info(
            "artifact.write.start",
            "Writing experiment labels",
            artifact_kind="ground_truth_json",
            output_path=output_path,
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    chars_written = output_path.write_text(
        json.dumps(ground_truth, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if logger:
        logger.info(
            "artifact.write.done",
            "Experiment labels written",
            artifact_kind="ground_truth_json",
            output_path=output_path,
            chars_written=chars_written,
        )
    return ground_truth
