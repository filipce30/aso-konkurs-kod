#!/usr/bin/env Rscript
# Fit LC, CBD, RH and APC under COVID variants A, B, C; backtest; model table.
suppressPackageStartupMessages({library(ggplot2); library(svglite)})
source("analysis/mortality/lib_mortality.R")
set.seed(2026)
dir.create("analysis/mortality", showWarnings = FALSE, recursive = TRUE)
t_start <- Sys.time()

SEXES <- c("m", "f")
VARIANTS <- list(
  A = list(years = 2003:2019, zero = integer(0),
           label = "А: 2003-2019 (пред-ковид)"),
  B = list(years = 2003:2023, zero = c(2020, 2021, 2022),
           label = "Б: 2003-2023, нулти тегови 2020-2022"),
  C = list(years = 2003:2023, zero = c(2022),
           label = "В: наивен 2003-2023")
)
RH_ON <- TRUE

RH_COHORT_AGE_FUN <- "1"
RH_APPROX_CONST   <- TRUE
RH_ITER_MAX       <- 10000L

fit_rh_attempts <- function(dd, years, zero_years, lcfit, clip = CLIP,
                            cohortAgeFun = RH_COHORT_AGE_FUN) {
  ages <- dd$ages
  w <- eff_weight_mat(ages, years, zero_years, clip = clip)
  extra <- attr(w, "extra_clipped")
  yy <- as.character(years)
  ddy <- list(D = dd$D[, yy, drop = FALSE], E = dd$E[, yy, drop = FALSE],
              ages = ages, years = years, sex = dd$sex)
  obj <- as_stmomo(ddy, "central")
  k0 <- lcfit$kt
  specs <- list(
    list(tag = "start=LC",              kt = k0),
    list(tag = "start=LC+N(0,0.5)",     kt = k0 + rnorm(length(k0), 0, 0.5)),
    list(tag = "start=LC+N(1,1.0)",     kt = k0 + rnorm(length(k0), 1, 1.0)),
    list(tag = "start=linear kt, flat bx",
         kt = matrix(seq(5, -5, length.out = length(years)), nrow = 1),
         bx = matrix(1 / length(ages), nrow = length(ages)))
  )
  out <- list()
  for (sp in specs) {
    t0 <- Sys.time()
    args <- list(object = rh(link = "log", cohortAgeFun = cohortAgeFun,
                             approxConst = RH_APPROX_CONST),
                 data = obj, ages.fit = ages, years.fit = years, wxt = w,
                 verbose = FALSE, iterMax = RH_ITER_MAX)
    args$start.ax <- lcfit$ax
    args$start.bx <- if (is.null(sp$bx)) lcfit$bx else sp$bx
    args$start.kt <- sp$kt
    f <- tryCatch(suppressWarnings(do.call(fit, args)), error = function(e) NULL)
    secs <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
    degenerate <- !is.null(f) && (all(is.na(f$gc)) || !is.finite(f$loglik) || f$loglik == 0)
    if (is.null(f) || degenerate) {
      out[[sp$tag]] <- list(tag = sp$tag, ok = FALSE,
                            err = if (is.null(f)) "gnm error" else "degenerate fit (no cohort effect returned)",
                            secs = secs)
    } else {
      f$wxt <- w
      gcv <- f$gc[!is.na(f$gc)]
      out[[sp$tag]] <- list(tag = sp$tag, ok = TRUE, conv = isTRUE(f$conv),
                            fail = isTRUE(f$fail), loglik = f$loglik, npar = f$npar,
                            nobs = f$nobs, gc_absmax = max(abs(gcv)), gc_range = range(gcv),
                            secs = secs, fit = f)
    }
    message(sprintf("    RH [%s] %.1fs  loglik=%s gc|max|=%s", sp$tag, secs,
                    if (is.null(out[[sp$tag]]$loglik)) "NA" else
                      formatC(out[[sp$tag]]$loglik, format = "f", digits = 3),
                    if (is.null(out[[sp$tag]]$gc_absmax)) "NA" else
                      formatC(out[[sp$tag]]$gc_absmax, format = "g", digits = 3)))
  }
  ok <- Filter(function(z) isTRUE(z$ok), out)
  stable <- FALSE; reason <- "no attempt returned a fit"
  if (length(ok)) {
    lls <- sapply(ok, `[[`, "loglik"); gcm <- sapply(ok, `[[`, "gc_absmax")
    convs <- sapply(ok, `[[`, "conv")
    ll_spread <- diff(range(lls))
    stable <- all(convs) && length(ok) >= 3L && ll_spread < 1 && all(gcm < 1)
    reason <- sprintf("cohortAgeFun=%s, clip=%d (cohorts %s also clipped), %d/%d starts converged; loglik spread=%.3g; max|gamma_c|=%.3f",
                      cohortAgeFun, clip,
                      if (length(extra)) paste(extra, collapse = ",") else "none",
                      length(ok), length(out), ll_spread, max(gcm))
  }
  list(attempts = out, stable = stable, reason = reason, wxt = w,
       extra_clipped = extra, clip = clip,
       best = if (length(ok)) ok[[which.max(sapply(ok, `[[`, "loglik"))]]$fit else NULL)
}

fits <- list(); rh_diag <- list()
for (s in SEXES) {
  dd <- load_sex(s)
  fits[[s]] <- list()
  for (v in names(VARIANTS)) {
    yr <- VARIANTS[[v]]$years; ze <- VARIANTS[[v]]$zero
    message(sprintf("[fit] sex=%s variant=%s years=%d-%d zero={%s}", s, v,
                    min(yr), max(yr), paste(ze, collapse = ",")))
    L <- list()
    for (mn in c("lc", "cbd", "apc")) L[[mn]] <- fit_one(mn, dd, yr, ze)
    fits[[s]][[v]] <- L
  }
  if (RH_ON) {
    message(sprintf("[RH ] sex=%s variant=B (convergence study)", s))
    # RH runs on its own RNG stream so the other fits do not depend on it.
    .rng <- get(".Random.seed", .GlobalEnv); set.seed(2026L)
    rh_diag[[s]] <- fit_rh_attempts(dd, VARIANTS$B$years, VARIANTS$B$zero,
                                    fits[[s]][["B"]][["lc"]])
    assign(".Random.seed", .rng, .GlobalEnv)
    message(sprintf("    RH stable for %s: %s (%s)", s, rh_diag[[s]]$stable,
                    rh_diag[[s]]$reason))
    if (rh_diag[[s]]$stable) fits[[s]][["B"]][["rh"]] <- rh_diag[[s]]$best
  }
}
RH_KEEP <- RH_ON && all(sapply(SEXES, function(s) isTRUE(rh_diag[[s]]$stable)))

if (RH_KEEP) for (s in SEXES) {
  dd <- load_sex(s)
  for (v in c("A", "C")) {
    .rng <- get(".Random.seed", .GlobalEnv); set.seed(2026L)
    r <- fit_rh_attempts(dd, VARIANTS[[v]]$years, VARIANTS[[v]]$zero,
                         fits[[s]][[v]][["lc"]])
    assign(".Random.seed", .rng, .GlobalEnv)
    rh_diag[[paste0(s, v)]] <- r
    if (r$stable) fits[[s]][[v]][["rh"]] <- r$best
  }
}

kt_of <- function(f) {
  k <- f$kt
  if (is.null(k)) return(NULL)
  k[, colSums(f$wxt) == 0] <- NA
  k
}
rates_of <- function(f) {
  r <- fitted(f, type = "rates")
  if (f$model$link == "logit") r <- q_to_m(r)
  r
}
plaus_note <- function(mn, f) {
  if (mn == "lc") {
    b <- as.numeric(f$bx)
    sprintf("beta_x: min=%.4f, %d/%d негативни, грубост=%.4f",
            min(b), sum(b < 0), length(b),
            mean(abs(diff(diff(b)))) / mean(abs(b)))
  } else if (mn == "rh") {
    b <- as.numeric(f$bx); g <- f$gc[!is.na(f$gc)]
    sprintf("beta_x: min=%.4f, %d/%d негативни, грубост=%.4f; gamma_c: опсег [%.3f, %.3f], |max|=%.3f",
            min(b), sum(b < 0), length(b),
            mean(abs(diff(diff(b)))) / mean(abs(b)),
            min(g), max(g), max(abs(g)))
  } else if (mn == "cbd") {
    k2 <- kt_of(f)[2, ]; k2 <- k2[!is.na(k2)]
    sprintf("kappa2_t: min=%.4f, сите позитивни=%s", min(k2), all(k2 > 0))
  } else if (mn == "apc") {
    g <- f$gc[!is.na(f$gc)]
    sprintf("gamma_c: опсег [%.3f, %.3f], |max|=%.3f", min(g), max(g), max(abs(g)))
  } else "-"
}
gc_note <- function(f) {
  if (is.null(f$gc)) return(NA_real_)
  max(abs(f$gc[!is.na(f$gc)]))
}

rows <- list()
for (s in SEXES) for (v in names(VARIANTS)) for (mn in names(fits[[s]][[v]])) {
  f <- fits[[s]][[v]][[mn]]
  M <- rates_of(f)
  D <- f$Dxt
  E <- if (f$model$link == "logit") f$Ext - 0.5 * f$Dxt else f$Ext
  bc <- bic_common(D, E, M, f$wxt, f$npar)
  kt <- kt_of(f)
  rwd <- if (!is.null(kt)) fit_rwd(kt[1, ], f$years) else NULL
  rows[[length(rows) + 1]] <- data.table(
    sex = s, variant = v, model = mn,
    loglik_native = f$loglik, npar = f$npar, nobs = f$nobs,
    bic_native = BIC(f), loglik_pois = bc["loglik"], bic_common = bc["bic"],
    drift = if (is.null(rwd)) NA_real_ else rwd$drift,
    drift_se = if (is.null(rwd)) NA_real_ else rwd$se,
    sigma = if (is.null(rwd)) NA_real_ else rwd$sigma,
    gc_absmax = gc_note(f), plausibility = plaus_note(mn, f))
}
mt <- rbindlist(rows)

BT_FIT <- 2003:2014; BT_OUT <- 2015:2019
lt <- fread("data/clean/lifetables_period.csv")
actual_e65 <- function(s, y) lt[year == y & sex == s & age == 65, ex]

bt_rows <- list(); bt_paths <- list()
for (s in SEXES) {
  dd <- load_sex(s)
  Mact <- dd$D[, as.character(BT_OUT), drop = FALSE] / dd$E[, as.character(BT_OUT), drop = FALSE]
  bt_models <- c("lc", "cbd", "apc", if (RH_KEEP) "rh")
  for (mn in bt_models) {
    f <- tryCatch(if (mn == "rh")
      fit_rh_attempts(dd, BT_FIT, integer(0), fit_one("lc", dd, BT_FIT, integer(0)))$best
      else fit_one(mn, dd, BT_FIT, integer(0)), error = function(e) NULL)
    if (is.null(f)) next
    h <- length(BT_OUT)
    if (mn %in% c("apc", "rh")) {
      fc <- suppressWarnings(forecast(f, h = h))
      Mfc <- fc$rates
    } else {
      kt <- f$kt
      if (mn == "lc") {
        r <- fit_rwd(kt[1, ], BT_FIT)
        kfc <- central_rwd(r$last_value, r$drift, h)
        Mfc <- exp(outer(as.numeric(f$ax), rep(1, h)) + outer(as.numeric(f$bx), kfc))
      } else {
        r1 <- fit_rwd(kt[1, ], BT_FIT); r2 <- fit_rwd(kt[2, ], BT_FIT)
        k1 <- central_rwd(r1$last_value, r1$drift, h)
        k2 <- central_rwd(r2$last_value, r2$drift, h)
        xb <- mean(f$ages)
        eta <- outer(rep(1, length(f$ages)), k1) + outer(f$ages - xb, k2)
        Mfc <- q_to_m(1 / (1 + exp(-eta)))
      }
      dimnames(Mfc) <- list(as.character(f$ages), as.character(BT_OUT))
    }
    ok <- is.finite(Mact) & Mact > 0 & is.finite(Mfc) & Mfc > 0
    err <- log(Mfc[ok]) - log(Mact[ok])
    a60 <- rownames(Mact) %in% as.character(60:89)
    ok60 <- ok & a60
    e65_fc <- e65_from_closed(close_kannisto(t(Mfc[as.character(AGES_FIT), , drop = FALSE])))
    names(e65_fc) <- as.character(BT_OUT)
    bt_rows[[length(bt_rows) + 1]] <- data.table(
      sex = s, model = mn, n_cells = sum(ok),
      rmse_logm_55_89 = sqrt(mean(err^2)),
      rmse_logm_60_89 = sqrt(mean((log(Mfc[ok60]) - log(Mact[ok60]))^2)),
      bias_logm = mean(err),
      e65_2019_fc = unname(e65_fc["2019"]), e65_2019_act = actual_e65(s, 2019),
      e65_err_2019 = unname(e65_fc["2019"]) - actual_e65(s, 2019))
    for (ag in c(65, 75, 85)) bt_paths[[length(bt_paths) + 1]] <- data.table(
      sex = s, model = mn, age = ag, year = BT_OUT,
      logm_fc = log(Mfc[as.character(ag), ]), logm_act = log(Mact[as.character(ag), ]))
  }
}
bt <- rbindlist(bt_rows); btp <- rbindlist(bt_paths)
fwrite(btp, "analysis/mortality/backtest_paths.csv")

mt2 <- merge(mt, bt[, .(sex, model, rmse_logm_55_89, rmse_logm_60_89,
                        e65_err_2019)], by = c("sex", "model"), all.x = TRUE)
setorder(mt2, sex, variant, model)
fwrite(mt2, "analysis/mortality/model_table.csv")
fwrite(bt, "analysis/mortality/backtest.csv")

kt_long <- rbindlist(lapply(SEXES, function(s) rbindlist(lapply(names(VARIANTS), function(v)
  rbindlist(lapply(c("lc", "cbd"), function(mn) {
    f <- fits[[s]][[v]][[mn]]; k <- kt_of(f)
    rbindlist(lapply(seq_len(nrow(k)), function(i)
      data.table(sex = s, variant = v, model = mn, index = i,
                 year = f$years, kt = as.numeric(k[i, ]))))
  }))))))
fwrite(kt_long, "analysis/mortality/kt_series.csv")

saveRDS(list(fits = fits, rh_diag = lapply(rh_diag, function(z)
             list(attempts = lapply(z$attempts, function(a) a[setdiff(names(a), "fit")]),
                  stable = z$stable, reason = z$reason)),
             rh_keep = RH_KEEP, variants = VARIANTS, backtest = bt,
             model_table = mt2, kt = kt_long),
        "analysis/mortality/fits.rds", compress = "xz")

stage1 <- list(rh_keep = RH_KEEP,
               rh_reason = lapply(rh_diag, function(z) z$reason),
               rh_attempts = lapply(rh_diag, function(z)
                 lapply(z$attempts, function(a) a[setdiff(names(a), "fit")])))
write_json(stage1, "analysis/mortality/_stage1.json", auto_unbox = TRUE,
           pretty = TRUE, digits = 8, na = "null")

message(sprintf("[done] fit_models.R in %.1f min",
                as.numeric(difftime(Sys.time(), t_start, units = "mins"))))
print(mt2[, .(sex, variant, model, npar, bic_native, bic_common, drift, drift_se,
              rmse_logm_55_89, e65_err_2019)])
print(bt)
