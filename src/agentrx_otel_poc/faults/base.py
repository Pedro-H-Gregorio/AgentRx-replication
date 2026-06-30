"""Uniform fault-operator interface, registry and category→fault_type mapping.

Each operator is scripted and deterministic, acts only on its target node, and
forces a failure *via the node's state/output* — never by naming the category in
log text (R5 is preserved at the source). The `fault.injected` OTel event (which
does name the category/node) is added to the raw span by the node, then stripped
from the derived trajectories by the adapters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from agentrx_otel_poc.state import ExperimentState

CATEGORY_TO_FAULT: dict[str, str] = {
    "System Failure": "system_failure",
    "Invalid Invocation": "invalid_invocation",
    "Misinterpretation of Tool Output": "misinterpretation",
    "Invention of New Information": "invention",
    "Instruction/Plan Adherence Failure": "plan_adherence",
}


class CatalogServiceTimeoutError(TimeoutError):
    """Raised by the System Failure operator to model a dependency timeout."""


@dataclass(frozen=True)
class FaultOperator:
    fault_type: str
    node: str
    category: str
    apply: Callable[[ExperimentState], None]


_REGISTRY: dict[str, FaultOperator] = {}


def register(operator: FaultOperator) -> FaultOperator:
    _REGISTRY[operator.fault_type] = operator
    return operator


def select(fault_type: str | None) -> FaultOperator | None:
    """Return the operator for *fault_type*, or None when there is no fault."""
    return _REGISTRY.get(fault_type or "")


def for_node(fault_type: str | None, node: str) -> FaultOperator | None:
    """Return the operator only when it targets *node* (else None → no-op)."""
    operator = select(fault_type)
    return operator if operator and operator.node == node else None
