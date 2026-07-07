#!/usr/bin/env Rscript
# Análise A (telemetria) vs B (agentrx) sobre `metricas.csv` (PRD-07/PRD-10).
# Responde às RQs: a telemetria ajuda o juiz a LOCALIZAR (passo) e CLASSIFICAR
# (categoria) a falha? Gera tabelas (CSV + console) e figuras (PNG).
#
# Uso:
#   Rscript scripts/analysis/analyze_results.R [caminho/para/metricas.csv]
# Default:
#   data/experiment/results/Gemma3-27B/judge-codex-gpt-5-5/metricas.csv
#
# Saída: <dir do csv>/analysis/  (tabelas .csv, figuras .png, stats.txt)

# ---------------------------------------------------------------- pacotes ----
pkgs <- c("readr", "dplyr", "tidyr", "ggplot2", "scales")
for (p in pkgs) {
  if (!requireNamespace(p, quietly = TRUE)) {
    install.packages(p, repos = "https://cloud.r-project.org")
  }
}
suppressPackageStartupMessages(invisible(lapply(pkgs, library, character.only = TRUE)))

# ----------------------------------------------------------------- entrada ----
args <- commandArgs(trailingOnly = TRUE)
csv_path <- if (length(args) >= 1) args[[1]] else
  "data/experiment/results/Gemma3-27B/judge-codex-gpt-5-5/metricas.csv"
stopifnot("metricas.csv não encontrado" = file.exists(csv_path))

parts <- strsplit(normalizePath(csv_path), .Platform$file.sep)[[1]]
judge_id <- parts[length(parts) - 1]
mas_id <- parts[length(parts) - 2]
out_dir <- file.path(dirname(csv_path), "analysis")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
subtitle <- sprintf("MAS: %s   |   Juiz: %s   |   n = 30 cenários", mas_id, judge_id)

# ------------------------------------------------------------------- dados ----
INJECTABLE <- c(1, 2, 3, 4, 9) # as 5 categorias do estudo (FAILURE_CASE_TO_CATEGORY)
short_cat <- c(
  "System Failure" = "System Failure",
  "Invalid Invocation" = "Invalid Invocation",
  "Misinterpretation of Tool Output" = "Misinterpretation",
  "Invention of New Information" = "Invention",
  "Instruction/Plan Adherence Failure" = "Plan Adherence"
)
arm_cols <- c("Telemetria (A)" = "#0072B2", "AgentRx (B)" = "#E69F00")

d <- read_csv(csv_path, show_col_types = FALSE) |>
  mutate(
    arm_lab = factor(arm,
      levels = c("telemetry", "agentrx"),
      labels = names(arm_cols)
    ),
    cat_short = factor(
      dplyr::recode(gt_category_name, !!!short_cat),
      levels = unname(short_cat)
    ),
    in_scope = as.integer(most_common_category) %in% INJECTABLE
  )

save_fig <- function(plot, name, w = 7, h = 4.5) {
  ggsave(file.path(out_dir, name), plot, width = w, height = h, dpi = 150)
}
base_theme <- theme_minimal(base_size = 12) +
  theme(legend.title = element_blank(), legend.position = "top",
        plot.subtitle = element_text(color = "grey40", size = 9))

# ======================================================== TABELA 1: resumo ====
KEY <- c("step_acc_exact", "step_acc_tol1", "step_acc_tol3", "step_acc_tol5",
         "avg_step_distance", "avg_step_distance_norm", "cat_acc_critical",
         "cat_acc_any")
lbl <- c(
  step_acc_exact = "Passo exato", step_acc_tol1 = "Passo ±1",
  step_acc_tol3 = "Passo ±3", step_acc_tol5 = "Passo ±5",
  avg_step_distance = "Dist. passo (média)",
  avg_step_distance_norm = "Dist. passo (norm.)",
  cat_acc_critical = "Categoria crítica", cat_acc_any = "Categoria (any)"
)
summary_by_arm <- d |>
  group_by(arm_lab) |>
  summarise(across(all_of(KEY), mean), .groups = "drop") |>
  pivot_longer(-arm_lab, names_to = "metric", values_to = "value") |>
  pivot_wider(names_from = arm_lab, values_from = value) |>
  mutate(
    metrica = lbl[metric],
    delta_A_menos_B = `Telemetria (A)` - `AgentRx (B)`,
    melhor = ifelse(grepl("^avg_", metric),
      ifelse(delta_A_menos_B < 0, "A", "B"),
      ifelse(delta_A_menos_B > 0, "A", "B")
    ),
    melhor = ifelse(abs(delta_A_menos_B) < 1e-9, "empate", melhor)
  ) |>
  select(metrica, `Telemetria (A)`, `AgentRx (B)`, delta_A_menos_B, melhor)
write_csv(summary_by_arm, file.path(out_dir, "summary_by_arm.csv"))

# ==================================================== TABELA 2: por categoria ==
by_category <- d |>
  group_by(cat_short, arm_lab) |>
  summarise(
    cat_critical = mean(cat_acc_critical),
    step_exact = mean(step_acc_exact),
    dist_passo = mean(avg_step_distance),
    .groups = "drop"
  )
write_csv(by_category, file.path(out_dir, "by_category.csv"))

# ================================================= TABELA 3: pareado (vitórias) =
paired_wins <- lapply(c("cat_acc_critical", "step_acc_exact", "avg_step_distance"),
  function(m) {
    w <- d |>
      select(scenario_id, arm, all_of(m)) |>
      pivot_wider(names_from = arm, values_from = all_of(m))
    better_is_low <- grepl("^avg_", m)
    a <- w$telemetry; b <- w$agentrx
    A_vence <- if (better_is_low) sum(a < b) else sum(a > b)
    B_vence <- if (better_is_low) sum(a > b) else sum(a < b)
    data.frame(metrica = m, A_vence, B_vence, empate = sum(a == b))
  }
) |> bind_rows()
write_csv(paired_wins, file.path(out_dir, "paired_wins.csv"))

# ================================================= TABELA 4: fora do escopo =====
out_of_scope <- d |>
  group_by(arm_lab) |>
  summarise(
    fora_escopo = sum(!in_scope),
    de = n(),
    .groups = "drop"
  )
write_csv(out_of_scope, file.path(out_dir, "out_of_scope.csv"))

# ===================================================== ESTATÍSTICA (leve) ======
stats_lines <- c(sprintf("Análise: %s / %s (n=30, pareado por cenário)", mas_id, judge_id), "")

# McNemar (categoria crítica): discordâncias A-certo/B-errado vs A-errado/B-certo
wc <- d |>
  select(scenario_id, arm, cat_acc_critical) |>
  pivot_wider(names_from = arm, values_from = cat_acc_critical)
tab <- table(factor(wc$telemetry, c(1, 0)), factor(wc$agentrx, c(1, 0)))
mc <- suppressWarnings(mcnemar.test(tab))
stats_lines <- c(stats_lines,
  "== Categoria crítica (McNemar, discordâncias A vs B) ==",
  sprintf("  A certo / B errado: %d    A errado / B certo: %d",
    tab["1", "0"], tab["0", "1"]),
  sprintf("  McNemar chi2 = %.3f, p = %.3f", mc$statistic, mc$p.value), "")

# Bootstrap IC95% do delta médio de distância (A - B), pareado
set.seed(42)
wd <- d |>
  select(scenario_id, arm, avg_step_distance) |>
  pivot_wider(names_from = arm, values_from = avg_step_distance)
delta <- wd$telemetry - wd$agentrx
boot <- replicate(5000, mean(sample(delta, length(delta), replace = TRUE)))
ci <- quantile(boot, c(.025, .975))
stats_lines <- c(stats_lines,
  "== Distância de passo: delta médio (A - B), IC95% bootstrap ==",
  sprintf("  delta medio = %+.3f   IC95%% [%+.3f, %+.3f]  (>0 = telemetria PIOR)",
    mean(delta), ci[1], ci[2]),
  sprintf("  IC inclui zero? %s", ifelse(ci[1] <= 0 & ci[2] >= 0, "SIM (nao distinguivel)", "NAO")))
writeLines(stats_lines, file.path(out_dir, "stats.txt"))

# ================================================== FIGURA 1: métricas-chave ===
f1 <- d |>
  group_by(arm_lab) |>
  summarise(
    `Passo exato` = mean(step_acc_exact),
    `Passo ±1` = mean(step_acc_tol1),
    `Categoria crítica` = mean(cat_acc_critical),
    .groups = "drop"
  ) |>
  pivot_longer(-arm_lab, names_to = "metric", values_to = "value") |>
  mutate(metric = factor(metric, c("Passo exato", "Passo ±1", "Categoria crítica")))
p1 <- ggplot(f1, aes(metric, value, fill = arm_lab)) +
  geom_col(position = position_dodge(.7), width = .6) +
  geom_text(aes(label = percent(value, accuracy = .1)),
    position = position_dodge(.7), vjust = -.4, size = 3) +
  scale_y_continuous(labels = percent, limits = c(0, 1.08)) +
  scale_fill_manual(values = arm_cols) +
  labs(title = "Métricas-chave: telemetria vs baseline", subtitle = subtitle,
    x = NULL, y = "Acurácia") + base_theme
save_fig(p1, "fig1_metricas_chave.png")

# ============================================= FIGURA 2: curva de tolerância ===
f2 <- d |>
  group_by(arm_lab) |>
  summarise(exato = mean(step_acc_exact), `±1` = mean(step_acc_tol1),
    `±3` = mean(step_acc_tol3), `±5` = mean(step_acc_tol5), .groups = "drop") |>
  pivot_longer(-arm_lab, names_to = "tol", values_to = "acc") |>
  mutate(tol = factor(tol, c("exato", "±1", "±3", "±5")))
p2 <- ggplot(f2, aes(tol, acc, color = arm_lab, group = arm_lab)) +
  geom_line(linewidth = 1) + geom_point(size = 3) +
  scale_y_continuous(labels = percent, limits = c(0, 1.02)) +
  scale_color_manual(values = arm_cols) +
  labs(title = "Localização de passo por tolerância (efeito-teto)",
    subtitle = subtitle, x = "Tolerância (passos)", y = "Acurácia") + base_theme
save_fig(p2, "fig2_curva_tolerancia.png")

# ============================================ FIGURA 3: dispersão da distância ==
p3 <- ggplot(d, aes(arm_lab, avg_step_distance, fill = arm_lab)) +
  geom_boxplot(width = .4, alpha = .4, outlier.shape = NA) +
  geom_jitter(aes(color = arm_lab), width = .08, height = 0, alpha = .7, size = 2) +
  scale_fill_manual(values = arm_cols) + scale_color_manual(values = arm_cols) +
  labs(title = "Dispersão do erro de localização (distância |passo−gt|)",
    subtitle = subtitle, x = NULL, y = "Distância de passo") +
  base_theme + theme(legend.position = "none")
save_fig(p3, "fig3_dispersao_distancia.png", h = 4.5)

# ============================================ FIGURA 4: categoria por tipo ======
p4 <- ggplot(by_category, aes(cat_short, cat_critical, fill = arm_lab)) +
  geom_col(position = position_dodge(.7), width = .6) +
  scale_y_continuous(labels = percent, limits = c(0, 1.05)) +
  scale_fill_manual(values = arm_cols) +
  labs(title = "Acurácia de categoria por tipo de falha (H1/H2)",
    subtitle = subtitle, x = NULL, y = "Categoria crítica") +
  base_theme + theme(axis.text.x = element_text(angle = 20, hjust = 1))
save_fig(p4, "fig4_categoria_por_tipo.png", h = 5)

# ============================================ FIGURA 5: dispersão pareada =======
sc <- d |>
  select(scenario_id, arm, avg_step_distance) |>
  pivot_wider(names_from = arm, values_from = avg_step_distance)
lim <- c(0, max(sc$telemetry, sc$agentrx) * 1.05)
p5 <- ggplot(sc, aes(agentrx, telemetry)) +
  geom_abline(slope = 1, intercept = 0, linetype = 2, color = "grey50") +
  geom_jitter(width = .02, height = .02, alpha = .7, size = 2, color = "#0072B2") +
  coord_equal(xlim = lim, ylim = lim) +
  labs(title = "Distância pareada por cenário (acima da linha = telemetria pior)",
    subtitle = subtitle, x = "AgentRx (B) — distância", y = "Telemetria (A) — distância") +
  base_theme
save_fig(p5, "fig5_dispersao_pareada.png", w = 6, h = 6)

# ------------------------------------------------------------------ console ----
cat("\n================= RESUMO POR BRAÇO =================\n")
print(as.data.frame(summary_by_arm), row.names = FALSE, digits = 3)
cat("\n================= POR CATEGORIA ===================\n")
print(as.data.frame(by_category), row.names = FALSE, digits = 3)
cat("\n================= PAREADO (vitórias / 30) =========\n")
print(paired_wins, row.names = FALSE)
cat("\n================= FORA DO ESCOPO ==================\n")
print(as.data.frame(out_of_scope), row.names = FALSE)
cat("\n================= ESTATÍSTICA =====================\n")
writeLines(stats_lines)
cat(sprintf("\nTabelas e figuras salvas em: %s\n", out_dir))
