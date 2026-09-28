#!/usr/bin/env Rscript
# Mortality figures from the saved fits and projections; the backtest is re-derived and checked against backtest.csv.
suppressPackageStartupMessages({
  library(ggplot2); library(svglite); library(data.table); library(jsonlite); library(scales)
})
source("analysis/mortality/lib_mortality.R")

VARIANTS <- list(
  A = list(years = 2003:2019, zero = integer(0),
           label = "А: 2003-2019 (пред-ковид)"),
  B = list(years = 2003:2023, zero = c(2020, 2021, 2022),
           label = "Б: 2003-2023, нулти тежини 2020-2022"),
  C = list(years = 2003:2023, zero = c(2022),
           label = "В: наивен 2003-2023")
)
VARLAB  <- sapply(VARIANTS, `[[`, "label")
MODLAB  <- c(lc = "Ли-Картер (LC)", cbd = "Кернс-Блејк-Дауд (CBD)", apc = "Возраст-период-кохорта (APC)",
             rh = "Реншо-Хаберман (RH, H1)")
MODLAB_SHORT <- c(lc = "LC", cbd = "CBD", apc = "APC", rh = "RH")

S1  <- readRDS("analysis/mortality/fits.rds")
fits <- S1$fits
kt_long <- fread("analysis/mortality/kt_series.csv")
mt2 <- fread("analysis/mortality/model_table.csv")
bt  <- fread("analysis/mortality/backtest.csv")
MJ  <- fromJSON("results/mortality.json")
lt  <- fread("data/clean/lifetables_period.csv")
SEXES <- c("m", "f")

kt_parts <- lapply(SEXES, function(s) {
  dB <- kt_long[sex == s & variant == "B" & model == "lc" & index == 1]
  setorder(dB, year)
  ident <- dB[!is.na(kt)]
  segs_dash <- data.table(sex = s, x = ident$year[-nrow(ident)], xend = ident$year[-1],
                          y = ident$kt[-nrow(ident)], yend = ident$kt[-1],
                          dashed = diff(ident$year) > 1)

  dC <- kt_long[sex == s & variant == "C" & model == "lc" & index == 1 & year %in% c(2020, 2021)]
  dA <- kt_long[sex == s & variant == "A" & model == "lc" & index == 1]

  drift <- MJ[[sprintf("drift_kt_%s_B", s)]]
  last_year <- max(ident$year); last_value <- ident[year == last_year, kt]
  proj_years <- (last_year):2040
  proj <- data.table(sex = s, year = proj_years, kt = last_value + drift * (proj_years - last_year))
  list(ident = ident[, .(sex, year, kt)], segs = segs_dash, dC = dC[, .(sex, year, kt)],
       dA = dA[, .(sex, year, kt)], proj = proj)
})
kt_bind <- function(k) { d <- rbindlist(lapply(kt_parts, `[[`, k)); d[, sexf := SEXF(sex)]; d }
ident <- kt_bind("ident"); segs_dash <- kt_bind("segs"); dC <- kt_bind("dC")
dA <- kt_bind("dA"); proj <- kt_bind("proj")

yrng <- range(c(ident$kt, dC$kt, proj$kt, dA$kt), na.rm = TRUE)
ann_y <- yrng[1] + 0.10 * diff(yrng)
ann <- function(...) data.table(sexf = SEXF("m"), ...)
p <- ggplot() +
  geom_segment(data = segs_dash, aes(x = x, xend = xend, y = y, yend = yend, linetype = dashed,
                                     colour = sexf), linewidth = 0.55, show.legend = FALSE) +
  scale_linetype_manual(values = c(`FALSE` = "solid", `TRUE` = "22")) +
  geom_line(data = dA, aes(year, kt), colour = COL_GREY,
            linetype = "dotted", linewidth = 0.45, na.rm = TRUE) +
  geom_line(data = proj, aes(year, kt, colour = sexf), linetype = "22", linewidth = 0.6) +
  geom_point(data = ident, aes(year, kt, colour = sexf, fill = sexf), shape = 21, size = 1.5) +
  geom_point(data = dC, aes(year, kt), colour = COL_GREY, fill = "white", shape = 21,
             stroke = 0.8, size = 1.8) +
  SCALE_COL_SEX(guide = "none") + SCALE_FILL_SEX(guide = "none") +
  geom_vline(xintercept = 2023, colour = "grey40", linewidth = 0.35, linetype = "dashed") +
  geom_text(data = ann(x = 2024, y = yrng[2]), aes(x, y), hjust = 0, vjust = 1, size = 2.6,
            lineheight = 0.9, colour = "grey25", label = "почеток на\nпроекцијата") +
  geom_point(data = kt_bind("ident")[, .(x = 2022, y = ann_y), by = sexf], aes(x, y),
             shape = 4, size = 1.6, colour = "grey40") +
  geom_text(data = ann(x = 2021, y = ann_y), aes(x, y), hjust = 1,
            size = 2.6, lineheight = 0.9, colour = "grey25", label = "2022:\nнема податоци") +
  geom_text(data = ann(x = 2019.8, y = yrng[2]), aes(x, y), hjust = 1, vjust = 1, size = 2.6,
            lineheight = 0.9, colour = "grey35", label = "ковид-години\n(вар. В)") +
  facet_wrap(~sexf, nrow = 1) +
  scale_x_year(limits = c(2003, 2041)) +
  scale_y_continuous(name = expression(paste("Периоден индекс ", kappa[t])), labels = mk_num(),
                     breaks = seq(-20, 10, 5)) +
  theme_mk() + theme(legend.position = "none")
save_fig(p, "mortality_kt", height = 3.1)
message("[fig] mortality_kt")

par_long <- rbindlist(lapply(SEXES, function(s) {
  f <- fits[[s]][["B"]][["lc"]]
  kt <- f$kt; kt[, colSums(f$wxt) == 0] <- NA
  rbind(data.table(sex = s, par = "alpha[x]", x = f$ages, value = as.numeric(f$ax)),
        data.table(sex = s, par = "beta[x]",  x = f$ages, value = as.numeric(f$bx)),
        data.table(sex = s, par = "kappa[t]", x = f$years, value = as.numeric(kt[1, ])))
}))
p <- ggplot(par_long, aes(x, value, colour = SEXF(sex), shape = SEXF(sex))) +
  geom_line(na.rm = TRUE, linewidth = 0.5) + geom_point(na.rm = TRUE, size = 1.3) +
  SCALE_COL_SEX() +
  facet_wrap(~par, scales = "free", labeller = label_parsed) +
  scale_y_continuous(labels = mk_num()) +
  labs(x = "Возраст / година", y = "Вредност") + theme_mk()
save_fig(p, "mortality_params_lc", height = 3.0)
message("[fig] mortality_params_lc")

res_long <- rbindlist(lapply(SEXES, function(s) rbindlist(lapply(c("lc", "cbd"), function(mn) {
  f <- fits[[s]][["B"]][[mn]]
  r <- residuals(f, scale = TRUE)$residuals
  r[f$wxt == 0] <- NA
  dt <- as.data.table(as.table(r)); setnames(dt, c("age", "year", "res"))
  dt[, `:=`(age = as.integer(as.character(age)), year = as.integer(as.character(year)),
            sex = s, model = MODLAB_SHORT[mn])]
}))))
p <- ggplot(res_long, aes(year, age, fill = res)) + geom_tile(na.rm = TRUE) +
  facet_grid(model ~ SEXF(sex)) +
  scale_fill_gradient2(low = "#0072B2", mid = "white", high = "#D55E00",
                       midpoint = 0, na.value = "grey90", name = "Остаток",
                       labels = mk_num()) +
  scale_x_year() + scale_y_continuous(name = "Возраст", labels = mk_num(accuracy = 1)) +
  theme_mk() + theme(legend.position = "right", legend.title = element_text(size = 8))
save_fig(p, "mortality_residuals", height = 3.5)
message("[fig] mortality_residuals")

BT_FIT <- 2003:2014; BT_OUT <- 2015:2019
actual_e65 <- function(s, y) lt[year == y & sex == s & age == 65, ex]
bt_paths <- list(); bt_check <- list()
for (s in SEXES) {
  dd <- load_sex(s)
  Mact <- dd$D[, as.character(BT_OUT), drop = FALSE] / dd$E[, as.character(BT_OUT), drop = FALSE]
  for (mn in c("lc", "cbd", "apc")) {
    f <- fit_one(mn, dd, BT_FIT, integer(0))
    h <- length(BT_OUT)
    if (mn == "apc") {
      fc <- suppressWarnings(forecast::forecast(f, h = h)); Mfc <- fc$rates
    } else {
      kt <- f$kt
      if (mn == "lc") {
        r <- fit_rwd(kt[1, ], BT_FIT)
        kfc <- central_rwd(r$last_value, r$drift, h)
        Mfc <- exp(outer(as.numeric(f$ax), rep(1, h)) + outer(as.numeric(f$bx), kfc))
      } else {
        r1 <- fit_rwd(kt[1, ], BT_FIT); r2 <- fit_rwd(kt[2, ], BT_FIT)
        k1 <- central_rwd(r1$last_value, r1$drift, h); k2 <- central_rwd(r2$last_value, r2$drift, h)
        xb <- mean(f$ages)
        eta <- outer(rep(1, length(f$ages)), k1) + outer(f$ages - xb, k2)
        Mfc <- q_to_m(1 / (1 + exp(-eta)))
      }
      dimnames(Mfc) <- list(as.character(f$ages), as.character(BT_OUT))
    }
    ok <- is.finite(Mact) & Mact > 0 & is.finite(Mfc) & Mfc > 0
    err <- log(Mfc[ok]) - log(Mact[ok])
    rmse_chk <- sqrt(mean(err^2))
    bt_check[[length(bt_check) + 1]] <- data.table(sex = s, model = mn, rmse_reproduced = rmse_chk)
    for (ag in c(65, 75, 85)) bt_paths[[length(bt_paths) + 1]] <- data.table(
      sex = s, model = mn, age = ag, year = BT_OUT,
      logm_fc = log(Mfc[as.character(ag), ]), logm_act = log(Mact[as.character(ag), ]))
  }
}
btp <- rbindlist(bt_paths)
chk <- merge(rbindlist(bt_check), bt[, .(sex, model, rmse_logm_55_89)], by = c("sex", "model"))
stopifnot("backtest reproduction drifted from analysis/mortality/backtest.csv" =
            all(abs(chk$rmse_reproduced - chk$rmse_logm_55_89) < 1e-6))
message("[check] backtest reproduction matches analysis/mortality/backtest.csv exactly (max diff ",
        format(max(abs(chk$rmse_reproduced - chk$rmse_logm_55_89)), scientific = TRUE), ")")

btp[, lab := MODLAB_SHORT[model]]
bl <- unique(rbind(
  btp[, .(sex, age, year, series = "Набљудувано", logm = logm_act)],
  btp[, .(sex, age, year, series = paste0("Проекција ", lab), logm = logm_fc)]))
bl[, panel := factor(paste0(SEXF(sex), ", возраст ", age),
                     levels = c(t(outer(c("Мажи", "Жени"), c(65, 75, 85),
                                        function(a, b) paste0(a, ", возраст ", b)))))]
COL_BT <- c("Набљудувано" = "#595959", "Проекција LC" = unname(COL_MODEL["lc"]),
            "Проекција CBD" = unname(COL_MODEL["cbd"]), "Проекција APC" = unname(COL_MODEL["apc"]))
bl[, series := factor(series, levels = names(COL_BT))]
p <- ggplot(bl, aes(year, logm, colour = series, linetype = series, shape = series)) +
  geom_line(linewidth = 0.5) + geom_point(size = 1.2) +
  scale_colour_manual(values = COL_BT) +
  facet_wrap(~panel, scales = "free_y", ncol = 3) +
  scale_x_continuous(name = "Година", breaks = c(2015, 2017, 2019),
                     labels = scales::label_number(accuracy = 1, big.mark = "")) +
  scale_y_continuous(name = "ln m(x,t)", labels = mk_num(accuracy = 0.01),
                     breaks = function(l) {
                       w <- if (diff(l) < 0.25) 0.05 else 0.1
                       round(seq(ceiling(l[1] / w) * w, floor(l[2] / w) * w, by = w), 2)
                     }) +
  theme_mk()
save_fig(p, "mortality_backtest", height = 3.5)
message("[fig] mortality_backtest")

mj <- jsonlite::fromJSON("results/mortality.json")
cmp <- bt[, .(sex, model, rmse = rmse_logm_60_89, e65err = abs(e65_err_2019))]
cmp[, bic := vapply(seq_len(.N), function(i) mj[[sprintf("bic_eff_%s_%s_B", model[i], sex[i])]], numeric(1))]
cl <- melt(cmp, id.vars = c("sex", "model"), variable.name = "metric", value.name = "value")
cl[, metric := factor(metric, levels = c("rmse", "e65err", "bic"),
                      labels = c("RMSE на ln m, 60-89",
                                 "Апсолутна грешка во e65,\n2019 (год.)",
                                 "BIC, исти ќелии (вар. Б)"))]
cl[, model_lab := factor(MODLAB_SHORT[model], levels = unname(MODLAB_SHORT[c("rh", "cbd", "apc", "lc")]))]
p <- ggplot(cl, aes(value, model_lab, shape = SEXF(sex), colour = SEXF(sex))) +
  geom_point(size = 2.2, fill = "white") + scale_shape_manual(values = c(16, 17)) +
  SCALE_COL_SEX() +
  facet_wrap(~metric, scales = "free_x", strip.position = "bottom") +
  scale_x_continuous(labels = mk_num(), expand = expansion(mult = 0.12),
                     breaks = scales::breaks_extended(n = 4)) +
  labs(x = NULL, y = NULL) + theme_mk() +
  theme(strip.placement = "outside", strip.background = element_blank(),
        strip.text = element_text(size = 8.5), panel.spacing.x = unit(10, "pt"))
save_fig(p, "mortality_model_comparison", height = 2.4)
message("[fig] mortality_model_comparison")

PR <- readRDS("analysis/mortality/projection.rds")
qall <- PR$qall; e65_var <- PR$e65_var; coherence <- PR$coherence; vd <- PR$vd
NSIM <- 5000L
MAIN_MODEL <- "lc"; VAR_MAIN <- "B"
YRS_VD <- c(2050, 2080)

hist_e65 <- lt[age == 65 & year %in% 2003:2023, .(sex, year, e65 = ex)]
fq <- copy(qall)[sex %in% SEXES][, sexf := SEXF(sex)]
fh <- copy(hist_e65)[, sexf := SEXF(sex)]
p <- ggplot(fq, aes(year)) +
  geom_ribbon(aes(ymin = p025, ymax = p975, fill = sexf), alpha = 0.15) +
  geom_ribbon(aes(ymin = p100, ymax = p900, fill = sexf), alpha = 0.25) +
  geom_ribbon(aes(ymin = p250, ymax = p750, fill = sexf), alpha = 0.40) +
  geom_line(aes(y = central, colour = sexf), linewidth = 0.6) +
  SCALE_COL_SEX(guide = "none") + SCALE_FILL_SEX(guide = "none") +
  geom_line(data = fh, aes(year, e65, group = year > 2022),
            linetype = "22", linewidth = 0.45, colour = "grey25", na.rm = TRUE) +
  geom_point(data = fh, aes(year, e65), size = 0.7, colour = "grey25", na.rm = TRUE) +
  geom_text(data = data.table(sexf = SEXF("m"), x = 2004, y = max(fh[sex == "m"]$e65, na.rm = TRUE) + 0.8),
            aes(x, y), hjust = 0, vjust = 0, size = 2.6, colour = "grey20", label = "набљудувано\n(ДЗС)", lineheight = 0.9) +
  geom_text(data = data.table(sexf = SEXF("m"), x = 2079, y = min(fq$p025)), aes(x, y),
            hjust = 1, vjust = 0, size = 2.6, colour = "grey20",
            label = "централна проекција и\nинтервали 50% / 80% / 95%", lineheight = 0.9) +
  facet_wrap(~sexf, nrow = 1) +
  scale_x_year(breaks = seq(2020, 2080, 20)) +
  scale_y_continuous(name = "e65 (години)", labels = mk_num()) +
  theme_mk()
save_fig(p, "mortality_fan_e65", height = 3.1)
message("[fig] mortality_fan_e65")

ev <- copy(e65_var)[model == MAIN_MODEL]
ev[, variant_lab := factor(VARLAB[variant], levels = unname(VARLAB))]
p <- ggplot(ev, aes(year, e65, colour = variant_lab, linetype = variant_lab)) +
  geom_line(linewidth = 0.6) +
  scale_colour_manual(values = unname(COL_VARIANT[c("A", "B", "C")])) +
  geom_line(data = hist_e65[!is.na(e65)],
            aes(year, e65, group = interaction(sex, year > 2022)),
            inherit.aes = FALSE, linewidth = 0.4, colour = "grey30") +
  geom_point(data = hist_e65[!is.na(e65)], aes(year, e65), inherit.aes = FALSE,
             size = 0.8, colour = "grey30") +
  facet_wrap(~SEXF(sex), scales = "free_y") +
  scale_x_year(breaks = seq(2020, 2080, 20)) +
  scale_y_continuous(name = "e65 (години)", labels = mk_num()) +
  theme_mk()
save_fig(p, "mortality_covid_variants", height = 3.3)
message("[fig] mortality_covid_variants")

if (isTRUE(coherence$ok)) {
  ce <- rbind(coherence$paths[, .(sex, year, e65, spec = "Ли-Ли (кохерентен)")],
              e65_var[variant == VAR_MAIN & model == MAIN_MODEL,
                      .(sex, year, e65, spec = "по пол (главен модел)")])
  gp <- dcast(ce, year + spec ~ sex, value.var = "e65")[, .(year, spec, gap = f - m)]
  p <- ggplot(gp, aes(year, gap, linetype = spec)) + geom_line(linewidth = 0.7, colour = "#0072B2") +
    scale_x_year() +
    scale_y_continuous(name = "e65 (жени) − e65 (мажи), години", labels = mk_num()) +
    theme_mk()
  save_fig(p, "mortality_coherence_gap", height = 3.0)
  message("[fig] mortality_coherence_gap")
}

vdl <- rbindlist(lapply(SEXES, function(s) rbindlist(lapply(seq_along(YRS_VD), function(k)
  data.table(sex = s, year = YRS_VD[k],
             src = c("параметри (бутстрап)", "неизвесност на трендот", "процесен шум"),
             v = c(vd[[s]]$v_boot[k], vd[[s]]$v_drift[k], vd[[s]]$v_proc[k]))))))
vdl[, src := factor(src, levels = c("процесен шум", "неизвесност на трендот",
                                    "параметри (бутстрап)"))]
vdr <- rbindlist(lapply(SEXES, function(s) data.table(
  sex = s, year = YRS_VD, v = vd[[s]]$realised)))
p <- ggplot(vdl, aes(factor(year), v, fill = src)) +
  geom_col(colour = "black", linewidth = 0.3, width = 0.6) +
  geom_point(data = vdr, aes(factor(year), v, shape = "реализирана вкупна варијанса"),
             inherit.aes = FALSE, size = 2.2, fill = "white", stroke = 0.6) +
  scale_shape_manual(values = 23) +
  scale_fill_manual(values = c("#F0E442", "#0072B2", "#D55E00")) +
  facet_wrap(~SEXF(sex)) +
  scale_y_continuous(name = expression(paste("Варијанса на e65 (години"^2, ")")),
                     labels = mk_num()) +
  labs(x = "Година") + theme_mk() +
  theme(legend.box = "vertical", legend.spacing.y = unit(1, "pt"),
        legend.key.size = unit(9, "pt")) +
  guides(fill = guide_legend(order = 1), shape = guide_legend(order = 2))
save_fig(p, "mortality_variance_decomposition", height = 3.2)
message("[fig] mortality_variance_decomposition")

par_rh <- fread("analysis/mortality/rh_params.csv")
par_rh[par == "gamma[c]", par := "gamma[t-x]"]
par_rh[, par := factor(par, levels = c("alpha[x]", "beta[x]", "kappa[t]", "gamma[t-x]"))]
p <- ggplot(par_rh, aes(x, value, colour = SEXF(sex), shape = SEXF(sex))) +
  geom_line(na.rm = TRUE, linewidth = 0.45) + geom_point(na.rm = TRUE, size = 0.9) +
  SCALE_COL_SEX() +
  facet_wrap(~par, scales = "free", labeller = label_parsed, nrow = 2) +
  scale_x_continuous(labels = scales::label_number(accuracy = 1, big.mark = "")) +
  scale_y_continuous(labels = mk_num()) +
  labs(x = "Возраст / година / година на раѓање", y = "Вредност") + theme_mk()
save_fig(p, "mortality_params_rh", height = 3.5)
message("[fig] mortality_params_rh")

message("[done] make_figures.R")
