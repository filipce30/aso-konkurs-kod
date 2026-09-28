"""Life-table, old-age closure and age-heaping helpers."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

OPEN_AGE = 110


def a0_coale_demeny(m0: float, sex: str) -> float:
    if sex == "m":
        if m0 >= 0.107:
            return 0.330
        return 0.0425 + 2.684 * m0
    else:
        if m0 >= 0.107:
            return 0.350
        return 0.0500 + 3.219 * m0


def build_life_table(mx: pd.Series, sex: str, open_age: int = OPEN_AGE) -> pd.DataFrame:
    ages = list(range(0, open_age + 1))
    mx = mx.reindex(ages)
    if mx.isna().any():
        missing = mx[mx.isna()].index.tolist()
        raise ValueError(f"build_life_table: NaN mx at ages {missing}")

    ax = pd.Series(0.5, index=ages, dtype=float)
    ax.loc[0] = a0_coale_demeny(float(mx.loc[0]), sex)

    qx = mx / (1 + (1 - ax) * mx)
    qx = qx.clip(upper=1.0)
    qx.loc[open_age] = 1.0

    lx = pd.Series(index=ages, dtype=float)
    lx.loc[0] = 100000.0
    for x in ages[1:]:
        lx.loc[x] = lx.loc[x - 1] * (1 - qx.loc[x - 1])

    dx = pd.Series(index=ages, dtype=float)
    for x in ages[:-1]:
        dx.loc[x] = lx.loc[x] - lx.loc[x + 1]
    dx.loc[open_age] = lx.loc[open_age]

    Lx = pd.Series(index=ages, dtype=float)
    for x in ages[:-1]:
        Lx.loc[x] = lx.loc[x + 1] + ax.loc[x] * dx.loc[x]
    m_open = float(mx.loc[open_age])
    Lx.loc[open_age] = lx.loc[open_age] / m_open if m_open > 0 else 0.0

    Tx = Lx[::-1].cumsum()[::-1]
    ex = Tx / lx

    out = pd.DataFrame({"age": ages, "mx": mx.values, "ax": ax.values,
                         "qx": qx.values, "lx": lx.values, "dx": dx.values,
                         "Lx": Lx.values, "Tx": Tx.values, "ex": ex.values})
    return out


def fit_kannisto_poisson(ages, D, E):
    ages = np.asarray(ages, dtype=float)
    D = np.asarray(D, dtype=float)
    E = np.asarray(E, dtype=float)
    mask = (E > 0) & np.isfinite(D) & np.isfinite(E)
    ages, D, E = ages[mask], D[mask], E[mask]
    if len(ages) < 5:
        return np.nan, np.nan, False, int(len(ages))

    raw_mx = np.clip(D / E, 1e-8, 1 - 1e-8)
    logit = np.log(raw_mx / (1 - raw_mx))
    X = np.vstack([np.ones_like(ages), ages]).T
    coef, *_ = np.linalg.lstsq(X, logit, rcond=None)
    alpha0, beta0 = coef

    def neg_log_lik(params):
        alpha, beta = params
        lin = alpha + beta * ages
        mu = 1.0 / (1.0 + np.exp(-lin))
        mu = np.clip(mu, 1e-12, 1 - 1e-12)
        ll = D * np.log(mu) - E * mu
        return -np.sum(ll)

    res = minimize(neg_log_lik, x0=[alpha0, beta0], method="Nelder-Mead",
                    options={"xatol": 1e-10, "fatol": 1e-10, "maxiter": 5000})
    alpha, beta = res.x
    return float(alpha), float(beta), bool(res.success), int(len(ages))


def kannisto_mu(alpha: float, beta: float, ages) -> np.ndarray:
    ages = np.asarray(ages, dtype=float)
    lin = alpha + beta * ages
    return 1.0 / (1.0 + np.exp(-lin))


def fit_and_close(D: pd.Series, E: pd.Series, kan_lo: int = 80, kan_hi: int = 99,
                   open_age: int = OPEN_AGE):
    raw_mx = D / E
    alpha, beta, conv, nobs = fit_kannisto_poisson(
        range(kan_lo, kan_hi + 1), D.reindex(range(kan_lo, kan_hi + 1)).values,
        E.reindex(range(kan_lo, kan_hi + 1)).values)
    mu = kannisto_mu(alpha, beta, range(kan_lo, open_age + 1))
    mx_full = pd.Series(index=range(0, open_age + 1), dtype=float)
    mx_full.loc[0:kan_lo - 1] = raw_mx.reindex(range(0, kan_lo)).values
    mx_full.loc[kan_lo:open_age] = mu
    return mx_full, alpha, beta, conv, nobs


def whipple_index(pop_by_age: pd.Series, lo: int = 23, hi: int = 62) -> float:
    ages = list(range(lo, hi + 1))
    total = float(pop_by_age.reindex(ages).sum())
    mult5 = [x for x in ages if x % 5 == 0]
    num = float(pop_by_age.reindex(mult5).sum())
    factor = len(ages) / len(mult5)
    return num / total * factor * 100.0


def myers_blended_index(pop_by_age: pd.Series, lo: int = 60, hi: int = 99):
    span = hi - lo + 1
    assert span % 10 == 0 and span >= 20, "myers_blended_index needs >=2 complete decades"
    n_decades = span // 10

    def sum_a(d):
        return sum(float(pop_by_age.get(lo + 10 * k + d, 0.0) or 0.0) for k in range(0, n_decades - 1))

    def sum_b(d):
        return sum(float(pop_by_age.get(lo + 10 * k + d, 0.0) or 0.0) for k in range(1, n_decades))

    blended = {d: (d + 1) * sum_a(d) + (9 - d) * sum_b(d) for d in range(10)}
    total = sum(blended.values())
    pct = {d: blended[d] / total * 100.0 for d in range(10)}
    index = 0.5 * sum(abs(pct[d] - 10.0) for d in range(10))
    return index, pct


def detrended_heaping_excess_pct(pop_by_age: pd.Series, lo: int = 55, hi: int = 95, deg: int = 4) -> float:
    ages = np.arange(lo, hi + 1)
    obs = pop_by_age.reindex(ages).astype(float).values
    y = np.log(obs)
    coef = np.polyfit(ages, y, deg)
    pred = np.exp(np.polyval(coef, ages))
    mult5 = (ages % 5 == 0)
    excess = float((obs[mult5] - pred[mult5]).sum())
    denom = float(pred.sum())
    return excess / denom * 100.0
