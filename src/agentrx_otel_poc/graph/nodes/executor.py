"""Executor node: synthesize the final answer.

When an Executor-targeted fault forces a (wrong) answer, that forced answer governs
the output — the LLM still runs for realistic telemetry but does not override the
injected failure. Otherwise the agent LLM phrases the answer when USE_LLM=true.
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
        with ctx.tracer.start_as_current_span("agent.executor") as span:
            begin(
                span,
                4,
                "Executor",
                "build_answer",
                "response_synthesis",
                op_type,
                ctx.settings.agent_model,
            )
            items = state.get("products") or []
            operator = for_node(ctx.fault_type, "Executor")
            if operator:
                emit_fault(span, operator)
                operator.apply(state)
            if items:
                shown = ", ".join(i["item_id"] for i in items[:5])
                base = f"Found {len(items)} item(s) from the catalog tool: {shown}."
            else:
                base = spec.failure_response
            prompt = (
                "You are the Executor. Write the final answer to the task using ONLY "
                "the tool evidence; if there is no evidence, say the task could not be "
                "completed.\n"
                f"Task: {state['task']}\nTool result: {dumps(state.get('tool_result', {}))}"
            )
            text, usage = agent_message(
                ctx,
                prompt,
                base,
                label="Executor",
                logger=ctx.logger.child("executor"),
            )
            summary = state.get("forced_answer") or text
            state["summary"] = summary
            set_usage(span, usage)
            span.set_attribute("agent.reasoning_summary", "")
            span.add_event("artifact_created", {"artifact.type": "answer_summary"})
            io(span, f"Synthesize answer for: {state['task']}", summary)
            set_success(span)
        return state

    return node
