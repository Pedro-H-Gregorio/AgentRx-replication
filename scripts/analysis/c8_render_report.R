#!/usr/bin/env Rscript

script_path <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
here <- dirname(normalizePath(script_path))
source(file.path(here, "c8_lib.R"))

REPORT_PACKAGES <- c("rmarkdown", "knitr", "ggplot2")
REPORT_TEMPLATE <- file.path(here, "analysis_report.Rmd")
REPORT_FILENAME <- "analysis_report.md"

report_metrics_path <- function(args) {
  if (length(args) != 1) {
    stop("Uso: Rscript scripts/analysis/c8_render_report.R <metricas.csv>", call. = FALSE)
  }
  c8_find_csv(args[[1]])
}

report_require_pandoc <- function() {
  if (!rmarkdown::pandoc_available()) {
    stop("Pandoc não encontrado. Instale-o antes de renderizar o relatório.", call. = FALSE)
  }
}

report_output_paths <- function(out_dir) {
  list(
    markdown = file.path(out_dir, REPORT_FILENAME),
    figures = file.path(out_dir, "analysis_report_files"),
    html = file.path(out_dir, "analysis_report.html")
  )
}

report_relativize_paths <- function(markdown_path, out_dir) {
  absolute_dir <- paste0(normalizePath(out_dir, winslash = "/", mustWork = TRUE), "/")
  contents <- readLines(markdown_path, warn = FALSE, encoding = "UTF-8")
  writeLines(gsub(absolute_dir, "", contents, fixed = TRUE), markdown_path, useBytes = TRUE)
}

render_report <- function(csv_path) {
  c8_require_packages(REPORT_PACKAGES)
  report_require_pandoc()
  if (!file.exists(REPORT_TEMPLATE)) stop("Template Rmd não encontrado: ", REPORT_TEMPLATE)

  ctx <- c8_context(csv_path)
  dir.create(ctx$out_dir, showWarnings = FALSE, recursive = TRUE)
  paths <- report_output_paths(ctx$out_dir)
  unlink(paths$figures, recursive = TRUE, force = TRUE)
  unlink(paths$html, force = TRUE)

  rmarkdown::render(
    input = REPORT_TEMPLATE,
    output_format = "github_document",
    output_file = "analysis_report.md",
    output_dir = ctx$out_dir,
    params = list(csv = ctx$csv_path),
    quiet = TRUE,
    envir = new.env(parent = globalenv())
  )

  if (!file.exists(paths$markdown)) stop("Relatório Markdown não foi produzido.")
  report_relativize_paths(paths$markdown, ctx$out_dir)
  if (file.exists(paths$html)) stop("Renderização produziu HTML inesperado.")
  cat(sprintf("Relatório escrito em %s\n", paths$markdown))
}

render_report(report_metrics_path(commandArgs(trailingOnly = TRUE)))
