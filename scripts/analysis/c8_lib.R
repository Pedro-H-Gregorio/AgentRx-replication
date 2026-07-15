ANALYSIS_PACKAGES <- c("readr", "dplyr", "tidyr", "scales", "boot", "broom")

c8_require_packages <- function(packages) {
  missing <- packages[!vapply(packages, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing) == 0) return(invisible())

  stop(
    "Pacotes R ausentes: ", paste(missing, collapse = ", "),
    ". Instale-os antes de executar a análise.",
    call. = FALSE
  )
}

c8_require_packages(ANALYSIS_PACKAGES)

# Parallel vroom writing corrupts multibyte ✓/✗ cells; keep outputs byte-stable.
options(readr.num_threads = 1)

ARM_A <- "Telemetria (A)"
ARM_B <- "Log textual (B)"

INJECTABLE <- c(1, 2, 3, 4, 9)
CAT_ORDER <- c(
  "System Failure",
  "Invalid Invocation",
  "Misinterpretation of Tool Output",
  "Invention of New Information",
  "Instruction/Plan Adherence Failure"
)

c8_find_csv <- function(p) {
  if (file.exists(p)) {
    return(normalizePath(p))
  }
  dir <- normalizePath(".")
  repeat {
    cand <- file.path(dir, p)
    if (file.exists(cand)) {
      return(normalizePath(cand))
    }
    parent <- dirname(dir)
    if (parent == dir) stop("metricas.csv não encontrado: ", p)
    dir <- parent
  }
}

c8_read <- function(path) {
  readr::read_csv(path, show_col_types = FALSE)
}

c8_wide <- function(d, metric) {
  d |>
    dplyr::select(scenario_id, arm, dplyr::all_of(metric)) |>
    tidyr::pivot_wider(names_from = arm, values_from = dplyr::all_of(metric))
}

c8_contingency <- function(w) {
  c(
    ambos = sum(w$telemetry == 1 & w$agentrx == 1),
    so_a = sum(w$telemetry == 1 & w$agentrx == 0),
    so_b = sum(w$telemetry == 0 & w$agentrx == 1),
    nenhum = sum(w$telemetry == 0 & w$agentrx == 0)
  )
}

mean_paired_distance_delta <- function(data, indices) {
  pairs <- data[indices, , drop = FALSE]
  mean(pairs$telemetry - pairs$agentrx)
}

c8_context <- function(csv_path) {
  csv_path <- c8_find_csv(csv_path)
  runs_path <- file.path(dirname(csv_path), "runs_long.csv")
  if (!file.exists(runs_path)) {
    stop("runs_long.csv não encontrado ao lado de metricas.csv: ", runs_path)
  }

  judge_dir <- dirname(csv_path)
  mas_dir <- dirname(judge_dir)
  results_dir <- dirname(mas_dir)
  experiment_dir <- dirname(results_dir)
  judge_id <- basename(judge_dir)
  mas_id <- basename(mas_dir)
  # Preserve results' namespace to avoid collisions between MAS corpora.
  out_dir <- file.path(experiment_dir, "analysis", mas_id, judge_id)

  d <- c8_read(csv_path) |>
    dplyr::mutate(
      arm_lab = factor(arm,
        levels = c("telemetry", "agentrx"),
        labels = c(ARM_A, ARM_B)
      ),
      cat_full = factor(gt_category_name, levels = CAT_ORDER),
      in_scope = as.integer(most_common_category) %in% INJECTABLE
    )
  runs <- c8_read(runs_path)

  rep_d <- runs |>
    dplyr::left_join(
      d |> dplyr::select(
        scenario_id, arm, gt_step, gt_category, gt_category_name,
        cat_full, arm_lab
      ),
      by = c("scenario_id", "arm")
    ) |>
    dplyr::mutate(
      pred_step = as.integer(pred_step),
      pred_category = as.integer(pred_category),
      step_hit = pred_step == gt_step,
      cat_hit = pred_category == gt_category,
      step_abs_error = abs(pred_step - gt_step)
    )

  n_scen <- length(unique(d$scenario_id))
  n_judge_reps <- paste(sort(unique(d$n_judge_runs)), collapse = "/")

  wc <- c8_wide(d, "cat_acc_critical")
  mc_cat <- suppressWarnings(mcnemar.test(
    table(factor(wc$telemetry, c(1, 0)), factor(wc$agentrx, c(1, 0)))
  ))
  ws <- c8_wide(d, "step_acc_exact")
  mc_step <- suppressWarnings(mcnemar.test(
    table(factor(ws$telemetry, c(1, 0)), factor(ws$agentrx, c(1, 0)))
  ))
  wd <- c8_wide(d, "avg_step_distance")
  delta <- wd$telemetry - wd$agentrx
  wil <- suppressWarnings(wilcox.test(wd$telemetry, wd$agentrx, paired = TRUE))
  set.seed(42)
  booted <- boot::boot(data = wd, statistic = mean_paired_distance_delta, R = 5000)
  ci_bca <- broom::tidy(
    booted,
    conf.level = .95, conf.method = "bca", conf.int = TRUE
  )
  ci <- c(ci_bca$conf.low, ci_bca$conf.high)

  list(
    d = d, runs = runs, rep_d = rep_d,
    csv_path = csv_path,
    mas_id = mas_id, judge_id = judge_id, out_dir = out_dir,
    n_scen = n_scen, n_judge_reps = n_judge_reps,
    mc_cat = mc_cat, mc_step = mc_step, wil = wil,
    delta = delta, ci = ci,
    ct_cat = c8_contingency(wc), ct_step = c8_contingency(ws)
  )
}
