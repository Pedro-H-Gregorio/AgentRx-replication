from typing import Any, TypedDict


class ExperimentState(TypedDict, total=False):
    run_id: str
    task_id: str
    task: str
    plan: str
    query: dict[str, Any]
    expected_result: str
    success_criteria: list[str]
    tool_name: str
    tool_args: dict[str, Any]
    tool_result: dict[str, Any]
    products: list[dict[str, Any]]
    summary: str
    conversation: list[dict[str, Any]]
    constraint_violations: list[str]
    failure_observations: list[dict[str, Any]]
    validation_status: str
    validation_reason: str
    status: str
    error: str | None
    fault_type: str | None
    steps: list[dict[str, Any]]
