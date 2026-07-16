#!/usr/bin/env Rscript

here <- dirname(normalizePath(sub(
  "^--file=", "",
  grep("^--file=", commandArgs(FALSE), value = TRUE)[1]
)))
source(file.path(here, "c8_lib.R"))
source(file.path(here, "c8_tables.R"))

args <- commandArgs(trailingOnly = TRUE)
csv_path <- if (length(args) >= 1) {
  args[[1]]
} else {
  "data/experiment/results/MAS-SIM/judge-codex-gpt-5-5/metricas.csv"
}

ctx <- c8_context(csv_path)
dir.create(ctx$out_dir, showWarnings = FALSE, recursive = TRUE)

tables <- list(
  tab_acuracias = tab_acuracias(ctx),
  tab_distancia_passo = tab_distancia_passo(ctx),
  tab_por_categoria = tab_por_categoria(ctx),
  tab_frequencia_mae_categoria = tab_frequencia_mae_categoria(ctx),
  tab_inferencial = tab_inferencial(ctx),
  tab_estimativas_por_cenario = tab_estimativas_por_cenario(ctx)
)

cat(sprintf(
  "C8 análise — MAS: %s | Juiz: %s | n = %d cenários (%s reps)\n",
  ctx$mas_id, ctx$judge_id, ctx$n_scen, ctx$n_judge_reps
))
for (nm in names(tables)) {
  path <- file.path(ctx$out_dir, paste0(nm, ".csv"))
  # Single-thread writing prevents vroom from corrupting multibyte cells.
  readr::write_csv(tables[[nm]], path, na = "", num_threads = 1)
  cat(sprintf("  ✓ %s\n", path))
}
cat(sprintf("Tabelas escritas em %s\n", ctx$out_dir))
