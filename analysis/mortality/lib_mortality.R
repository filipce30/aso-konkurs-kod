# Shared helpers for the mortality models: data, weights, life tables, Kannisto closure, RWD, figures.
suppressPackageStartupMessages({
  library(StMoMo); library(forecast); library(data.table); library(jsonlite)
})

AGES_FIT   <- 55:89
AGE_OPEN   <- 110
KAN_LO     <- 80
KAN_HI     <- 89
YEAR_FIRST <- 2003
YEAR_LAST  <- 2023
COVID_YRS  <- c(2020, 2021, 2022)
MISSING_YR <- 2022
CLIP       <- 3

read_mat <- function(path) {
  m <- as.matrix(read.csv(path, check.names = FALSE, row.names = 1))
  colnames(m) <- sub("^X", "", colnames(m))
  m
}

load_sex <- function(sex, ages = AGES_FIT, years = YEAR_FIRST:YEAR_LAST, root = "data/clean") {
  D <- read_mat(file.path(root, sprintf("deaths_Dxt_%s.csv", sex)))
  E <- read_mat(file.path(root, sprintf("exposures_Ext_%s.csv", sex)))
  a <- as.character(ages); y <- as.character(years)
  D <- D[a, y, drop = FALSE]; E <- E[a, y, drop = FALSE]
  D[is.na(D)] <- 0
  stopifnot(all(is.finite(E)), all(E > 0))
  list(D = D, E = E, ages = ages, years = years, sex = sex)
}

as_stmomo <- function(dd, type = c("central", "initial")) {
  type <- match.arg(type)
  obj <- structure(list(Dxt = dd$D, Ext = dd$E, ages = dd$ages, years = dd$years,
                        type = "central",
                        series = if (dd$sex == "m") "male" else "female",
                        label = "MKD"), class = "StMoMoData")
  if (type == "initial") obj <- central2initial(obj)
  obj
}

weight_mat <- function(ages, years, zero_years = integer(0), clip = CLIP) {
  w <- genWeightMat(ages, years, clip = clip)
  zy <- as.character(intersect(zero_years, years))
  if (length(zy)) w[, zy] <- 0
  w
}

eff_weight_mat <- function(ages, years, zero_years = integer(0), clip = CLIP) {
  w <- weight_mat(ages, years, zero_years, clip = clip)
  C <- outer(ages, years, function(x, t) t - x)
  n <- tapply(as.vector(w), as.vector(C), sum)
  bad <- as.numeric(names(n))[n > 0 & n < clip]
  if (length(bad)) w[C %in% bad] <- 0
  attr(w, "extra_clipped") <- bad
  w
}

unidentified_years <- function(wxt, years) years[colSums(wxt) == 0]

ex_from_m <- function(Mmat, ages_vec) {
  stopifnot(tail(ages_vec, 1) == AGE_OPEN, is.matrix(Mmat), ncol(Mmat) == length(ages_vec))
  A <- ncol(Mmat)
  q <- Mmat / (1 + 0.5 * Mmat)
  q[q > 1] <- 1
  q[, A] <- 1
  lx <- matrix(0, nrow(Mmat), A)
  lx[, 1] <- 1
  if (A > 1) for (j in 2:A) lx[, j] <- lx[, j - 1] * (1 - q[, j - 1])
  dx <- lx * q
  Lx <- lx - 0.5 * dx
  Lx[, A] <- lx[, A] / Mmat[, A]
  rowSums(Lx) / lx[, 1]
}
ex_from_m_vec <- function(mvec, ages_vec) ex_from_m(matrix(mvec, nrow = 1), ages_vec)[1]

ex_from_m_trunc <- function(Mmat, ages_vec) {
  A <- ncol(Mmat)
  q <- Mmat / (1 + 0.5 * Mmat); q[q > 1] <- 1; q[, A] <- 1
  lx <- matrix(0, nrow(Mmat), A); lx[, 1] <- 1
  if (A > 1) for (j in 2:A) lx[, j] <- lx[, j - 1] * (1 - q[, j - 1])
  dx <- lx * q; Lx <- lx - 0.5 * dx
  rowSums(Lx) / lx[, 1]
}

kannisto_operator <- function(fit_ages = KAN_LO:KAN_HI, tgt_ages = (KAN_HI + 1):AGE_OPEN) {
  xb <- mean(fit_ages); Sxx <- sum((fit_ages - xb)^2); n <- length(fit_ages)
  outer(tgt_ages, fit_ages, function(t, j) 1 / n + (j - xb) * (t - xb) / Sxx)
}
KAN_OP <- kannisto_operator()

LOGIT_CLAMP_HI <- 1 - 1e-6
CLAMP_HITS <- new.env(); CLAMP_HITS$n <- 0; CLAMP_HITS$tot <- 0
clamp_rate <- function(M) {
  CLAMP_HITS$n   <- CLAMP_HITS$n + sum(M > LOGIT_CLAMP_HI)
  CLAMP_HITS$tot <- CLAMP_HITS$tot + length(M)
  pmin(pmax(M, 1e-8), LOGIT_CLAMP_HI)
}

kan_slope <- function(Mfit, ages = AGES_FIT) {
  idx <- match(KAN_LO:KAN_HI, ages)
  mm <- clamp_rate(Mfit[, idx, drop = FALSE])
  y <- log(mm / (1 - mm))
  x <- KAN_LO:KAN_HI; xb <- mean(x)
  as.numeric((y %*% (x - xb)) / sum((x - xb)^2))
}

close_kannisto <- function(Mfit, ages = AGES_FIT, slope = NULL) {
  idx <- match(KAN_LO:KAN_HI, ages)
  mm  <- clamp_rate(Mfit[, idx, drop = FALSE])
  y   <- log(mm / (1 - mm))
  if (is.null(slope)) {
    hi <- 1 / (1 + exp(-(y %*% t(KAN_OP))))
  } else {
    x <- KAN_LO:KAN_HI; xb <- mean(x); tg <- (KAN_HI + 1):AGE_OPEN
    lin <- outer(rowMeans(y), rep(1, length(tg))) +
           outer(as.numeric(slope), tg - xb)
    hi <- 1 / (1 + exp(-lin))
  }
  cbind(Mfit, hi)
}
AGES_FULL <- c(AGES_FIT, (KAN_HI + 1):AGE_OPEN)

e65_from_closed <- function(Mclosed) {
  j <- match(65:AGE_OPEN, AGES_FULL)
  ex_from_m(Mclosed[, j, drop = FALSE], 65:AGE_OPEN)
}

ma3 <- function(b, renorm = TRUE) {
  b <- as.numeric(b); n <- length(b); o <- b
  if (n > 2) for (i in 2:(n - 1)) o[i] <- mean(b[(i - 1):(i + 1)])
  if (renorm) o <- o / sum(o)
  o
}

refit_kt_poisson <- function(ax, bx, D, E, wxt, tol = 1e-10, maxit = 100L) {
  ax <- as.numeric(ax); bx <- as.numeric(bx)
  nt <- ncol(D); kt <- rep(NA_real_, nt)
  for (j in seq_len(nt)) {
    w <- wxt[, j]; if (all(w == 0)) next
    d <- D[, j]; e <- E[, j]; k <- 0
    for (it in seq_len(maxit)) {
      mu <- e * exp(ax + bx * k)
      g  <- sum(w * bx * (d - mu))
      h  <- -sum(w * bx^2 * mu)
      step <- g / h
      k <- k - step
      if (abs(step) < tol) break
    }
    kt[j] <- k
  }
  ok <- !is.na(kt); mk <- mean(kt[ok])
  list(kt = kt - mk, ax = ax + bx * mk, bx = bx)
}

rwd_stats <- function(kt, years) {
  ok <- which(!is.na(as.numeric(kt)))
  k <- as.numeric(kt)[ok]; t <- years[ok]
  dk <- diff(k); dt <- diff(t); N <- length(dk); span <- sum(dt)
  mu <- sum(dk) / span
  sigma <- sqrt(sum((dk - mu * dt)^2 / dt) / (N - 1))
  se <- sigma / sqrt(span)
  list(drift = mu, sigma = sigma, se = se, df = N - 1L, n_inc = N, span = span,
       tstat = mu / se, pvalue = 2 * stats::pt(-abs(mu / se), N - 1),
       last_value = k[length(k)], last_year = t[length(t)],
       resid_std = (dk - mu * dt) / sqrt(dt))
}

monotone_fix <- function(Q, ages, from = 65L) {
  j <- which(ages >= from)
  L <- log(Q[, j, drop = FALSE])
  bad <- which(rowSums(L[, -1, drop = FALSE] - L[, -ncol(L), drop = FALSE] < 0) > 0)
  n_bad <- length(bad)
  if (n_bad) for (i in bad) L[i, ] <- stats::isoreg(L[i, ])$yf
  Q[, j] <- exp(L)
  list(Q = Q, n_rows_fixed = n_bad,
       n_reversals = sum(L[, -1, drop = FALSE] - L[, -ncol(L), drop = FALSE] < -1e-12))
}
count_reversals <- function(Q, ages, from = 65L) {
  j <- which(ages >= from); L <- log(Q[, j, drop = FALSE])
  sum(L[, -1, drop = FALSE] - L[, -ncol(L), drop = FALSE] < -1e-12)
}

fit_rwd <- function(kt, years) {
  y  <- ts(as.numeric(kt), start = years[1])
  fm <- forecast::Arima(y, order = c(0, 1, 0), include.drift = TRUE, method = "ML")
  ok <- which(!is.na(as.numeric(kt)))
  list(drift = unname(coef(fm)["drift"]),
       se    = unname(sqrt(fm$var.coef["drift", "drift"])),
       sigma = sqrt(fm$sigma2),
       last_value = as.numeric(kt)[max(ok)],
       last_year  = years[max(ok)],
       n_inc = length(ok) - 1,
       model = fm)
}

sim_rwd <- function(last_value, drift, sigma, h, nsim) {
  eps <- matrix(rnorm(nsim * h, 0, sigma), nrow = nsim, ncol = h)
  last_value + t(apply(sweep(eps, 2, drift, "+"), 1, cumsum))
}
central_rwd <- function(last_value, drift, h) last_value + drift * seq_len(h)

poisson_loglik <- function(D, E, M, w) {
  ok <- w > 0 & is.finite(M) & M > 0
  lam <- E[ok] * M[ok]; d <- D[ok]
  sum(d * log(lam) - lam - lgamma(d + 1))
}
bic_common <- function(D, E, M, w, npar) {
  ll <- poisson_loglik(D, E, M, w)
  c(loglik = ll, bic = -2 * ll + npar * log(sum(w > 0)))
}

fitted_rates <- function(f) {
  r <- fitted(f, type = "rates")
  if (f$model$link == "logit") r <- r / (1 - 0.5 * r)
  r
}
q_to_m <- function(q) q / (1 - 0.5 * q)
m_to_q <- function(m) m / (1 + 0.5 * m)

fit_one <- function(model_name, dd, years, zero_years) {
  ages <- dd$ages
  w <- weight_mat(ages, years, zero_years)
  yy <- as.character(years)
  ddy <- list(D = dd$D[, yy, drop = FALSE], E = dd$E[, yy, drop = FALSE],
              ages = ages, years = years, sex = dd$sex)
  if (model_name == "cbd") {
    obj <- as_stmomo(ddy, "initial"); mdl <- cbd(link = "logit")
  } else if (model_name == "lc") {
    obj <- as_stmomo(ddy, "central"); mdl <- lc(link = "log")
  } else if (model_name == "apc") {
    obj <- as_stmomo(ddy, "central"); mdl <- apc(link = "log")
  } else stop("unknown model")
  f <- suppressWarnings(fit(mdl, data = obj, ages.fit = ages, years.fit = years,
                            wxt = w, verbose = FALSE))
  f$wxt <- w
  f
}

save_fig <- function(plot, name, width = 6.3, height = 3.5) {
  dir.create("figures", showWarnings = FALSE)
  ggplot2::ggsave(file.path("figures", paste0(name, ".png")), plot,
                  width = width, height = height, dpi = 300, bg = "white")
  ggplot2::ggsave(file.path("figures", paste0(name, ".svg")), plot,
                  width = width, height = height, device = svglite::svglite, bg = "white")
  invisible(NULL)
}
SEXLAB <- c(m = "Мажи", f = "Жени")
SEXF <- function(s) factor(unname(SEXLAB[s]), levels = c("Мажи", "Жени"))
SRC_MK <- "Извор: пресметки на авторот врз основа на податоци од ДЗС и Евростат."
theme_mk <- function(base = 8.5) {
  ggplot2::theme_bw(base_size = base) +
    ggplot2::theme(panel.grid.minor = ggplot2::element_blank(),
                   axis.text = ggplot2::element_text(size = 8, colour = "grey20"),
                   axis.title = ggplot2::element_text(size = base),
                   legend.text = ggplot2::element_text(size = 8),
                   strip.text = ggplot2::element_text(size = 8, margin = ggplot2::margin(2, 2, 2, 2)),
                   legend.position = "bottom", legend.title = ggplot2::element_blank(),
                   legend.margin = ggplot2::margin(0, 0, 0, 0),
                   legend.box.spacing = ggplot2::unit(2, "pt"),
                   plot.margin = ggplot2::margin(4, 6, 2, 2),
                   strip.background = ggplot2::element_rect(fill = "grey92"))
}

COL_M      <- "#0072B2"
COL_F      <- "#D55E00"
COL_SEX    <- c(m = COL_M, f = COL_F)
COL_VARIANT<- c(A = "#009E73", B = "#0072B2", C = "#E69F00")
COL_MODEL  <- c(lc = "#000000", cbd = "#009E73", apc = "#E69F00",
                 rh = "#CC79A7")
COL_GREY   <- "#7F7F7F"
SCALE_COL_SEX <- function(...) ggplot2::scale_colour_manual(values = unname(COL_SEX[c("m","f")]), ...)
SCALE_FILL_SEX <- function(...) ggplot2::scale_fill_manual(values = unname(COL_SEX[c("m","f")]), ...)

mk_num <- function(accuracy = NULL, big.mark = ".") {
  scales::label_number(accuracy = accuracy, decimal.mark = ",", big.mark = big.mark,
                       style_negative = "minus")
}
mk_pct <- function(accuracy = 1) scales::label_percent(accuracy = accuracy, decimal.mark = ",")
mk_year_breaks <- function(x) {
  rng <- range(x, na.rm = TRUE)
  b <- scales::extended_breaks(n = 6)(rng)
  unique(round(b))
}
scale_x_year <- function(name = "Година", breaks = mk_year_breaks, ...) {
  ggplot2::scale_x_continuous(name = name, breaks = breaks,
                              labels = scales::label_number(accuracy = 1, big.mark = ""), ...)
}
