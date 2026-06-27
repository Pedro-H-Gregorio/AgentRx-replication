from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from agentrx_otel_poc.runtime_logging import RunLogger


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    user_request: str
    domain: str
    tool_name: str
    tool_operation: str
    default_tool_args: dict[str, Any]
    expected_result: str
    success_criteria: list[str]
    failure_response: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


TASKS: dict[str, TaskSpec] = {
    "catalog_dell_price_filter": TaskSpec(
        task_id="catalog_dell_price_filter",
        user_request="Quais computadores Dell estão custando mais que R$ 5000?",
        domain="product_catalog",
        tool_name="ProductCatalogSearch",
        tool_operation="catalog.search",
        default_tool_args={"brand": "Dell", "price_min_brl": 5000},
        expected_result="Uma lista de computadores Dell com preco acima de R$ 5000.",
        success_criteria=[
            "A resposta final deve ser baseada nos itens retornados pela ferramenta de catalogo.",
            "Cada item listado deve ter marca Dell.",
            "Cada item listado deve ter preco em BRL maior que 5000.",
            "Se a ferramenta falhar, a resposta deve deixar claro que a tarefa nao foi concluida.",
        ],
        failure_response="Nao foi possivel concluir a busca no catalogo de produtos.",
    )
}


def get_task_spec(task_id: str) -> TaskSpec:
    try:
        return TASKS[task_id]
    except KeyError as exc:
        available = ", ".join(sorted(TASKS))
        raise ValueError(
            f"Unknown TASK_ID={task_id!r}. Available tasks: {available}"
        ) from exc


def build_ground_truth(task: TaskSpec, fault_type: str | None) -> dict[str, Any] | None:
    if fault_type != "system_timeout":
        return None

    return {
        "run_task_id": task.task_id,
        "critical_failure_step": 3,
        "failure_category": "System Failure",
        "failed_component": task.tool_name,
        "fault_mode": fault_type,
        "reason": "The catalog search dependency timed out before returning evidence to the agents.",
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

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chars_written = output_path.write_text(
            json.dumps(ground_truth, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        if logger:
            logger.exception(
                "artifact.write.failed",
                "Failed to write experiment labels",
                artifact_kind="ground_truth_json",
                output_path=output_path,
            )
        raise

    if logger:
        logger.info(
            "artifact.write.done",
            "Experiment labels written",
            artifact_kind="ground_truth_json",
            output_path=output_path,
            chars_written=chars_written,
        )

    return ground_truth
