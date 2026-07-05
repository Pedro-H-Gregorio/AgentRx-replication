"""Evaluator node: deterministic verdict (evidence-based); LLM phrases the reason.

The APPROVED/REJECTED decision is deterministic (it drives run status); when
USE_LLM=true the agent LLM only rewrites the human-readable reason text.
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
        with ctx.tracer.start_as_current_span("agent.evaluator") as span:
            begin(
                span,
                5,
                "Evaluator",
                "validate_answer",
                "quality_assurance",
                op_type,
                ctx.settings.agent_model,
            )
            span.set_attribute("validation.criteria_json", dumps(spec.success_criteria))
            operator = for_node(ctx.fault_type, "Evaluator")
            if operator:
                emit_fault(span, operator)
                operator.apply(state)
            result = state.get("tool_result") or {}
            items = state.get("products") or []
            approved = (
                bool(result.get("ok"))
                and bool(items)
                and state.get("status") != "FAILED"
            )
            if approved:
                status, reason, violations = (
                    "APPROVED",
                    "Tool evidence is available.",
                    [],
                )
                state["status"] = "SUCCESS"
                span.add_event(
                    "validation_passed", {"criterion": "tool_evidence_available"}
                )
            else:
                status, reason = "REJECTED", "Tool evidence is unavailable."
                violations = ["Tool evidence unavailable."]
                state["status"] = "FAILED"
                span.add_event("validation_failed", {"reason": reason})
            prompt = (
                "You are the Evaluator. In one sentence, justify the given verdict for "
                "the answer.\n"
                f"Verdict: {status}\nAnswer: {state.get('summary')}\n"
                f"Tool result: {dumps(result)}"
            )
            reason_text, usage = agent_message(
                ctx,
                prompt,
                reason,
                label="Evaluator",
                logger=ctx.logger.child("evaluator"),
            )
            state["validation_status"] = status
            state["validation_reason"] = reason_text
            state["constraint_violations"] = violations
            set_usage(span, usage)
            span.set_attribute("validation.status", status)
            span.set_attribute("validation.reason", reason_text)
            span.set_attribute("constraint.violations_json", dumps(violations))
            io(span, f"Evaluate answer: {state.get('summary')}", reason_text)
            set_success(span)
        return state

    return node
