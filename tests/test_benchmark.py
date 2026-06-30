"""Validator for the generated benchmark (PRD-02): balance, schema, recompute."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from agentrx_otel_poc.benchmark.catalog import load_catalog
from agentrx_otel_poc.benchmark.generator import (
    CATEGORIES,
    PER_CATEGORY,
    build_benchmark,
)

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "external" / "taubench_retail" / "products.json"
BENCHMARK = ROOT / "data" / "benchmark" / "benchmark_30.json"
REQUIRED = {
    "task_id",
    "domain",
    "user_request",
    "tool_name",
    "tool_operation",
    "default_tool_args",
    "expected_result",
    "expected_answer",
    "success_criteria",
    "target_fault_category",
    "injection_node",
    "template_id",
}
NODE_OF = {cat: node for cat, node, _ in CATEGORIES}
KNOWN_ARGS = {"product_type", "price_min", "available_only", "sort", "op"}


@pytest.fixture(scope="module")
def scenarios() -> list[dict]:
    return json.loads(BENCHMARK.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def products():
    return load_catalog(CATALOG)


def test_count_and_balance(scenarios: list[dict]) -> None:
    assert len(scenarios) == len(CATEGORIES) * PER_CATEGORY
    counts = Counter(s["target_fault_category"] for s in scenarios)
    for category, _, _ in CATEGORIES:
        assert counts[category] == PER_CATEGORY


def test_injection_node_coherent(scenarios: list[dict]) -> None:
    for s in scenarios:
        assert s["injection_node"] == NODE_OF[s["target_fault_category"]]


def test_schema_and_english(scenarios: list[dict]) -> None:
    for s in scenarios:
        assert REQUIRED <= set(s), f"missing fields in {s['task_id']}"
        assert isinstance(s["user_request"], str) and s["user_request"]
        assert s["user_request"].isascii(), f"non-English text in {s['task_id']}"
        assert s["domain"] == "product_catalog"


def test_invention_answer_non_empty(scenarios: list[dict]) -> None:
    for s in scenarios:
        if s["target_fault_category"] != "Invention of New Information":
            continue
        answer = s["expected_answer"]
        assert any(bool(v) for v in answer.values()), s["task_id"]


def test_rerun_is_byte_identical(scenarios: list[dict]) -> None:
    again = build_benchmark(CATALOG)
    on_disk = json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n"
    regenerated = json.dumps(again, indent=2, ensure_ascii=False) + "\n"
    assert regenerated == on_disk


def _by_type(products):
    return {p.product_type: p for p in products}


def _by_item(products):
    return {(p.product_id, v.item_id): v for p in products for v in p.variants}


def test_expected_answer_recomputes(scenarios, products) -> None:
    by_type = _by_type(products)
    by_item = _by_item(products)
    for s in scenarios:
        tid = s["template_id"]
        args = s["default_tool_args"]
        answer = s["expected_answer"]
        if tid == "T1_cheapest":
            available = by_type[args["product_type"]].available_variants()
            cheapest = min(available, key=lambda v: (v.price, v.item_id))
            assert answer == {"item_id": cheapest.item_id, "price": cheapest.price}
        elif tid == "T2_count":
            available = by_type[args["product_type"]].available_variants()
            assert answer == {"count": len(available)}
        elif tid == "T3_spec_filter":
            opt = next(k for k in args if k not in KNOWN_ARGS)
            val, threshold = args[opt], args["price_min"]
            available = by_type[args["product_type"]].available_variants()
            ids = sorted(
                v.item_id
                for v in available
                if v.options.get(opt) == val and v.price > threshold
            )
            assert answer == {"item_ids": ids, "count": len(ids)}
        elif tid == "T5_item_price":
            variant = by_item[(args["product_id"], args["item_id"])]
            assert answer == {"price": variant.price}
        elif tid == "T4_item_option":
            variant = by_item[(args["product_id"], args["item_id"])]
            assert isinstance(answer["answer"], bool)
            assert variant is not None
