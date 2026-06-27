from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph
from opentelemetry import trace

from agentrx_otel_poc.adapters.agentrx_adapter import convert_otel_to_agentrx_trajectory
from agentrx_otel_poc.adapters.metrics_adapter import write_metrics_json
from agentrx_otel_poc.adapters.text_adapter import convert_otel_to_text_baseline
from agentrx_otel_poc.llm import invoke_llm, parse_json_object
from agentrx_otel_poc.mock_tools import search_products
from agentrx_otel_poc.runtime_logging import RunLogger, configure_logging
from agentrx_otel_poc.settings import Settings
from agentrx_otel_poc.state import ExperimentState
from agentrx_otel_poc.tasks import (
    TaskSpec,
    build_ground_truth,
    get_task_spec,
    write_ground_truth_json,
)
from agentrx_otel_poc.telemetry import (
    add_step,
    configure_tracer,
    set_error,
    set_success,
    write_otel_json,
)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _merge_tool_args(defaults: dict[str, Any], raw_args: Any) -> dict[str, Any]:
    args = dict(defaults)
    if isinstance(raw_args, dict):
        for key, value in raw_args.items():
            if value is not None:
                args[key] = value

    for key, default in defaults.items():
        if isinstance(default, int):
            args[key] = _safe_int(args.get(key), default)
        elif isinstance(default, str):
            args[key] = str(args.get(key) or default)

    return args


def _append_conversation(state: ExperimentState, role: str, content: str) -> None:
    state.setdefault("conversation", []).append({"role": role, "content": content})


def _set_io(span: trace.Span, input_message: str, output_message: str) -> None:
    span.set_attribute("agent.input_message", input_message)
    span.set_attribute("agent.output_message", output_message)


def _set_llm_usage(
    span: trace.Span, settings: Settings, tokens: dict[str, int]
) -> None:
    span.set_attribute("gen_ai.request.model", settings.openai_model)
    span.set_attribute("gen_ai.usage.input_tokens", tokens["input_tokens"])
    span.set_attribute("gen_ai.usage.output_tokens", tokens["output_tokens"])
    span.set_attribute("gen_ai.usage.total_tokens", tokens["total_tokens"])


def _zero_llm_usage(span: trace.Span) -> None:
    span.set_attribute("gen_ai.usage.input_tokens", 0)
    span.set_attribute("gen_ai.usage.output_tokens", 0)
    span.set_attribute("gen_ai.usage.total_tokens", 0)


def _call_agent_json(
    settings: Settings,
    prompt: str,
    *,
    logger: RunLogger,
) -> tuple[dict[str, Any], str, dict[str, int]]:
    content, tokens = invoke_llm(settings, prompt, logger=logger)
    return parse_json_object(content), content, tokens


def _format_items(items: list[dict[str, Any]]) -> str:
    formatted: list[str] = []
    for item in items:
        model = item.get("model") or item.get("name") or "item"
        price = item.get("price_brl")
        if price is None:
            formatted.append(str(model))
        else:
            formatted.append(f"{model} - R$ {price}")
    return "; ".join(formatted)


def _execute_tool(
    task_spec: TaskSpec,
    tool_args: dict[str, Any],
    fault_type: str | None,
    *,
    logger: RunLogger,
) -> dict[str, Any]:
    if task_spec.tool_name != "ProductCatalogSearch":
        raise ValueError(f"Unsupported tool: {task_spec.tool_name}")

    items = search_products(
        str(tool_args.get("brand") or ""),
        _safe_int(tool_args.get("price_min_brl"), 0),
        fault_type,
        logger=logger,
    )
    return {
        "ok": True,
        "source": "catalog-service",
        "query": tool_args,
        "items": items,
        "count": len(items),
    }


def build_graph(
    settings: Settings, task_spec: TaskSpec, tracer: trace.Tracer, logger: RunLogger
) -> StateGraph:
    graph = StateGraph(ExperimentState)
    coordinator_logger = logger.child("coordinator")
    researcher_logger = logger.child("researcher")
    tool_logger = logger.child("tool")
    executor_logger = logger.child("executor")
    evaluator_logger = logger.child("evaluator")
    llm_logger = logger.child("llm")

    def coordinator(state: ExperimentState) -> ExperimentState:
        input_message = (
            "Create a short execution plan and identify the tool query.\n"
            f"Task: {state['task']}\n"
            f"Expected result: {state['expected_result']}\n"
            f"Available tool: {task_spec.tool_name}\n"
            f"Default tool args: {_json_dumps(task_spec.default_tool_args)}"
        )
        coordinator_logger.info(
            "node.start",
            "Coordinator received task",
            task_id=state["task_id"],
            domain=task_spec.domain,
        )
        with tracer.start_as_current_span("agent.coordinator") as span:
            add_step(span, 1, "Coordinator", "task_decomposition")
            span.set_attribute(
                "experiment.operation_type",
                "agent_llm" if settings.use_llm else "agent_fallback",
            )
            span.set_attribute("agent.role", "orchestration")
            span.set_attribute("task.id", state["task_id"])
            span.set_attribute("task.input", state["task"])
            span.set_attribute("task.expected_result", state["expected_result"])
            if settings.use_llm:
                prompt = (
                    "You are the Coordinator in a multi-agent workflow. "
                    "Return only JSON with keys: plan, tool_query, message_to_researcher. "
                    "tool_query must be an object compatible with the available tool defaults.\n\n"
                    f"Task: {state['task']}\n"
                    f"Expected result: {state['expected_result']}\n"
                    f"Available tool: {task_spec.tool_name}\n"
                    f"Default tool args: {_json_dumps(task_spec.default_tool_args)}"
                )
                try:
                    parsed, raw_content, tokens = _call_agent_json(
                        settings, prompt, logger=llm_logger
                    )
                    state["query"] = _merge_tool_args(
                        task_spec.default_tool_args, parsed.get("tool_query")
                    )
                    state["plan"] = str(
                        parsed.get("plan")
                        or "Query the tool and synthesize the answer."
                    )
                    output_message = str(
                        parsed.get("message_to_researcher") or raw_content
                    )
                    _set_llm_usage(span, settings, tokens)
                except Exception as exc:
                    state["query"] = dict(task_spec.default_tool_args)
                    state["plan"] = (
                        f"Use {task_spec.tool_name} and answer from the returned evidence."
                    )
                    output_message = f"Coordinator fallback plan after LLM error: {exc}"
                    span.add_event(
                        "llm_fallback_triggered", {"error.type": exc.__class__.__name__}
                    )
                    _zero_llm_usage(span)
                    coordinator_logger.exception(
                        "llm.failed",
                        "Coordinator LLM failed; using configured task defaults",
                    )
            else:
                state["query"] = dict(task_spec.default_tool_args)
                state["plan"] = (
                    f"Use {task_spec.tool_name} and answer from the returned evidence."
                )
                output_message = f"Researcher should call {task_spec.tool_name} with {_json_dumps(state['query'])}."
                _zero_llm_usage(span)

            state["tool_name"] = task_spec.tool_name
            span.add_event(
                "task_delegated",
                {
                    "target_agent": "Researcher",
                    "delegated_goal": state["plan"],
                },
            )
            _append_conversation(state, "Coordinator", output_message)
            _set_io(span, input_message, output_message)
            set_success(span)
        coordinator_logger.info(
            "node.done", "Coordinator produced tool query", query=state["query"]
        )
        return state

    def researcher(state: ExperimentState) -> ExperimentState:
        input_message = (
            "Prepare the tool call from the plan and query.\n"
            f"Plan: {state.get('plan')}\n"
            f"Tool: {task_spec.tool_name}\n"
            f"Query: {_json_dumps(state.get('query', {}))}"
        )
        researcher_logger.info(
            "node.start",
            "Researcher preparing tool call",
            task_id=state["task_id"],
            tool_name=task_spec.tool_name,
        )
        with tracer.start_as_current_span("agent.researcher") as span:
            add_step(span, 2, "Researcher", "prepare_tool_call")
            span.set_attribute(
                "experiment.operation_type",
                "agent_llm" if settings.use_llm else "agent_fallback",
            )
            span.set_attribute("agent.role", "information_retrieval")
            span.set_attribute("tool.name", task_spec.tool_name)
            query = state.get("query", task_spec.default_tool_args)
            if settings.use_llm:
                prompt = (
                    "You are the Researcher. Select the tool and final arguments. "
                    "Return only JSON with keys: tool_name, tool_args, message_to_tool.\n\n"
                    f"Task: {state['task']}\n"
                    f"Plan: {state.get('plan')}\n"
                    f"Available tool: {task_spec.tool_name}\n"
                    f"Default tool args: {_json_dumps(task_spec.default_tool_args)}\n"
                    f"Coordinator query: {_json_dumps(query)}"
                )
                try:
                    parsed, raw_content, tokens = _call_agent_json(
                        settings, prompt, logger=llm_logger
                    )
                    tool_args = _merge_tool_args(
                        task_spec.default_tool_args, parsed.get("tool_args")
                    )
                    output_message = str(parsed.get("message_to_tool") or raw_content)
                    _set_llm_usage(span, settings, tokens)
                except Exception as exc:
                    tool_args = _merge_tool_args(task_spec.default_tool_args, query)
                    output_message = (
                        f"Researcher fallback tool call after LLM error: {exc}"
                    )
                    span.add_event(
                        "llm_fallback_triggered", {"error.type": exc.__class__.__name__}
                    )
                    _zero_llm_usage(span)
                    researcher_logger.exception(
                        "llm.failed", "Researcher LLM failed; using coordinator query"
                    )
            else:
                tool_args = _merge_tool_args(task_spec.default_tool_args, query)
                output_message = (
                    f"Call {task_spec.tool_name} with {_json_dumps(tool_args)}."
                )
                _zero_llm_usage(span)

            state["tool_args"] = tool_args
            span.set_attribute("tool.args_json", _json_dumps(tool_args))
            span.add_event(
                "tool_call_planned",
                {"tool.name": task_spec.tool_name, "tool.args": _json_dumps(tool_args)},
            )
            _append_conversation(state, "Researcher", output_message)
            _set_io(span, input_message, output_message)
            set_success(span)
        researcher_logger.info("node.done", "Researcher prepared tool call")
        return state

    def tool_call(state: ExperimentState) -> ExperimentState:
        tool_args = _merge_tool_args(
            task_spec.default_tool_args, state.get("tool_args")
        )
        input_message = f"{task_spec.tool_name} input: {_json_dumps(tool_args)}"
        tool_logger.info(
            "node.start",
            "Tool execution started",
            tool_name=task_spec.tool_name,
            operation=task_spec.tool_operation,
        )
        with tracer.start_as_current_span("tool.product_catalog_search") as span:
            add_step(span, 3, task_spec.tool_name, task_spec.tool_operation)
            span.set_attribute("experiment.operation_type", "tool_call")
            span.set_attribute("tool.name", task_spec.tool_name)
            span.set_attribute("tool.args_json", _json_dumps(tool_args))
            span.set_attribute("peer.service", "catalog-service")
            span.set_attribute("server.address", "catalog-service.local")
            span.set_attribute("rpc.system", "http")
            span.set_attribute("http.request.method", "POST")
            for key, value in tool_args.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"tool.input.{key}", value)
            _zero_llm_usage(span)
            try:
                result = _execute_tool(
                    task_spec, tool_args, state.get("fault_type"), logger=tool_logger
                )
                items = result.get("items", [])
                state["tool_result"] = result
                state["products"] = items
                output_message = f"{task_spec.tool_name} returned {len(items)} item(s)."
                span.set_attribute("tool.output.count", len(items))
                span.set_attribute("tool.result_json", _json_dumps(result))
                span.add_event(
                    "dependency_call_completed", {"tool.output.count": len(items)}
                )
                _set_io(span, input_message, output_message)
                _append_conversation(state, task_spec.tool_name, output_message)
                set_success(span)
                tool_logger.info(
                    "node.done",
                    "Tool execution completed",
                    tool_name=task_spec.tool_name,
                    result_count=len(items),
                )
            except Exception as exc:
                result = {
                    "ok": False,
                    "source": "catalog-service",
                    "query": tool_args,
                    "error": {"type": exc.__class__.__name__, "message": str(exc)},
                }
                state["tool_result"] = result
                state["products"] = []
                state["error"] = str(exc)
                state["status"] = "FAILED"
                state.setdefault("failure_observations", []).append(
                    {
                        "component": task_spec.tool_name,
                        "operation": task_spec.tool_operation,
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    }
                )
                output_message = f"{task_spec.tool_name} failed: {exc}"
                span.add_event(
                    "dependency_call_failed",
                    {
                        "peer.service": "catalog-service",
                        "exception.type": exc.__class__.__name__,
                    },
                )
                span.set_attribute("tool.result_json", _json_dumps(result))
                _set_io(span, input_message, output_message)
                _append_conversation(state, task_spec.tool_name, output_message)
                set_error(span, exc)
                tool_logger.exception(
                    "node.failed",
                    "Tool dependency call failed",
                    tool_name=task_spec.tool_name,
                    operation=task_spec.tool_operation,
                    error_type=exc.__class__.__name__,
                )
        return state

    def executor(state: ExperimentState) -> ExperimentState:
        items = state.get("products", [])
        input_message = (
            "Synthesize the final user answer from the task, conversation, expected result, and tool evidence.\n"
            f"Task: {state['task']}\n"
            f"Expected result: {state['expected_result']}\n"
            f"Tool result: {_json_dumps(state.get('tool_result', {}))}"
        )
        executor_logger.info(
            "node.start",
            "Executor preparing answer",
            use_llm=settings.use_llm,
            evidence_count=len(items),
        )
        with tracer.start_as_current_span("agent.executor") as span:
            add_step(span, 4, "Executor", "build_answer")
            span.set_attribute(
                "experiment.operation_type",
                "agent_llm" if settings.use_llm else "agent_fallback",
            )
            span.set_attribute("agent.role", "response_synthesis")
            if settings.use_llm:
                usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
                prompt = (
                    "You are the Executor. Produce the final answer in Portuguese. "
                    "Use only the conversation and tool evidence. If evidence is unavailable, "
                    "explain that the request could not be completed. Return only JSON with "
                    "keys: answer, reasoning_summary.\n\n"
                    f"Task: {state['task']}\n"
                    f"Expected result: {state['expected_result']}\n"
                    f"Conversation: {_json_dumps(state.get('conversation', []))}\n"
                    f"Tool result: {_json_dumps(state.get('tool_result', {}))}"
                )
                try:
                    parsed, raw_content, tokens = _call_agent_json(
                        settings, prompt, logger=llm_logger
                    )
                    state["summary"] = str(parsed.get("answer") or raw_content)
                    output_message = state["summary"]
                    span.set_attribute(
                        "agent.reasoning_summary",
                        str(parsed.get("reasoning_summary") or ""),
                    )
                    _set_llm_usage(span, settings, tokens)
                    usage = tokens
                except Exception as exc:
                    state["summary"] = (
                        task_spec.failure_response
                        if not items
                        else _format_items(items)
                    )
                    output_message = f"Executor fallback answer after LLM error: {state['summary']} ({exc})"
                    span.add_event(
                        "llm_fallback_triggered", {"error.type": exc.__class__.__name__}
                    )
                    _zero_llm_usage(span)
                    executor_logger.exception(
                        "llm.failed", "Executor LLM failed; using deterministic answer"
                    )
                executor_logger.info(
                    "node.done",
                    "Executor produced answer with LLM path",
                    summary_chars=len(state["summary"]),
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    total_tokens=usage["total_tokens"],
                )
            else:
                state["summary"] = (
                    task_spec.failure_response if not items else _format_items(items)
                )
                output_message = state["summary"]
                _zero_llm_usage(span)
                executor_logger.info(
                    "node.done",
                    "Executor produced deterministic answer",
                    summary_chars=len(state["summary"]),
                    evidence_count=len(items),
                )
            span.add_event("artifact_created", {"artifact.type": "answer_summary"})
            _append_conversation(state, "Executor", state["summary"])
            _set_io(span, input_message, output_message)
            set_success(span)
        return state

    def evaluator(state: ExperimentState) -> ExperimentState:
        items = state.get("products", [])
        input_message = (
            "Evaluate whether the final answer satisfies the task using the success criteria and tool evidence.\n"
            f"Task: {state['task']}\n"
            f"Success criteria: {_json_dumps(state['success_criteria'])}\n"
            f"Answer: {state.get('summary')}\n"
            f"Tool result: {_json_dumps(state.get('tool_result', {}))}"
        )
        evaluator_logger.info(
            "node.start",
            "Evaluator validating answer",
            evidence_count=len(items),
        )
        with tracer.start_as_current_span("agent.evaluator") as span:
            add_step(span, 5, "Evaluator", "validate_answer")
            span.set_attribute(
                "experiment.operation_type",
                "agent_llm" if settings.use_llm else "agent_fallback",
            )
            span.set_attribute("agent.role", "quality_assurance")
            span.set_attribute(
                "validation.criteria_json", _json_dumps(state["success_criteria"])
            )
            constraint_violations: list[str] = []
            output_message = ""
            if settings.use_llm:
                prompt = (
                    "You are the Evaluator. Judge whether the final answer satisfies the task. "
                    "Return only JSON with keys: validation_status (APPROVED or REJECTED), "
                    "validation_reason, constraint_violations (list of strings).\n\n"
                    f"Task: {state['task']}\n"
                    f"Expected result: {state['expected_result']}\n"
                    f"Success criteria: {_json_dumps(state['success_criteria'])}\n"
                    f"Conversation: {_json_dumps(state.get('conversation', []))}\n"
                    f"Answer: {state.get('summary')}\n"
                    f"Tool result: {_json_dumps(state.get('tool_result', {}))}"
                )
                try:
                    parsed, raw_content, tokens = _call_agent_json(
                        settings, prompt, logger=llm_logger
                    )
                    output_message = str(parsed.get("validation_reason") or raw_content)
                    raw_violations = parsed.get("constraint_violations")
                    if isinstance(raw_violations, list):
                        constraint_violations = [str(v) for v in raw_violations]
                    state["validation_status"] = (
                        str(parsed.get("validation_status") or "").upper() or "REJECTED"
                    )
                    _set_llm_usage(span, settings, tokens)
                except Exception as exc:
                    output_message = (
                        f"Evaluator fallback validation after LLM error: {exc}"
                    )
                    span.add_event(
                        "llm_fallback_triggered", {"error.type": exc.__class__.__name__}
                    )
                    _zero_llm_usage(span)
                    evaluator_logger.exception(
                        "llm.failed",
                        "Evaluator LLM failed; using deterministic validation",
                    )
            else:
                _zero_llm_usage(span)

            tool_result = state.get("tool_result", {})
            if not settings.use_llm:
                if tool_result.get("ok") and items:
                    state["validation_status"] = "APPROVED"
                    output_message = "A resposta foi aprovada porque ha evidencia retornada pela ferramenta."
                else:
                    state["validation_status"] = "REJECTED"
                    output_message = "A resposta foi rejeitada porque a evidencia da ferramenta nao esta disponivel."
                    constraint_violations = ["Tool evidence unavailable."]

            if state.get("validation_status") == "APPROVED":
                state["status"] = "SUCCESS"
                span.add_event(
                    "validation_passed", {"criterion": "tool_evidence_available"}
                )
                evaluator_logger.info(
                    "node.done",
                    "Evaluator approved answer",
                    validation_status=state["validation_status"],
                    evidence_count=len(items),
                )
            else:
                state["validation_status"] = "REJECTED"
                state["status"] = "FAILED"
                if not constraint_violations:
                    constraint_violations = [
                        "Task success criteria were not satisfied."
                    ]
                span.add_event("validation_failed", {"reason": output_message})
                evaluator_logger.warning(
                    "node.done",
                    "Evaluator rejected answer",
                    validation_status=state["validation_status"],
                    reason=output_message,
                )

            state["validation_reason"] = output_message
            state["constraint_violations"] = constraint_violations
            span.set_attribute("validation.status", state["validation_status"])
            span.set_attribute("validation.reason", output_message)
            span.set_attribute(
                "constraint.violations_json", _json_dumps(constraint_violations)
            )
            _append_conversation(state, "Evaluator", output_message)
            _set_io(span, input_message, output_message)
            set_success(span)
        return state

    graph.add_node("coordinator", coordinator)
    graph.add_node("researcher", researcher)
    graph.add_node("tool_call", tool_call)
    graph.add_node("executor", executor)
    graph.add_node("evaluator", evaluator)

    graph.set_entry_point("coordinator")
    graph.add_edge("coordinator", "researcher")
    graph.add_edge("researcher", "tool_call")
    graph.add_edge("tool_call", "executor")
    graph.add_edge("executor", "evaluator")
    graph.add_edge("evaluator", END)
    return graph


def run_experiment() -> None:
    settings = Settings()
    task_spec = get_task_spec(settings.task_id)
    logger = configure_logging(settings.run_id)
    logger.info(
        "run.start",
        "Starting agentrx_otel_poc execution",
        task_id=task_spec.task_id,
        domain=task_spec.domain,
        use_llm=settings.use_llm,
        otel_service_name=settings.otel_service_name,
        openai_model=settings.openai_model,
    )

    tracer, exporter, provider = configure_tracer(
        settings.otel_service_name, settings.run_id
    )
    logger.info(
        "telemetry.ready",
        "OpenTelemetry tracer configured",
        service_name=settings.otel_service_name,
    )

    graph = build_graph(settings, task_spec, tracer, logger.child("graph")).compile()
    logger.info("graph.ready", "LangGraph compiled successfully")

    initial_state: ExperimentState = {
        "run_id": settings.run_id,
        "task_id": task_spec.task_id,
        "task": task_spec.user_request,
        "expected_result": task_spec.expected_result,
        "success_criteria": task_spec.success_criteria,
        "tool_name": task_spec.tool_name,
        "fault_type": settings.fault_type,
        "status": "RUNNING",
        "error": None,
    }
    logger.info(
        "graph.invoke.start",
        "Invoking graph with the initial state",
        run_id=settings.run_id,
        task_id=task_spec.task_id,
        status=initial_state["status"],
    )
    with tracer.start_as_current_span("run.experiment") as span:
        span.set_attribute("experiment.operation_type", "workflow")
        span.set_attribute("experiment.run_id", settings.run_id)
        span.set_attribute("task.id", task_spec.task_id)
        span.set_attribute("task.domain", task_spec.domain)
        span.set_attribute("task.input", task_spec.user_request)
        span.set_attribute("task.expected_result", task_spec.expected_result)
        span.set_attribute(
            "task.success_criteria_json", _json_dumps(task_spec.success_criteria)
        )
        span.set_attribute(
            "gen_ai.request.model", settings.openai_model if settings.use_llm else ""
        )
        span.set_attribute("gen_ai.agent.framework", "langgraph")
        final_state = graph.invoke(initial_state)
        span.set_attribute("run.status", final_state.get("status", "UNKNOWN"))
        span.set_attribute(
            "run.validation_status", final_state.get("validation_status", "UNKNOWN")
        )
        set_success(span)
    logger.info(
        "graph.invoke.done",
        "Graph execution completed",
        status=final_state.get("status"),
        validation_status=final_state.get("validation_status"),
        evidence_count=len(final_state.get("products", [])),
        summary_chars=len(final_state.get("summary", "")),
    )
    provider.force_flush()
    logger.info("telemetry.flush.done", "OpenTelemetry exporter flushed")

    base = Path("data")
    otel_path = base / "otel" / f"{settings.run_id}.otel.json"
    payload = write_otel_json(
        otel_path,
        run_id=settings.run_id,
        task_id=task_spec.task_id,
        task=task_spec.user_request,
        task_metadata=task_spec.to_dict(),
        exporter=exporter,
        ground_truth=None,
        run_status=final_state.get("status", "SUCCESS"),
        logger=logger.child("telemetry"),
    )

    agentrx_path = base / "agentrx" / f"{settings.run_id}.trajectory.json"
    text_path = base / "text_baseline" / f"{settings.run_id}.txt"
    metrics_path = base / "metrics" / f"{settings.run_id}.metrics.json"
    ground_truth_path = base / "ground_truth" / f"{settings.run_id}.ground_truth.json"
    ground_truth = build_ground_truth(task_spec, settings.fault_type)

    convert_otel_to_agentrx_trajectory(
        payload, agentrx_path, logger=logger.child("agentrx_adapter")
    )
    convert_otel_to_text_baseline(
        payload, text_path, logger=logger.child("text_adapter")
    )
    write_metrics_json(payload, metrics_path, logger=logger.child("metrics_adapter"))
    write_ground_truth_json(
        ground_truth, ground_truth_path, logger=logger.child("ground_truth")
    )

    logger.info(
        "run.complete",
        "Experiment outputs written to data",
        otel_json_path=otel_path,
        agentrx_path=agentrx_path,
        text_baseline_path=text_path,
        metrics_path=metrics_path,
        ground_truth_path=ground_truth_path if ground_truth else None,
        status=final_state.get("status"),
    )
