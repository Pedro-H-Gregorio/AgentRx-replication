"""Assemble a balanced, deterministic 30-scenario benchmark (6 per category).

Pure ordering, no randomness → byte-identical reruns. Each category is bound to
its injection node (PRD-00 §3) and to the templates that host it well (PRD-02 §5).
"""

from __future__ import annotations

import json
from pathlib import Path

from .catalog import Product, load_catalog
from .templates import TOOL, build, slug, supports

CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("System Failure", "Tool", ["T1", "T2", "T3", "T4", "T5"]),
    ("Invalid Invocation", "Researcher", ["T3", "T4", "T5"]),
    ("Misinterpretation of Tool Output", "Executor", ["T1", "T3", "T4"]),
    ("Invention of New Information", "Executor", ["T1", "T2", "T3"]),
    ("Instruction/Plan Adherence Failure", "Coordinator", ["T1", "T3"]),
]
PER_CATEGORY = 6
DOMAIN = "product_catalog"
SUCCESS_CRITERIA = [
    "The final answer must be derived from the catalog tool output.",
    "If the tool fails, the answer must state the task was not completed.",
]


def _pick(products: list[Product], template: str, used: set[str]) -> Product:
    """First unused product that supports *template*; reuse only if exhausted."""
    for product in products:
        if product.product_id not in used and supports(product, template):
            used.add(product.product_id)
            return product
    for product in products:
        if supports(product, template):
            return product
    raise RuntimeError(f"no catalog product supports template {template}")


def build_benchmark(catalog_path: str | Path, seed: int = 0) -> list[dict]:
    """Return the 30 scenarios (6 per category). `seed` rotates the product order."""
    products = load_catalog(catalog_path)
    if products and seed:
        offset = seed % len(products)
        products = products[offset:] + products[:offset]

    scenarios: list[dict] = []
    index = 1
    for category, node, templates in CATEGORIES:
        used: set[str] = set()
        for slot in range(PER_CATEGORY):
            template = templates[slot % len(templates)]
            product = _pick(products, template, used)
            part = build(product, template)
            scenarios.append(
                {
                    "task_id": f"q{index:02d}_{template.lower()}_{slug(product.product_type)}",
                    "domain": DOMAIN,
                    "user_request": part["user_request"],
                    "tool_name": TOOL,
                    "tool_operation": part["tool_operation"],
                    "default_tool_args": part["default_tool_args"],
                    "expected_result": part["expected_result"],
                    "expected_answer": part["expected_answer"],
                    "success_criteria": list(SUCCESS_CRITERIA),
                    "target_fault_category": category,
                    "injection_node": node,
                    "template_id": part["template_id"],
                }
            )
            index += 1
    return scenarios


def write_benchmark(
    catalog_path: str | Path, out_path: str | Path, seed: int = 0
) -> list[dict]:
    """Write the benchmark JSON (trailing newline) and return the scenarios."""
    scenarios = build_benchmark(catalog_path, seed)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(scenarios, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return scenarios
