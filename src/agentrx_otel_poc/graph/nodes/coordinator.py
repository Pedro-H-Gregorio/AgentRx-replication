"""Coordinator node: plan the run and choose the tool query.

Structure (plan/query) is deterministic and may be altered by a Coordinator-targeted
fault; the natural-language output is phrased by the agent LLM when USE_LLM=true.
"""

from __future__ import annotations

from typing import Callable

from agentrx_otel_poc.faults import for_node
from agentrx_otel_poc.state import ExperimentState

from ..agent_llm import agent_message
from ..context import GraphContext
from ..spans import begin, dumps, emit_fault, io, set_success, set_usage


def build(ctx: GraphContext) -> Callable[[ExperimentState], ExperimentState]:
    spec = ctx.task_spec
    op_type = "agent_llm" if ctx.settings.use_llm else "agent_fallback"

    def node(state: ExperimentState) -> ExperimentState:
        with ctx.tracer.start_as_current_span("agent.coordinator") as span:
            begin(
                span,
                1,
                "Coordinator",
                "task_decomposition",
                "orchestration",
                op_type,
                ctx.settings.agent_model,
            )
            span.set_attribute("task.id", state["task_id"])
            span.set_attribute("task.input", state["task"])
            span.set_attribute("task.expected_result", state["expected_result"])
            state["query"] = dict(spec.default_tool_args)
            state["plan"] = (
                f"Use {spec.tool_name} and answer from the returned evidence."
            )
            state["tool_name"] = spec.tool_name
            operator = for_node(ctx.fault_type, "Coordinator")
            if operator:
                emit_fault(span, operator)
                operator.apply(state)
            fallback = f"Plan ready; query {dumps(state['query'])}."
            prompt = (
                "You are the Coordinator in a multi-agent workflow. In one sentence, "
                "describe the plan to answer the task using the available tool.\n"
                f"Task: {state['task']}\nTool: {spec.tool_name}\n"
                f"Query: {dumps(state['query'])}"
            )
            output, usage = agent_message(
                ctx, prompt, fallback, logger=ctx.logger.child("coordinator")
            )
            set_usage(span, usage)
            span.add_event("task_delegated", {"target_agent": "Researcher"})
            io(span, f"Task: {state['task']}", output)
            set_success(span)
        return state

    return node
