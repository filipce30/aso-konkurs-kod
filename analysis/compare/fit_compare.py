#!/usr/bin/env python3
"""Comparator-country study: 20-year truncation backtest of the Lee-Carter projection and regional context 2003-2023."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "scripts", "clean"))
from lib_jsonstat import load_jsonstat
from lib_lifetable import fit_kannisto_poisson, kannisto_mu

SEED = 2026
OPEN_AGE = 110
E65_AGE = 65
N_BOOT = 500
PATHS_PER_BOOT = 10
OUT_DIR = os.path.join(REPO, "analysis", "compare")
FIG_DIR = os.path.join(REPO, "figures")
RAW_DIR = os.path.join(REPO, "data", "raw", "compare")


def _age_code(a: str):
    if a == "Y_LT1":
        return 0
    if a.startswith("Y") and a[1:].isdigit():
        return int(a[1:])
    return None


def load_geo(geo: str) -> dict:
    out = {}
    tabs = {}
    for slug, key in (("demo_magec", "D"), ("demo_pjan", "P")):
        df, _ = load_jsonstat(os.path.join(RAW_DIR, f"demo_{slug.split('_')[1]}_{geo}.json"))
        df = df[df["sex"].isin(["M", "F"])].copy()
        df["a"] = [_age_code(x) for x in df["age"]]
        df = df[df["a"].notna()].copy()
        df["a"] = df["a"].astype(int)
        df["t"] = df["time"].astype(int)
        tabs[key] = df
    for sx, code in (("m", "M"), ("f", "F")):
        d = {}
        for key in ("D", "P"):
            s = tabs[key]
            s = s[s["sex"] == code]
            d[key] = s.pivot(index="a", columns="t", values="value").sort_index()
        out[sx] = d
    return out


def load_mk_project() -> dict:
    out = {}
    for sx in ("m", "f"):
        D = pd.read_csv(os.path.join(REPO, "data", "clean", f"deaths_Dxt_{sx}.csv"), index_col=0)
        E = pd.read_csv(os.path.join(REPO, "data", "clean", f"exposures_Ext_{sx}.csv"), index_col=0)
        D.columns = [int(c) for c in D.columns]
        E.columns = [int(c) for c in E.columns]
        out[sx] = {"D": D, "E": E}
    return out


def build_DEW(D: pd.DataFrame, exposure, ages, years, zero_years=(), clip=3):
    A, T = len(ages), len(years)
    Dm = np.zeros((A, T))
    Em = np.zeros((A, T))
    W = np.ones((A, T))
    kind, X = exposure
    for j, t in enumerate(years):
        for i, x in enumerate(ages):
            dv = D.at[x, t] if (x in D.index and t in D.columns) else np.nan
            if kind == "pjan":
                p0 = X.at[x, t] if (x in X.index and t in X.columns) else np.nan
                p1 = X.at[x, t + 1] if (x in X.index and (t + 1) in X.columns) else np.nan
                ev = 0.5 * (p0 + p1)
            else:
                ev = X.at[x, t] if (x in X.index and t in X.columns) else np.nan
            if not np.isfinite(dv) or not np.isfinite(ev) or ev <= 0:
                W[i, j] = 0.0
                Dm[i, j] = 0.0
                Em[i, j] = ev if np.isfinite(ev) and ev > 0 else 1.0
            else:
                Dm[i, j] = dv
                Em[i, j] = ev
    for t in zero_years:
        if t in years:
            W[:, years.index(t)] = 0.0
            Dm[:, years.index(t)] = 0.0
    if clip and clip > 0:
        coh = np.array([[t - x for t in years] for x in ages])
        uniq = sorted(set(coh.ravel().tolist()))
        bad = np.isin(coh, uniq[:clip] + uniq[-clip:])
        W[bad] = 0.0
        Dm[bad] = 0.0
    return Dm, Em, W


def _normalise(alpha, beta, kappa):
    c1 = beta.sum()
    beta = beta / c1
    kappa = kappa * c1
    kb = kappa.mean()
    kappa = kappa - kb
    alpha = alpha + beta * kb
    return alpha, beta, kappa


def _dev(D, Dh, W):
    with np.errstate(divide="ignore", invalid="ignore"):
        term = np.where(D > 0, D * np.log(np.where(D > 0, D / Dh, 1.0)), 0.0)
    return 2.0 * np.sum(W * (term - (D - Dh)))


def fit_lc(D, E, W, tol=1e-10, maxit=2000):
    A, T = D.shape
    with np.errstate(divide="ignore", invalid="ignore"):
        lm = np.log(np.where((D > 0) & (W > 0), D / E, np.nan))
    alpha = np.array([np.nanmean(lm[i][W[i] > 0]) if np.any(W[i] > 0) else 0.0
                      for i in range(A)])
    Z = np.where(np.isfinite(lm), lm - alpha[:, None], 0.0)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    beta = U[:, 0] * (1.0 if U[:, 0].sum() >= 0 else -1.0)
    kappa = S[0] * Vt[0] * (1.0 if U[:, 0].sum() >= 0 else -1.0)
    alpha, beta, kappa = _normalise(alpha, beta, kappa)

    prev = np.inf
    for it in range(1, maxit + 1):
        Dh = E * np.exp(alpha[:, None] + np.outer(beta, kappa))
        num = np.sum(W * (D - Dh), axis=1)
        den = np.sum(W * Dh, axis=1)
        alpha = alpha + np.where(den > 0, num / np.maximum(den, 1e-300), 0.0)

        Dh = E * np.exp(alpha[:, None] + np.outer(beta, kappa))
        num = np.sum(W * (D - Dh) * kappa[None, :], axis=1)
        den = np.sum(W * Dh * (kappa ** 2)[None, :], axis=1)
        beta = beta + np.where(den > 0, num / np.maximum(den, 1e-300), 0.0)

        Dh = E * np.exp(alpha[:, None] + np.outer(beta, kappa))
        num = np.sum(W * (D - Dh) * beta[:, None], axis=0)
        den = np.sum(W * Dh * (beta ** 2)[:, None], axis=0)
        kappa = kappa + np.where(den > 0, num / np.maximum(den, 1e-300), 0.0)

        alpha, beta, kappa = _normalise(alpha, beta, kappa)
        Dh = E * np.exp(alpha[:, None] + np.outer(beta, kappa))
        dv = _dev(D, Dh, W)
        if abs(prev - dv) < tol:
            break
        prev = dv
    Dh = E * np.exp(alpha[:, None] + np.outer(beta, kappa))
    ll = np.sum(W * (D * np.log(np.maximum(Dh, 1e-300)) - Dh))
    return alpha, beta, kappa, float(ll), it


def ma3(b):
    out = b.copy()
    out[1:-1] = (b[:-2] + b[1:-1] + b[2:]) / 3.0
    return out


def refit_kappa(D, E, W, alpha, beta, k0, tol=1e-12, maxit=200):
    kappa = k0.copy()
    for _ in range(maxit):
        Dh = E * np.exp(alpha[:, None] + np.outer(beta, kappa))
        num = np.sum(W * (D - Dh) * beta[:, None], axis=0)
        den = np.sum(W * Dh * (beta ** 2)[:, None], axis=0)
        step = np.where(den > 0, num / np.maximum(den, 1e-300), 0.0)
        kappa = kappa + step
        if np.max(np.abs(step)) < tol:
            break
    kb = kappa.mean()
    return alpha + beta * kb, kappa - kb


def fit_lc_smoothed(D, E, W):
    a, b, k, ll, it = fit_lc(D, E, W)
    bs = ma3(b)
    bs = bs / bs.sum()
    a2, k2 = refit_kappa(D, E, W, a, bs, k)
    Dh = E * np.exp(a2[:, None] + np.outer(bs, k2))
    ll2 = float(np.sum(W * (D * np.log(np.maximum(Dh, 1e-300)) - Dh)))
    return dict(alpha=a2, beta=bs, kappa=k2, loglik=ll2, loglik_raw=ll,
                alpha_raw=a, beta_raw=b, kappa_raw=k, n_iter=it)


def gap_aware_drift(kappa, years):
    ok = np.isfinite(kappa)
    k = np.asarray(kappa)[ok]
    t = np.asarray(years, dtype=float)[ok]
    dk = np.diff(k)
    dt = np.diff(t)
    span = t[-1] - t[0]
    N = len(dk)
    mu = (k[-1] - k[0]) / span
    s2 = np.sum((dk - mu * dt) ** 2 / dt) / (N - 1)
    sigma = np.sqrt(s2)
    return dict(mu=float(mu), sigma=float(sigma), se=float(sigma / np.sqrt(span)),
                span=float(span), n_incr=int(N), df=int(N - 1),
                k_last=float(k[-1]), t_last=float(t[-1]))


def trend_stationary(kappa, years):
    ok = np.isfinite(kappa)
    k = np.asarray(kappa)[ok]
    t = np.asarray(years, dtype=float)[ok]
    X = np.column_stack([np.ones_like(t), t])
    XtXi = np.linalg.inv(X.T @ X)
    coef = XtXi @ X.T @ k
    u = k - X @ coef
    num = float(np.sum(u[1:] * u[:-1]))
    den = float(np.sum(u[:-1] ** 2))
    phi = num / den if den > 0 else 0.0
    phi = float(np.clip(phi, -0.99, 0.99))
    e = u[1:] - phi * u[:-1]
    s2e = float(np.sum(e ** 2) / max(len(e) - 1, 1))
    s2u = s2e / (1.0 - phi ** 2)
    lag = np.abs(t[:, None] - t[None, :])
    Omega = s2u * phi ** lag
    V = XtXi @ X.T @ Omega @ X @ XtXi
    return dict(a=float(coef[0]), b=float(coef[1]), phi=phi,
                sigma_e=float(np.sqrt(s2e)), sigma_u=float(np.sqrt(s2u)),
                V=V, u_last=float(u[-1]), t_last=float(t[-1]),
                se_b=float(np.sqrt(V[1, 1])))


def variance_ratios(kappa, years, lags=(2, 4, 8)):
    ok = np.isfinite(kappa)
    k = np.asarray(kappa)[ok]
    d1 = np.diff(k)
    v1 = float(np.var(d1, ddof=1))
    out = {}
    for q in lags:
        if len(k) <= q:
            out[q] = np.nan
            continue
        dq = k[q:] - k[:-q]
        out[q] = float(np.var(dq, ddof=1) / (q * v1)) if v1 > 0 else np.nan
    return out


def kannisto_ols_logit(logm, ages, slope_lo=-np.inf, slope_hi=np.inf):
    m = np.clip(np.exp(logm), 1e-12, 1.0 - 1e-6)
    y = np.log(m / (1.0 - m))
    x = np.asarray(ages, dtype=float)
    xbar = x.mean()
    xc = x - xbar
    sxx = float(np.sum(xc ** 2))
    b = np.sum(y * xc, axis=-1) / sxx
    wins = (b < slope_lo) | (b > slope_hi)
    b = np.clip(b, slope_lo, slope_hi)
    a = np.mean(y, axis=-1) - b * xbar
    return a, b, wins


def e65_from_qx(qx, m_open):
    n = qx.shape[-1]
    surv = np.cumprod(1.0 - qx[..., :-1], axis=-1)
    lx = np.concatenate([np.ones(qx.shape[:-1] + (1,)), surv], axis=-1)
    dx = lx[..., :-1] - lx[..., 1:]
    Lx = lx[..., 1:] + 0.5 * dx
    L_open = lx[..., -1] / np.maximum(m_open, 1e-12)
    T65 = np.sum(Lx, axis=-1) + L_open
    return T65 / lx[..., 0]


def _pav_increasing(y):
    v = list(y)
    w = [1.0] * len(v)
    i = 0
    while i < len(v) - 1:
        if v[i] > v[i + 1] + 1e-15:
            tot = v[i] * w[i] + v[i + 1] * w[i + 1]
            ww = w[i] + w[i + 1]
            v[i] = tot / ww
            w[i] = ww
            del v[i + 1], w[i + 1]
            while i > 0 and v[i - 1] > v[i] + 1e-15:
                tot = v[i - 1] * w[i - 1] + v[i] * w[i]
                ww = w[i - 1] + w[i]
                v[i - 1] = tot / ww
                w[i - 1] = ww
                del v[i], w[i]
                i -= 1
        else:
            i += 1
    out = []
    for val, ww in zip(v, w):
        out.extend([val] * int(round(ww)))
    return np.array(out)


def isotonic_logqx(qx):
    lq = np.log(np.maximum(qx, 1e-300))
    bad = np.any(np.diff(lq, axis=-1) < -1e-12, axis=-1)
    idx = np.flatnonzero(bad)
    for r in idx:
        lq[r] = _pav_increasing(lq[r])
    return np.exp(lq), int(len(idx))


def surface_to_e65(logm_fit, fit_ages, kan_ages, slope_lo, slope_hi, iso=True):
    fit_ages = np.asarray(fit_ages)
    kidx = [int(np.flatnonzero(fit_ages == a)[0]) for a in kan_ages]
    a_k, b_w, wins = kannisto_ols_logit(logm_fit[..., kidx], kan_ages,
                                        slope_lo, slope_hi)
    kan_hi = int(max(kan_ages))
    ext = np.arange(kan_hi + 1, OPEN_AGE + 1)
    lin = a_k[..., None] + b_w[..., None] * ext[None, :]
    m_ext = 1.0 / (1.0 + np.exp(-lin))
    lo_idx = [int(np.flatnonzero(fit_ages == a)[0])
              for a in range(E65_AGE, kan_hi + 1)]
    m_low = np.exp(logm_fit[..., lo_idx])
    m_all = np.concatenate([m_low, m_ext], axis=-1)
    shp = m_all.shape
    flat = m_all.reshape(-1, shp[-1])
    qx = flat[:, :-1] / (1.0 + 0.5 * flat[:, :-1])
    if iso:
        qx, n_iso = isotonic_logqx(qx)
    else:
        n_iso = 0
    qx = np.clip(qx, 1e-12, 1.0)
    qx_full = np.concatenate([qx, np.ones((flat.shape[0], 1))], axis=1)
    e = e65_from_qx(qx_full, flat[:, -1])
    return e.reshape(shp[:-1]), float(np.mean(wins)), n_iso, flat.shape[0]


def observed_e65(D: pd.DataFrame, Eser: pd.Series, year, kan_lo, kan_hi):
    ages_k = list(range(kan_lo, kan_hi + 1))
    Dk = np.array([D.at[x, year] if x in D.index else np.nan for x in ages_k], dtype=float)
    Ek = np.array([Eser.get(x, np.nan) for x in ages_k], dtype=float)
    al, bk, conv, nobs = fit_kannisto_poisson(ages_k, Dk, Ek)
    if not np.isfinite(bk):
        return np.nan, np.nan, nobs
    ages_lo = list(range(E65_AGE, kan_lo))
    m_lo = np.array([D.at[x, year] / Eser[x] for x in ages_lo], dtype=float)
    m_hi = kannisto_mu(al, bk, range(kan_lo, OPEN_AGE + 1))
    m = np.concatenate([m_lo, m_hi])
    qx = m[:-1] / (1.0 + 0.5 * m[:-1])
    qx = np.clip(qx, 1e-12, 1.0)
    qx = np.concatenate([qx, [1.0]])
    e = e65_from_qx(qx[None, :], np.array([m[-1]]))[0]
    return float(e), float(bk), nobs


def observed_slope_range(D: pd.DataFrame, P: pd.DataFrame, years, kan_ages):
    bs, ses = [], []
    for t in years:
        m = []
        for x in kan_ages:
            d = D.at[x, t] if (x in D.index and t in D.columns) else np.nan
            p0 = P.at[x, t] if (x in P.index and t in P.columns) else np.nan
            p1 = P.at[x, t + 1] if (x in P.index and (t + 1) in P.columns) else np.nan
            e = 0.5 * (p0 + p1)
            m.append(d / e if (np.isfinite(d) and d > 0 and np.isfinite(e) and e > 0)
                     else np.nan)
        m = np.array(m, dtype=float)
        if not np.all(np.isfinite(m)):
            continue
        y = np.log(m / (1.0 - m))
        x = np.asarray(kan_ages, dtype=float)
        xc = x - x.mean()
        sxx = float(np.sum(xc ** 2))
        b = float(np.sum(y * xc) / sxx)
        a = float(np.mean(y) - b * x.mean())
        rss = float(np.sum((y - a - b * x) ** 2))
        ses.append(np.sqrt(rss / (len(x) - 2) / sxx))
        bs.append(b)
    if len(bs) < 5:
        raise ValueError("observed_slope_range: fewer than 5 usable annual slopes")
    return float(np.min(bs)), float(np.max(bs)), float(np.mean(ses)), len(bs)


def exposure_series(P: pd.DataFrame, t: int, ages) -> pd.Series:
    v = {}
    for x in ages:
        p0 = P.at[x, t] if (x in P.index and t in P.columns) else np.nan
        p1 = P.at[x, t + 1] if (x in P.index and (t + 1) in P.columns) else np.nan
        v[x] = 0.5 * (p0 + p1)
    return pd.Series(v)


def bootstrap_fits(D, E, W, fit, rng, n_boot):
    Dh = E * np.exp(fit["alpha"][:, None] + np.outer(fit["beta"], fit["kappa"]))
    reps = []
    for _ in range(n_boot):
        Db = rng.poisson(np.maximum(Dh, 0.0)).astype(float)
        Db = np.where(W > 0, Db, 0.0)
        try:
            fb = fit_lc_smoothed(Db, E, W)
        except Exception:
            continue
        reps.append(fb)
    return reps


def simulate_e65(fit, reps, rwd, ts, years_fit, test_years, fit_ages, kan_model,
                 slope_lo, slope_hi, rng, mode, paths_per_boot=PATHS_PER_BOOT):
    H = len(test_years)
    h = np.arange(1, H + 1, dtype=float)
    n_sim = len(reps) * paths_per_boot
    A = len(fit_ages)
    K = np.empty((n_sim, H))
    AL = np.empty((n_sim, A))
    BE = np.empty((n_sim, A))
    for bi, fb in enumerate(reps):
        kb = gap_aware_drift(fb["kappa"], years_fit)
        tb = trend_stationary(fb["kappa"], years_fit)
        k_last_b = fb["kappa"][-1]
        for p in range(paths_per_boot):
            i = bi * paths_per_boot + p
            AL[i] = fb["alpha"]
            BE[i] = fb["beta"]
            if mode == "rwd":
                mu_d = rng.normal(rwd["mu"], rwd["se"])
                eps = rng.normal(0.0, rwd["sigma"], size=H)
                K[i] = k_last_b + h * mu_d + np.cumsum(eps)
            elif mode == "rwd_wide":
                mu_d = rng.normal(kb["mu"], kb["se"])
                eps = rng.normal(0.0, kb["sigma"], size=H)
                K[i] = k_last_b + h * mu_d + np.cumsum(eps)
            elif mode == "ts":
                ad, bd = rng.multivariate_normal([ts["a"], ts["b"]], ts["V"])
                phi = ts["phi"]
                u0 = k_last_b - (ad + bd * ts["t_last"])
                e = rng.normal(0.0, ts["sigma_e"], size=H)
                u = np.empty(H)
                prev = u0
                for j in range(H):
                    prev = phi * prev + e[j]
                    u[j] = prev
                K[i] = ad + bd * (ts["t_last"] + h) + u
            else:
                raise ValueError(mode)
    logm = AL[:, None, :] + BE[:, None, :] * K[:, :, None]
    e, wshare, n_iso, n_rows = surface_to_e65(logm, fit_ages, kan_model,
                                              slope_lo, slope_hi)
    if mode == "ts":
        u0 = fit["kappa"][-1] - (ts["a"] + ts["b"] * ts["t_last"])
        kc = ts["a"] + ts["b"] * (ts["t_last"] + h) + ts["phi"] ** h * u0
    else:
        kc = fit["kappa"][-1] + h * rwd["mu"]
    logm_c = fit["alpha"][None, :] + fit["beta"][None, :] * kc[:, None]
    ec, cw, _, _ = surface_to_e65(logm_c[None, :, :], fit_ages, kan_model,
                                  slope_lo, slope_hi)
    ecn, _, _, _ = surface_to_e65(logm_c[None, :, :], fit_ages, kan_model,
                                  -np.inf, np.inf)
    eci, _, _, _ = surface_to_e65(logm_c[None, :, :], fit_ages, kan_model,
                                  slope_lo, slope_hi, iso=False)
    return dict(e65=e, central=ec[0], central_nowins=ecn[0], central_noiso=eci[0],
                central_winsor=cw, winsor_share=wshare, iso_rows=n_iso,
                n_rows=n_rows, n_sim=n_sim)


def run_backtest(tag, geo, data, cfg, rng, n_boot, res, diag):
    fit_ages = list(range(cfg["fit_lo"], cfg["fit_hi"] + 1))
    years_fit = list(range(cfg["fit_y0"], cfg["fit_y1"] + 1))
    test_years = list(range(cfg["test_y0"], cfg["test_y1"] + 1))
    kan_model = list(range(cfg["fit_hi"] - 9, cfg["fit_hi"] + 1))
    H = len(test_years)
    for sx in ("m", "f"):
        t0 = time.time()
        D, P = data[sx]["D"], data[sx]["P"]
        Dm, Em, W = build_DEW(D, ("pjan", P), fit_ages, years_fit)
        assert np.all(W.sum(axis=0) > 0), f"{tag} {sx}: a whole year is unidentified"
        diag[f"{tag}_{sx}_zero_weight_cells"] = int((W == 0).sum())
        diag[f"{tag}_{sx}_cells"] = int(W.size)
        fit = fit_lc_smoothed(Dm, Em, W)
        rwd = gap_aware_drift(fit["kappa"], years_fit)
        ts = trend_stationary(fit["kappa"], years_fit)
        vr = variance_ratios(fit["kappa"], years_fit)
        s_lo, s_hi, s_se, n_slope = observed_slope_range(D, P, years_fit, kan_model)
        slo, shi = s_lo - 2.0 * s_se, np.inf
        diag[f"{tag}_{cfg['label']}_{sx}_n_annual_slopes"] = n_slope
        diag[f"{tag}_{cfg['label']}_{sx}_kannisto_slope_se_bar"] = s_se
        diag[f"{tag}_{cfg['label']}_{sx}_kannisto_slope_floor"] = float(slo)
        reps = bootstrap_fits(Dm, Em, W, fit, rng, n_boot)
        sims = {m: simulate_e65(fit, reps, rwd, ts, years_fit, test_years,
                                fit_ages, kan_model, slo, shi, rng, m)
                for m in ("rwd", "rwd_wide", "ts")}

        ages_obs = list(range(E65_AGE, cfg["kan_obs_hi"] + 1))
        act = []
        for t in test_years:
            Es = exposure_series(P, t, ages_obs)
            e, bk, nb = observed_e65(D, Es, t, cfg["kan_obs_lo"], cfg["kan_obs_hi"])
            act.append(e)
        act = np.array(act)
        Es0 = exposure_series(P, cfg["fit_y1"], ages_obs)
        e_jump_act, _, _ = observed_e65(D, Es0, cfg["fit_y1"],
                                       cfg["kan_obs_lo"], cfg["kan_obs_hi"])
        logm_j = fit["alpha"] + fit["beta"] * fit["kappa"][-1]
        e_jump_fit, _, _, _ = surface_to_e65(logm_j[None, None, :], fit_ages,
                                            kan_model, slo, shi)

        pre = f"backtest_{tag}_{sx}" if cfg["label"] == "w1" else f"backtest_w2_{tag}_{sx}"
        i10, i20 = 9, H - 1
        covid = [i for i, t in enumerate(test_years) if t in (2020, 2021)]
        keep = [i for i in range(H) if i not in covid]

        res[f"{pre}_e65_{cfg['yr10']}_actual" if cfg["label"] == "w1"
            else f"{pre}_e65_h10_actual"] = float(act[i10])
        res[f"{pre}_e65_{cfg['yr20']}_actual" if cfg["label"] == "w1"
            else f"{pre}_e65_h20_actual"] = float(act[i20])
        for mode, suf in (("rwd", ""), ("ts", "_trendstat"), ("rwd_wide", "_rwdwide")):
            e = sims[mode]["e65"]
            c = sims[mode]["central"]
            lo = np.quantile(e, 0.025, axis=0)
            hi = np.quantile(e, 0.975, axis=0)
            ins = (act >= lo) & (act <= hi)
            for idx, hz in ((i10, "h10"), (i20, "h20")):
                lbl = (f"e65_{cfg['yr10'] if hz == 'h10' else cfg['yr20']}"
                       if cfg["label"] == "w1" else f"e65_{hz}")
                res[f"{pre}_{lbl}_central{suf}"] = float(c[idx])
                res[f"{pre}_{lbl}_p025{suf}"] = float(lo[idx])
                res[f"{pre}_{lbl}_p975{suf}"] = float(hi[idx])
                res[f"{pre}_{lbl}_inside_band{suf}"] = bool(ins[idx])
                res[f"{pre}_abs_err_{'10y' if hz == 'h10' else '20y'}{suf}"] = \
                    float(abs(c[idx] - act[idx]))
            res[f"{pre}_years_inside_of_{H}{suf}"] = int(ins.sum())
            res[f"{pre}_years_inside_of_{len(keep)}_excovid{suf}"] = int(ins[keep].sum())
            res[f"{pre}_band_width_20y{suf}"] = float(hi[i20] - lo[i20])
            res[f"{pre}_band_width_10y{suf}"] = float(hi[i10] - lo[i10])
            cname = {"rwd": "rwd", "ts": "trendstat", "rwd_wide": "rwd_wide"}[mode]
            pfx = "coverage" if cfg["label"] == "w1" else "coverage_w2"
            res[f"{pfx}_{cname}_{tag}_{sx}"] = float(ins.mean())
            res[f"{pfx}_{cname}_excovid_{tag}_{sx}"] = float(ins[keep].mean())
            diag[f"{tag}_{cfg['label']}_{sx}_{cname}_winsor_share"] = sims[mode]["winsor_share"]
            diag[f"{tag}_{cfg['label']}_{sx}_{cname}_iso_rows"] = sims[mode]["iso_rows"]
            diag[f"{tag}_{cfg['label']}_{sx}_{cname}_n_rows"] = sims[mode]["n_rows"]
            diag[f"{tag}_{cfg['label']}_{sx}_{cname}_central_nowins_h20"] = \
                float(sims[mode]["central_nowins"][i20])
            diag[f"{tag}_{cfg['label']}_{sx}_{cname}_central_winsor_share"] = \
                sims[mode]["central_winsor"]
            diag[f"{tag}_{cfg['label']}_{sx}_{cname}_iso_delta_e65_h20"] = float(
                sims[mode]["central"][i20] - sims[mode]["central_noiso"][i20])
        res[f"{pre}_drift"] = rwd["mu"]
        res[f"{pre}_drift_se"] = rwd["se"]
        res[f"{pre}_sigma"] = rwd["sigma"]
        res[f"{pre}_ts_slope"] = ts["b"]
        res[f"{pre}_ts_slope_se"] = ts["se_b"]
        res[f"{pre}_ts_phi"] = ts["phi"]
        res[f"{pre}_vr4"] = vr[4]
        res[f"{pre}_vr8"] = vr[8]
        res[f"{pre}_e65_jumpoff_fitted"] = float(np.ravel(e_jump_fit)[0])
        res[f"{pre}_e65_jumpoff_actual"] = float(e_jump_act)
        res[f"{pre}_e65_jumpoff_bias"] = float(np.ravel(e_jump_fit)[0] - e_jump_act)
        res[f"{pre}_n_sim"] = sims["rwd"]["n_sim"]
        diag[f"{tag}_{cfg['label']}_{sx}_loglik"] = fit["loglik"]
        diag[f"{tag}_{cfg['label']}_{sx}_beta_min"] = float(fit["beta"].min())
        diag[f"{tag}_{cfg['label']}_{sx}_beta_neg_share"] = float(
            (fit["beta"] < 0).mean())
        diag[f"{tag}_{cfg['label']}_{sx}_kannisto_slope_obs_lo"] = s_lo
        diag[f"{tag}_{cfg['label']}_{sx}_kannisto_slope_obs_hi"] = s_hi
        diag[f"{tag}_{cfg['label']}_{sx}_n_boot_ok"] = len(reps)
        cov_key = f"{pfx}_rwd_{tag}_{sx}"
        cov_ts_key = f"{pfx}_trendstat_{tag}_{sx}"
        print(f"  {tag} {cfg['label']} {sx}: mu={rwd['mu']:+.4f} se={rwd['se']:.4f} "
              f"sig={rwd['sigma']:.4f} vr4={vr[4]:.3f} phi={ts['phi']:+.3f} "
              f"act20={act[i20]:.3f} cen20={sims['rwd']['central'][i20]:.3f} "
              f"cov_rwd={res[cov_key]:.2f} cov_ts={res[cov_ts_key]:.2f} "
              f"[{time.time()-t0:.0f}s]")
        rows = []
        for mode in ("rwd", "ts"):
            e = sims[mode]["e65"]
            lo = np.quantile(e, 0.025, axis=0)
            hi = np.quantile(e, 0.975, axis=0)
            p25 = np.quantile(e, 0.25, axis=0)
            p75 = np.quantile(e, 0.75, axis=0)
            for j, t in enumerate(test_years):
                rows.append(dict(geo=tag, window=cfg["label"], sex=sx, mode=mode,
                                 year=t, actual=act[j],
                                 central=sims[mode]["central"][j],
                                 p025=lo[j], p250=p25[j], p750=p75[j], p975=hi[j]))
        diag.setdefault("_paths", []).extend(rows)
        hist = []
        for j, t in enumerate(years_fit):
            Es = exposure_series(P, t, ages_obs)
            e, _, _ = observed_e65(D, Es, t, cfg["kan_obs_lo"], cfg["kan_obs_hi"])
            hist.append(dict(geo=tag, window=cfg["label"], sex=sx, year=t, actual=e))
        diag.setdefault("_hist", []).extend(hist)


CONTEXT_GEOS = ["MK", "BG", "EE", "SI", "HR", "LT"]
CONTEXT_Y0, CONTEXT_Y1 = 2003, 2023
COVID_ZERO = (2020, 2021, 2022)


def improvement_rate(Dm, Em, W, years):
    keep = [j for j in range(len(years)) if W[:, j].sum() > 0]
    y = []
    for j in keep:
        ok = W[:, j] > 0
        with np.errstate(divide="ignore"):
            y.append(float(np.mean(np.log(Dm[ok, j] / Em[ok, j]))))
    t = np.array([years[j] for j in keep], dtype=float)
    y = np.array(y)
    X = np.column_stack([np.ones_like(t), t])
    XtXi = np.linalg.inv(X.T @ X)
    coef = XtXi @ X.T @ y
    r = y - X @ coef
    s2 = float(r @ r / (len(t) - 2))
    se = float(np.sqrt(s2 * XtXi[1, 1]))
    return -float(coef[1]), se, len(t)


def run_context(res, diag):
    ages = list(range(55, 90))
    years = list(range(CONTEXT_Y0, CONTEXT_Y1 + 1))
    rows = []
    mk = load_mk_project()
    lt_mk = pd.read_csv(os.path.join(REPO, "data", "clean", "lifetables_period.csv"))
    for geo in CONTEXT_GEOS:
        data = mk if geo == "MK" else load_geo(geo)
        for sx in ("m", "f"):
            if geo == "MK":
                D, expo = data[sx]["D"], ("central", data[sx]["E"])
                P = None
            else:
                D, P = data[sx]["D"], data[sx]["P"]
                expo = ("pjan", P)
            Dm, Em, W = build_DEW(D, expo, ages, years, zero_years=COVID_ZERO)
            assert np.all(W.sum(axis=0)[[years.index(t) for t in years
                                        if t not in COVID_ZERO]] > 0)
            k = fit_lc_smoothed(Dm, Em, W)
            kap = k["kappa"].copy()
            for t in COVID_ZERO:
                kap[years.index(t)] = np.nan
            rwd = gap_aware_drift(kap, years)
            ir, ir_se, n_ir = improvement_rate(Dm, Em, W, years)
            if geo == "MK":
                e03 = float(lt_mk[(lt_mk.year == 2003) & (lt_mk.sex == sx)
                                  & (lt_mk.age == 65)].ex.iloc[0])
                e23 = float(lt_mk[(lt_mk.year == 2023) & (lt_mk.sex == sx)
                                  & (lt_mk.age == 65)].ex.iloc[0])
            else:
                ao = list(range(E65_AGE, 100))
                e03 = observed_e65(D, exposure_series(P, 2003, ao), 2003, 80, 99)[0]
                e23 = observed_e65(D, exposure_series(P, 2023, ao), 2023, 80, 99)[0]
            g = geo.lower()
            res[f"e65_2003_{g}_{sx}"] = e03
            res[f"e65_2023_{g}_{sx}"] = e23
            res[f"e65_gain_2003_2023_{g}_{sx}"] = e23 - e03
            res[f"drift_{g}_{sx}"] = rwd["mu"]
            res[f"drift_se_{g}_{sx}"] = rwd["se"]
            res[f"drift_tstat_{g}_{sx}"] = rwd["mu"] / rwd["se"]
            res[f"sigma_kt_{g}_{sx}"] = rwd["sigma"]
            res[f"improve_rate_{g}_{sx}"] = ir
            res[f"improve_rate_se_{g}_{sx}"] = ir_se
            vr = variance_ratios(k["kappa"][:17], years[:17])
            res[f"vr4_{g}_{sx}"] = vr[4]
            res[f"vr8_{g}_{sx}"] = vr[8]
            diag[f"context_{g}_{sx}_zero_weight_cells"] = int((W == 0).sum())
            diag[f"context_{g}_{sx}_n_years_improve"] = n_ir
            rows.append(dict(geo=geo, sex=sx, e65_2003=e03, e65_2023=e23,
                             gain=e23 - e03, drift=rwd["mu"], drift_se=rwd["se"],
                             sigma=rwd["sigma"], improve_rate=ir,
                             improve_rate_se=ir_se, vr4=vr[4], vr8=vr[8]))
            print(f"  ctx {geo} {sx}: e65 {e03:.2f}->{e23:.2f} mu={rwd['mu']:+.4f}"
                  f" se={rwd['se']:.4f} impr={ir*100:.2f}%/y (se {ir_se*100:.2f})")
    with open(os.path.join(REPO, "results", "mortality.json"), encoding="utf-8") as f:
        mj = json.load(f)
    for sx in ("m", "f"):
        res[f"mk_drift_repro_abs_diff_{sx}"] = abs(
            res[f"drift_mk_{sx}"] - mj[f"drift_kt_{sx}_B"])
        res[f"mk_drift_se_repro_abs_diff_{sx}"] = abs(
            res[f"drift_se_mk_{sx}"] - mj[f"drift_se_kt_{sx}_B"])
        res[f"mk_sigma_repro_abs_diff_{sx}"] = abs(
            res[f"sigma_kt_mk_{sx}"] - mj[f"sigma_kt_{sx}_B"])
    res["mk_repro_max_abs_diff"] = max(
        res[f"mk_{k}_repro_abs_diff_{sx}"] for k in ("drift", "drift_se", "sigma")
        for sx in ("m", "f"))
    res["mk_repro_ok"] = bool(res["mk_repro_max_abs_diff"] < 1e-5)
    print(f"  MK reproduction of results/mortality.json: max |diff| = "
          f"{res['mk_repro_max_abs_diff']:.2e} -> {res['mk_repro_ok']}")

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, "context_region.csv"), index=False)
    for sx in ("m", "f"):
        oth = df[(df.sex == sx) & (df.geo != "MK")]
        mkr = df[(df.sex == sx) & (df.geo == "MK")].iloc[0]
        res[f"region_improve_rate_median_{sx}"] = float(oth.improve_rate.median())
        res[f"region_improve_rate_min_{sx}"] = float(oth.improve_rate.min())
        res[f"region_improve_rate_max_{sx}"] = float(oth.improve_rate.max())
        res[f"mk_improve_rate_rank_of_6_{sx}"] = int(
            (df[df.sex == sx].improve_rate > mkr.improve_rate).sum() + 1)
        res[f"region_drift_se_median_{sx}"] = float(oth.drift_se.median())
        res[f"mk_drift_se_ratio_to_region_median_{sx}"] = float(
            mkr.drift_se / oth.drift_se.median())
        res[f"mk_drift_se_rank_of_6_{sx}"] = int(
            (df[df.sex == sx].drift_se > mkr.drift_se).sum() + 1)
    return df


def convention_check(res, diag):
    df, lab = load_jsonstat(os.path.join(REPO, "data", "raw", "makstat",
                                         "population_revised_1jan_2003_2021.json"))
    acol, ycol, scol = "Восраст", "Година", "Пол"
    df = df.copy()
    df["age"] = [lab[acol][c] for c in df[acol]]
    df["year"] = [int(lab[ycol][c]) for c in df[ycol]]
    df["sexl"] = [lab[scol][c] for c in df[scol]]
    df = df[df["age"].str.fullmatch(r"\d+")]
    df["age"] = df["age"].astype(int)
    mk = load_mk_project()
    deltas = []
    for sx, lbl in (("m", "Мажи"), ("f", "Жени")):
        P = (df[df.sexl == lbl].pivot(index="age", columns="year", values="value")
             .sort_index())
        D = mk[sx]["D"]
        Emid = mk[sx]["E"]
        for t in range(2003, 2020):
            ao = list(range(E65_AGE, 100))
            e_mid = observed_e65(D, Emid[t].reindex(ao), t, 80, 99)[0]
            e_jan = observed_e65(D, exposure_series(P, t, ao), t, 80, 99)[0]
            deltas.append(dict(sex=sx, year=t, e65_midyear=e_mid,
                               e65_janavg=e_jan, delta=e_jan - e_mid))
    dd = pd.DataFrame(deltas)
    dd.to_csv(os.path.join(OUT_DIR, "mk_exposure_convention.csv"), index=False)
    res["mk_exposure_convention_mean_abs_delta_e65"] = float(dd.delta.abs().mean())
    res["mk_exposure_convention_max_abs_delta_e65"] = float(dd.delta.abs().max())
    for sx in ("m", "f"):
        s = dd[dd.sex == sx]
        res[f"mk_exposure_convention_mean_abs_delta_e65_{sx}"] = float(s.delta.abs().mean())
        res[f"mk_exposure_convention_mean_signed_delta_e65_{sx}"] = float(s.delta.mean())
    res["mk_exposure_convention_years"] = "2003-2019"
    diag["convention_n_cells"] = len(dd)
    print(f"  convention: mean |de65| = {dd.delta.abs().mean():.4f} y, "
          f"max {dd.delta.abs().max():.4f} y")
    return dd


OKABE = dict(m="#0072B2", f="#D55E00", grey="#555555", green="#009E73",
             orange="#E69F00", purple="#CC79A7")
SEXMK = dict(m="мажи", f="жени")
GEOMK = dict(MK="Северна Македонија", BG="Бугарија", EE="Естонија",
             SI="Словенија", HR="Хрватска", LT="Литванија")
TAGMK = dict(bg="Бугарија", ee="Естонија", bg84="Бугарија (55-84)")


def _mk_ticks():
    import matplotlib.ticker as mt

    class MkTickFormatter(mt.Formatter):
        def __call__(self, v, pos=None):
            locs = list(getattr(self, "locs", [])) or [v]
            nd = next((d for d in range(5)
                       if all(abs(round(x, d) - x) < 1e-9 * max(1.0, abs(x)) for x in locs)), 4)
            return f"{v:,.{nd}f}".replace(",", " ").replace(".", ",").replace("-", "\u2212")
    return MkTickFormatter()


def _mk_rc(plt):
    plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
                         "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5})


def _mk_comma(ax, axis="both", nd=1):
    import matplotlib.ticker as mt
    fmt = _mk_ticks()
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(fmt)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(mt.FuncFormatter(lambda v, p: f"{int(v):d}"))


def fig_backtest(tag, paths, hist, cfg, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _mk_rc(plt)
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.5), sharex=True, layout="constrained")
    for ax, sx in zip(axes, ("m", "f")):
        h = hist[(hist.geo == tag) & (hist.window == cfg["label"]) & (hist.sex == sx)]
        p = paths[(paths.geo == tag) & (paths.window == cfg["label"]) & (paths.sex == sx)]
        pr = p[p["mode"] == "rwd"].sort_values("year")
        pt = p[p["mode"] == "ts"].sort_values("year")
        ax.plot(h.year, h.actual, color=OKABE["grey"], lw=1.1, marker="o", ms=2,
                label="реализирано (период на оценување)")
        ax.fill_between(pr.year, pr.p025, pr.p975, color=OKABE[sx], alpha=0.16,
                        lw=0, label="95% интервал: случајно талкање со наклон")
        ax.fill_between(pr.year, pr.p250, pr.p750, color=OKABE[sx], alpha=0.26, lw=0,
                        label="50% интервал: случајно талкање со наклон")
        ax.plot(pt.year, pt.p025, color=OKABE["green"], lw=1.0, ls=(0, (4, 2)),
                label="95% интервал: стационарен тренд")
        ax.plot(pt.year, pt.p975, color=OKABE["green"], lw=1.0, ls=(0, (4, 2)))
        ax.plot(pr.year, pr.central, color=OKABE[sx], lw=1.4, ls=(0, (1, 1.2)),
                label="централна проекција (случајно талкање)")
        jy = list(h.year)[-1:] + list(pr.year)
        ja = list(h.actual)[-1:] + list(pr.actual)
        ax.plot(jy, ja, color="black", lw=1.4, marker="s", ms=2.6,
                label="реализирано (период на проверка)")
        ax.axvline(cfg["fit_y1"], color="black", lw=0.7, alpha=0.5)
        if 2020 in list(pr.year):
            ax.axvspan(2019.5, 2021.5, color="black", alpha=0.05, lw=0)
        ax.set_title(SEXMK[sx].capitalize())
        ax.set_xlabel("Година")
        ax.grid(alpha=0.22, lw=0.5)
        _mk_comma(ax, nd=1)
        ax.set_xticks([y for y in range(cfg["fit_y0"], cfg["test_y1"] + 1) if y % 10 == 0])
    axes[0].set_ylabel("e₆₅ (години)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncol=2,
               frameon=False)
    base = os.path.join(FIG_DIR, f"compare_backtest_{tag}"
                        + ("" if cfg["label"] == "w1" else "_w2"))
    fig.savefig(base + ".png", dpi=300)
    fig.savefig(base + ".svg")
    plt.close(fig)
    return base


def fig_region(df):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    order = ["MK", "BG", "EE", "LT", "SI", "HR"]
    _mk_rc(plt)
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.3), layout="constrained")
    ax = axes[0]
    ypos = np.arange(len(order))
    for k, sx in enumerate(("m", "f")):
        off = -0.17 if sx == "m" else 0.17
        e0 = [float(df[(df.geo == g) & (df.sex == sx)].e65_2003.iloc[0]) for g in order]
        e1 = [float(df[(df.geo == g) & (df.sex == sx)].e65_2023.iloc[0]) for g in order]
        for i in range(len(order)):
            ax.plot([e0[i], e1[i]], [ypos[i] + off] * 2, color=OKABE[sx], lw=2.0,
                    alpha=0.55, solid_capstyle="round", zorder=1)
        ax.scatter(e0, ypos + off, s=16, facecolor="white", edgecolor=OKABE[sx],
                   zorder=3, label=f"{SEXMK[sx]}, 2003")
        ax.scatter(e1, ypos + off, s=18, color=OKABE[sx], zorder=3,
                   label=f"{SEXMK[sx]}, 2023")
    ax.set_yticks(ypos)
    ax.set_yticklabels([GEOMK[g] for g in order])
    ax.invert_yaxis()
    ax.set_xlabel("e₆₅ (години)")
    ax.set_title("e₆₅ во 2003 и 2023 година")
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.xaxis.set_major_formatter(_mk_ticks())
    ax.set_xlim(right=float(df.e65_2023.max()) + 3.0)
    ax.legend(frameon=False, loc="upper right", handletextpad=0.2, borderaxespad=0.2)
    ax.axhspan(-0.5, 0.5, color="black", alpha=0.045, lw=0)

    ax = axes[1]
    for sx in ("m", "f"):
        off = -0.17 if sx == "m" else 0.17
        r = [float(df[(df.geo == g) & (df.sex == sx)].improve_rate.iloc[0]) * 100 for g in order]
        s = [float(df[(df.geo == g) & (df.sex == sx)].improve_rate_se.iloc[0]) * 100 for g in order]
        ax.errorbar(r, ypos + off, xerr=[1.96 * v for v in s], fmt="o", ms=5,
                    color=OKABE[sx], ecolor=OKABE[sx], elinewidth=1.2, capsize=2.6,
                    label=SEXMK[sx])
    ax.axvline(0, color="black", lw=0.7, alpha=0.6)
    ax.set_yticks(ypos)
    ax.set_yticklabels([])
    ax.invert_yaxis()
    ax.set_xlabel("годишна стапка на подобрување\nна смртноста, 55-89 г. (%)")
    ax.set_title("Подобрување, 95% интервал")
    ax.grid(axis="x", alpha=0.22, lw=0.5)
    ax.xaxis.set_major_formatter(_mk_ticks())
    ax.legend(frameon=False, loc="lower right")
    ax.axhspan(-0.5, 0.5, color="black", alpha=0.045, lw=0)
    base = os.path.join(FIG_DIR, "compare_region_e65")
    fig.savefig(base + ".png", dpi=300)
    fig.savefig(base + ".svg")
    plt.close(fig)
    return base


CFGS = [
    dict(tag="bg", geo="BG", fit_lo=55, fit_hi=89, fit_y0=1984, fit_y1=2003,
         test_y0=2004, test_y1=2023, kan_obs_lo=80, kan_obs_hi=99,
         label="w1", yr10=2013, yr20=2023),
    dict(tag="ee", geo="EE", fit_lo=55, fit_hi=84, fit_y0=1984, fit_y1=2003,
         test_y0=2004, test_y1=2023, kan_obs_lo=75, kan_obs_hi=84,
         label="w1", yr10=2013, yr20=2023),
    dict(tag="bg", geo="BG", fit_lo=55, fit_hi=89, fit_y0=1974, fit_y1=1993,
         test_y0=1994, test_y1=2013, kan_obs_lo=80, kan_obs_hi=99,
         label="w2", yr10=2003, yr20=2013),
    dict(tag="ee", geo="EE", fit_lo=55, fit_hi=84, fit_y0=1974, fit_y1=1993,
         test_y0=1994, test_y1=2013, kan_obs_lo=75, kan_obs_hi=84,
         label="w2", yr10=2003, yr20=2013),
    dict(tag="bg84", geo="BG", fit_lo=55, fit_hi=84, fit_y0=1984, fit_y1=2003,
         test_y0=2004, test_y1=2023, kan_obs_lo=75, kan_obs_hi=84,
         label="w1", yr10=2013, yr20=2023),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true",
                    help="20 bootstrap replicates instead of 500 (quick test)")
    ap.add_argument("--only", default="", help="comma list of run tags to do")
    ap.add_argument("--figures-only", action="store_true",
                    help="redraw the figures from the saved analysis/compare/*.csv, no refit")
    args = ap.parse_args()
    if args.figures_only:
        paths = pd.read_csv(os.path.join(OUT_DIR, "backtest_paths.csv"))
        hist = pd.read_csv(os.path.join(OUT_DIR, "backtest_hist.csv"))
        for cfg in CFGS:
            if cfg["tag"] == "bg84":
                continue
            sub = paths[(paths.geo == cfg["tag"]) & (paths.window == cfg["label"])]
            if len(sub):
                print("  fig:", fig_backtest(cfg["tag"], paths, hist, cfg, {}))
        df = pd.read_csv(os.path.join(OUT_DIR, "context_region.csv"))
        print("  fig:", fig_region(df))
        return
    n_boot = 20 if args.quick else N_BOOT
    np.random.seed(SEED)
    rng = np.random.default_rng(SEED)
    res, diag = {}, {}
    res["seed"] = SEED
    res["n_boot"] = n_boot
    res["paths_per_boot"] = PATHS_PER_BOOT
    res["exposure_convention_compare"] = ("average of 1 January populations for t "
                                          "and t+1 (Eurostat demo_pjan)")
    res["exposure_convention_mk_project"] = "MAKSTAT revised mid-year (30 June) population"

    print("Task 1 - truncation backtest")
    cache = {}
    for cfg in CFGS:
        if args.only and f"{cfg['tag']}_{cfg['label']}" not in args.only.split(","):
            continue
        if cfg["geo"] not in cache:
            cache[cfg["geo"]] = load_geo(cfg["geo"])
        res[f"ages_fit_lo_{cfg['tag']}"] = cfg["fit_lo"]
        res[f"ages_fit_hi_{cfg['tag']}"] = cfg["fit_hi"]
        res[f"fit_window_{cfg['tag']}_{cfg['label']}"] = f"{cfg['fit_y0']}-{cfg['fit_y1']}"
        res[f"test_window_{cfg['tag']}_{cfg['label']}"] = f"{cfg['test_y0']}-{cfg['test_y1']}"
        res[f"kannisto_obs_window_{cfg['tag']}"] = f"{cfg['kan_obs_lo']}-{cfg['kan_obs_hi']}"
        run_backtest(cfg["tag"], cfg["geo"], cache[cfg["geo"]], cfg, rng, n_boot,
                     res, diag)

    paths = pd.DataFrame(diag.pop("_paths", []))
    hist = pd.DataFrame(diag.pop("_hist", []))
    if len(paths):
        paths.to_csv(os.path.join(OUT_DIR, "backtest_paths.csv"), index=False)
        hist.to_csv(os.path.join(OUT_DIR, "backtest_hist.csv"), index=False)
        for cfg in CFGS:
            if cfg["tag"] == "bg84":
                continue
            sub = paths[(paths.geo == cfg["tag"]) & (paths.window == cfg["label"])]
            if len(sub):
                print("  fig:", fig_backtest(cfg["tag"], paths, hist, cfg, res))

    print("Task 2 - regional context")
    df = run_context(res, diag)
    print("  fig:", fig_region(df))

    print("Exposure-convention check on Macedonian data")
    convention_check(res, diag)

    prim = [("bg", "w1"), ("ee", "w1"), ("bg", "w2"), ("ee", "w2")]
    for cname in ("rwd", "trendstat", "rwd_wide"):
        for suf in ("", "_excovid"):
            for scope, sel in (("w1", [p for p in prim if p[1] == "w1"]),
                               ("all", prim)):
                vals = []
                for tag, lab in sel:
                    pfx = "coverage" if lab == "w1" else "coverage_w2"
                    for sx in ("m", "f"):
                        k = (f"{pfx}_{cname}{suf}_{tag}_{sx}" if suf
                             else f"{pfx}_{cname}_{tag}_{sx}")
                        if k in res:
                            vals.append(res[k])
                if vals:
                    res[f"coverage_pooled_{scope}_{cname}{suf}"] = float(np.mean(vals))
                    res[f"coverage_pooled_{scope}_{cname}{suf}_n"] = len(vals)
    for cname, suf in (("rwd", ""), ("trendstat", "_trendstat"), ("rwd_wide", "_rwdwide")):
        for hz, lab10 in (("10y", "h10"), ("20y", "h20")):
            hits, errs, widths = [], [], []
            for tag, lab in prim:
                pre = f"backtest_{tag}" if lab == "w1" else f"backtest_w2_{tag}"
                yr = {"w1": {"h10": 2013, "h20": 2023}}.get(lab, {})
                for sx in ("m", "f"):
                    stem = (f"{pre}_{sx}_e65_{yr[lab10]}" if lab == "w1"
                            else f"{pre}_{sx}_e65_{lab10}")
                    kb = f"{stem}_inside_band{suf}"
                    if kb in res:
                        hits.append(1.0 if res[kb] else 0.0)
                        errs.append(res[f"{pre}_{sx}_abs_err_{hz}{suf}"])
                        widths.append(res[f"{pre}_{sx}_band_width_{hz}{suf}"])
            if hits:
                res[f"hitrate_{hz}_{cname}"] = float(np.mean(hits))
                res[f"hitrate_{hz}_{cname}_n"] = len(hits)
                res[f"mean_abs_err_{hz}_{cname}"] = float(np.mean(errs))
                res[f"mean_band_width_{hz}_{cname}"] = float(np.mean(widths))
                res[f"err_to_halfwidth_ratio_{hz}_{cname}"] = float(
                    np.mean(errs) / (0.5 * np.mean(widths)))
    trs = []
    for tag, lab in prim:
        pre = f"backtest_{tag}" if lab == "w1" else f"backtest_w2_{tag}"
        pfx = "coverage" if lab == "w1" else "coverage_w2"
        for sx in ("m", "f"):
            s10 = f"{pre}_{sx}_e65_" + ("2013" if lab == "w1" else "h10")
            s20 = f"{pre}_{sx}_e65_" + ("2023" if lab == "w1" else "h20")
            trs.append(dict(
                geo=tag, window=res[f"fit_window_{tag}_{lab}"],
                test=res[f"test_window_{tag}_{lab}"], sex=sx,
                drift=res[f"{pre}_{sx}_drift"], drift_se=res[f"{pre}_{sx}_drift_se"],
                vr4=res[f"{pre}_{sx}_vr4"], phi=res[f"{pre}_{sx}_ts_phi"],
                e65_10y_actual=res[f"{s10}_actual"],
                e65_10y_central=res[f"{s10}_central"],
                e65_10y_p025=res[f"{s10}_p025"], e65_10y_p975=res[f"{s10}_p975"],
                e65_20y_actual=res[f"{s20}_actual"],
                e65_20y_central=res[f"{s20}_central"],
                e65_20y_p025=res[f"{s20}_p025"], e65_20y_p975=res[f"{s20}_p975"],
                e65_20y_p025_ts=res[f"{s20}_p025_trendstat"],
                e65_20y_p975_ts=res[f"{s20}_p975_trendstat"],
                abs_err_10y=res[f"{pre}_{sx}_abs_err_10y"],
                abs_err_20y=res[f"{pre}_{sx}_abs_err_20y"],
                inside_20y=res[f"{s20}_inside_band"],
                years_inside=res[f"{pre}_{sx}_years_inside_of_20"],
                coverage_rwd=res[f"{pfx}_rwd_{tag}_{sx}"],
                coverage_ts=res[f"{pfx}_trendstat_{tag}_{sx}"],
                coverage_rwd_excovid=res[f"{pfx}_rwd_excovid_{tag}_{sx}"],
                jumpoff_bias=res[f"{pre}_{sx}_e65_jumpoff_bias"]))
    pd.DataFrame(trs).to_csv(os.path.join(OUT_DIR, "backtest_table.csv"), index=False)
    with open(os.path.join(REPO, "results", "compare.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2, sort_keys=True)
    with open(os.path.join(OUT_DIR, "diagnostics.json"), "w", encoding="utf-8") as f:
        json.dump(diag, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)
    print(f"wrote results/compare.json ({len(res)} keys)")


if __name__ == "__main__":
    main()
