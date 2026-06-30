"""The 5 scripted fault operators (PRD-03 §4), one per category/node.

Each `_apply` mutates only state the node legitimately controls (raise, args,
forced answer, query) — no category-naming markers in any rendered text.
"""

from __future__ import annotations

from agentrx_otel_poc.state import ExperimentState

from .base import CatalogServiceTimeoutError, FaultOperator, register

_TOOL_ARG_KEYS = {
    "product_type",
    "price_min",
    "available_only",
    "sort",
    "op",
    "product_id",
    "item_id",
}


def _system_failure(state: ExperimentState) -> None:
    """Tool dependency times out before returning evidence."""
    raise CatalogServiceTimeoutError(
        "catalog search dependency timed out after 30000ms"
    )


def _invalid_invocation(state: ExperimentState) -> None:
    """Researcher emits malformed args for an otherwise healthy tool."""
    args = dict(state.get("tool_args") or {})
    if "item_id" in args:
        args.pop("item_id")  # drop a required field
    if "product_id" in args:
        args["product_id"] = 0  # wrong type (int instead of str)
    else:
        args.pop("product_type", None)  # missing required field for search
    state["tool_args"] = args


def _misinterpretation(state: ExperimentState) -> None:
    """Executor misreads a valid tool output — wrong but plausible for the question."""
    answer = state.get("expected_answer") or {}
    items = state.get("products") or []
    if "answer" in answer:  # T4 yes/no → flip the verdict
        state["forced_answer"] = (
            "No, it does not." if answer["answer"] else "Yes, it does."
        )
    elif "item_ids" in answer:  # T3 filter → misread as an empty match set
        state["forced_answer"] = "No items match that filter above the given price."
    elif items:  # T1 cheapest → name the most expensive as the cheapest
        wrong = max(items, key=lambda i: (i["price"], i["item_id"]))
        state["forced_answer"] = (
            f"The cheapest available item is {wrong['item_id']} "
            f"at ${wrong['price']:.2f}."
        )
    else:
        state["forced_answer"] = "The selected item does not match the evidence."


def _invention(state: ExperimentState) -> None:
    """Executor fabricates information not grounded in the tool evidence."""
    answer = state.get("expected_answer") or {}
    items = state.get("products") or []
    if "count" in answer:  # T2 → a count not derived from the evidence
        state["forced_answer"] = f"There are {len(items) + 7} options available."
    elif "item_ids" in answer:  # T3 → non-existent items
        state["forced_answer"] = "Items 0000000000 and 1111111111 match the filter."
    else:  # T1 → a non-existent cheapest item
        state["forced_answer"] = "Item 0000000000 is the cheapest, priced at $0.01."
    state["fabricated"] = True


def _plan_adherence(state: ExperimentState) -> None:
    """Coordinator plans a query that violates an explicit question constraint."""
    query = dict(state.get("query") or {})
    if "price_min" in query:
        query.pop("price_min")  # drop a constraint the question demanded
    else:
        for key in list(query):
            if key not in _TOOL_ARG_KEYS:
                query[key] = f"{query[key]}_violated"  # alter the asked option
                break
    state["query"] = query
    state["plan_violated"] = True


register(FaultOperator("system_failure", "Tool", "System Failure", _system_failure))
register(
    FaultOperator(
        "invalid_invocation", "Researcher", "Invalid Invocation", _invalid_invocation
    )
)
register(
    FaultOperator(
        "misinterpretation",
        "Executor",
        "Misinterpretation of Tool Output",
        _misinterpretation,
    )
)
register(
    FaultOperator("invention", "Executor", "Invention of New Information", _invention)
)
register(
    FaultOperator(
        "plan_adherence",
        "Coordinator",
        "Instruction/Plan Adherence Failure",
        _plan_adherence,
    )
)
