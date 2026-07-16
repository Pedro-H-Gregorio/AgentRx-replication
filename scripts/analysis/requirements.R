#!/usr/bin/env Rscript

packages <- c(
  "readr",
  "dplyr",
  "tidyr",
  "scales",
  "boot",
  "broom",
  "rmarkdown",
  "knitr",
  "ggplot2"
)

missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
if (length(missing) == 0L) {
  message("Todos os pacotes de análise já estão instalados.")
} else {
  message("Instalando: ", paste(missing, collapse = ", "))
  install.packages(missing)
}
