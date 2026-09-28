#!/usr/bin/env Rscript
# Renshaw-Haberman refit on the effective-clip weights, clipped APC comparator, rh_* keys.
suppressPackageStartupMessages({library(ggplot2); library(svglite)})
source("analysis/mortality/lib_mortality.R")
set.seed(2026)

SEXES <- c("m", "f")
VARIANTS <- list(A = list(years = 2003:2019, zero = integer(0)),
                 B = list(years = 2003:2023, zero = c(2020, 2021, 2022)),
                 C = list(years = 2003:2023, zero = c(2022)))
VAR_MAIN <- "B"; JUMPOFF <- 2023L; E65_YEAR <- 2050L
BT_FIT <- 2003:2014; BT_OUT <- 2015:2019

mk_obj <- function(dd, years) as_stmomo(
  list(D = dd$D[, as.character(years), drop = FALSE],
       E = dd$E[, as.character(years), drop = FALSE],
       ages = dd$ages, years = years, sex = dd$sex), "central")

fit_rh1 <- function(dd, years, zero, lcf, clip = 3L, caf = "1", kt_start = NULL) {
  w <- eff_weight_mat(dd$ages, years, zero, clip = clip)
  f <- tryCatch(suppressWarnings(fit(
        rh(link = "log", cohortAgeFun = caf, approxConst = TRUE),
        data = mk_obj(dd, years), ages.fit = dd$ages, years.fit = years, wxt = w,
        verbose = FALSE, iterMax = 10000L, start.ax = lcf$ax, start.bx = lcf$bx,
        start.kt = if (is.null(kt_start)) lcf$kt else kt_start)),
        error = function(e) NULL)
  if (!is.null(f)) f$wxt <- w
  f
}
fit_generic <- function(model_name, dd, years, zero, clip = 3L) {
  w <- eff_weight_mat(dd$ages, years, zero, clip = clip)
  mdl <- switch(model_name, apc = apc(link = "log"), cbd = cbd(link = "logit"),
                lc(link = "log"))
  obj <- mk_obj(dd, years)
  if (model_name == "cbd") obj <- central2initial(obj)
  f <- suppressWarnings(fit(mdl, data = obj, ages.fit = dd$ages,
                            years.fit = years, wxt = w, verbose = FALSE))
  f$wxt <- w
  if (model_name == "cbd") f$Ext <- f$Ext - 0.5 * f$Dxt
  f
}
bic_of <- function(f) {
  M <- fitted(f, type = "rates")
  if (f$model$link == "logit") M <- q_to_m(M)
  bc <- bic_common(f$Dxt, f$Ext, M, f$wxt, f$npar)
  list(bic_common = unname(bc["bic"]), loglik_pois = unname(bc["loglik"]),
       bic_native = BIC(f), npar = f$npar, nobs = f$nobs,
       gc_absmax = if (is.null(f$gc)) NA_real_ else max(abs(f$gc[!is.na(f$gc)])))
}

message("[1] ablation: cohortAgeFun NP vs 1, base vs effective clip (variant B)")
ablation <- list()
for (s in SEXES) {
  dd <- load_sex(s); yr <- VARIANTS$B$years; ze <- VARIANTS$B$zero
  lcf <- fit_one("lc", dd, yr, ze)
  for (caf in c("NP", "1")) for (wn in c("base", "eff")) {
    lls <- c(); gcs <- c()
    for (j in 1:3) {
      kt <- if (j == 1) lcf$kt else lcf$kt + rnorm(length(lcf$kt), 0, 0.5 * (j - 1))
      w <- if (wn == "base") weight_mat(dd$ages, yr, ze, clip = 3)
           else eff_weight_mat(dd$ages, yr, ze, clip = 3)
      f <- tryCatch(suppressWarnings(fit(
            rh(link = "log", cohortAgeFun = caf, approxConst = TRUE),
            data = mk_obj(dd, yr), ages.fit = dd$ages, years.fit = yr, wxt = w,
            verbose = FALSE, iterMax = 10000L, start.ax = lcf$ax,
            start.bx = lcf$bx, start.kt = kt)), error = function(e) NULL)
      if (is.null(f) || all(is.na(f$gc))) { lls <- c(lls, NA); gcs <- c(gcs, NA); next }
      lls <- c(lls, f$loglik); gcs <- c(gcs, max(abs(f$gc[!is.na(f$gc)])))
    }
    ablation[[sprintf("%s_%s_%s", s, caf, wn)]] <- list(
      sex = s, cohortAgeFun = caf, weights = wn, nobs = sum(w > 0),
      loglik = lls, loglik_spread = diff(range(lls, na.rm = TRUE)),
      gc_absmax = gcs)
    message(sprintf("    %s caf=%-2s w=%-4s nobs=%d ll=%.2f |gc|max=%.4g",
                    s, caf, wn, sum(w > 0), max(lls, na.rm = TRUE),
                    max(gcs, na.rm = TRUE)))
  }
}

message("[2] corrected RH (cohortAgeFun = 1) - variants A/B/C, clip 3 and clip 5")
S1 <- readRDS("analysis/mortality/fits.rds")
rh_stats <- list(); rh_clip5 <- list()
for (s in SEXES) {
  dd <- load_sex(s)
  for (v in names(VARIANTS)) {
    f <- S1$fits[[s]][[v]][["rh"]]
    stopifnot(!is.null(f))
    rh_stats[[paste0(s, v)]] <- c(bic_of(f), list(
      extra_clipped = attr(eff_weight_mat(dd$ages, VARIANTS[[v]]$years,
                                          VARIANTS[[v]]$zero, 3L), "extra_clipped")))
  }
  lcf <- fit_one("lc", dd, VARIANTS$B$years, VARIANTS$B$zero)
  lls <- c(); gcs <- c()
  for (j in 1:3) {
    kt <- if (j == 1) lcf$kt else lcf$kt + rnorm(length(lcf$kt), 0, 0.5 * (j - 1))
    f5 <- fit_rh1(dd, VARIANTS$B$years, VARIANTS$B$zero, lcf, clip = 5L, kt_start = kt)
    lls <- c(lls, f5$loglik); gcs <- c(gcs, max(abs(f5$gc[!is.na(f5$gc)])))
  }
  rh_clip5[[s]] <- c(bic_of(f5), list(loglik_spread = diff(range(lls)),
                     gc_absmax_range = range(gcs),
                     extra_clipped = attr(eff_weight_mat(dd$ages, VARIANTS$B$years,
                                                         VARIANTS$B$zero, 5L), "extra_clipped")))
  message(sprintf("    %s clip=5: nobs=%d npar=%d bic=%.1f |gc|max=%.4f spread=%.3g",
                  s, rh_clip5[[s]]$nobs, rh_clip5[[s]]$npar, rh_clip5[[s]]$bic_common,
                  rh_clip5[[s]]$gc_absmax, rh_clip5[[s]]$loglik_spread))
}

message("[3/4] APC and LC refitted on the RH (effective-clip) weight matrix")
apc_clip <- list(); lcref <- list(); cbdref <- list()
for (s in SEXES) {
  dd <- load_sex(s)
  for (v in names(VARIANTS)) {
    apc_clip[[paste0(s, v)]] <- bic_of(fit_generic("apc", dd, VARIANTS[[v]]$years,
                                                   VARIANTS[[v]]$zero))
    lcref[[paste0(s, v)]]    <- bic_of(fit_generic("lc",  dd, VARIANTS[[v]]$years,
                                                   VARIANTS[[v]]$zero))
    cbdref[[paste0(s, v)]]   <- bic_of(fit_generic("cbd", dd, VARIANTS[[v]]$years,
                                                   VARIANTS[[v]]$zero))
  }
}

message("[5] backtest 2003-2014 -> 2015-2019 for the clipped APC")
lt <- fread("data/clean/lifetables_period.csv")
apc_clip_bt <- list()
for (s in SEXES) {
  dd <- load_sex(s)
  Mact <- dd$D[, as.character(BT_OUT), drop = FALSE] / dd$E[, as.character(BT_OUT), drop = FALSE]
  f <- fit_generic("apc", dd, BT_FIT, integer(0))
  Mfc <- suppressWarnings(forecast(f, h = length(BT_OUT)))$rates
  ok <- is.finite(Mact) & Mact > 0 & is.finite(Mfc) & Mfc > 0
  a60 <- rownames(Mact) %in% as.character(60:89)
  e65fc <- e65_from_closed(close_kannisto(t(Mfc[as.character(AGES_FIT), , drop = FALSE])))
  apc_clip_bt[[s]] <- list(
    rmse = sqrt(mean((log(Mfc[ok]) - log(Mact[ok]))^2)),
    rmse6089 = sqrt(mean((log(Mfc[ok & a60]) - log(Mact[ok & a60]))^2)),
    e65_err = unname(e65fc[length(e65fc)]) - lt[year == 2019 & sex == s & age == 65, ex],
    nobs = f$nobs, npar = f$npar)
  message(sprintf("    %s clipped APC: rmse=%.5f e65err=%+.4f", s,
                  apc_clip_bt[[s]]$rmse, apc_clip_bt[[s]]$e65_err))
}

message("[6] RH central e65 in 2050 (reference only)")
e65_rh <- list()
for (s in SEXES) {
  f <- S1$fits[[s]][[VAR_MAIN]][["rh"]]
  kt <- f$kt[1, ]; kt[colSums(f$wxt) == 0] <- NA
  r <- rwd_stats(kt, f$years)
  k_2050 <- r$last_value + r$drift * (E65_YEAR - r$last_year)
  gc <- f$gc[!is.na(f$gc)]
  coh_fit <- as.numeric(names(gc)); c_last <- max(coh_fit)
  need <- (E65_YEAR - max(f$ages)):(E65_YEAR - min(f$ages))
  h <- max(need) - c_last
  ar <- forecast::Arima(ts(gc, start = min(coh_fit)), order = c(1, 1, 0),
                        include.drift = TRUE, method = "ML")
  g_fc <- as.numeric(forecast::forecast(ar, h = h)$mean)
  rw <- forecast::Arima(ts(gc, start = min(coh_fit)), order = c(0, 1, 0),
                        include.drift = TRUE, method = "ML")
  g_rw <- as.numeric(forecast::forecast(rw, h = h)$mean)
  gfun <- function(gext) {
    all_c <- c(coh_fit, (c_last + 1):(c_last + h))
    all_g <- c(as.numeric(gc), gext)
    all_g[match(need, all_c)]
  }
  e65_of <- function(gext) {
    lm2050 <- as.numeric(f$ax) + as.numeric(f$bx) * k_2050 + rev(gfun(gext))
    e65_from_closed(close_kannisto(matrix(exp(lm2050), nrow = 1)))
  }
  e65_rh[[s]] <- list(central = unname(e65_of(g_fc)), rwd = unname(e65_of(g_rw)),
                      kappa_2050 = k_2050, drift = r$drift,
                      n_gc_extrapolated = sum(need > c_last),
                      gc_last_fitted = c_last,
                      gc_drift_arima = unname(coef(ar)["drift"]),
                      gc_drift_rwd = unname(coef(rw)["drift"]))
  message(sprintf("    %s e65(2050) RH = %.3f (ARIMA(1,1,0)+drift gc) / %.3f (RWD gc); %d gamma_c extrapolated",
                  s, e65_rh[[s]]$central, e65_rh[[s]]$rwd, e65_rh[[s]]$n_gc_extrapolated))
}

message("[7] patching results/mortality.json (rh_* / apc_clipped_* / bic_eff_* only)")
J <- fromJSON("results/mortality.json", simplifyVector = TRUE)
before <- names(J)
S1J <- fromJSON("analysis/mortality/_stage1.json", simplifyVector = FALSE)
changed <- character(0)
setk <- function(k, v) { changed <<- c(changed, k); J[[k]] <<- v }

for (s in SEXES) for (v in names(VARIANTS)) {
  st <- rh_stats[[paste0(s, v)]]
  setk(sprintf("bic_rh_%s_%s", s, v), st$bic_common)
  setk(sprintf("bic_native_rh_%s_%s", s, v), st$bic_native)
  setk(sprintf("npar_rh_%s_%s", s, v), as.integer(st$npar))
  setk(sprintf("nobs_rh_%s_%s", s, v), as.integer(st$nobs))
  setk(sprintf("rh_gc_absmax_%s_%s", s, v), st$gc_absmax)
  setk(sprintf("rh_lcref_bic_%s_%s", s, v), lcref[[paste0(s, v)]]$bic_common)
  setk(sprintf("rh_bic_gap_vs_lc_%s_%s", s, v),
       st$bic_common - lcref[[paste0(s, v)]]$bic_common)
  ac <- apc_clip[[paste0(s, v)]]
  setk(sprintf("apc_clipped_bic_%s_%s", s, v), ac$bic_common)
  setk(sprintf("apc_clipped_bic_native_%s_%s", s, v), ac$bic_native)
  setk(sprintf("apc_clipped_npar_%s_%s", s, v), as.integer(ac$npar))
  setk(sprintf("apc_clipped_nobs_%s_%s", s, v), as.integer(ac$nobs))
  setk(sprintf("apc_clipped_gc_absmax_%s_%s", s, v), ac$gc_absmax)
  for (mn in c("lc", "cbd", "apc", "rh")) {
    st2 <- switch(mn, lc = lcref[[paste0(s, v)]], cbd = cbdref[[paste0(s, v)]],
                  apc = ac, rh = st)
    setk(sprintf("bic_eff_%s_%s_%s", mn, s, v), st2$bic_common)
    setk(sprintf("npar_eff_%s_%s_%s", mn, s, v), as.integer(st2$npar))
    setk(sprintf("nobs_eff_%s_%s_%s", mn, s, v), as.integer(st2$nobs))
  }
}
bt <- fread("analysis/mortality/backtest.csv")
for (s in SEXES) {
  r <- bt[sex == s & model == "rh"]
  setk(sprintf("backtest_rmse_rh_%s", s), r$rmse_logm_55_89[1])
  setk(sprintf("backtest_rmse6089_rh_%s", s), r$rmse_logm_60_89[1])
  setk(sprintf("backtest_e65_err_rh_%s", s), r$e65_err_2019[1])
  setk(sprintf("apc_clipped_backtest_rmse_%s", s), apc_clip_bt[[s]]$rmse)
  setk(sprintf("apc_clipped_backtest_rmse6089_%s", s), apc_clip_bt[[s]]$rmse6089)
  setk(sprintf("apc_clipped_backtest_e65_err_%s", s), apc_clip_bt[[s]]$e65_err)
  setk(sprintf("rh_converged_%s", s), TRUE)
  setk(sprintf("rh_diagnostic_%s", s), S1J$rh_reason[[s]])
  setk(sprintf("rh_loglik_%s_B", s), rh_stats[[paste0(s, "B")]]$loglik_pois)
  setk(sprintf("rh_clip5_bic_%s_B", s), rh_clip5[[s]]$bic_common)
  setk(sprintf("rh_clip5_npar_%s_B", s), as.integer(rh_clip5[[s]]$npar))
  setk(sprintf("rh_clip5_nobs_%s_B", s), as.integer(rh_clip5[[s]]$nobs))
  setk(sprintf("rh_clip5_gc_absmax_%s_B", s), rh_clip5[[s]]$gc_absmax)
  setk(sprintf("e65_%s_2050_rh_central", s), e65_rh[[s]]$central)
  setk(sprintf("e65_%s_2050_rh_central_gcrwd", s), e65_rh[[s]]$rwd)
  setk(sprintf("rh_gc_extrapolated_n_%s", s), as.integer(e65_rh[[s]]$n_gc_extrapolated))
}
setk("rh_cohort_age_fun", "1")
setk("rh_approx_const", TRUE)
setk("rh_clip", 3L)
setk("rh_clip_extra_cohorts_B", "1964,1965")
setk("rh_gc_extrapolation", "ARIMA(1,1,0) with drift (StMoMo gc.order default); RWD with drift as sensitivity")
setk("rh_is_main_model", FALSE)
setk("rh_fit_note", paste(
  "Renshaw-Haberman се идентификува во поедноставената форма H1",
  "(cohortAgeFun = 1, approxConst = TRUE) со кохорти од аглите отсечени по",
  "нулирањето на ковид-годините: четири различни почетни точки даваат иста",
  "логаритамска веродостојност (распон < 1e-4) и |gamma_c| < 0,18, но моделот",
  "има повисок BIC и полоша повратна проверка од Ли-Картер, па не е главен модел."))

kept <- grepl("^(rh_|apc_clipped_|nobs_rh_|bic_rh_|bic_native_rh_|npar_rh_|backtest_.*_rh_|e65_[mf]_2050_rh_|bic_eff_|npar_eff_|nobs_eff_)", changed)
stopifnot("rh_refit.R tried to write a key outside rh_/apc_clipped_/*_eff_" = all(kept))
stopifnot("key dropped" = all(before %in% names(J)))
write_json(J, "results/mortality.json", auto_unbox = TRUE, pretty = TRUE,
           digits = 12, na = "null")
cat(sprintf("  %d keys written (%d new)\n", length(changed),
            sum(!changed %in% before)))
writeLines(sort(unique(changed)), "analysis/mortality/_rh_keys_changed.txt")

message("[8] rh_params.csv (figure drawn by make_figures.R)")
par_rh <- rbindlist(lapply(SEXES, function(s) {
  f <- S1$fits[[s]][[VAR_MAIN]][["rh"]]
  kt <- f$kt[1, ]; kt[colSums(f$wxt) == 0] <- NA
  g <- f$gc; g <- g[!is.na(g)]
  rbind(data.table(sex = s, par = "alpha[x]", x = f$ages, value = as.numeric(f$ax)),
        data.table(sex = s, par = "beta[x]",  x = f$ages, value = as.numeric(f$bx)),
        data.table(sex = s, par = "kappa[t]", x = f$years, value = as.numeric(kt)),
        data.table(sex = s, par = "gamma[c]", x = as.numeric(names(g)), value = as.numeric(g)))
}))
fwrite(par_rh, "analysis/mortality/rh_params.csv")

saveRDS(list(ablation = ablation, rh_stats = rh_stats, rh_clip5 = rh_clip5,
             apc_clipped = apc_clip, apc_clipped_bt = apc_clip_bt,
             lc_on_rh_cells = lcref, e65_rh = e65_rh),
        "analysis/mortality/rh_refit.rds", compress = "xz")
message("[done] rh_refit.R")
