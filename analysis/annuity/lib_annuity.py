"""Annuity mathematics: discounting, annuity factors, life expectancy and closure helpers."""
from __future__ import annotations

import numpy as np

OMEGA = 110
M = 12


def kpx(q: np.ndarray) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    return np.concatenate([[1.0], np.cumprod(1.0 - q)])


def kpx_matrix(Q: np.ndarray) -> np.ndarray:
    Q = np.asarray(Q, dtype=float)
    n = Q.shape[0]
    return np.concatenate([np.ones((n, 1)), np.cumprod(1.0 - Q, axis=1)], axis=1)


def survival_grid(q: np.ndarray, m: int = M) -> tuple[np.ndarray, np.ndarray]:
    q = np.asarray(q, dtype=float)
    K = len(q)
    lx = kpx(q)[:K]
    u = np.arange(m, dtype=float) / m
    S = lx[:, None] * (1.0 - u[None, :] * q[:, None])
    t = np.arange(K, dtype=float)[:, None] + u[None, :]
    return t.ravel(), S.ravel()


def a_due_m(q: np.ndarray, vfun, m: int = M) -> float:
    t, S = survival_grid(q, m)
    return float((S * vfun(t)).sum() / m)


def a_due_annual(q: np.ndarray, vfun) -> float:
    q = np.asarray(q, dtype=float)
    K = len(q)
    lx = kpx(q)[:K]
    k = np.arange(K, dtype=float)
    return float((lx * vfun(k)).sum())


def a_due_m_paths(Q: np.ndarray, vfun, m: int = M) -> np.ndarray:
    Q = np.asarray(Q, dtype=float)
    n, K = Q.shape
    LX = kpx_matrix(Q)[:, :K]
    u = np.arange(m, dtype=float) / m
    t = (np.arange(K, dtype=float)[:, None] + u[None, :]).ravel()
    V = vfun(t).reshape(K, m)
    A = LX * V.sum(axis=1)[None, :] - LX * Q * (u[None, :] * V).sum(axis=1)[None, :]
    return A.sum(axis=1) / m


def a_woolhouse(q: np.ndarray, i: float, m: int = M) -> float:
    vfun = flat_discount(i)
    return a_due_annual(q, vfun) - (m - 1) / (2 * m)


def ex_curtate(q: np.ndarray) -> float:
    return float(kpx(q)[1:].sum())


def ex_lifetable(q: np.ndarray, m_omega: float | None = None) -> float:
    q = np.asarray(q, dtype=float)
    K = len(q)
    lx = kpx(q)
    L = lx[: K - 1] - 0.5 * (lx[: K - 1] - lx[1:K])
    tail = lx[K - 1] / m_omega if m_omega else 0.5 * lx[K - 1]
    return float(L.sum() + tail)


def flat_discount(i: float):
    def vfun(t):
        return np.power(1.0 + i, -np.asarray(t, dtype=float))
    return vfun


def curve_discount(maturities: np.ndarray, spot: np.ndarray, spread: float = 0.0):
    tau = np.asarray(maturities, dtype=float)
    s = np.asarray(spot, dtype=float) + spread
    lnv = -tau * np.log1p(s)
    tau_full = np.concatenate([[0.0], tau])
    lnv_full = np.concatenate([[0.0], lnv])

    def vfun(t):
        t = np.asarray(t, dtype=float)
        return np.exp(np.interp(t, tau_full, lnv_full))
    return vfun


def scale_qx(q: np.ndarray, factor: float, keep_terminal: bool = True) -> np.ndarray:
    out = np.minimum(np.asarray(q, dtype=float) * factor, 1.0)
    if keep_terminal:
        out[-1] = 1.0
    return out


def scale_qx_paths(Q: np.ndarray, factor: float) -> np.ndarray:
    out = np.minimum(np.asarray(Q, dtype=float) * factor, 1.0)
    out[:, -1] = 1.0
    return out


def bel_runoff(q: np.ndarray, vfun, m: int = M) -> np.ndarray:
    q = np.asarray(q, dtype=float)
    K = len(q)
    t, S = survival_grid(q, m)
    cf = S * vfun(t) / m
    cf = cf.reshape(K, m)
    tail = np.concatenate([np.cumsum(cf.sum(axis=1)[::-1])[::-1], [0.0]])[:K]
    return tail / vfun(np.arange(K, dtype=float))


def taper_factor(t: np.ndarray, lam: float = 0.96, floor: float = 0.5) -> np.ndarray:
    return np.maximum(np.power(lam, np.asarray(t, dtype=float)), floor)


def risk_margin(q: np.ndarray, vfun, scr0: float, coc: float,
                taper: bool = False, m: int = M) -> float:
    bel = bel_runoff(q, vfun, m)
    t = np.arange(len(bel), dtype=float)
    w = taper_factor(t) if taper else np.ones_like(t)
    return float(coc * scr0 * (w * (bel / bel[0]) * vfun(t + 1.0)).sum())


def kannisto_close(mx: np.ndarray, ages: np.ndarray, fit_lo: int = 80,
                   fit_hi: int = 89, omega: int = OMEGA) -> np.ndarray:
    ages = np.asarray(ages)
    mx = np.asarray(mx, dtype=float)
    sel = (ages >= fit_lo) & (ages <= fit_hi)
    x = ages[sel].astype(float)
    y = np.log(mx[sel] / (1.0 - mx[sel]))
    b, a = np.polyfit(x, y, 1)
    new_ages = np.arange(ages[sel].max() + 1, omega + 1, dtype=float)
    z = a + b * new_ages
    mx_new = np.exp(z) / (1.0 + np.exp(z))
    keep = ages <= fit_hi
    return np.concatenate([mx[keep], mx_new])


def qx_from_mx(mx: np.ndarray, omega_index: int = -1) -> np.ndarray:
    q = np.asarray(mx, dtype=float) / (1.0 + np.asarray(mx, dtype=float) / 2.0)
    q = np.minimum(q, 1.0)
    q[omega_index] = 1.0
    return q
