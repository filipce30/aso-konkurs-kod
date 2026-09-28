#!/usr/bin/env Rscript
# Stochastic projection to 2080: bootstrap, drift and process uncertainty, Kannisto closure, exports.
suppressPackageStartupMessages({library(ggplot2); library(svglite); library(arrow)})
source("analysis/mortality/lib_mortality.R")
t_start <- Sys.time()

MAIN_MODEL   <- "lc"
ROBUST_MODEL <- "cbd"
VAR_MAIN     <- "B"
NBOOT        <- as.integer(Sys.getenv("MORT_NBOOT", "500"))
NSIM_PER     <- as.integer(Sys.getenv("MORT_NSIM_PER", "10"))
NSIM         <- NBOOT * NSIM_PER
YEARS_FUT    <- 2024:2080
H            <- length(YEARS_FUT)
SEXES        <- c("m", "f")
AGES_FULL_N  <- length(AGES_FULL)
CBD_QCAP <- 0; CBD_NCELL <- 0

# Reduced runs write *_reduced files and never overwrite the production outputs.
REDUCED <- (as.integer(Sys.getenv("MORT_NBOOT", "500")) *
          as.integer(Sys.getenv("MORT_NSIM_PER", "10"))) < 1000L
out_path <- function(path) if (REDUCED) sub("\\.parquet$", "_reduced.parquet", path) else path

write_parquet_atomic <- function(x, path, ...) {
  path <- out_path(path)
  tmp <- paste0(path, ".tmp-", Sys.getpid())
  on.exit(if (file.exists(tmp)) unlink(tmp), add = TRUE)
  write_parquet(x, tmp, ...)
  n <- nrow(read_parquet(tmp, col_select = 1))
  stopifnot(n == nrow(x))
  ok <- file.rename(tmp, path); stopifnot(ok)
  n
}

S1 <- readRDS("analysis/mortality/fits.rds")
fits <- S1$fits; VARIANTS <- S1$variants
lt <- fread("data/clean/lifetables_period.csv")
act_e65 <- function(s, y) lt[year == y & sex == s & age == 65, ex]
kt_of <- function(f) { k <- f$kt; k[, colSums(f$wxt) == 0] <- NA; k }

lc_surface <- function(f) {
  bxs <- ma3(f$bx)
  rf <- refit_kt_poisson(f$ax, bxs, f$Dxt, f$Ext, f$wxt)
  kk <- rf$kt; kk[colSums(f$wxt) == 0] <- NA
  list(ax = rf$ax, bx = rf$bx, kt = kk, rwd = rwd_stats(kk, f$years))
}

PT <- list()
for (s in SEXES) {
  f <- fits[[s]][[VAR_MAIN]][[MAIN_MODEL]]
  k <- kt_of(f)[1, ]
  dd <- load_sex(s, ages = KAN_LO:KAN_HI)
  Mr <- dd$D / dd$E
  Mr <- Mr[, setdiff(colnames(Mr), as.character(MISSING_YR)), drop = FALSE]
  sl <- apply(Mr, 2, function(m) kan_slope(matrix(m, nrow = 1), KAN_LO:KAN_HI))
  xk <- KAN_LO:KAN_HI; wj <- (xk - mean(xk)) / sum((xk - mean(xk))^2)
  cols <- setdiff(colnames(dd$D), as.character(MISSING_YR))
  se_t <- sqrt(colSums(wj^2 / (dd$D[, cols] * (1 - Mr[, cols])^2)))
  se_bar <- mean(se_t)
  su <- lc_surface(f)
  PT[[s]] <- list(fit = f, ax_raw = as.numeric(f$ax), bx_raw = as.numeric(f$bx),
                  kt_raw = k, rwd_raw = rwd_stats(k, f$years),
                  ax = su$ax, bx = su$bx, kt = su$kt, rwd = su$rwd,
                  slope_lo = min(sl) - 2 * se_bar, slope_hi = max(sl) + 2 * se_bar,
                  slope_obs_lo = min(sl), slope_obs_hi = max(sl), slope_se = se_bar)
  message(sprintf("[pt] %s  mu=%.6f (raw beta %.6f)  sigma=%.4f (%.4f)  SE=%.4f  t=%.3f  p(%d df)=%.4f | Kannisto obs %.4f-%.4f",
                  s, PT[[s]]$rwd$drift, PT[[s]]$rwd_raw$drift,
                  PT[[s]]$rwd$sigma, PT[[s]]$rwd_raw$sigma, PT[[s]]$rwd$se,
                  PT[[s]]$rwd$tstat, PT[[s]]$rwd$df, PT[[s]]$rwd$pvalue,
                  PT[[s]]$slope_lo, PT[[s]]$slope_hi))
  message(sprintf("      observed slope range %.4f-%.4f, mean SE %.5f -> FLOOR ONLY at min - 2 SE",
                  PT[[s]]$slope_obs_lo, PT[[s]]$slope_obs_hi, PT[[s]]$slope_se))
}
RHO_MF <- unname(cor(PT$m$rwd$resid_std, PT$f$rwd$resid_std))
message(sprintf("[pt] cross-sex kappa innovation correlation rho = %.4f (n = %d)",
                RHO_MF, length(PT$m$rwd$resid_std)))
WINSOR <- c(m = TRUE, f = TRUE)

lc_rates <- function(ax, bx, K) {
  n <- nrow(K); h <- ncol(K); nA <- length(ax)
  exp(array(rep(ax, each = n * h), c(n, h, nA)) +
      array(rep(bx, each = n * h), c(n, h, nA)) *
      array(rep(K, times = nA), c(n, h, nA)))
}
cbd_rates <- function(ages, K1, K2) {
  n <- nrow(K1); h <- ncol(K1); nA <- length(ages); xb <- mean(ages)
  eta <- array(rep(K1, times = nA), c(n, h, nA)) +
         array(rep(K2, times = nA), c(n, h, nA)) * rep(ages - xb, each = n * h)
  q <- 1 / (1 + exp(-eta))
  CBD_QCAP <<- CBD_QCAP + sum(q > 0.999)
  CBD_NCELL <<- CBD_NCELL + length(q)
  q_to_m(pmin(q, 0.999))
}
flat <- function(arr) matrix(arr, nrow = dim(arr)[1] * dim(arr)[2], ncol = dim(arr)[3])

close_perpath <- function(Mfit, lo = NULL, hi = NULL, ages = AGES_FIT) {
  idx <- match(KAN_LO:KAN_HI, ages)
  breach <- mean(rowSums(Mfit[, idx, drop = FALSE] >= 1) > 0)
  sl <- kan_slope(Mfit, ages)
  raw_min <- min(sl); raw_p01 <- unname(quantile(sl, 0.01)); raw_neg <- mean(sl <= 0)
  n_w <- 0L; n_lo <- 0L; n_hi <- 0L
  if (!is.null(hi)) n_hi <- sum(sl > hi)
  # Slope bound is a floor only: a non-positive Kannisto slope is impossible; steep slopes are left alone.
  if (!is.null(lo)) { n_lo <- sum(sl < lo); n_w <- n_lo; sl <- pmax(sl, lo) }
  list(M = close_kannisto(Mfit, ages, slope = sl),
       slope_min = raw_min, slope_p01 = raw_p01, slope_negshare = raw_neg,
       winsor_share = n_w / length(sl), winsor_share_lo = n_lo / length(sl),
       above_hi_share = n_hi / length(sl), breach_share = breach)
}
qx_table <- function(Mclosed) {
  Q0 <- m_to_q(Mclosed)
  before <- count_reversals(Q0, AGES_FULL, 65L)
  fx <- monotone_fix(Q0, AGES_FULL, 65L)
  Q <- fx$Q; Q[, AGES_FULL_N] <- 1
  j <- which(AGES_FULL >= 65 & AGES_FULL < AGE_OPEN)
  list(Q = Q, before = before, after = count_reversals(Q, AGES_FULL, 65L),
       rows_fixed = fx$n_rows_fixed,
       max_logdelta = max(abs(log(Q[, j, drop = FALSE] / Q0[, j, drop = FALSE]))))
}
e65_export <- function(Mclosed) {
  Q <- qx_table(Mclosed)$Q
  ex_from_m(q_to_m(Q[, match(65:AGE_OPEN, AGES_FULL), drop = FALSE]), 65:AGE_OPEN)
}

sims_long <- function(Q) {
  dt <- data.table(
    sim  = rep(rep(seq_len(NSIM), times = H), each = AGES_FULL_N),
    year = rep(rep(YEARS_FUT, each = NSIM), each = AGES_FULL_N),
    age  = rep(AGES_FULL, times = NSIM * H),
    qx   = as.vector(t(Q)))
  dt[, `:=`(sim = as.integer(sim), year = as.integer(year), age = as.integer(age))]
  dt
}

set.seed(2026)
BOOT <- list(); BR <- list()
for (s in SEXES) {
  set.seed(2026L + which(SEXES == s))
  bs <- suppressWarnings(bootstrap(PT[[s]]$fit, nBoot = NBOOT, type = "semiparametric"))
  f <- PT[[s]]$fit
  BOOT[[s]] <- lapply(bs$bootParameters, function(p) {
    bxs <- ma3(p$bx)
    rf <- refit_kt_poisson(p$ax, bxs, f$Dxt, f$Ext, f$wxt)
    kk <- rf$kt; kk[colSums(f$wxt) == 0] <- NA
    list(ax = rf$ax, bx = rf$bx, kt = kk)
  })
  BR[[s]] <- lapply(BOOT[[s]], function(p) {
    r <- rwd_stats(p$kt, PT[[s]]$fit$years)
    list(last_value = r$last_value, last_year = r$last_year)
  })
}
message(sprintf("[boot] %d paired replicates per sex", NBOOT))

R2 <- matrix(c(1, RHO_MF, RHO_MF, 1), 2); CH <- chol(R2)
KAPPA <- list(m = matrix(NA_real_, NSIM, H), f = matrix(NA_real_, NSIM, H))
MUT   <- list(m = numeric(NSIM), f = numeric(NSIM))
BIDX  <- rep(seq_len(NBOOT), each = NSIM_PER)
set.seed(2026)
for (b in seq_len(NBOOT)) {
  idx <- ((b - 1) * NSIM_PER + 1):(b * NSIM_PER)
  rm_ <- BR$m[[b]]; rf_ <- BR$f[[b]]
  pm <- PT$m$rwd; pf <- PT$f$rwd
  zmu <- matrix(rnorm(2 * NSIM_PER), ncol = 2) %*% CH
  mu_m <- pm$drift + zmu[, 1] * pm$se
  mu_f <- pf$drift + zmu[, 2] * pf$se
  MUT$m[idx] <- mu_m; MUT$f[idx] <- mu_f
  ze <- matrix(rnorm(2 * NSIM_PER * H), ncol = 2) %*% CH
  em <- matrix(ze[, 1], NSIM_PER, H) * pm$sigma
  ef <- matrix(ze[, 2], NSIM_PER, H) * pf$sigma
  hh <- matrix(rep(YEARS_FUT - rm_$last_year, each = NSIM_PER), NSIM_PER, H)
  KAPPA$m[idx, ] <- rm_$last_value + mu_m * hh + t(apply(em, 1, cumsum))
  hh <- matrix(rep(YEARS_FUT - rf_$last_year, each = NSIM_PER), NSIM_PER, H)
  KAPPA$f[idx, ] <- rf_$last_value + mu_f * hh + t(apply(ef, 1, cumsum))
}

central_lc <- function(f, years_fut, bx = NULL, lo = NULL, hi = NULL, raw = FALSE) {
  if (raw) { su <- list(ax = as.numeric(f$ax), bx = as.numeric(f$bx),
                        rwd = rwd_stats(kt_of(f)[1, ], f$years)) }
  else     { su <- lc_surface(f) }
  r <- su$rwd
  K <- matrix(r$last_value + r$drift * (years_fut - r$last_year), 1)
  M <- lc_rates(su$ax, su$bx, K)
  cl <- close_perpath(flat(M), lo, hi)
  list(M = cl$M, e65 = e65_export(cl$M), rwd = r, jumpoff_year = r$last_year)
}
central_cbd <- function(f, years_fut, lo = NULL, hi = NULL) {
  k <- kt_of(f)
  r1 <- rwd_stats(k[1, ], f$years); r2 <- rwd_stats(k[2, ], f$years)
  K1 <- matrix(r1$last_value + r1$drift * (years_fut - r1$last_year), 1)
  K2 <- matrix(r2$last_value + r2$drift * (years_fut - r2$last_year), 1)
  M <- cbd_rates(f$ages, K1, K2)
  cl <- close_perpath(flat(M), lo, hi)
  list(M = cl$M, e65 = e65_export(cl$M), rwd = list(r1, r2),
       jumpoff_year = r1$last_year)
}
central <- list(); e65_variant_rows <- list()
for (s in SEXES) {
  lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
  hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
  for (v in names(VARIANTS)) {
    cl <- central_lc(fits[[s]][[v]][["lc"]], YEARS_FUT, lo = lo, hi = hi)
    cc <- central_cbd(fits[[s]][[v]][["cbd"]], YEARS_FUT, lo, hi)
    e65_variant_rows[[length(e65_variant_rows) + 1]] <-
      data.table(sex = s, variant = v, model = "lc", year = YEARS_FUT,
                 e65 = cl$e65, jumpoff = cl$jumpoff_year)
    e65_variant_rows[[length(e65_variant_rows) + 1]] <-
      data.table(sex = s, variant = v, model = "cbd", year = YEARS_FUT,
                 e65 = cc$e65, jumpoff = cc$jumpoff_year)
    if (v == VAR_MAIN) { central[[s]] <- cl; central[[paste0(s, "_rob")]] <- cc }
  }
  craw <- central_lc(fits[[s]][[VAR_MAIN]][["lc"]], YEARS_FUT, lo = lo, hi = hi, raw = TRUE)
  central[[paste0(s, "_rawbeta")]] <- craw
}
e65_var <- rbindlist(e65_variant_rows)
if (!REDUCED) fwrite(e65_var, "analysis/mortality/e65_central_by_variant.csv")

SIM <- list(); DIAG <- list()
for (s in SEXES) {
  lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
  hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
  AX <- do.call(rbind, lapply(BOOT[[s]], `[[`, "ax"))[BIDX, , drop = FALSE]
  BX <- do.call(rbind, lapply(BOOT[[s]], `[[`, "bx"))[BIDX, , drop = FALSE]
  nA <- ncol(AX)
  Mf <- exp(array(AX[, rep(seq_len(nA), each = H)], c(NSIM, H, nA)) +
            array(BX[, rep(seq_len(nA), each = H)], c(NSIM, H, nA)) *
            array(rep(KAPPA[[s]], times = nA), c(NSIM, H, nA)))
  Mf_keep <- flat(Mf); rm(Mf); gc(FALSE)
  cl <- close_perpath(Mf_keep, lo, hi)
  qt <- qx_table(cl$M)
  e65 <- matrix(ex_from_m(q_to_m(qt$Q[, match(65:AGE_OPEN, AGES_FULL), drop = FALSE]),
                          65:AGE_OPEN), nrow = NSIM, ncol = H)
  clnw <- close_perpath(Mf_keep, NULL, NULL)
  e65_nw <- matrix(e65_export(clnw$M), nrow = NSIM, ncol = H)
  Qnw <- qx_table(clnw$M)$Q
  write_parquet_atomic(sims_long(Qnw),
    sprintf("analysis/mortality/qx_sims_%s_nowinsor.parquet", s), compression = "zstd")
  rm(clnw, Qnw); gc(FALSE)
  SIM[[s]] <- list(e65 = e65, Q = qt$Q, e65_nowinsor = e65_nw)
  DIAG[[s]] <- list(breach = cl$breach_share, winsor_lo = cl$winsor_share_lo,
                    above_hi = cl$above_hi_share,
                    slope_min = cl$slope_min, slope_p01 = cl$slope_p01,
                    slope_negshare = cl$slope_negshare, winsor = cl$winsor_share,
                    rev_before = qt$before, rev_after = qt$after,
                    rows_fixed = qt$rows_fixed)
  message(sprintf("[sim] %s: slope min %.4f p1 %.4f, floored %.4f (above upper ref %.4f, not clamped) | qx reversals %d -> %d (%d of %d path-years repaired)",
                  s, cl$slope_min, cl$slope_p01, cl$winsor_share,
                  cl$above_hi_share,
                  qt$before, qt$after, qt$rows_fixed, NSIM * H))
  rm(cl, qt, Mf_keep); gc(FALSE)
}
SIMS_CORR <- unname(cor(SIM$m$e65[, H], SIM$f$e65[, H]))
message(sprintf("[sim] corr(e65 2080) across sexes = %.4f", SIMS_CORR))

YRS_VD <- c(2050, 2080); jvd <- match(YRS_VD, YEARS_FUT)
vd_e65 <- function(s, AX, BX, K) {
  lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
  hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
  n <- nrow(K); h <- ncol(K); nA <- ncol(AX)
  M <- exp(array(AX[, rep(seq_len(nA), each = h)], c(n, h, nA)) +
           array(BX[, rep(seq_len(nA), each = h)], c(n, h, nA)) *
           array(rep(K, times = nA), c(n, h, nA)))
  cl <- close_perpath(flat(M), lo, hi)
  matrix(e65_export(cl$M), nrow = n, ncol = h)
}
VD <- list()
for (s in SEXES) {
  nA <- length(PT[[s]]$ax)
  AXb <- do.call(rbind, lapply(BOOT[[s]], `[[`, "ax"))[BIDX, , drop = FALSE]
  BXb <- do.call(rbind, lapply(BOOT[[s]], `[[`, "bx"))[BIDX, , drop = FALSE]
  AXp <- matrix(PT[[s]]$ax, NSIM, nA, byrow = TRUE)
  BXp <- matrix(PT[[s]]$bx, NSIM, nA, byrow = TRUE)
  r <- PT[[s]]$rwd; hh <- matrix(rep(YRS_VD - r$last_year, each = NSIM), NSIM, 2)
  eps <- KAPPA[[s]][, jvd, drop = FALSE] -
         (sapply(BR[[s]], `[[`, "last_value")[BIDX] +
          MUT[[s]] * matrix(rep(YRS_VD - r$last_year, each = NSIM), NSIM, 2))
  K_proc  <- r$last_value + r$drift * hh + eps
  K_drift <- r$last_value + MUT[[s]] * hh
  K_boot  <- sapply(BR[[s]], `[[`, "last_value")[BIDX] + r$drift * hh
  v_proc  <- apply(vd_e65(s, AXp, BXp, K_proc),  2, var)
  v_drift <- apply(vd_e65(s, AXp, BXp, K_drift), 2, var)
  v_boot  <- apply(vd_e65(s, AXb, BXb, K_boot),  2, var)
  v_real  <- apply(SIM[[s]]$e65[, jvd, drop = FALSE], 2, var)
  tot <- v_proc + v_drift + v_boot
  VD[[s]] <- list(v_proc = v_proc, v_drift = v_drift, v_boot = v_boot,
                  realised = v_real,
                  share_proc = v_proc / tot, share_drift = v_drift / tot,
                  share_boot = v_boot / tot, sum_over_realised = tot / v_real)
  message(sprintf("[vd] %s ablation Var(e65) y^2 | 2050 proc %.3f drift %.3f boot %.3f (sum %.3f vs realised %.3f) | 2080 proc %.3f drift %.3f boot %.3f (sum %.3f vs realised %.3f)",
                  s, v_proc[1], v_drift[1], v_boot[1], tot[1], v_real[1],
                  v_proc[2], v_drift[2], v_boot[2], tot[2], v_real[2]))
}

RWDX <- list()
for (s in SEXES) {
  f <- PT[[s]]$fit
  kk <- as.numeric(PT[[s]]$kt); yrs <- f$years
  g  <- kk[yrs %in% 2003:2019]
  d1 <- diff(g); n1 <- length(d1)
  v1 <- sum((d1 - mean(d1))^2) / n1
  vr <- sapply(c(2, 4, 8), function(q) {
    dq <- g[(q + 1):length(g)] - g[1:(length(g) - q)]
    (sum((dq - q * mean(d1))^2) / length(dq)) / (q * v1)
  })
  a1 <- unname(acf(d1, lag.max = 1, plot = FALSE)$acf[2])
  lb <- Box.test(d1, lag = 1, type = "Ljung-Box")$p.value
  ok <- !is.na(kk); tt <- yrs - mean(yrs[ok])
  ts_fit <- forecast::Arima(ts(kk, start = yrs[1]), order = c(1, 0, 0),
                            xreg = tt, method = "ML")
  cn <- tail(names(coef(ts_fit)), 1)
  phi <- unname(coef(ts_fit)["ar1"]); bt <- unname(coef(ts_fit)[cn])
  bse <- unname(sqrt(ts_fit$var.coef[cn, cn]))
  lo1 <- rwd_stats(ifelse(yrs == 2023, NA, kk), yrs)
  lo2 <- rwd_stats(ifelse(yrs == 2003, NA, kk), yrs)
  RWDX[[s]] <- list(vr2 = vr[1], vr4 = vr[2], vr8 = vr[3], acf1 = a1, lb_p = lb,
                    ar1_phi = phi, trend_b = bt, trend_se = bse,
                    trend_t = bt / bse, ts_fit = ts_fit,
                    drop2023 = lo1, drop2003 = lo2)
  message(sprintf("[rwd] %s VR(2)=%.3f VR(4)=%.3f VR(8)=%.3f acf1=%.3f LB p=%.3f | trend+AR(1): phi=%.3f b=%.4f t=%.1f | drop2023 p=%.3f drop2003 p=%.3f",
                  s, vr[1], vr[2], vr[3], a1, lb, phi, bt, bt / bse,
                  lo1$pvalue, lo2$pvalue))
}
set.seed(7026)
TSALT <- list(); TSK <- list()
zz <- matrix(rnorm(2 * NSIM * H), ncol = 2) %*% CH
for (si in seq_along(SEXES)) {
  s <- SEXES[si]
  f <- PT[[s]]$fit; yrs <- f$years; kk <- as.numeric(PT[[s]]$kt)
  fitx <- RWDX[[s]]$ts_fit
  cf <- coef(fitx); cn <- tail(names(cf), 1)
  phi <- unname(cf["ar1"]); a <- unname(cf["intercept"]); b <- unname(cf[cn])
  sde <- sqrt(fitx$sigma2); tbar <- mean(yrs[!is.na(kk)])
  T_last <- max(yrs[!is.na(kk)])
  u_T <- kk[yrs == T_last] - a - b * (T_last - tbar)
  hh <- YEARS_FUT - T_last
  det <- a + b * (YEARS_FUT - tbar)
  u_cen <- phi^hh * u_T
  K_cen <- matrix(det + u_cen, 1)
  E_sh <- matrix(zz[, si], NSIM, H) * sde
  U <- matrix(NA_real_, NSIM, H); prev <- rep(u_T, NSIM)
  for (k in seq_len(H)) { prev <- phi * prev + E_sh[, k]; U[, k] <- prev }
  K_sim <- sweep(U, 2, det, "+")
  TSK[[s]] <- list(cen = K_cen, sim = K_sim)
  TSALT[[s]] <- list(sd_kappa = apply(K_sim, 2, sd), phi = phi, b = b)
  message(sprintf("[ts ] %s trend-stationary: phi=%.3f b=%.4f sd(kappa 2080)=%.2f",
                  s, phi, b, TSALT[[s]]$sd_kappa[H]))
}
set.seed(3026)
RB <- list()
for (s in SEXES) {
  f <- fits[[s]][[VAR_MAIN]][[ROBUST_MODEL]]
  bs <- suppressWarnings(bootstrap(f, nBoot = NBOOT, type = "semiparametric"))
  RB[[s]] <- list(fit = f, bp = bs$bootParameters)
}
RK <- list()
set.seed(3026)
for (s in SEXES) RK[[s]] <- list(K1 = matrix(NA_real_, NSIM, H),
                                 K2 = matrix(NA_real_, NSIM, H))
RPT <- list()
RHO12 <- sapply(SEXES, function(s) {
  k <- kt_of(RB[[s]]$fit)
  r1 <- rwd_stats(k[1, ], RB[[s]]$fit$years); r2 <- rwd_stats(k[2, ], RB[[s]]$fit$years)
  RPT[[s]] <<- list(r1 = r1, r2 = r2)
  cor(r1$resid_std, r2$resid_std)
})
set.seed(3026)
for (b in seq_len(NBOOT)) {
  idx <- ((b - 1) * NSIM_PER + 1):(b * NSIM_PER)
  z1 <- matrix(rnorm(2 * NSIM_PER), ncol = 2) %*% CH
  w1 <- matrix(rnorm(2 * NSIM_PER * H), ncol = 2) %*% CH
  for (si in seq_along(SEXES)) {
    s <- SEXES[si]; f <- RB[[s]]$fit
    k <- RB[[s]]$bp[[b]]$kt
    b1 <- rwd_stats(k[1, ], f$years); b2 <- rwd_stats(k[2, ], f$years)
    r1 <- RPT[[s]]$r1; r2 <- RPT[[s]]$r2
    rho <- RHO12[[s]]
    mu1 <- r1$drift + z1[, si] * r1$se
    mu2 <- r2$drift + (rho * z1[, si] + sqrt(1 - rho^2) * rnorm(NSIM_PER)) * r2$se
    e1 <- matrix(w1[, si], NSIM_PER, H) * r1$sigma
    e2 <- (rho * matrix(w1[, si], NSIM_PER, H) +
           sqrt(1 - rho^2) * matrix(rnorm(NSIM_PER * H), NSIM_PER, H)) * r2$sigma
    hh <- matrix(rep(YEARS_FUT - r1$last_year, each = NSIM_PER), NSIM_PER, H)
    RK[[s]]$K1[idx, ] <- b1$last_value + mu1 * hh + t(apply(e1, 1, cumsum))
    RK[[s]]$K2[idx, ] <- b2$last_value + mu2 * hh + t(apply(e2, 1, cumsum))
  }
}
RSIM <- list(); RBREACH <- list()
for (s in SEXES) {
  lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
  hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
  M <- cbd_rates(RB[[s]]$fit$ages, RK[[s]]$K1, RK[[s]]$K2)
  cl <- close_perpath(flat(M), lo, hi); rm(M); gc(FALSE)
  RBREACH[[s]] <- cl$breach_share
  RSIM[[s]] <- matrix(e65_export(cl$M), nrow = NSIM, ncol = H)
  rm(cl); gc(FALSE)
}
message("[sim] robustness (CBD) done")

REV <- list(); MONO <- list(); ROWS <- list()
write_central <- function(Mclosed, m23, path) {
  Q <- qx_table(rbind(m23, Mclosed))
  dt <- data.table(year = rep(c(2023L, YEARS_FUT), each = AGES_FULL_N),
                   age = rep(AGES_FULL, H + 1),
                   qx = as.vector(t(Q$Q)), mx = as.vector(t(rbind(m23, Mclosed))))
  write_parquet_atomic(dt, path, compression = "zstd")
  c(before = Q$before, after = Q$after)
}
for (s in SEXES) {
  lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
  hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
  f <- PT[[s]]$fit
  m23 <- close_perpath(matrix(exp(PT[[s]]$ax + PT[[s]]$bx *
                     as.numeric(PT[[s]]$kt)[which(f$years == 2023)]), nrow = 1), lo, hi)$M
  MONO[[s]] <- qx_table(rbind(m23, central[[s]]$M))$max_logdelta
  REV[[paste0("main_", s)]] <- write_central(central[[s]]$M, m23,
                     sprintf("analysis/mortality/qx_central_%s.parquet", s))
  fr <- central[[paste0(s, "_rob")]]
  fq <- RB[[s]]$fit
  q23r <- fitted(fq, type = "rates")[, "2023"]
  m23r <- close_perpath(matrix(q_to_m(q23r), nrow = 1), lo, hi)$M
  REV[[paste0("robust_", s)]] <- write_central(fr$M, m23r,
                     sprintf("analysis/mortality/qx_central_robust_%s.parquet", s))
  Q <- SIM[[s]]$Q
  dt <- data.table(sim  = rep(rep(seq_len(NSIM), times = H), each = AGES_FULL_N),
                   year = rep(rep(YEARS_FUT, each = NSIM), each = AGES_FULL_N),
                   age  = rep(AGES_FULL, times = NSIM * H),
                   qx   = as.vector(t(Q)))
  dt[, `:=`(sim = as.integer(sim), year = as.integer(year), age = as.integer(age))]
  set.seed(9000L + which(SEXES == s))
  for (ss in sample.int(NSIM, 3)) for (yy in sample(YEARS_FUT, 2)) {
    jy <- which(YEARS_FUT == yy); rowi <- (jy - 1L) * NSIM + ss
    stopifnot(max(abs(dt[sim == ss & year == yy][order(age), qx] - Q[rowi, ])) < 1e-12)
  }
  ROWS[[s]] <- write_parquet_atomic(dt, sprintf("analysis/mortality/qx_sims_%s.parquet", s),
                                    compression = "zstd")
  stopifnot(ROWS[[s]] == NSIM * H * AGES_FULL_N)
  rm(dt); gc(FALSE)
}
TSE <- list()
for (s in SEXES) {
  lo <- PT[[s]]$slope_lo; hi <- PT[[s]]$slope_hi
  nA <- length(PT[[s]]$ax)
  Mc <- lc_rates(PT[[s]]$ax, PT[[s]]$bx, TSK[[s]]$cen)
  clc <- close_perpath(flat(Mc), lo, hi)
  m23 <- close_perpath(matrix(exp(PT[[s]]$ax + PT[[s]]$bx *
             as.numeric(PT[[s]]$kt)[which(PT[[s]]$fit$years == 2023)]), nrow = 1), lo, hi)$M
  write_central(clc$M, m23,
                sprintf("analysis/mortality/qx_central_%s_trendstationary.parquet", s))
  e_cen <- e65_export(clc$M)
  Ms <- lc_rates(PT[[s]]$ax, PT[[s]]$bx, TSK[[s]]$sim)
  cls <- close_perpath(flat(Ms), lo, hi); rm(Ms); gc(FALSE)
  e_sim <- matrix(e65_export(cls$M), nrow = NSIM, ncol = H)
  write_parquet_atomic(sims_long(qx_table(cls$M)$Q),
    sprintf("analysis/mortality/qx_sims_%s_trendstationary.parquet", s),
    compression = "zstd")
  TSE[[s]] <- list(central = e_cen, p025 = apply(e_sim, 2, quantile, 0.025),
                   p500 = apply(e_sim, 2, quantile, 0.5),
                   p975 = apply(e_sim, 2, quantile, 0.975))
  rm(cls, Mc, clc); gc(FALSE)
  message(sprintf("[ts ] %s exported: e65 2050 %.2f [%.2f,%.2f], 2080 %.2f [%.2f,%.2f]",
                  s, e_cen[which(YEARS_FUT == 2050)],
                  TSE[[s]]$p025[which(YEARS_FUT == 2050)], TSE[[s]]$p975[which(YEARS_FUT == 2050)],
                  e_cen[H], TSE[[s]]$p025[H], TSE[[s]]$p975[H]))
}

read2080 <- function(path) {
  path <- out_path(path)
  d <- as.data.table(open_dataset(path) |>
         dplyr::filter(year == 2080L, age >= 65L) |>
         dplyr::select(sim, age, qx) |> dplyr::collect())
  setorder(d, sim, age)
  ex_from_m(q_to_m(matrix(d$qx, nrow = NSIM, byrow = TRUE)), 65:AGE_OPEN)
}
e_m <- read2080("analysis/mortality/qx_sims_m.parquet")
e_f <- read2080("analysis/mortality/qx_sims_f.parquet")
SIMS_CORR_EXPORT <- unname(cor(e_m, e_f))
message(sprintf("[chk] corr(e65 2080) recomputed from the exported parquet = %.4f",
                SIMS_CORR_EXPORT))
rm(e_m, e_f); gc(FALSE)

qtab <- rbindlist(lapply(SEXES, function(s) {
  E <- SIM[[s]]$e65
  data.table(sex = s, year = YEARS_FUT, central = central[[s]]$e65,
    mean = colMeans(E), p025 = apply(E, 2, quantile, 0.025),
    p100 = apply(E, 2, quantile, 0.10), p250 = apply(E, 2, quantile, 0.25),
    p500 = apply(E, 2, quantile, 0.50), p750 = apply(E, 2, quantile, 0.75),
    p900 = apply(E, 2, quantile, 0.90), p975 = apply(E, 2, quantile, 0.975),
    p995 = apply(E, 2, quantile, 0.995))
}))
qall <- qtab
if (!REDUCED) fwrite(qall, "analysis/mortality/e65_quantiles_main.csv")
rqall <- rbindlist(lapply(SEXES, function(s) data.table(sex = s, year = YEARS_FUT,
  central = central[[paste0(s, "_rob")]]$e65,
  p025 = apply(RSIM[[s]], 2, quantile, 0.025),
  p500 = apply(RSIM[[s]], 2, quantile, 0.50),
  p975 = apply(RSIM[[s]], 2, quantile, 0.975))))
if (!REDUCED) fwrite(rqall, "analysis/mortality/e65_quantiles_robust.csv")

coherence <- tryCatch({
  set.seed(2026)
  dm <- load_sex("m"); df <- load_sex("f")
  yr <- VARIANTS[[VAR_MAIN]]$years; ze <- VARIANTS[[VAR_MAIN]]$zero
  w <- weight_mat(dm$ages, yr, ze)
  pooled <- structure(list(Dxt = dm$D + df$D, Ext = dm$E + df$E, ages = dm$ages,
                           years = yr, type = "central", series = "total",
                           label = "MKD"), class = "StMoMoData")
  fcom <- suppressWarnings(fit(lc(link = "log"), data = pooled, ages.fit = dm$ages,
                               years.fit = yr, wxt = w, verbose = FALSE))
  kcom <- kt_of(fcom); rK <- rwd_stats(kcom[1, ], yr)
  Bx <- ma3(fcom$bx)
  Kfut <- rK$last_value + rK$drift * (YEARS_FUT - rK$last_year)
  BK_fit <- outer(as.numeric(fcom$bx), as.numeric(kcom[1, ])); BK_fit[is.na(BK_fit)] <- 0
  out <- list(); gap <- list(); revs <- list()
  for (s in SEXES) {
    lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
    hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
    dd <- if (s == "m") dm else df
    fs <- suppressWarnings(fit(lc(link = "log"), data = as_stmomo(dd, "central"),
                               ages.fit = dd$ages, years.fit = yr, wxt = w,
                               oxt = BK_fit, verbose = FALSE))
    ks <- kt_of(fs)[1, ]
    ar <- forecast::Arima(ts(as.numeric(ks), start = yr[1]), order = c(1, 0, 0),
                          include.mean = TRUE, method = "ML")
    kf <- as.numeric(forecast::forecast(ar, h = H)$mean)
    su <- lc_surface(fs)
    bxs <- su$bx; ks <- su$kt
    ar <- forecast::Arima(ts(as.numeric(ks), start = yr[1]), order = c(1, 0, 0),
                          include.mean = TRUE, method = "ML")
    kf <- as.numeric(forecast::forecast(ar, h = H)$mean)
    lm_ <- outer(su$ax, rep(1, H)) + outer(Bx, Kfut) + outer(bxs, kf)
    cl <- close_perpath(t(exp(lm_)), lo, hi)
    k23 <- as.numeric(kcom[1, ])[which(yr == 2023)]; ks23 <- as.numeric(ks)[which(yr == 2023)]
    m23 <- close_perpath(matrix(exp(su$ax + Bx * k23 + bxs * ks23), nrow = 1), lo, hi)$M
    revs[[s]] <- write_central(cl$M, m23,
                   sprintf("analysis/mortality/qx_central_coherent_%s.parquet", s))
    e <- e65_export(cl$M)
    out[[s]] <- data.table(sex = s, year = YEARS_FUT, e65 = e)
    gap[[s]] <- e[YEARS_FUT == 2050]
    message(sprintf("   Li-Lee %s: AR(1) phi=%.3f mean=%.3f, e65 2050=%.3f",
                    s, coef(ar)["ar1"], coef(ar)["intercept"], gap[[s]]))
  }
  list(paths = rbindlist(out), gap2050 = gap$f - gap$m, revs = revs, ok = TRUE)
}, error = function(e) { message("   Li-Lee failed: ", conditionMessage(e)); list(ok = FALSE) })
if (isTRUE(coherence$ok)) if (!REDUCED) fwrite(coherence$paths, "analysis/mortality/e65_coherent_lilee.csv")

J <- list()
J$main_model <- toupper(MAIN_MODEL); J$robust_model <- toupper(ROBUST_MODEL)
J$variant_main <- VAR_MAIN
J$n_boot <- NBOOT; J$n_sim <- NSIM; J$seed <- 2026L
J$proj_year_last <- 2080L; J$jumpoff_year <- 2023L
J$ages_sim_lo <- min(AGES_FULL); J$ages_sim_hi <- max(AGES_FULL)
J$revision <- "2"

mt <- fread("analysis/mortality/model_table.csv")
bt <- fread("analysis/mortality/backtest.csv")
for (s in SEXES) for (v in c("A", "B", "C")) for (mn in c("lc", "cbd", "rh", "apc")) {
  r <- mt[sex == s & variant == v & model == mn]
  J[[sprintf("bic_%s_%s_%s", mn, s, v)]] <- if (nrow(r)) r$bic_common[1] else NA
  J[[sprintf("bic_native_%s_%s_%s", mn, s, v)]] <- if (nrow(r)) r$bic_native[1] else NA
  J[[sprintf("npar_%s_%s_%s", mn, s, v)]] <- if (nrow(r)) as.integer(r$npar[1]) else NA
}
for (s in SEXES) for (mn in c("lc", "cbd", "rh", "apc")) {
  r <- bt[sex == s & model == mn]
  J[[sprintf("backtest_rmse_%s_%s", mn, s)]] <- if (nrow(r)) r$rmse_logm_55_89[1] else NA
  J[[sprintf("backtest_rmse6089_%s_%s", mn, s)]] <- if (nrow(r)) r$rmse_logm_60_89[1] else NA
  J[[sprintf("backtest_e65_err_%s_%s", mn, s)]] <- if (nrow(r)) r$e65_err_2019[1] else NA
}
S1J <- fromJSON("analysis/mortality/_stage1.json", simplifyVector = FALSE)
for (s in SEXES) {
  J[[sprintf("rh_converged_%s", s)]] <- isTRUE(S1$rh_keep)
  J[[sprintf("rh_diagnostic_%s", s)]] <- S1J$rh_reason[[s]]
}
J$apc_included <- TRUE

for (s in SEXES) {
  for (v in c("A", "B", "C")) {
    f <- fits[[s]][[v]][[MAIN_MODEL]]
    r <- if (v == VAR_MAIN) PT[[s]]$rwd else lc_surface(f)$rwd
    a <- fit_rwd(kt_of(f)[1, ], f$years)
    J[[sprintf("drift_kt_%s_%s", s, v)]]      <- r$drift
    J[[sprintf("drift_se_kt_%s_%s", s, v)]]   <- r$se
    J[[sprintf("drift_se_arima_%s_%s", s, v)]] <- a$se
    J[[sprintf("sigma_kt_%s_%s", s, v)]]      <- r$sigma
    J[[sprintf("tstat_kt_%s_%s", s, v)]]      <- r$tstat
    J[[sprintf("pvalue_kt_%s_%s", s, v)]]     <- r$pvalue
    J[[sprintf("df_kt_%s_%s", s, v)]]         <- as.integer(r$df)
    J[[sprintf("kt_n_increments_%s_%s", s, v)]] <- as.integer(r$n_inc)
    J[[sprintf("kt_span_%s_%s", s, v)]]       <- as.integer(r$span)
  }
  rr <- PT[[s]]$rwd_raw
  J[[sprintf("drift_kt_%s_B_rawbeta", s)]] <- rr$drift
  J[[sprintf("drift_se_kt_%s_B_rawbeta", s)]] <- rr$se
  J[[sprintf("sigma_kt_%s_B_rawbeta", s)]] <- rr$sigma
  J[[sprintf("tstat_kt_%s_B_rawbeta", s)]] <- rr$tstat
  J[[sprintf("pvalue_kt_%s_B_rawbeta", s)]] <- rr$pvalue
  J[[sprintf("h1_tstat_%s", s)]]  <- J[[sprintf("tstat_kt_%s_B", s)]]
  J[[sprintf("h1_pvalue_%s", s)]] <- J[[sprintf("pvalue_kt_%s_B", s)]]
  J[[sprintf("h1_tstat_%s_A", s)]]  <- J[[sprintf("tstat_kt_%s_A", s)]]
  J[[sprintf("h1_pvalue_%s_A", s)]] <- J[[sprintf("pvalue_kt_%s_A", s)]]
}
for (v in c("A", "B", "C")) J[[sprintf("h1_crit_tstat_%s", v)]] <-
  qt(0.975, J[[sprintf("df_kt_m_%s", v)]])
J$h1_supported <- all(sapply(SEXES, function(s)
  J[[sprintf("drift_kt_%s_B", s)]] < 0 &&
  abs(J[[sprintf("h1_tstat_%s", s)]]) >= J$h1_crit_tstat_B))
J$h1_supported_pvalue <- all(sapply(SEXES, function(s) J[[sprintf("h1_pvalue_%s", s)]] < 0.05))
J$h1_supported_A <- all(sapply(SEXES, function(s)
  J[[sprintf("drift_kt_%s_A", s)]] < 0 && J[[sprintf("pvalue_kt_%s_A", s)]] < 0.05))
J$h1_supported_A_pvalue <- all(sapply(SEXES, function(s) J[[sprintf("pvalue_kt_%s_A", s)]] < 0.05))
J$h1_supported_C <- all(sapply(SEXES, function(s)
  J[[sprintf("drift_kt_%s_C", s)]] < 0 && J[[sprintf("pvalue_kt_%s_C", s)]] < 0.05))
J$h1_crit_abs_tstat <- J$h1_crit_tstat_B
J$kt_increment_corr_mf <- RHO_MF
J$sims_e65_2080_corr_mf <- SIMS_CORR_EXPORT
J$beta_smoothing <- "3-point moving average of beta_x"

for (s in SEXES) {
  f <- PT[[s]]$fit
  lo <- if (WINSOR[[s]]) PT[[s]]$slope_lo else NULL
  hi <- if (WINSOR[[s]]) PT[[s]]$slope_hi else NULL
  m23 <- close_perpath(matrix(exp(PT[[s]]$ax + PT[[s]]$bx *
             as.numeric(PT[[s]]$kt)[which(f$years == 2023)]), nrow = 1), lo, hi)$M
  ef <- e65_export(m23)
  J[[sprintf("e65_%s_2023_fitted", s)]] <- ef
  J[[sprintf("e65_%s_2023_actual", s)]] <- act_e65(s, 2023)
  J[[sprintf("e65_%s_2023_jumpoff_bias", s)]] <- ef - act_e65(s, 2023)
  E <- SIM[[s]]$e65; qa <- qall[sex == s]
  for (y in c(2030, 2040, 2050, 2060, 2070, 2080)) {
    i <- which(YEARS_FUT == y)
    J[[sprintf("e65_%s_%d_central", s, y)]] <- central[[s]]$e65[i]
    J[[sprintf("e65_%s_%d_p025", s, y)]] <- qa$p025[i]
    J[[sprintf("e65_%s_%d_p500", s, y)]] <- qa$p500[i]
    J[[sprintf("e65_%s_%d_p975", s, y)]] <- qa$p975[i]
    J[[sprintf("e65_%s_%d_p995", s, y)]] <- qa$p995[i]
  }
  i80 <- which(YEARS_FUT == 2080)
  g <- (E[, i80] - ef) / (2080 - 2023)
  J[[sprintf("e65_gain_per_year_%s", s)]] <- (central[[s]]$e65[i80] - ef) / (2080 - 2023)
  J[[sprintf("e65_gain_per_year_%s_p025", s)]] <- unname(quantile(g, 0.025))
  J[[sprintf("e65_gain_per_year_%s_p975", s)]] <- unname(quantile(g, 0.975))
  rq <- rqall[sex == s]; i50 <- which(YEARS_FUT == 2050)
  J[[sprintf("e65_%s_2050_robust", s)]] <- rq$central[i50]
  J[[sprintf("e65_%s_2080_robust", s)]] <- rq$central[i80]
  J[[sprintf("e65_%s_2050_robust_p025", s)]] <- rq$p025[i50]
  J[[sprintf("e65_%s_2050_robust_p975", s)]] <- rq$p975[i50]
  for (v in c("A", "B", "C")) J[[sprintf("e65_%s_2050_variant%s", s, v)]] <-
    e65_var[sex == s & variant == v & model == MAIN_MODEL & year == 2050, e65]
  cr <- central[[paste0(s, "_rawbeta")]]
  J[[sprintf("beta_smoothing_delta_e65_%s_2050", s)]] <- central[[s]]$e65[i50] - cr$e65[i50]
  J[[sprintf("beta_smoothing_delta_e65_%s_2080", s)]] <- central[[s]]$e65[i80] - cr$e65[i80]
  J[[sprintf("kannisto_slope_obs_lo_%s", s)]] <- PT[[s]]$slope_obs_lo
  J[[sprintf("kannisto_slope_obs_hi_%s", s)]] <- PT[[s]]$slope_obs_hi
  J[[sprintf("kannisto_slope_bound_lo_%s", s)]] <- PT[[s]]$slope_lo
  J[[sprintf("kannisto_slope_bound_hi_%s", s)]] <- PT[[s]]$slope_hi
  J[[sprintf("kannisto_slope_annual_se_%s", s)]] <- PT[[s]]$slope_se
  J[[sprintf("kannisto_winsorised_%s", s)]] <- unname(WINSOR[[s]])
  J[[sprintf("kannisto_winsor_share_%s", s)]] <- DIAG[[s]]$winsor
  J[[sprintf("kannisto_winsor_share_low_%s", s)]] <- DIAG[[s]]$winsor_lo
  J[[sprintf("kannisto_above_upper_ref_share_%s", s)]] <- DIAG[[s]]$above_hi
  J[[sprintf("kannisto_slope_perpath_min_%s", s)]] <- DIAG[[s]]$slope_min
  J[[sprintf("kannisto_slope_perpath_p01_%s", s)]] <- DIAG[[s]]$slope_p01
  Enw <- SIM[[s]]$e65_nowinsor
  for (y in c(2050, 2080)) {
    i <- which(YEARS_FUT == y)
    J[[sprintf("e65_%s_%d_p025_nowinsor", s, y)]] <- unname(quantile(Enw[, i], 0.025))
    J[[sprintf("e65_%s_%d_p500_nowinsor", s, y)]] <- unname(quantile(Enw[, i], 0.50))
    J[[sprintf("e65_%s_%d_p975_nowinsor", s, y)]] <- unname(quantile(Enw[, i], 0.975))
    J[[sprintf("e65_%s_%d_p995_nowinsor", s, y)]] <- unname(quantile(Enw[, i], 0.995))
  }
  J[[sprintf("kannisto_slope_perpath_negshare_%s", s)]] <- DIAG[[s]]$slope_negshare
  J[[sprintf("qx_reversals_before_%s", s)]] <- unname(REV[[paste0("main_", s)]]["before"])
  J[[sprintf("qx_reversals_after_%s", s)]]  <- unname(REV[[paste0("main_", s)]]["after"])
  J[[sprintf("qx_monotone_max_logdelta_%s", s)]] <- MONO[[s]]
  J[[sprintf("qx_sims_rows_%s", s)]] <- as.integer(ROWS[[s]])
  J[[sprintf("sanity_breach_share_main_%s", s)]] <- DIAG[[s]]$breach
  J[[sprintf("sanity_breach_share_robust_%s", s)]] <- RBREACH[[s]]
  J[[sprintf("qx_reversals_sims_before_%s", s)]] <- DIAG[[s]]$rev_before
  J[[sprintf("qx_reversals_sims_after_%s", s)]]  <- DIAG[[s]]$rev_after
  J[[sprintf("qx_sims_pathyears_repaired_%s", s)]] <- DIAG[[s]]$rows_fixed
  for (k in seq_along(YRS_VD)) {
    y <- YRS_VD[k]
    J[[sprintf("var_share_boot_%s_%d", s, y)]]  <- VD[[s]]$share_boot[k]
    J[[sprintf("var_share_drift_%s_%d", s, y)]] <- VD[[s]]$share_drift[k]
    J[[sprintf("var_share_proc_%s_%d", s, y)]]  <- VD[[s]]$share_proc[k]
    J[[sprintf("var_abl_boot_%s_%d", s, y)]]  <- VD[[s]]$v_boot[k]
    J[[sprintf("var_abl_drift_%s_%d", s, y)]] <- VD[[s]]$v_drift[k]
    J[[sprintf("var_abl_proc_%s_%d", s, y)]]  <- VD[[s]]$v_proc[k]
    J[[sprintf("var_abl_sum_%s_%d", s, y)]]   <- (VD[[s]]$v_boot + VD[[s]]$v_drift +
                                                  VD[[s]]$v_proc)[k]
    J[[sprintf("e65_var_realised_%s_%d", s, y)]] <- VD[[s]]$realised[k]
    J[[sprintf("var_abl_sum_over_realised_%s_%d", s, y)]] <- VD[[s]]$sum_over_realised[k]
  }
}
for (s in SEXES) {
  x <- RWDX[[s]]
  J[[sprintf("kt_vr2_%s", s)]] <- x$vr2
  J[[sprintf("kt_vr4_%s", s)]] <- x$vr4
  J[[sprintf("kt_vr8_%s", s)]] <- x$vr8
  J[[sprintf("kt_increment_acf1_%s", s)]] <- x$acf1
  J[[sprintf("kt_ljungbox_p_%s", s)]] <- x$lb_p
  J[[sprintf("kt_trend_ar1_phi_%s", s)]] <- x$ar1_phi
  J[[sprintf("kt_trend_slope_%s", s)]] <- x$trend_b
  J[[sprintf("kt_trend_slope_se_%s", s)]] <- x$trend_se
  J[[sprintf("kt_trend_tstat_%s", s)]] <- x$trend_t
  J[[sprintf("drift_kt_%s_B_drop2023", s)]] <- x$drop2023$drift
  J[[sprintf("tstat_kt_%s_B_drop2023", s)]] <- x$drop2023$tstat
  J[[sprintf("pvalue_kt_%s_B_drop2023", s)]] <- x$drop2023$pvalue
  J[[sprintf("drift_kt_%s_B_drop2003", s)]] <- x$drop2003$drift
  J[[sprintf("tstat_kt_%s_B_drop2003", s)]] <- x$drop2003$tstat
  J[[sprintf("pvalue_kt_%s_B_drop2003", s)]] <- x$drop2003$pvalue
  for (k in seq_along(YRS_VD)) {
    y <- YRS_VD[k]
    iy <- which(YEARS_FUT == y)
    J[[sprintf("kt_sd_trendstationary_%s_%d", s, y)]] <- TSALT[[s]]$sd_kappa[iy]
    J[[sprintf("e65_%s_%d_central_trendstationary", s, y)]] <- TSE[[s]]$central[iy]
    J[[sprintf("e65_%s_%d_p025_trendstationary", s, y)]] <- TSE[[s]]$p025[iy]
    J[[sprintf("e65_%s_%d_p500_trendstationary", s, y)]] <- TSE[[s]]$p500[iy]
    J[[sprintf("e65_%s_%d_p975_trendstationary", s, y)]] <- TSE[[s]]$p975[iy]
  }
}
J$rwd_assumption_tested <- TRUE
J$kannisto_bound_one_sided <- TRUE
J$kannisto_winsor_symmetric <- TRUE
J$qx_reversals_before <- sum(sapply(SEXES, function(s) J[[sprintf("qx_reversals_before_%s", s)]]))
J$qx_reversals_after  <- sum(sapply(SEXES, function(s) J[[sprintf("qx_reversals_after_%s", s)]]))
J$qx_export_closes_at_110 <- TRUE
J$cbd_qcap_share <- if (CBD_NCELL > 0) CBD_QCAP / CBD_NCELL else 0
J$logit_clamp_share <- if (CLAMP_HITS$tot > 0) CLAMP_HITS$n / CLAMP_HITS$tot else 0
J$kannisto_slope_source <- "per simulated path, FLOOR ONLY at the observed 2003-2023 minimum less 2 x the mean sampling SE of the annual slope estimates; no ceiling; same rule for both sexes"
J$coherence_done <- isTRUE(coherence$ok)
if (isTRUE(coherence$ok)) {
  J$coherence_gap_2050_sexspecific <- J$e65_f_2050_central - J$e65_m_2050_central
  J$coherence_gap_2050_coherent <- coherence$gap2050
  J$coherence_gap_2023_fitted <- J$e65_f_2023_fitted - J$e65_m_2023_fitted
}
# Keys written by rh_refit.R are preserved whatever the run order.
if (file.exists("results/mortality.json")) {
  prev <- fromJSON("results/mortality.json", simplifyVector = FALSE)
  keep <- grep("^(rh_|apc_clipped_|bic_eff_|npar_eff_|nobs_eff_|e65_[mf]_2050_rh_)",
               names(prev), value = TRUE)
  for (k in setdiff(keep, names(J))) J[[k]] <- prev[[k]]
}
J <- J[order(names(J))]
if (REDUCED) {
  message("[reduced run] results/mortality.json NOT written (run under 1,000 paths)")
} else {
  write_json(J, "results/mortality.json", auto_unbox = TRUE, pretty = TRUE,
             digits = 12, na = "null")
}
ktl <- rbindlist(lapply(SEXES, function(s) rbindlist(lapply(names(VARIANTS), function(v) {
  flc <- fits[[s]][[v]][["lc"]]; su <- lc_surface(flc)
  fcb <- fits[[s]][[v]][["cbd"]]; kc <- kt_of(fcb)
  rbind(data.table(sex = s, variant = v, model = "lc", index = 1L,
                   year = flc$years, kt = as.numeric(su$kt),
                   kt_rawbeta = as.numeric(kt_of(flc)[1, ])),
        rbindlist(lapply(seq_len(nrow(kc)), function(i)
          data.table(sex = s, variant = v, model = "cbd", index = i,
                     year = fcb$years, kt = as.numeric(kc[i, ]),
                     kt_rawbeta = as.numeric(kc[i, ])))))
}))))
if (!REDUCED) fwrite(ktl, "analysis/mortality/kt_series.csv")

if (!REDUCED) saveRDS(list(central = central, qall = qall, rqall = rqall, e65_var = e65_var,
             rho_mf = RHO_MF, vd = VD, diag = DIAG, coherence = coherence, json = J),
        "analysis/mortality/projection.rds", compress = "xz")

if (!REDUCED) {
  JJ <- fromJSON("results/mortality.json", simplifyVector = TRUE)
  bad <- character(0)
  for (s in SEXES) {
    for (y in c(2050L, 2080L)) {
      d <- as.data.table(open_dataset(sprintf("analysis/mortality/qx_sims_%s.parquet", s)) |>
             dplyr::filter(year == y, age >= 65L) |>
             dplyr::select(sim, age, qx) |> dplyr::collect())
      setorder(d, sim, age)
      e <- ex_from_m(q_to_m(matrix(d$qx, nrow = NSIM, byrow = TRUE)), 65:AGE_OPEN)
      for (q in c("p025", "p500", "p975")) {
        got <- unname(quantile(e, as.numeric(sub("p", "0.", q))))
        have <- JJ[[sprintf("e65_%s_%d_%s", s, y, q)]]
        if (!isTRUE(abs(got - have) < 1e-6))
          bad <- c(bad, sprintf("e65_%s_%d_%s: parquet %.6f vs json %.6f", s, y, q, got, have))
      }
    }
  }
  if (length(bad)) {
    stop("results/mortality.json disagrees with the exported qx_sims_* files:\n  ",
         paste(bad, collapse = "\n  "))
  }
  message(sprintf("[chk] registry vs exported surfaces: %d e65 quantiles agree to <1e-6",
                  length(SEXES) * 2 * 3))
}

message(sprintf("[done] project_simulate.R in %.1f min",
                as.numeric(difftime(Sys.time(), t_start, units = "mins"))))
