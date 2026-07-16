"""Static contracts for the reproducible R analysis environment."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _content(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_analysis_r_environment_contract_is_reproducible() -> None:
    lockfile = json.loads(_content(ROOT / "renv.lock"))
    packages = lockfile["Packages"]
    makefile = _content(ROOT / "Makefile")
    restore_script = _content(ROOT / "scripts" / "analysis" / "restore_renv.R")
    dockerfile = _content(ROOT / "docker" / "analysis" / "Dockerfile")
    analysis_guide = _content(ROOT / "data" / "experiment" / "analysis" / "README.md")

    assert lockfile["R"]["Version"] == "4.1.2"
    assert set(
        "renv readr dplyr tidyr scales boot broom rmarkdown knitr ggplot2".split()
    ) <= set(packages)
    assert "renv::restore" in restore_script
    assert '"renv", "library"' in restore_script

    for target in ("r-restore:", "analyze-container:", "R_ANALYSIS_LIBRARY"):
        assert target in makefile
    assert '--volume "$(CURDIR):/workspace"' in makefile
    for token in (
        "FROM rocker/r-ver:4.1.2",
        "curl",
        "libuv1-dev",
        "pandoc",
        "restore_renv.R",
    ):
        assert token in dockerfile
    assert '--user "$$(id -u):$$(id -g)"' in makefile
    for command in ("`make r-restore`", "`make analyze-container`", "`renv.lock`"):
        assert command in analysis_guide
    for heading in (
        "## Escolha como executar a análise",
        "### Opção A — R local",
        "### Opção B — Docker (sem R local)",
    ):
        assert heading in analysis_guide
