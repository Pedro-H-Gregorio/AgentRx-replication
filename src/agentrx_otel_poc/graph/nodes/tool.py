"""Tool node: run ProductCatalogSearch; honor a Tool-targeted fault."""

from __future__ import annotations

from typing import Callable

from agentrx_otel_poc.faults import for_node
from agentrx_otel_poc.mock_tools import CatalogServiceTimeoutError, run_tool
from agentrx_otel_poc.state import ExperimentState

from ..context import GraphContext
from ..spans import begin, dumps, emit_fault, io, mark_error, set_error, set_success


def build(ctx: GraphContext) -> Callable[[ExperimentState], ExperimentState]:
    spec = ctx.task_spec

    def node(state: ExperimentState) -> ExperimentState:
        with ctx.tracer.start_as_current_span("tool.product_catalog_search") as span:
            begin(
                span,
                3,
                spec.tool_name,
                spec.tool_operation,
                "dependency",
                "tool_call",
                ctx.settings.agent_model,
            )
            span.set_attribute("tool.name", spec.tool_name)
            span.set_attribute("peer.service", "catalog-service")
            span.set_attribute("server.address", "catalog-service.local")
            span.set_attribute("rpc.system", "http")
            span.set_attribute("http.request.method", "POST")
            args = dict(state.get("tool_args") or spec.default_tool_args)
            span.set_attribute("tool.args_json", dumps(args))
            inp = f"{spec.tool_name} input: {dumps(args)}"
            operator = for_node(ctx.fault_type, "Tool")
            try:
                if operator:
                    emit_fault(span, operator)
                    operator.apply(state)
                if state.get("dependency_timeout"):
                    raise CatalogServiceTimeoutError(
                        "catalog search dependency timed out after 30000ms"
                    )
                result = run_tool(
                    spec.tool_operation, dict(state.get("tool_args") or args)
                )
                state["tool_result"] = result
                items = result.get("items", [])
                state["products"] = items
                span.set_attribute("tool.result_json", dumps(result))
                if result.get("ok"):
                    span.set_attribute("tool.output.count", len(items))
                    span.add_event(
                        "dependency_call_completed", {"tool.output.count": len(items)}
                    )
                    io(span, inp, f"{spec.tool_name} returned {len(items)} item(s).")
                    set_success(span)
                else:
                    error = result.get("error", {})
                    state["status"] = "FAILED"
                    span.add_event(
                        "dependency_call_failed",
                        {
                            "peer.service": "catalog-service",
                            "exception.type": error.get("type", "ToolError"),
                        },
                    )
                    mark_error(
                        span, error.get("type", "ToolError"), error.get("message", "")
                    )
                    io(span, inp, f"{spec.tool_name} rejected the call.")
            except Exception as exc:  # noqa: BLE001 (we record any tool failure)
                result = {
                    "ok": False,
                    "error": {"type": exc.__class__.__name__, "message": str(exc)},
                }
                state["tool_result"] = result
                state["products"] = []
                state["status"] = "FAILED"
                span.set_attribute("tool.result_json", dumps(result))
                span.add_event(
                    "dependency_call_failed",
                    {
                        "peer.service": "catalog-service",
                        "exception.type": exc.__class__.__name__,
                    },
                )
                io(span, inp, f"{spec.tool_name} failed.")
                set_error(span, exc)
        return state

    return node
