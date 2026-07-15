tab_acuracias <- function(ctx) {
  acc_map <- c(
    step_acc_exact = "Critical Step Accuracy",
    step_acc_tol1 = "Passo ±1",
    step_acc_tol3 = "Passo ±3",
    step_acc_tol5 = "Passo ±5",
    cat_acc_critical = "Failure Category Accuracy"
  )
  w <- ctx$d |>
    dplyr::group_by(arm_lab) |>
    dplyr::summarise(dplyr::across(dplyr::all_of(names(acc_map)), mean),
      .groups = "drop"
    ) |>
    tidyr::pivot_longer(-arm_lab, names_to = "m", values_to = "v") |>
    tidyr::pivot_wider(names_from = arm_lab, values_from = v)
  a <- w[[ARM_A]]
  b <- w[[ARM_B]]
  out <- data.frame(
    Métrica = unname(acc_map[w$m]),
    A = scales::percent(a, .1),
    B = scales::percent(b, .1),
    d = sprintf("%+.1f", (a - b) * 100),
    check.names = FALSE
  )
  names(out) <- c("Métrica", ARM_A, ARM_B, "Δ (A−B) p.p.")
  out
}

tab_distancia_passo <- function(ctx) {
  ctx$d |>
    dplyr::group_by(`Braço` = arm_lab) |>
    dplyr::summarise(
      `Média` = sprintf("%.3f", mean(avg_step_distance)),
      DP = sprintf("%.3f", sd(avg_step_distance)),
      `Med.` = median(avg_step_distance),
      `Mín.` = min(avg_step_distance),
      `Máx.` = max(avg_step_distance),
      `Norm.` = sprintf("%.3f", mean(avg_step_distance_norm)),
      MAE = sprintf("%.3f", mean(step_mae)),
      .groups = "drop"
    )
}

tab_por_categoria <- function(ctx) {
  ctx$d |>
    dplyr::group_by(Categoria = cat_full, `Braço` = arm_lab) |>
    dplyr::summarise(
      `Failure Category Accuracy` = scales::percent(mean(cat_acc_critical), .1),
      `Critical Step Accuracy` = sprintf("%d/%d", sum(step_acc_exact), dplyr::n()),
      `Average Step Distance` = sprintf("%.3f", mean(avg_step_distance)),
      .groups = "drop"
    ) |>
    dplyr::arrange(Categoria, `Braço`)
}

tab_frequencia_mae_categoria <- function(ctx) {
  ctx$rep_d |>
    dplyr::group_by(cat_full, arm) |>
    dplyr::summarise(
      n = dplyr::n(),
      cat_hits = sum(cat_hit, na.rm = TRUE),
      step_hits = sum(step_hit, na.rm = TRUE),
      mae = sprintf("%.3f", mean(step_abs_error, na.rm = TRUE)),
      .groups = "drop"
    ) |>
    dplyr::mutate(
      cat_freq = sprintf("%d/%d", cat_hits, n - cat_hits),
      step_freq = sprintf("%d/%d", step_hits, n - step_hits)
    ) |>
    dplyr::select(cat_full, arm, cat_freq, step_freq, mae) |>
    tidyr::pivot_wider(
      names_from = arm,
      values_from = c(cat_freq, step_freq, mae),
      names_sep = "__"
    ) |>
    dplyr::arrange(cat_full) |>
    dplyr::transmute(
      Categoria = cat_full,
      `Cat. A` = cat_freq__telemetry,
      `Cat. B` = cat_freq__agentrx,
      `Passo A` = step_freq__telemetry,
      `Passo B` = step_freq__agentrx,
      `MAE A` = mae__telemetry,
      `MAE B` = mae__agentrx
    )
}

tab_inferencial <- function(ctx) {
  ci <- ctx$ci
  delta <- ctx$delta
  data.frame(
    Teste = c(
      "McNemar — Failure Category Accuracy",
      "McNemar — Critical Step Accuracy",
      "Wilcoxon pareado — Average Step Distance",
      "Bootstrap BCa IC95% — Δ Average Step Distance (A−B)"
    ),
    Ambos = c(ctx$ct_cat[["ambos"]], ctx$ct_step[["ambos"]], NA, NA),
    `Só A` = c(ctx$ct_cat[["so_a"]], ctx$ct_step[["so_a"]], NA, NA),
    `Só B` = c(ctx$ct_cat[["so_b"]], ctx$ct_step[["so_b"]], NA, NA),
    Nenhum = c(ctx$ct_cat[["nenhum"]], ctx$ct_step[["nenhum"]], NA, NA),
    Resultado = c(
      sprintf("p = %.3f", ctx$mc_cat$p.value),
      sprintf("p = %.3f", ctx$mc_step$p.value),
      sprintf("p = %.3f", ctx$wil$p.value),
      sprintf("%+.3f [%+.3f, %+.3f]", mean(delta), ci[1], ci[2])
    ),
    Leitura = c(
      ifelse(ctx$mc_cat$p.value > .05, "sem diferença detectável", "diferença significativa"),
      ifelse(ctx$mc_step$p.value > .05, "sem diferença detectável", "diferença significativa"),
      ifelse(ctx$wil$p.value > .05, "sem diferença detectável", "A distinguivelmente pior"),
      ifelse(ci[1] <= 0 & ci[2] >= 0, "IC inclui zero", "IC exclui zero → A pior")
    ),
    check.names = FALSE
  )
}

tab_estimativas_por_cenario <- function(ctx) {
  mark <- function(hit) ifelse(hit == 1, "✓", "✗")
  arm_est <- function(a) {
    ctx$d |>
      dplyr::filter(arm == a) |>
      dplyr::transmute(
        Cenário = scenario_id,
        cat = paste0(most_common_category_name, " ", mark(cat_acc_critical)),
        passo = paste0(round(step_mean), " ", mark(step_acc_exact))
      )
  }
  tel <- arm_est("telemetry")
  names(tel)[2:3] <- c("A categoria", "A passo")
  agx <- arm_est("agentrx")
  names(agx)[2:3] <- c("B categoria", "B passo")
  ctx$d |>
    dplyr::filter(arm == "telemetry") |>
    dplyr::transmute(
      Cenário = scenario_id,
      `GT categoria` = as.character(cat_full),
      `GT passo` = gt_step
    ) |>
    dplyr::left_join(tel, by = "Cenário") |>
    dplyr::left_join(agx, by = "Cenário")
}
