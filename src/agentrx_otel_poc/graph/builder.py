"""Wire the 5 nodes into the LangGraph state machine."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agentrx_otel_poc.state import ExperimentState

from .context import GraphContext
from .nodes import coordinator, evaluator, executor, researcher, tool


def build_graph(ctx: GraphContext) -> StateGraph:
    graph = StateGraph(ExperimentState)
    graph.add_node("coordinator", coordinator.build(ctx))
    graph.add_node("researcher", researcher.build(ctx))
    graph.add_node("tool_call", tool.build(ctx))
    graph.add_node("executor", executor.build(ctx))
    graph.add_node("evaluator", evaluator.build(ctx))

    graph.set_entry_point("coordinator")
    graph.add_edge("coordinator", "researcher")
    graph.add_edge("researcher", "tool_call")
    graph.add_edge("tool_call", "executor")
    graph.add_edge("executor", "evaluator")
    graph.add_edge("evaluator", END)
    return graph
