#!/usr/bin/env Rscript

script_file <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)[1])
analysis_dir <- dirname(normalizePath(script_file))
project_root <- normalizePath(file.path(analysis_dir, "..", ".."))

analysis_library_path <- function(root) {
  configured <- Sys.getenv("R_ANALYSIS_LIBRARY")
  if (nzchar(configured)) return(configured)

  r_series <- paste(
    R.version$major,
    sub("\\..*$", "", R.version$minor),
    sep = "."
  )
  file.path(root, "renv", "library", paste0("R-", r_series), R.version$platform)
}

project_library <- analysis_library_path(project_root)
bootstrap_library <- file.path(project_root, ".renv", "bootstrap")

if (!nzchar(Sys.getenv("RENV_PATHS_CACHE"))) {
  Sys.setenv(RENV_PATHS_CACHE = file.path(project_root, ".renv", "cache"))
}

dir.create(project_library, recursive = TRUE, showWarnings = FALSE)
dir.create(bootstrap_library, recursive = TRUE, showWarnings = FALSE)

if (!requireNamespace("renv", quietly = TRUE, lib.loc = bootstrap_library)) {
  utils::install.packages(
    "renv",
    lib = bootstrap_library,
    repos = "https://cloud.r-project.org"
  )
}

library(renv, lib.loc = bootstrap_library)
renv::restore(project = project_root, library = project_library, prompt = FALSE)
cat(sprintf("Ambiente R restaurado em %s\\n", project_library))
