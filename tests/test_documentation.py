"""Documentation contracts stay aligned with generated data artifacts."""

from __future__ import annotations

from pathlib import Path
from re import MULTILINE, findall

from agentrx_otel_poc.collect.csv_writer import (
    METRICAS_COLUMNS,
    RUNS_LONG_COLUMNS,
    TRAJECTORY_INDEX_COLUMNS,
)

ROOT = Path(__file__).resolve().parent.parent
OPERATION_GUIDE = ROOT / "docs" / "operacao.md"
TESTS_GUIDE = ROOT / "tests" / "README.md"
INTERNAL_GUIDE = ROOT / "data" / "internal" / "README.md"
RESULTS_GUIDE = ROOT / "data" / "experiment" / "results" / "README.md"
ANALYSIS_GUIDE = ROOT / "data" / "experiment" / "analysis" / "README.md"
ANALYSIS_COLUMNS = {
    "tab_acuracias.csv": (
        "Métrica",
        "Telemetria (A)",
        "Log textual (B)",
        "Δ (A−B) p.p.",
    ),
    "tab_distancia_passo.csv": (
        "Braço",
        "Média",
        "DP",
        "Med.",
        "Mín.",
        "Máx.",
        "Norm.",
        "MAE",
    ),
    "tab_por_categoria.csv": (
        "Categoria",
        "Braço",
        "Failure Category Accuracy",
        "Critical Step Accuracy",
        "Average Step Distance",
    ),
    "tab_frequencia_mae_categoria.csv": (
        "Categoria",
        "Cat. A",
        "Cat. B",
        "Passo A",
        "Passo B",
        "MAE A",
        "MAE B",
    ),
    "tab_inferencial.csv": (
        "Teste",
        "Ambos",
        "Só A",
        "Só B",
        "Nenhum",
        "Resultado",
        "Leitura",
    ),
    "tab_estimativas_por_cenario.csv": (
        "Cenário",
        "GT categoria",
        "GT passo",
        "A categoria",
        "A passo",
        "B categoria",
        "B passo",
    ),
}


def _content(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_documentation_guides_exist() -> None:
    for path in (
        OPERATION_GUIDE,
        TESTS_GUIDE,
        INTERNAL_GUIDE,
        RESULTS_GUIDE,
        ANALYSIS_GUIDE,
    ):
        assert path.is_file(), path


def test_root_readme_links_to_operational_and_data_guides() -> None:
    readme = _content(ROOT / "README.md")
    for target in (
        "docs/operacao.md",
        "data/internal/README.md",
        "data/experiment/results/README.md",
        "data/experiment/analysis/README.md",
        "tests/README.md",
    ):
        assert target in readme


def test_results_dictionary_covers_collector_columns() -> None:
    dictionary = _content(RESULTS_GUIDE)
    for column in RUNS_LONG_COLUMNS + TRAJECTORY_INDEX_COLUMNS + METRICAS_COLUMNS:
        assert f"`{column}`" in dictionary


def test_operation_guide_covers_example_environment_keys() -> None:
    guide = _content(OPERATION_GUIDE)
    keys = findall(
        r"^(?:# )?([A-Z][A-Z0-9_]+)=", _content(ROOT / "example.env"), MULTILINE
    )
    for key in keys:
        assert f"`{key}`" in guide


def test_analysis_dictionary_covers_every_output_column() -> None:
    dictionary = _content(ANALYSIS_GUIDE)
    for table, columns in ANALYSIS_COLUMNS.items():
        assert f"`{table}`" in dictionary
        for column in columns:
            assert f"`{column}`" in dictionary


def test_internal_dictionary_replaces_legacy_document() -> None:
    assert not (ROOT / "docs" / "data-artifacts.md").exists()
    dictionary = _content(INTERNAL_GUIDE)
    for artifact in (
        "otel/",
        "trajectory_telemetry/",
        "trajectory_agentrx/",
        "ground_truth/",
        "manifests/",
        "agentrx/",
    ):
        assert artifact in dictionary
