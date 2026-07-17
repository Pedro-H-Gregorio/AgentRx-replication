"""Researcher node: prepare the concrete tool call from the plan/query."""

from __future__ import annotations

from typing import Callable

from agentrx_otel_poc.faults import for_node
from agentrx_otel_poc.mock_tools import tool_parameters
from agentrx_otel_poc.state import ExperimentState

from ..agent_llm import agent_message
from ..context import GraphContext
from ..spans import begin, dumps, emit_fault, io, set_success, set_usage


def build(ctx: GraphContext) -> Callable[[ExperimentState], ExperimentState]:
    spec = ctx.task_spec
    op_type = "agent_llm" if ctx.settings.use_llm else "agent_fallback"

    def node(state: ExperimentState) -> ExperimentState:
        with ctx.tracer.start_as_current_span("agent.researcher") as span:
            begin(
                span,
                2,
                "Researcher",
                "prepare_tool_call",
                "information_retrieval",
                op_type,
                ctx.settings.agent_model,
            )
            span.set_attribute("tool.name", spec.tool_name)
            span.set_attribute(
                "gen_ai.tool.parameters", dumps(tool_parameters(spec.tool_operation))
            )
            state["tool_args"] = dict(state.get("query") or spec.default_tool_args)
            operator = for_node(ctx.fault_type, "Researcher")
            if operator:
                emit_fault(span, operator)
                operator.apply(state)
            args = state["tool_args"]
            span.set_attribute("tool.args_json", dumps(args))
            span.add_event("tool_call_planned", {"tool.name": spec.tool_name})
            fallback = f"Call {spec.tool_name} with {dumps(args)}."
            prompt = (
                "You are the Researcher. In one sentence, state the tool call you will "
                "make to satisfy the plan.\n"
                f"Plan: {state.get('plan')}\nTool: {spec.tool_name}\n"
                f"Arguments: {dumps(args)}"
            )
            output, usage = agent_message(
                ctx,
                prompt,
                fallback,
                label="Researcher",
                logger=ctx.logger.child("researcher"),
            )
            set_usage(span, usage)
            io(span, f"Plan: {state.get('plan')}", output)
            set_success(span)
        return state

    return node
