#!/usr/bin/env python3
"""Value second-pillar life annuities on projected mortality: period vs cohort, Solvency II shock vs 99.5% VaR."""
from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from scipy.optimize import brentq
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "annuity"))
import lib_annuity as la

MORT = ROOT / "analysis" / "mortality"
CLEAN = ROOT / "data" / "clean"
RAW = ROOT / "data" / "raw"
RESULTS = ROOT / "results"
FIG = ROOT / "figures"
OUT = ROOT / "analysis" / "annuity"
READ_RESULTS = RESULTS

DRY_RUN = "--dry-run" in sys.argv

SEED = 2026
OMEGA = la.OMEGA
YEAR_MIN, YEAR_MAX = 2023, 2080
JUMPOFF = 2023
COHORT_YEARS = [2026, 2030, 2035]
SYSTEM_YEARS = list(range(2026, 2041))
SEX_AGE = {"m": 64, "f": 62}
SELECTIONS = [1.0, 0.9, 0.8]
MIN_PATHS = 1000

rng = np.random.default_rng(SEED)

legal = json.load(open(READ_RESULTS / "legal.json"))
mortality = json.load(open(READ_RESULTS / "mortality.json"))
system = json.load(open(READ_RESULTS / "system.json"))

if DRY_RUN:
    _scratch = Path("/tmp/annuity_dryrun")
    _scratch.mkdir(exist_ok=True)
    RESULTS = FIG = OUT = _scratch
    print("*** DRY RUN: writing to /tmp/annuity_dryrun, nothing published ***")

VARIANT = mortality["variant_main"]
MAIN_MODEL = mortality["main_model"]
SHOCK = 1.0 - legal["sii_longevity_shock_pct"]
COC6 = legal["sii_coc_rate_pre2027_pct"]
COC475 = legal["sii_coc_rate_2027_pct"]
DOM_YIELD = system["bond_yield_15y_latest"]
assert SEX_AGE["m"] == legal["retirement_age_m"]
assert SEX_AGE["f"] == legal["retirement_age_f"]

checks: list[dict] = []


def check(name, ok, detail="", blocking=True):
    checks.append({"check": name, "pass": bool(ok), "blocking": bool(blocking),
                   "detail": detail})
    tag = "PASS" if ok else ("FAIL" if blocking else "NOTE")
    print(f"[{tag}] {name}: {detail}")
    return bool(ok)


def load_surface(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    df = pq.read_table(path).to_pandas()
    qp = df.pivot(index="year", columns="age", values="qx").sort_index()
    mp = df.pivot(index="year", columns="age", values="mx").sort_index()
    return (qp.index.to_numpy(), qp.columns.to_numpy(),
            qp.to_numpy(float), mp.to_numpy(float))


SURF = {}
for sex in ("m", "f"):
    SURF[("lc", sex)] = load_surface(MORT / f"qx_central_{sex}.parquet")
    SURF[("cbd", sex)] = load_surface(MORT / f"qx_central_robust_{sex}.parquet")
    _coh = MORT / f"qx_central_coherent_{sex}.parquet"
    if _coh.exists():
        SURF[("coherent", sex)] = load_surface(_coh)
HAS_COHERENT = ("coherent", "m") in SURF and ("coherent", "f") in SURF

YEARS, AGES = SURF[("lc", "m")][0], SURF[("lc", "m")][1]
assert YEARS[0] == YEAR_MIN and YEARS[-1] == YEAR_MAX
assert AGES[0] == 55 and AGES[-1] == OMEGA

ai = {a: i for i, a in enumerate(AGES)}
yi = {y: i for i, y in enumerate(YEARS)}


def period_qx(model: str, sex: str, x: int, year: int = JUMPOFF) -> np.ndarray:
    Q = SURF[(model, sex)][2]
    return Q[yi[year], ai[x]:].copy()


def cohort_qx(model: str, sex: str, x: int, y0: int) -> np.ndarray:
    Q = SURF[(model, sex)][2]
    ages = np.arange(x, OMEGA + 1)
    yrs = np.minimum(y0 + (ages - x), YEAR_MAX)
    return Q[[yi[y] for y in yrs], [ai[a] for a in ages]].copy()


def cohort_qx_extrap(model: str, sex: str, x: int, y0: int) -> np.ndarray:
    Q = SURF[(model, sex)][2]
    ages = np.arange(x, OMEGA + 1)
    out = np.empty(len(ages))
    for j, a in enumerate(ages):
        y = y0 + j
        if y <= YEAR_MAX:
            out[j] = Q[yi[y], ai[a]]
        else:
            r = Q[yi[YEAR_MAX], ai[a]] / Q[yi[YEAR_MAX - 1], ai[a]]
            out[j] = min(Q[yi[YEAR_MAX], ai[a]] * r ** (y - YEAR_MAX), 1.0)
    out[-1] = 1.0
    return out


_lt = pd.read_csv(CLEAN / "lifetables_period.csv")
RAW_2023 = {}
for sex in ("m", "f"):
    s = _lt[(_lt.year == 2023) & (_lt.sex == sex)].sort_values("age")
    q = s.set_index("age").qx.reindex(range(0, OMEGA + 1)).to_numpy(float)
    q[-1] = 1.0
    RAW_2023[sex] = q


def period_raw_qx(sex: str, x: int) -> np.ndarray:
    return RAW_2023[sex][x:].copy()


def load_eiopa_eur(zip_path: Path) -> tuple[np.ndarray, np.ndarray, str]:
    import openpyxl
    z = zipfile.ZipFile(zip_path)
    name = [n for n in z.namelist() if n.endswith("Term_Structures.xlsx")][0]
    wb = openpyxl.load_workbook(io.BytesIO(z.read(name)), read_only=True, data_only=True)
    ws = wb["RFR_spot_no_VA"]
    rows = list(ws.iter_rows(min_row=1, max_row=200, max_col=3, values_only=True))
    tag = [r[2] for r in rows[:5] if r[2] and str(r[2]).startswith("EUR_")][0]
    mat, spot = [], []
    for r in rows:
        if isinstance(r[1], int) and r[1] >= 1 and r[2] is not None:
            mat.append(r[1])
            spot.append(float(r[2]))
    return np.array(mat, float), np.array(spot, float), str(tag)


EIOPA_MAT, EIOPA_SPOT, EIOPA_TAG = load_eiopa_eur(RAW / "eiopa" / "EIOPA_RFR_20260831.zip")
EIOPA_DATE = "2026-08-31"

RATES = {
    "i2": ("Рамна каматна стапка 2%", la.flat_discount(0.02)),
    "i3": ("Рамна каматна стапка 3%", la.flat_discount(0.03)),
    "i4": ("Рамна каматна стапка 4%", la.flat_discount(0.04)),
    "eiopa": (f"EIOPA EUR безризична крива, {EIOPA_DATE} (без VA)",
              la.curve_discount(EIOPA_MAT, EIOPA_SPOT)),
    "eiopa_sp100": (f"EIOPA EUR крива + 100 б.п. државен распон",
                    la.curve_discount(EIOPA_MAT, EIOPA_SPOT, spread=0.01)),
    "dom": (f"Домашен принос на 15-г. обврзница {DOM_YIELD:.3%} (09/2026)",
            la.flat_discount(DOM_YIELD)),
}
HEAD = "i3"


def resolve_kannisto_rule(sex: str, model: str = "lc", tol: float = 1e-10):
    _, ages_, _, MXs = SURF[(model, sex)]
    fit = (ages_ >= 80) & (ages_ <= 89)
    ext = ages_ >= 90
    fa = ages_[fit].astype(float)
    xa = fa - fa.mean()
    sxx = (xa ** 2).sum()
    xe = ages_[ext].astype(float)
    xec = xe - xe.mean()
    sxxe = (xec ** 2).sum()
    raw, exp = [], []
    for r in range(MXs.shape[0]):
        m = MXs[r]
        lg = np.log(m[fit] / (1.0 - m[fit]))
        raw.append(float((lg * xa).sum() / sxx))
        lge = np.log(m[ext] / (1.0 - m[ext]))
        exp.append(float((lge * xec).sum() / sxxe))
    raw = np.array(raw)
    exp = np.array(exp)
    up = exp > raw + tol
    dn = exp < raw - tol
    lo = float(exp[up].max()) if up.any() else None
    hi = float(exp[dn].min()) if dn.any() else None
    src = []
    if lo is not None:
        src.append(f"floor {lo:.6f} observed binding on {up.sum()} central years")
    if hi is not None:
        src.append(f"ceiling {hi:.6f} observed binding on {dn.sum()} central years")
    key_lo = mortality.get(f"kannisto_slope_bound_lo_{sex}",
                           mortality.get(f"kannisto_slope_obs_lo_{sex}"))
    key_hi = mortality.get(f"kannisto_slope_bound_hi_{sex}",
                           mortality.get(f"kannisto_slope_obs_hi_{sex}"))
    if lo is None and key_lo is not None and raw.min() >= key_lo:
        lo = float(key_lo)
        src.append(f"floor {lo:.6f} from results/mortality.json (never binds centrally)")
    if hi is None:
        _one_sided = bool(mortality.get("kannisto_bound_one_sided", False))
        _share_hi = mortality.get(f"kannisto_winsor_share_high_{sex}")
        if _one_sided:
            src.append("NO ceiling: kannisto_bound_one_sided is true (floor-only rule)")
        elif _share_hi is not None and _share_hi == 0:
            src.append("NO ceiling: kannisto_winsor_share_high is zero")
        elif _share_hi is None and key_hi is not None:
            src.append("NO ceiling: no kannisto_winsor_share_high_* key is published, "
                       "so no bound is applied from above")
        elif key_hi is not None and raw.max() > key_hi + tol:
            src.append(f"NO ceiling: raw slope reaches {raw.max():.6f} > published "
                       f"{key_hi:.6f} yet the export is unclipped -> one-sided rule")
        elif key_hi is not None:
            hi = float(key_hi)
            src.append(f"ceiling {hi:.6f} from results/mortality.json "
                       f"(never binds centrally)")
    return lo, hi, "; ".join(src) if src else "no clipping detected"


def equiv_multiplier(q, vfun, target_a12, lo=0.20, hi=1.0):
    return float(brentq(
        lambda lam: la.a_due_m(la.scale_qx(q, lam), vfun) - target_a12,
        lo, hi, xtol=1e-12))


e65_rebuilt = {}
for sex in ("m", "f"):
    Q, MX = SURF[("lc", sex)][2], SURF[("lc", sex)][3]
    q = Q[yi[2023], ai[65]:]
    m_omega = MX[yi[2023], ai[OMEGA]]
    e65_rebuilt[sex] = la.ex_lifetable(q, m_omega)
    tgt = mortality[f"e65_{sex}_2023_fitted"]
    check(f"e65_{sex}_2023 vs results/mortality.json",
          abs(e65_rebuilt[sex] - tgt) < 0.05,
          f"rebuilt {e65_rebuilt[sex]:.6f} vs {tgt:.6f} (diff {e65_rebuilt[sex]-tgt:+.2e} y)")

mono_viol = {}
for sex in ("m", "f"):
    for model in ("lc", "cbd"):
        Q = SURF[(model, sex)][2]
        ok_dom = np.all(Q > 0) and np.all(Q <= 1) and not np.isnan(Q).any()
        ok_close = np.allclose(Q[:, ai[OMEGA]], 1.0)
        sub = Q[:, ai[70]:]
        d = np.diff(sub, axis=1)
        viol = int((d < 0).sum())
        worst = float((d / sub[:, :-1]).min())
        mono_viol[(model, sex)] = (viol, worst)
        check(f"qx domain/closure {model}/{sex}", ok_dom and ok_close,
              f"min {Q.min():.3e}, max {Q.max():.4f}, q(110)=1 {ok_close}")
        check(f"qx non-decreasing from age 70 {model}/{sex}", viol == 0,
              f"{viol} decreasing steps out of {sub.shape[0]*(sub.shape[1]-1)}; "
              f"worst relative drop {worst:+.1%}", blocking=False)

SIMS = {sex: ds.dataset(MORT / f"qx_sims_{sex}.parquet", format="parquet")
        for sex in ("m", "f")}


def sims_year_slice(sex: str, year: int, age_from: int) -> np.ndarray:
    tb = SIMS[sex].to_table(
        filter=(ds.field("year") == year) & (ds.field("age") >= age_from),
        columns=["sim", "age", "qx"])
    return (tb.to_pandas().pivot(index="sim", columns="age", values="qx")
            .sort_index().to_numpy(float))


def sims_cohort_diag(sex: str, x: int, y0: int) -> np.ndarray:
    d = y0 - x
    tb = SIMS[sex].to_table(
        filter=((ds.field("year") - ds.field("age")) == d) & (ds.field("age") >= x),
        columns=["sim", "age", "qx"])
    return (tb.to_pandas().pivot(index="sim", columns="age", values="qx")
            .sort_index().to_numpy(float))


for sex in ("m", "f"):
    Qp = sims_year_slice(sex, 2050, 65)
    LX = la.kpx_matrix(Qp)
    K = Qp.shape[1]
    L = LX[:, :K - 1] - 0.5 * (LX[:, :K - 1] - LX[:, 1:K])
    e65_paths = L.sum(axis=1) + 0.5 * LX[:, K - 1]
    got = np.quantile(e65_paths, [0.025, 0.5, 0.975])
    tgt = [mortality[f"e65_{sex}_2050_p025"], mortality[f"e65_{sex}_2050_p500"],
           mortality[f"e65_{sex}_2050_p975"]]
    check(f"qx_sims_{sex} contains the full path set",
          Qp.shape[0] >= MIN_PATHS,
          f"{Qp.shape[0]} paths on disk; the simulation design specifies >= 5,000. A smaller "
          f"number means the mortality simulation was a reduced test run or did not "
          f"complete -- the 99.5% VaR must not be computed from it.",
          blocking=not DRY_RUN)
    check(f"e65_{sex}_2050 path quantiles vs results/mortality.json",
          np.max(np.abs(got - np.array(tgt))) < 0.05,
          f"p2.5/p50/p97.5 {got[0]:.4f}/{got[1]:.4f}/{got[2]:.4f} vs "
          f"{tgt[0]:.4f}/{tgt[1]:.4f}/{tgt[2]:.4f}; n_paths {Qp.shape[0]}")
    N_PATHS = Qp.shape[0]

for sex, x in SEX_AGE.items():
    q = period_qx("lc", sex, x)
    a0 = la.a_due_m(q, la.flat_discount(0.0))
    tgt0 = la.ex_curtate(q) + 13.0 / 24.0
    check(f"a12(i=0) = e_{x} + 13/24 ({sex})", abs(a0 - tgt0) < 1e-8,
          f"{a0:.10f} vs {tgt0:.10f}")
    aa0 = la.a_due_annual(q, la.flat_discount(0.0))
    check(f"a_annual(i=0) = 1 + e_{x} ({sex})",
          abs(aa0 - (1 + la.ex_curtate(q))) < 1e-8, f"{aa0:.10f}")
    seq = [la.a_due_m(q, la.flat_discount(i)) for i in (0.0, 0.01, 0.02, 0.03, 0.04, 0.05)]
    check(f"a12 decreasing in i ({sex})", all(np.diff(seq) < 0),
          " > ".join(f"{v:.3f}" for v in seq))
    qc = cohort_qx("lc", sex, x, 2026)
    check(f"a12 increasing with life expectancy ({sex}, cohort vs period at 3%)",
          la.a_due_m(qc, RATES["i3"][1]) > la.a_due_m(q, RATES["i3"][1]),
          f"cohort {la.a_due_m(qc, RATES['i3'][1]):.4f} > "
          f"period {la.a_due_m(q, RATES['i3'][1]):.4f}; "
          f"e_x cohort {la.ex_curtate(qc):.3f} vs period {la.ex_curtate(q):.3f}")

if not all(c["pass"] for c in checks if c["blocking"]):
    pd.DataFrame(checks).to_csv(OUT / "unit_checks.csv", index=False)
    sys.exit("A required unit check failed -- see analysis/annuity/unit_checks.csv")

from scipy.optimize import isotonic_regression

ISO = {}
for sex in ("m", "f"):
    Q = SURF[("lc", sex)][2].copy()
    j0, j1 = ai[70], ai[OMEGA]
    for r in range(Q.shape[0]):
        y = np.log(Q[r, j0:j1])
        Q[r, j0:j1] = np.exp(isotonic_regression(y, increasing=True).x)
    Q[:, ai[OMEGA]] = 1.0
    ISO[sex] = Q


def cohort_qx_iso(sex: str, x: int, y0: int) -> np.ndarray:
    ages = np.arange(x, OMEGA + 1)
    yrs = np.minimum(y0 + (ages - x), YEAR_MAX)
    return ISO[sex][[yi[y] for y in yrs], [ai[a] for a in ages]].copy()


holdflat = {}
for sex, x in SEX_AGE.items():
    for y0 in (2035, 2040):
        a_hold = la.a_due_m(cohort_qx("lc", sex, x, y0), RATES[HEAD][1])
        a_ext = la.a_due_m(cohort_qx_extrap("lc", sex, x, y0), RATES[HEAD][1])
        holdflat[(sex, y0)] = a_ext / a_hold - 1.0
check("hold-flat beyond 2080 immaterial",
      max(abs(v) for v in holdflat.values()) < 1e-3,
      "; ".join(f"{s}{y}: {v:+.3e}" for (s, y), v in holdflat.items()))


def unisex_weights() -> tuple[float, float, str]:
    j = json.load(open(RAW / "makstat" / "population_projections_2022_2070.json"))
    dim, size, val = j["dimension"], j["size"], j["value"]
    ids = j["id"]
    idx = {d: dim[d]["category"]["index"] for d in ids}
    lab = {d: dim[d]["category"]["label"] for d in ids}
    variant = [k for k, v in lab["Варијанта"].items() if "Среден" in v][0]

    def get(sex_code, year, age):
        pos = [idx["Пол"][sex_code], idx["Година"][str(year)],
               idx["Варијанта"][variant], idx["Возраст"][str(age)]]
        flat = 0
        for p, s in zip(pos, size):
            flat = flat * s + p
        v = val[str(flat)] if isinstance(val, dict) else val[flat]
        return float(v)

    nm = get("1", 2026, SEX_AGE["m"])
    nf = get("2", 2026, SEX_AGE["f"])
    w = nm / (nm + nf)
    note = (f"ДЗС проекции 2022-2070, варијанта „{lab['Варијанта'][variant]}“, 2026: "
            f"мажи на возраст {SEX_AGE['m']} = {nm:,.0f}, жени на возраст "
            f"{SEX_AGE['f']} = {nf:,.0f}".replace(",", " "))
    return w, 1 - w, note


W_M, W_F, UNISEX_NOTE = unisex_weights()


def unisex_surface(model: str) -> np.ndarray:
    return W_M * SURF[(model, "m")][2] + W_F * SURF[(model, "f")][2]


UNI = {m: unisex_surface(m) for m in ("lc", "cbd")}


def unisex_qx(model: str, x: int, y0: int | None) -> np.ndarray:
    Q = UNI[model]
    ages = np.arange(x, OMEGA + 1)
    if y0 is None:
        return Q[yi[JUMPOFF], ai[x]:].copy()
    yrs = np.minimum(y0 + (ages - x), YEAR_MAX)
    return Q[[yi[y] for y in yrs], [ai[a] for a in ages]].copy()


def qx_for(basis: str, model: str, sex: str, x: int, y0: int | None) -> np.ndarray:
    if basis == "period":
        return unisex_qx(model, x, None) if sex == "u" else period_qx(model, sex, x)
    if basis == "period_vintage":
        return period_qx(model, sex, x, year=y0)
    if basis == "period_raw":
        return period_raw_qx(sex, x)
    if basis == "cohort":
        return unisex_qx(model, x, y0) if sex == "u" else cohort_qx(model, sex, x, y0)
    raise ValueError(basis)


rows = []


def emit(sex, x, basis, model, y0, sel, q):
    qs = la.scale_qx(q, sel)
    for rk, (rlabel, vfun) in RATES.items():
        a12 = la.a_due_m(qs, vfun)
        rows.append(dict(
            sex=sex, age=x, basis=basis, model=model,
            cohort_year=("" if y0 is None else y0), selection=sel,
            rate=rk, rate_label=rlabel,
            a12=a12, a_annual=la.a_due_annual(qs, vfun),
            ex_curtate=la.ex_curtate(qs), ex_complete=la.ex_lifetable(qs),
            monthly_pension_per_1m_mkd=1e6 / (12.0 * a12),
        ))


for sex, x in SEX_AGE.items():
    for sel in SELECTIONS:
        emit(sex, x, "period", "lc", None, sel, period_qx("lc", sex, x))
        emit(sex, x, "period_raw", "lc", None, sel, period_raw_qx(sex, x))
        emit(sex, x, "period", "cbd", None, sel, period_qx("cbd", sex, x))
        for y0 in COHORT_YEARS:
            emit(sex, x, "cohort", "lc", y0, sel, cohort_qx("lc", sex, x, y0))
            emit(sex, x, "cohort", "cbd", y0, sel, cohort_qx("cbd", sex, x, y0))
            if HAS_COHERENT and sel == 1.0:
                emit(sex, x, "cohort", "coherent", y0, sel,
                     cohort_qx("coherent", sex, x, y0))
    if HAS_COHERENT:
        emit(sex, x, "period", "coherent", None, 1.0, period_qx("coherent", sex, x))
for sex, x in SEX_AGE.items():
    emit("u", x, "period", "lc", None, 1.0, unisex_qx("lc", x, None))
    for y0 in COHORT_YEARS:
        emit("u", x, "cohort", "lc", y0, 1.0, unisex_qx("lc", x, y0))
for sex, x in SEX_AGE.items():
    for y0 in SYSTEM_YEARS:
        if y0 not in COHORT_YEARS:
            emit(sex, x, "cohort", "lc", y0, 1.0, cohort_qx("lc", sex, x, y0))
for sex, x in SEX_AGE.items():
    for y0 in SYSTEM_YEARS:
        emit(sex, x, "period_vintage", "lc", y0, 1.0, period_qx("lc", sex, x, y0))

F = pd.DataFrame(rows)
F.to_csv(OUT / "factors.csv", index=False)


def f(sex, basis, rate, model="lc", sel=1.0, y0=2026, age=None):
    x = age if age is not None else SEX_AGE[sex if sex in SEX_AGE else "m"]
    sub = F[(F.sex == sex) & (F.age == x) & (F.basis == basis) & (F.model == model)
            & (F.selection == sel) & (F.rate == rate)
            & (F.cohort_year == ("" if basis == "period" or basis == "period_raw" else y0))]
    assert len(sub) == 1, (sex, basis, rate, model, sel, y0, len(sub))
    return float(sub.a12.iloc[0])


R: dict = {}

R["retirement_age_m"] = SEX_AGE["m"]
R["retirement_age_f"] = SEX_AGE["f"]
R["base_cohort_year"] = 2026
R["eiopa_curve_date"] = EIOPA_DATE
R["eiopa_curve_id"] = EIOPA_TAG
R["eiopa_spot_1y"] = float(EIOPA_SPOT[0])
R["eiopa_spot_10y"] = float(EIOPA_SPOT[9])
R["eiopa_spot_20y"] = float(EIOPA_SPOT[19])
R["dom_yield_15y"] = DOM_YIELD
R["headline_rate_key"] = HEAD
R["n_paths_valued"] = int(N_PATHS)
R["seed"] = SEED

for sex, x in SEX_AGE.items():
    tag = f"{sex}{x}"
    for rk in RATES:
        R[f"a12_{tag}_period_{rk}"] = f(sex, "period", rk)
        R[f"a12_{tag}_cohort_{rk}"] = f(sex, "cohort", rk)
        R[f"a12_{tag}_period_raw_{rk}"] = f(sex, "period_raw", rk)
    for y0 in COHORT_YEARS[1:]:
        R[f"a12_{tag}_cohort_{HEAD}_{y0}"] = f(sex, "cohort", HEAD, y0=y0)
        R[f"a12_{tag}_cohort_eiopa_{y0}"] = f(sex, "cohort", "eiopa", y0=y0)
    R[f"a12_{tag}_cohort_{HEAD}_2026"] = f(sex, "cohort", HEAD)
    R[f"ex_cohort_{tag}"] = float(la.ex_curtate(cohort_qx("lc", sex, x, 2026)))
    R[f"ex_period_{tag}"] = float(la.ex_curtate(period_qx("lc", sex, x)))

R["unisex_weight_m"] = W_M
R["unisex_weight_f"] = W_F
R["unisex_weight_source"] = UNISEX_NOTE
for rk in RATES:
    au64 = f("u", "cohort", rk, age=SEX_AGE["m"])
    au62 = f("u", "cohort", rk, age=SEX_AGE["f"])
    R[f"a12_unisex_m64_cohort_{rk}"] = au64
    R[f"a12_unisex_f62_cohort_{rk}"] = au62
    R[f"a12_unisex_cohort_{rk}"] = W_M * au64 + W_F * au62
    R[f"a12_unisex_m64_period_{rk}"] = f("u", "period", rk, age=SEX_AGE["m"])
    R[f"a12_unisex_f62_period_{rk}"] = f("u", "period", rk, age=SEX_AGE["f"])
R[f"unisex_crosssubsidy_m_{HEAD}"] = (R[f"a12_unisex_m64_cohort_{HEAD}"]
                                      / R[f"a12_m64_cohort_{HEAD}"] - 1.0)
R[f"unisex_crosssubsidy_f_{HEAD}"] = (R[f"a12_unisex_f62_cohort_{HEAD}"]
                                      / R[f"a12_f62_cohort_{HEAD}"] - 1.0)

for sex, x in SEX_AGE.items():
    for y0 in SYSTEM_YEARS:
        av = f(sex, "period_vintage", HEAD, y0=y0)
        R[f"a12_{sex}{x}_period_{HEAD}_{y0}"] = av
        R[f"a12_{sex}{x}_period_eiopa_{y0}"] = f(sex, "period_vintage", "eiopa", y0=y0)
        R[f"gap_pct_{sex}_{y0}_r3"] = f(sex, "cohort", HEAD, y0=y0) / av - 1.0
        R[f"gap_pct_stale2023_{sex}_{y0}_r3"] = (
            f(sex, "cohort", HEAD, y0=y0) / R[f"a12_{sex}{x}_period_{HEAD}"] - 1.0)
    R[f"gap_pct_{sex}_vintage_2040_minus_2026"] = (
        R[f"gap_pct_{sex}_2040_r3"] - R[f"gap_pct_{sex}_2026_r3"])
    R[f"gap_pct_{sex}_stale_component_2040"] = (
        R[f"gap_pct_stale2023_{sex}_2040_r3"] - R[f"gap_pct_{sex}_2040_r3"])
R["period_vintage_note"] = (
    "a12_*_period_i3_YYYY is the annuity factor on the projected period table for "
    "calendar year YYYY held constant thereafter, i.e. the table an insurer pricing in "
    "YYYY would hold if it ignored future improvement but used current experience. "
    "gap_pct_{sex}_YYYY_r3 = cohort/period(YYYY) - 1 is the genuine mispricing; "
    "gap_pct_stale2023_* keeps the 2023 comparator and therefore also carries base-table "
    "staleness. The difference of the two is the staleness component."
)

h2_all = []
for sex, x in SEX_AGE.items():
    for rk in RATES:
        g = R[f"a12_{sex}{x}_cohort_{rk}"] / R[f"a12_{sex}{x}_period_{rk}"] - 1.0
        R[f"h2_understatement_{sex}_{rk}"] = g
        h2_all.append(g)
        graw = (R[f"a12_{sex}{x}_cohort_{rk}"]
                / R[f"a12_{sex}{x}_period_raw_{rk}"] - 1.0)
        R[f"h2_understatement_raw2023_{sex}_{rk}"] = graw
    for y0 in COHORT_YEARS[1:]:
        R[f"h2_understatement_{sex}_{HEAD}_{y0}"] = (
            R[f"a12_{sex}{x}_cohort_{HEAD}_{y0}"] / R[f"a12_{sex}{x}_period_{HEAD}"] - 1.0)
R["h2_supported"] = bool(all(g > 0 for g in h2_all))
R["h2_min_gap"] = float(min(h2_all))
R["h2_max_gap"] = float(max(h2_all))

for sex, x in SEX_AGE.items():
    for basis in ("period", "cohort"):
        a = R[f"a12_{sex}{x}_{basis}_{HEAD}"]
        R[f"monthly_pension_per_1m_mkd_{basis}_{sex}"] = 1e6 / (12.0 * a)
        R[f"annual_pension_per_1mkd_{basis}_{sex}"] = 1.0 / a
    R[f"monthly_pension_drop_cohort_vs_period_{sex}"] = (
        R[f"monthly_pension_per_1m_mkd_cohort_{sex}"]
        / R[f"monthly_pension_per_1m_mkd_period_{sex}"] - 1.0)

shock_delta = {}
for sex, x in SEX_AGE.items():
    q = cohort_qx("lc", sex, x, 2026)
    qs = la.scale_qx(q, SHOCK)
    for rk, (_, vfun) in RATES.items():
        d = la.a_due_m(qs, vfun) / la.a_due_m(q, vfun) - 1.0
        R[f"bel_shock20_delta_{sex}_{rk}"] = d
        shock_delta[(sex, rk)] = d
    qp = period_qx("lc", sex, x)
    R[f"bel_shock20_delta_period_{sex}_{HEAD}"] = (
        la.a_due_m(la.scale_qx(qp, SHOCK), RATES[HEAD][1])
        / la.a_due_m(qp, RATES[HEAD][1]) - 1.0)
    R[f"ex_shock20_{sex}{x}"] = float(la.ex_curtate(qs))
    R[f"ex_shock20_gain_years_{sex}"] = float(la.ex_curtate(qs) - la.ex_curtate(q))

QUANT = {"90": 0.90, "95": 0.95, "99": 0.99, "995": 0.995}
path_a12 = {}
for sex, x in SEX_AGE.items():
    Qp = sims_cohort_diag(sex, x, 2026)
    assert Qp.shape[1] == OMEGA - x + 1
    path_a12[sex] = {}
    qc = cohort_qx("lc", sex, x, 2026)
    for rk, (_, vfun) in RATES.items():
        A = la.a_due_m_paths(Qp, vfun)
        path_a12[sex][rk] = A
        central = la.a_due_m(qc, vfun)
        for lbl, p in QUANT.items():
            R[f"bel_var{lbl}_delta_{sex}_{rk}"] = float(np.quantile(A, p) / central - 1.0)
        R[f"bel_paths_mean_delta_{sex}_{rk}"] = float(A.mean() / central - 1.0)
        R[f"bel_paths_median_delta_{sex}_{rk}"] = float(np.median(A) / central - 1.0)
        R[f"a12_{sex}{x}_cohort_{rk}_p995"] = float(np.quantile(A, 0.995))
        R[f"a12_{sex}{x}_cohort_{rk}_p005"] = float(np.quantile(A, 0.005))
    _A = path_a12[sex][HEAD]
    _j = int(np.argsort(_A)[min(int(np.ceil(0.995 * len(_A))) - 1, len(_A) - 1)])
    R[f"ex_var995_path_{sex}{x}"] = float(la.ex_curtate(Qp[_j]))
    R[f"ex_var995_path_gain_years_{sex}"] = float(
        la.ex_curtate(Qp[_j]) - la.ex_curtate(qc))
    vfun = RATES[HEAD][1]
    A = path_a12[sex][HEAD]
    target = float(np.quantile(A, 0.995))
    lam = equiv_multiplier(qc, vfun, target)
    R[f"var995_equiv_qx_multiplier_{sex}"] = float(lam)

    from scipy.stats import binom as _binom
    n_, p_ = len(A), 0.995
    r_ = int(max(1, _binom.ppf(0.025, n_, p_)))
    s_ = int(min(n_, _binom.ppf(0.975, n_, p_) + 1))
    As = np.sort(A)
    a_lo, a_hi = float(As[r_ - 1]), float(As[s_ - 1])
    R[f"bel_var995_delta_{sex}_{HEAD}_ci_lo"] = float(a_lo / la.a_due_m(qc, vfun) - 1.0)
    R[f"bel_var995_delta_{sex}_{HEAD}_ci_hi"] = float(a_hi / la.a_due_m(qc, vfun) - 1.0)
    m_hi = equiv_multiplier(qc, vfun, a_lo)
    m_lo = equiv_multiplier(qc, vfun, a_hi)
    R[f"var995_equiv_qx_multiplier_{sex}_ci_lo"] = float(m_lo)
    R[f"var995_equiv_qx_multiplier_{sex}_ci_hi"] = float(m_hi)
    R[f"var995_equiv_qx_shock_{sex}_ci_lo"] = float(1.0 - m_hi)
    R[f"var995_equiv_qx_shock_{sex}_ci_hi"] = float(1.0 - m_lo)
    R[f"var995_ci_order_stats_{sex}"] = f"order statistics {r_} and {s_} of {n_}"
    R[f"var995_equiv_qx_shock_pct_{sex}"] = float(1.0 - lam)
    R[f"ex_var995_{sex}{x}"] = float(la.ex_curtate(la.scale_qx(qc, lam)))
    R[f"ex_var995_gain_years_{sex}"] = float(
        la.ex_curtate(la.scale_qx(qc, lam)) - la.ex_curtate(qc))

W = {"m": W_M, "f": W_F}
vfun = RATES[HEAD][1]
A_m, A_f = path_a12["m"][HEAD], path_a12["f"][HEAD]
assert len(A_m) == len(A_f) == N_PATHS
bel_mixed_paths = W["m"] * A_m + W["f"] * A_f
central_mixed = sum(W[s_] * R[f"a12_{s_}{SEX_AGE[s_]}_cohort_{HEAD}"] for s_ in SEX_AGE)
shock_mixed = sum(
    W[s_] * la.a_due_m(la.scale_qx(cohort_qx("lc", s_, SEX_AGE[s_], 2026), SHOCK), vfun)
    for s_ in SEX_AGE)
R["mixed_weight_m"] = W["m"]
R["mixed_weight_f"] = W["f"]
R[f"a12_mixed_cohort_{HEAD}"] = float(central_mixed)
R[f"bel_shock20_delta_mixed_{HEAD}"] = float(shock_mixed / central_mixed - 1.0)
for lbl, pq_ in QUANT.items():
    R[f"bel_var{lbl}_delta_mixed_{HEAD}"] = float(
        np.quantile(bel_mixed_paths, pq_) / central_mixed - 1.0)
R["h3_shock_vs_var_ratio_mixed"] = float(
    R[f"bel_shock20_delta_mixed_{HEAD}"] / R[f"bel_var995_delta_mixed_{HEAD}"])
_rng_perm = np.random.default_rng(SEED)
perm = _rng_perm.permutation(N_PATHS)
bel_mixed_indep = W["m"] * A_m + W["f"] * A_f[perm]
R[f"bel_var995_delta_mixed_indep_{HEAD}"] = float(
    np.quantile(bel_mixed_indep, 0.995) / central_mixed - 1.0)
_indep = [np.quantile(W["m"] * A_m + W["f"] * A_f[_rng_perm.permutation(N_PATHS)], 0.995)
          for _ in range(200)]
R[f"bel_var995_delta_mixed_indep_{HEAD}_mean200"] = float(
    np.mean(_indep) / central_mixed - 1.0)
R[f"bel_var995_delta_mixed_indep_{HEAD}_sd200"] = float(
    np.std(_indep, ddof=1) / central_mixed)
R["mixed_indep_n_permutations"] = 200
R["mixed_indep_vs_joint_pct_mean200"] = float(
    R[f"bel_var995_delta_mixed_indep_{HEAD}_mean200"]
    / R[f"bel_var995_delta_mixed_{HEAD}"] - 1.0)

MAPAS_W_M = 0.531
R["mixed_mapas_weight_m"] = MAPAS_W_M
R["mixed_mapas_weight_source"] = (
    "МАПАС membership share of men, 53.1%: men / all members in "
    "analysis/system/mapas_chart53_membership.csv (МАПАС 2025 report, chart 5.3). Not present as a key in results/system.json."
)
_cm_mapas = (MAPAS_W_M * R[f"a12_m{SEX_AGE['m']}_cohort_{HEAD}"]
             + (1 - MAPAS_W_M) * R[f"a12_f{SEX_AGE['f']}_cohort_{HEAD}"])
R[f"a12_mixed_mapasw_cohort_{HEAD}"] = float(_cm_mapas)
R[f"bel_var995_delta_mixed_mapasw_{HEAD}"] = float(
    np.quantile(MAPAS_W_M * A_m + (1 - MAPAS_W_M) * A_f, 0.995) / _cm_mapas - 1.0)
R[f"bel_shock20_delta_mixed_mapasw_{HEAD}"] = float(
    (MAPAS_W_M * la.a_due_m(la.scale_qx(cohort_qx("lc", "m", SEX_AGE["m"], 2026), SHOCK), vfun)
     + (1 - MAPAS_W_M) * la.a_due_m(la.scale_qx(cohort_qx("lc", "f", SEX_AGE["f"], 2026), SHOCK), vfun))
    / _cm_mapas - 1.0)
R[f"bel_var99_delta_mixed_indep_{HEAD}"] = float(
    np.quantile(bel_mixed_indep, 0.99) / central_mixed - 1.0)
R["mixed_indep_vs_joint_pct"] = float(
    R[f"bel_var995_delta_mixed_indep_{HEAD}"] / R[f"bel_var995_delta_mixed_{HEAD}"] - 1.0)
R["path_a12_corr_mf"] = float(np.corrcoef(A_m, A_f)[0, 1])
R["mixed_var_note"] = (
    "Mixed book = w(m) men aged 64 + w(f) women aged 62, one unit of annual pension each, "
    "valued path by path on the SAME sim index (the mortality simulation draws the sexes jointly, "
    "rho_hat = 0.782). The independence counterfactual re-pairs the female sim indices at "
    "random (seed 2026) and is a counterfactual only -- the joint figure is the result."
)

for sex, x in SEX_AGE.items():
    q = cohort_qx("lc", sex, x, 2026)
    tg, S = la.survival_grid(q)
    wts = S * RATES[HEAD][1](tg)
    wsum = wts.sum()
    with np.errstate(divide="ignore"):
        H = -np.log(np.where(S > 0, S, np.nan))
    ok = np.isfinite(H)
    R[f"hbar_cumhazard_{sex}"] = float((wts[ok] * H[ok]).sum() / wts[ok].sum())
    R[f"mean_attained_age_at_payment_{sex}"] = float(x + (wts * tg).sum() / wsum)
    R[f"shock_sensitivity_{sex}"] = float(
        R[f"bel_shock20_delta_{sex}_{HEAD}"] / legal["sii_longevity_shock_pct"])
R["equiv_shock_ratio_var_f_over_m"] = float(
    R[f"bel_var995_delta_f_{HEAD}"] / R[f"bel_var995_delta_m_{HEAD}"])
R["equiv_shock_ratio_sens_f_over_m"] = float(
    R["shock_sensitivity_f"] / R["shock_sensitivity_m"])
R["equiv_shock_inversion_holds"] = bool(
    R["equiv_shock_ratio_var_f_over_m"] > R["equiv_shock_ratio_sens_f_over_m"])
R["equiv_shock_inversion_note"] = (
    "The female equivalent permanent shock exceeds the male one because a shock moves "
    "the BEL in proportion to the discounted-survival-weighted cumulative hazard, which "
    "is LOWER for women; longer duration raises, not lowers, that elasticity, and the "
    "female mean attained age at payment is in fact the lower of the two. The inversion "
    "is not arithmetically necessary: it requires VaR_f/VaR_m > sens_f/sens_m."
)

_nowin = {sx: MORT / f"qx_sims_{sx}_nowinsor.parquet" for sx in SEX_AGE}
if all(v.exists() for v in _nowin.values()):
    for sex, x in SEX_AGE.items():
        _d = ds.dataset(_nowin[sex], format="parquet")
        _tb = _d.to_table(
            filter=((ds.field("year") - ds.field("age")) == (2026 - x))
            & (ds.field("age") >= x), columns=["sim", "age", "qx"])
        _Q = (_tb.to_pandas().pivot(index="sim", columns="age", values="qx")
              .sort_index().to_numpy(float))
        _A = la.a_due_m_paths(_Q, RATES[HEAD][1])
        _c = R[f"a12_{sex}{x}_cohort_{HEAD}"]
        R[f"bel_var995_delta_{sex}_{HEAD}_nowinsor"] = float(
            np.quantile(_A, 0.995) / _c - 1.0)
        R[f"var995_equiv_qx_shock_{sex}_nowinsor"] = float(
            1.0 - equiv_multiplier(cohort_qx("lc", sex, x, 2026), RATES[HEAD][1],
                                   float(np.quantile(_A, 0.995))))
        R[f"nowinsor_n_paths_{sex}"] = int(_Q.shape[0])
    R["nowinsor_available"] = True
else:
    for sex in SEX_AGE:
        R[f"bel_var995_delta_{sex}_{HEAD}_nowinsor"] = None
        R[f"var995_equiv_qx_shock_{sex}_nowinsor"] = None
    R["nowinsor_available"] = False
    R["nowinsor_note"] = (
        "Note: results/mortality.json publishes e65_*_nowinsor quantiles, but no "
        "qx_sims_{m,f}_nowinsor.parquet exists, and the exported sims carry qx AFTER "
        "the Kannisto closure, so the guard-rail cannot be undone downstream. "
        "Pricing the run-off VaR without the guard-rail needs that export from the mortality projection "
        "(5,000 paths, schema sim/year/age/qx). Not approximated."
    )

_ts = {sx: MORT / f"qx_central_{sx}_trendstationary.parquet" for sx in SEX_AGE}
_tss = {sx: MORT / f"qx_sims_{sx}_trendstationary.parquet" for sx in SEX_AGE}
if all(v.exists() for v in _ts.values()):
    for sex in SEX_AGE:
        SURF[("trendstat", sex)] = load_surface(_ts[sex])
    for sex, x in SEX_AGE.items():
        R[f"trendstat_a12_{sex}{x}_cohort_{HEAD}"] = float(
            la.a_due_m(cohort_qx("trendstat", sex, x, 2026), RATES[HEAD][1]))
    R["trendstat_available"] = True
else:
    R["trendstat_available"] = False
for sex in SEX_AGE:
    if all(v.exists() for v in _tss.values()):
        _d = ds.dataset(_tss[sex], format="parquet")
        _x = SEX_AGE[sex]
        _tb = _d.to_table(
            filter=((ds.field("year") - ds.field("age")) == (2026 - _x))
            & (ds.field("age") >= _x), columns=["sim", "age", "qx"])
        _Q = (_tb.to_pandas().pivot(index="sim", columns="age", values="qx")
              .sort_index().to_numpy(float))
        _A = la.a_due_m_paths(_Q, RATES[HEAD][1])
        R[f"bel_var995_delta_{sex}_{HEAD}_trendstat"] = float(
            np.quantile(_A, 0.995) / R[f"a12_{sex}{_x}_cohort_{HEAD}"] - 1.0)
    else:
        R[f"bel_var995_delta_{sex}_{HEAD}_trendstat"] = None
if not all(v.exists() for v in _tss.values()):
    R["trendstat_note"] = (
        "Note: results/mortality.json publishes e65_*_trendstationary quantiles but "
        "no qx_{central,sims}_{m,f}_trendstationary.parquet. The trend-stationary "
        "run-off VaR -- the lower bound of the projection-uncertainty range -- needs "
        "that export from the mortality projection. Not approximated."
    )

H3_THRESHOLD = 0.10
R["h3_threshold_rel"] = H3_THRESHOLD
ratios = {}
for sex in SEX_AGE:
    r = R[f"bel_shock20_delta_{sex}_{HEAD}"] / R[f"bel_var995_delta_{sex}_{HEAD}"]
    R[f"h3_shock_vs_var_ratio_{sex}"] = float(r)
    ratios[sex] = r
    for rk in RATES:
        R[f"h3_shock_vs_var_ratio_{sex}_{rk}"] = float(
            R[f"bel_shock20_delta_{sex}_{rk}"] / R[f"bel_var995_delta_{sex}_{rk}"])
R["h3_supported"] = bool(all(abs(r - 1.0) > H3_THRESHOLD for r in ratios.values()))
R["h3_supported_strict_band"] = bool(
    all((r < 0.8) or (r > 1.25) for r in ratios.values()))
dirs = {sex: ("shock_exceeds_var" if ratios[sex] > 1 else "var_exceeds_shock")
        for sex in ratios}
R["h3_direction_m"] = dirs["m"]
R["h3_direction_f"] = dirs["f"]
R["h3_direction"] = dirs["m"] if dirs["m"] == dirs["f"] else "mixed"
R["h3_supported_runoff"] = R["h3_supported"]
R["h3_direction_runoff"] = R["h3_direction"]
R["h3_direction_m_runoff"] = dirs["m"]
R["h3_direction_f_runoff"] = dirs["f"]
for _s in SEX_AGE:
    R[f"h3_shock_vs_var_ratio_runoff_{_s}"] = R[f"h3_shock_vs_var_ratio_{_s}"]
R["h3_basis_note"] = (
    "Unsuffixed h3_* keys are the RUN-OFF basis, kept for backward compatibility. "
    "The regulatory (one-year) basis is h3_*_oneyear; the two point in OPPOSITE "
    "directions and must never be quoted without naming the horizon."
)

for sex, x in SEX_AGE.items():
    q = cohort_qx("lc", sex, x, 2026)
    qs = la.scale_qx(q, SHOCK)
    for rk in (HEAD, "eiopa"):
        vfun = RATES[rk][1]
        bel = la.a_due_m(q, vfun)
        scr0 = la.a_due_m(qs, vfun) - bel
        suff = "" if rk == HEAD else f"_{rk}"
        rm6 = la.risk_margin(q, vfun, scr0, COC6, taper=False)
        rm475 = la.risk_margin(q, vfun, scr0, COC475, taper=True)
        rm475_nt = la.risk_margin(q, vfun, scr0, COC475, taper=False)
        R[f"scr_longevity_pct_bel_{sex}{suff}"] = float(scr0 / bel)
        R[f"risk_margin_pct_bel_{sex}_coc6{suff}"] = float(rm6 / bel)
        R[f"risk_margin_pct_bel_{sex}_coc475{suff}"] = float(rm475 / bel)
        R[f"risk_margin_pct_bel_{sex}_coc475_notaper{suff}"] = float(rm475_nt / bel)
        R[f"risk_margin_change_2027_{sex}{suff}"] = float(rm475 / rm6 - 1.0)
        _bel = la.bel_runoff(q, vfun)
        _t = np.arange(len(_bel), dtype=float)
        R[f"rm_discounted_scr_sum_{sex}{suff}"] = float(
            ((_bel / _bel[0]) * vfun(_t + 1.0)).sum())
        if rk == HEAD:
            _tg, _S = la.survival_grid(q)
            _w = _S * vfun(_tg)
            R[f"bel_duration_{sex}"] = float((_tg * _w).sum() / _w.sum())
            R[f"risk_margin_pct_bel_{sex}_coc6_varscr"] = float(
                la.risk_margin(q, vfun, R[f"bel_var995_delta_{sex}_{HEAD}"] * bel,
                               COC6) / bel)
for _s in SEX_AGE:
    R[f"risk_margin_pct_bel_{_s}_coc6_sii"] = R[f"risk_margin_pct_bel_{_s}_coc6_eiopa"]
    R[f"risk_margin_pct_bel_{_s}_coc475_sii"] = R[f"risk_margin_pct_bel_{_s}_coc475_eiopa"]
R["risk_margin_basis_note"] = (
    "Art. 37(1) discounts at the BASIC RISK-FREE CURVE, so the Solvency II figures are "
    "the *_eiopa / *_sii keys. The flat-3% versions are kept only for comparability with "
    "the flat-rate annuity factors and are labelled as such. The Solvency II risk-margin figures are "
    "risk_margin_pct_bel_{m,f}_coc6_sii and ..._coc475_sii."
)
R["risk_margin_paper_key_coc6"] = "risk_margin_pct_bel_{sex}_coc6_sii"
R["risk_margin_paper_key_coc475"] = "risk_margin_pct_bel_{sex}_coc475_sii"
R["rm_taper_formula"] = "RM = CoC * sum_{t>=0} max(0.96^t; 50%) * SCR(t) / (1+r(t+1))^(t+1)"
R["rm_taper_lambda"] = 0.96
R["rm_taper_floor"] = 0.5
R["rm_taper_source"] = (
    "C(2025) 7206 final/2, 29.10.2025, point (8) amending Art. 37(1) of Delegated "
    "Regulation (EU) 2015/35 -- formula read verbatim from the Commission PDF cited in "
    "research/legal/brief.md D2; applies from 30.01.2027. Recital (9) states the factor "
    "'ensures an annual reduction of risks of at least 3,5%' and caps the reduction at 50%."
)
R["coc_rate_base"] = COC6
R["coc_rate_2027"] = COC475

for sel in (0.8, 0.9):
    tag = f"{int(sel*10):02d}"
    for sex, x in SEX_AGE.items():
        for basis in ("period", "cohort"):
            R[f"selection_{tag}_a12_{sex}{x}_{basis}_{HEAD}"] = f(sex, basis, HEAD, sel=sel)
        R[f"selection_{tag}_bel_delta_{sex}_{HEAD}"] = (
            f(sex, "cohort", HEAD, sel=sel) / f(sex, "cohort", HEAD) - 1.0)
        R[f"selection_{tag}_h2_understatement_{sex}_{HEAD}"] = (
            f(sex, "cohort", HEAD, sel=sel) / f(sex, "period", HEAD, sel=sel) - 1.0)
        qsel = la.scale_qx(cohort_qx("lc", sex, x, 2026), sel)
        R[f"selection_{tag}_bel_shock20_delta_{sex}_{HEAD}"] = float(
            la.a_due_m(la.scale_qx(qsel, SHOCK), RATES[HEAD][1])
            / la.a_due_m(qsel, RATES[HEAD][1]) - 1.0)

for sex, x in SEX_AGE.items():
    for rk in (HEAD, "eiopa"):
        suff = "" if rk == HEAD else f"_{rk}"
        R[f"robust_cbd_a12_{sex}{x}_cohort_{rk}"] = f(sex, "cohort", rk, model="cbd")
        R[f"robust_cbd_a12_{sex}{x}_period_{rk}"] = f(sex, "period", rk, model="cbd")
    R[f"robust_cbd_diff_pct_{sex}"] = (
        R[f"robust_cbd_a12_{sex}{x}_cohort_{HEAD}"] / R[f"a12_{sex}{x}_cohort_{HEAD}"] - 1.0)
    R[f"robust_cbd_h2_understatement_{sex}_{HEAD}"] = (
        f(sex, "cohort", HEAD, model="cbd") / f(sex, "period", HEAD, model="cbd") - 1.0)
    qc = cohort_qx("cbd", sex, x, 2026)
    R[f"robust_cbd_bel_shock20_delta_{sex}_{HEAD}"] = float(
        la.a_due_m(la.scale_qx(qc, SHOCK), RATES[HEAD][1])
        / la.a_due_m(qc, RATES[HEAD][1]) - 1.0)
    R[f"robust_cbd_shock20_diff_vs_lc_{sex}"] = (
        R[f"robust_cbd_bel_shock20_delta_{sex}_{HEAD}"]
        - R[f"bel_shock20_delta_{sex}_{HEAD}"])

if HAS_COHERENT:
    for sex, x in SEX_AGE.items():
        for rk in (HEAD, "eiopa"):
            R[f"coherent_a12_{sex}{x}_cohort_{rk}"] = f(sex, "cohort", rk, model="coherent")
        R[f"coherent_a12_{sex}{x}_period_{HEAD}"] = f(sex, "period", HEAD, model="coherent")
        R[f"coherent_diff_pct_{sex}"] = (
            R[f"coherent_a12_{sex}{x}_cohort_{HEAD}"] / R[f"a12_{sex}{x}_cohort_{HEAD}"] - 1.0)
        R[f"coherent_h2_understatement_{sex}_{HEAD}"] = (
            f(sex, "cohort", HEAD, model="coherent")
            / f(sex, "period", HEAD, model="coherent") - 1.0)
    R["coherent_source"] = (
        "qx_central_coherent_{m,f}.parquet (analysis/mortality/, Li-Lee "
        "coherent projection); prices the sex-gap coherence check."
    )
else:
    R["coherent_source"] = None

for sex, x in SEX_AGE.items():
    q = cohort_qx("lc", sex, x, 2026)
    R[f"woolhouse_diff_{sex}_{HEAD}"] = float(
        la.a_woolhouse(q, 0.03) - la.a_due_m(q, RATES[HEAD][1]))

for sex, x in SEX_AGE.items():
    R[f"annuity_factor_{sex}_{x}_period_3pct"] = f(sex, "period", HEAD)
    R[f"annuity_factor_{sex}_{x}_cohort_3pct"] = f(sex, "cohort", HEAD)
    for y0 in SYSTEM_YEARS:
        R[f"annuity_factor_{sex}_{x}_cohort_3pct_{y0}"] = f(sex, "cohort", HEAD, y0=y0)


MAPAS_REAL_RATE_FACTOR = 0.80
i_cap_price = MAPAS_REAL_RATE_FACTOR * DOM_YIELD
R["viability_pricing_rate_cap"] = float(i_cap_price)
R["viability_pricing_rate_cap_source"] = (
    f"МАПАС Правилник за каматни стапки (Сл. весник 177/2022): real rate <= "
    f"{MAPAS_REAL_RATE_FACTOR:.0%} of a nominal rate capped by domestic 5y+ government "
    f"bond yields; {DOM_YIELD:.3%} (NBRSM 15y, 09/2026) x {MAPAS_REAL_RATE_FACTOR:.2f} "
    f"= {i_cap_price:.4%}. Binds pension companies; no ASO-side insurer bylaw exists."
)
R["viability_commission_cap_pct"] = legal["commission_cap_pct"]
R["viability_is_stylised"] = True
R["viability_note"] = (
    "STYLISED TEST, NOT A BUSINESS PLAN. No expense loading beyond the capped "
    "commission, no lapse, no reinsurance, no profit target, no investment spread above "
    "the risk-free curve. It answers one question only: at the most generous pricing "
    "rate the domestic rules permit, does the interest margin cover the cost of "
    "longevity capital?"
)

for sex, x in SEX_AGE.items():
    a_be = la.a_due_m(cohort_qx("lc", sex, x, 2026), RATES["eiopa"][1])
    rm_rate = R[f"risk_margin_pct_bel_{sex}_coc6_eiopa"]
    scr_rate = R[f"scr_longevity_pct_bel_{sex}_eiopa"]

    def _net(i_price, a_be=a_be, rm_rate=rm_rate, sex=sex, x=x):
        a_p = la.a_due_m(cohort_qx("lc", sex, x, 2026), la.flat_discount(i_price))
        margin = 1.0 - a_be / a_p
        cap_cost = rm_rate * a_be / a_p
        return margin - cap_cost - legal["commission_cap_pct"]

    a_price = la.a_due_m(cohort_qx("lc", sex, x, 2026), la.flat_discount(i_cap_price))
    R[f"viability_a12_at_cap_{sex}"] = float(a_price)
    R[f"viability_a12_best_estimate_{sex}"] = float(a_be)
    R[f"viability_margin_pct_premium_{sex}"] = float(1.0 - a_be / a_price)
    R[f"viability_capital_cost_pct_premium_{sex}"] = float(rm_rate * a_be / a_price)
    R[f"viability_scr_pct_premium_{sex}"] = float(scr_rate * a_be / a_price)
    R[f"viability_net_pct_premium_{sex}"] = float(_net(i_cap_price))
    _lo, _hi = -0.02, i_cap_price
    R[f"viability_breakeven_rate_{sex}"] = (
        float(brentq(_net, _lo, _hi, xtol=1e-10)) if _net(_lo) * _net(_hi) < 0 else None)
    _br = R[f"viability_breakeven_rate_{sex}"]
    R[f"viability_pension_at_cap_{sex}"] = float(1e6 / (12.0 * a_price))
    if _br is not None:
        _a_br = la.a_due_m(cohort_qx("lc", sex, x, 2026), la.flat_discount(_br))
        R[f"viability_pension_at_breakeven_{sex}"] = float(1e6 / (12.0 * _a_br))
        R[f"viability_pension_cut_at_breakeven_{sex}"] = float(
            (1e6 / (12.0 * _a_br)) / (1e6 / (12.0 * a_price)) - 1.0)
for sex, x in SEX_AGE.items():
    a_dom = la.a_due_m(cohort_qx("lc", sex, x, 2026), RATES["dom"][1])
    a_price = R[f"viability_a12_at_cap_{sex}"]
    rm_rate = R[f"risk_margin_pct_bel_{sex}_coc6"]
    R[f"viability_margin_pct_premium_{sex}_dombe"] = float(1.0 - a_dom / a_price)
    R[f"viability_net_pct_premium_{sex}_dombe"] = float(
        1.0 - a_dom / a_price - rm_rate * a_dom / a_price - legal["commission_cap_pct"])
for sex, x in SEX_AGE.items():
    _bal = system[f"avg_balance_at_ret_{sex}_2026_mkd"]
    _a_cap = R[f"viability_a12_at_cap_{sex}"]
    R[f"annuity_monthly_at_cap_{sex}_2026"] = float(_bal / (12.0 * _a_cap))
    _pw = system.get(f"pw_monthly_first_year_{sex}_2026")
    R[f"pw_monthly_first_year_{sex}_2026_ref"] = _pw
    R[f"annuity_at_cap_vs_pw_{sex}"] = (
        float(R[f"annuity_monthly_at_cap_{sex}_2026"] / _pw - 1.0) if _pw else None)
    _br = R[f"viability_breakeven_rate_{sex}"]
    if _br is not None:
        _a_br = la.a_due_m(cohort_qx("lc", sex, x, 2026), la.flat_discount(_br))
        R[f"annuity_monthly_at_breakeven_{sex}_2026"] = float(_bal / (12.0 * _a_br))
        R[f"annuity_at_breakeven_vs_pw_{sex}"] = (
            float(R[f"annuity_monthly_at_breakeven_{sex}_2026"] / _pw - 1.0)
            if _pw else None)
for sex, x in SEX_AGE.items():
    _br = R[f"viability_breakeven_rate_{sex}"]
    if _br is None:
        continue
    R[f"viability_breakeven_spread_below_cap_{sex}"] = float(i_cap_price - _br)
    _mult = (R[f"annuity_monthly_at_breakeven_{sex}_2026"]
             / R[f"annuity_monthly_at_cap_{sex}_2026"])
    R[f"viability_pension_multiplier_cap_to_breakeven_{sex}"] = float(_mult)
    _idx = system.get(f"annuity_monthly_{sex}_2026")
    _pw = system.get(f"pw_monthly_first_year_{sex}_2026")
    if _idx and _pw:
        R[f"annuity_indexed_at_breakeven_{sex}_2026"] = float(_idx * _mult)
        R[f"annuity_indexed_at_breakeven_vs_pw_{sex}"] = float(_idx * _mult / _pw - 1.0)
        R[f"annuity_indexed_at_cap_vs_pw_{sex}"] = float(_idx / _pw - 1.0)
R["annuity_vs_pw_chain_note"] = (
    "The chain, on the drawdown's own (CPI-indexed, real-rate) basis: at the permitted "
    "rate the indexed annuity already opens below the programmed withdrawal "
    "(annuity_indexed_at_cap_vs_pw_*); requiring the insurer to price down to breakeven "
    "multiplies the payment by viability_pension_multiplier_cap_to_breakeven_*, giving "
    "annuity_indexed_at_breakeven_vs_pw_*. The two effects must be COMPOUNDED as a "
    "ratio, not added as percentages, and both must sit on the indexed basis -- the "
    "level/nominal figures in annuity_at_{cap,breakeven}_vs_pw_* are a cross-check, not "
    "the main measure, because a level annuity front-loads income and flatters itself."
)
R["annuity_vs_pw_basis_warning"] = (
    "The annuity here is LEVEL, discounted at a NOMINAL rate; results/system.json's "
    "annuity_monthly_* and pw_monthly_first_year_* are real-rate / CPI-indexed products "
    "(system.member_choice_real_rate = 2.0%). A level annuity front-loads income, so "
    "these ratios FLATTER the annuity relative to the drawdown. They must not be "
    "multiplied together with the annuity-vs-PW gap in results/system.json: that would "
    "compound two different products' rate bases. The bases have to be reconciled before "
    "a single number is quoted."
)
R["viability_rate_cap_reconciliation"] = (
    f"Superseded derivation. An earlier version of this calculation applied 80% to the single 15y yield "
    f"({DOM_YIELD:.3%}), giving a permitted NOMINAL rate of {i_cap_price:.4%}. That was a "
    f"misreading of the bylaw. results/system.json derives the nominal cap as the lowest "
    f"of three art. 5 tests, member_choice_nominal_rate_cap = "
    f"{system.get('member_choice_nominal_rate_cap'):.5f}, and the binding constraint is "
    f"the art. 6 cost-of-living deduction giving member_choice_real_rate_cap = "
    f"{system.get('member_choice_real_rate_cap'):.5f} REAL; the art. 4 80% test does not "
    f"bind. The two nominal figures differ by "
    f"{(system.get('member_choice_nominal_rate_cap') - i_cap_price)*100:.2f} pp, and they "
    f"are not the same quantity in any case. The reading in results/system.json is correct and "
    f"the per-form results on the {system.get('member_choice_real_rate_cap'):.3%} real cap "
    f"supersede every single-rate figure derived from {i_cap_price:.4%}."
)
R["viability_viable_at_cap"] = bool(
    all(R[f"viability_net_pct_premium_{s}"] > 0 for s in SEX_AGE))
R["viability_cap_is_binding_constraint"] = False
R["viability_reading"] = (
    "The rate cap is a MAXIMUM, not a floor, so the insurer may always price below it. "
    "The caps do not make the product unviable: on a "
    "Solvency II best estimate, viability requires pricing about 1.5 pp below the "
    "permitted maximum, and the resulting pension is materially smaller. On a "
    "domestic-yield best estimate the product is viable at the cap itself."
)

R["viability_viable_at_cap_dombe"] = bool(
    all(R[f"viability_net_pct_premium_{s}_dombe"] > 0 for s in SEX_AGE))
R["viability_basis_note"] = (
    "The unsuffixed keys discount the best estimate on the EIOPA risk-free curve (Solvency II "
    "basis). The *_dombe keys discount at the domestic 15y yield, i.e. they let the "
    "insurer recognise the sovereign spread it actually earns -- the current-regime "
    "case, since North Macedonia is not under Solvency II. The two bracket the answer "
    "and both are reported."
)

_life_cap = system["life_capital_2025_mkd"]
_liab100 = system["liability_pv2025_takeup100_mkd"]
_rm_mixed = sum(W * R[f"risk_margin_pct_bel_{s}_coc6_eiopa"]
                for s, W in (("m", W_M), ("f", W_F)))
R["absorbable_rm_rate_mixed"] = float(_rm_mixed)
for _tag, _risk in (("sf", R[f"bel_shock20_delta_mixed_{HEAD}"]),
                    ("var", R[f"bel_var995_delta_mixed_{HEAD}"])):
    _rate = _risk + _rm_mixed
    _req100 = _liab100 * _rate
    R[f"absorbable_capital_rate_{_tag}"] = float(_rate)
    R[f"absorbable_required_capital_takeup100_mkd_{_tag}"] = float(_req100)
    R[f"absorbable_takeup_full_capital_{_tag}"] = float(min(1.0, _life_cap / _req100))
    R[f"absorbable_takeup_half_capital_{_tag}"] = float(min(1.0, 0.5 * _life_cap / _req100))
R["absorbable_takeup_full_capital"] = R["absorbable_takeup_full_capital_sf"]
R["absorbable_takeup_half_capital"] = R["absorbable_takeup_half_capital_sf"]
R["absorbable_note"] = (
    "Take-up rate at which required longevity capital (SCR + risk margin, mixed book) "
    "equals the whole 2025 life-sector capital, and half of it. Liability PV from "
    "results/system.json (liability_pv2025_takeup100_mkd), capital from ASO returns. "
    "Assumes capital scales linearly with annuitised balances and that longevity is the "
    "only capital charge -- both optimistic, so these are UPPER bounds on absorption."
)


PI_LR = float(system["member_choice_inflation_lr"])
I_REAL_CAP = float(system["member_choice_real_rate_cap"])
I_REAL_ANALYST = float(system["member_choice_real_rate"])
FORMS = {"cpi": PI_LR, "1pct": 0.01, "3pct": 0.03}
R["viability_inflation_lr"] = PI_LR
R["viability_real_rate_cap"] = I_REAL_CAP
R["viability_rate_comparability_note"] = (
    f"NOT the same quantity. analysis/system §8's 4.17% is the EFFECTIVE rate "
    f"j = (1+i_real)(1+pi)/(1+g) - 1 for the fixed-nominal-1% form at i_real = "
    f"{I_REAL_ANALYST:.2%}, pi = {PI_LR:.2%}; the earlier 4.16% here was 0.8 x the "
    f"15y nominal yield read as a nominal cap. The near-equality is a coincidence. The "
    f"binding legal cap is the art. 6 cost-of-living deduction at {I_REAL_CAP:.3%} REAL, "
    f"so the per-form results below supersede the single-rate ones."
)


def _j(i_real, g):
    return (1.0 + i_real) * (1.0 + PI_LR) / (1.0 + g) - 1.0


for sex, x in SEX_AGE.items():
    _q = cohort_qx("lc", sex, x, 2026)
    _tgt = la.a_due_m(_q, RATES["eiopa"][1])
    _i_flat = brentq(lambda i: la.a_due_m(_q, la.flat_discount(i)) - _tgt, -0.02, 0.15,
                     xtol=1e-12)
    R[f"viability_eiopa_flat_equivalent_{sex}"] = float(_i_flat)
    _i_real_be = (1.0 + _i_flat) / (1.0 + PI_LR) - 1.0
    R[f"viability_real_rate_be_{sex}"] = float(_i_real_be)
    _bal = system[f"avg_balance_at_ret_{sex}_2026_mkd"]
    _pw = system[f"pw_monthly_first_year_{sex}_2026"]

    for _f, _g in FORMS.items():
        def _net_real(i_real, g=_g, q=_q, i_be=_i_real_be):
            a_p = la.a_due_m(q, la.flat_discount(_j(i_real, g)))
            a_b = la.a_due_m(q, la.flat_discount(_j(i_be, g)))
            scr = la.a_due_m(la.scale_qx(q, SHOCK),
                             la.flat_discount(_j(i_be, g))) - a_b
            rm = la.risk_margin(q, la.flat_discount(_j(i_be, g)), scr, COC6)
            return (1.0 - a_b / a_p) - legal["commission_cap_pct"] - rm / a_p

        def _pay(i_real, g=_g, q=_q, bal=_bal):
            return bal / (12.0 * la.a_due_m(q, la.flat_discount(_j(i_real, g))))

        R[f"viability_j_price_{sex}_idx{_f}"] = float(_j(I_REAL_CAP, _g))
        R[f"viability_net_pct_premium_{sex}_idx{_f}"] = float(_net_real(I_REAL_CAP))
        R[f"viability_net_pct_premium_{sex}_idx{_f}_at_analyst_rate"] = float(
            _net_real(I_REAL_ANALYST))
        _br = (brentq(_net_real, -0.05, I_REAL_CAP, xtol=1e-12)
               if _net_real(-0.05) * _net_real(I_REAL_CAP) < 0 else None)
        R[f"viability_breakeven_real_rate_{sex}_idx{_f}"] = (
            float(_br) if _br is not None else None)
        if _br is not None:
            R[f"viability_monthly_at_breakeven_{sex}_idx{_f}"] = float(_pay(_br))
            R[f"viability_breakeven_vs_pw_{sex}_idx{_f}"] = float(_pay(_br) / _pw - 1.0)
        R[f"viability_monthly_at_cap_{sex}_idx{_f}"] = float(_pay(I_REAL_CAP))
        R[f"viability_cap_vs_pw_{sex}_idx{_f}"] = float(_pay(I_REAL_CAP) / _pw - 1.0)
        _att = (brentq(lambda i: _pay(i) - _pw, -0.05, 0.15, xtol=1e-12)
                if (_pay(-0.05) - _pw) * (_pay(0.15) - _pw) < 0 else None)
        R[f"viability_attractive_real_rate_{sex}_idx{_f}"] = (
            float(_att) if _att is not None else None)
        R[f"viability_any_rate_works_{sex}_idx{_f}"] = bool(
            _att is not None and _br is not None
            and _att <= min(_br, I_REAL_CAP) + 1e-12)

PI_PEG = 0.02
R["viability_inflation_peg_consistent"] = PI_PEG
for sex, x in SEX_AGE.items():
    _q = cohort_qx("lc", sex, x, 2026)
    _bal = system[f"avg_balance_at_ret_{sex}_2026_mkd"]
    _pw = system[f"pw_monthly_first_year_{sex}_2026"]
    _i_flat = R[f"viability_eiopa_flat_equivalent_{sex}"]
    _i_real_be2 = (1.0 + _i_flat) / (1.0 + PI_PEG) - 1.0
    R[f"viability_real_rate_be_{sex}_pi2"] = float(_i_real_be2)

    def _j2(i_real, g):
        return (1.0 + i_real) * (1.0 + PI_PEG) / (1.0 + g) - 1.0

    for _f, _g in FORMS.items():
        def _net2(i_real, g=_g, q=_q, i_be=_i_real_be2):
            a_p = la.a_due_m(q, la.flat_discount(_j2(i_real, g)))
            a_b = la.a_due_m(q, la.flat_discount(_j2(i_be, g)))
            scr = la.a_due_m(la.scale_qx(q, SHOCK),
                             la.flat_discount(_j2(i_be, g))) - a_b
            rm = la.risk_margin(q, la.flat_discount(_j2(i_be, g)), scr, COC6)
            return (1.0 - a_b / a_p) - legal["commission_cap_pct"] - rm / a_p

        def _pay2(i_real, g=_g, q=_q, bal=_bal):
            return bal / (12.0 * la.a_due_m(q, la.flat_discount(_j2(i_real, g))))

        R[f"viability_net_pct_premium_{sex}_idx{_f}_pi2"] = float(_net2(I_REAL_CAP))
        _br2 = (brentq(_net2, -0.05, I_REAL_CAP, xtol=1e-12)
                if _net2(-0.05) * _net2(I_REAL_CAP) < 0 else None)
        R[f"viability_breakeven_real_rate_{sex}_idx{_f}_pi2"] = (
            float(_br2) if _br2 is not None else None)
        if _br2 is not None:
            R[f"viability_monthly_at_breakeven_{sex}_idx{_f}_pi2"] = float(_pay2(_br2))
            R[f"viability_breakeven_vs_pw_{sex}_idx{_f}_pi2"] = float(
                _pay2(_br2) / _pw - 1.0)
        _att2 = (brentq(lambda i: _pay2(i) - _pw, -0.05, 0.15, xtol=1e-12)
                 if (_pay2(-0.05) - _pw) * (_pay2(0.15) - _pw) < 0 else None)
        R[f"viability_attractive_real_rate_{sex}_idx{_f}_pi2"] = (
            float(_att2) if _att2 is not None else None)
        R[f"viability_any_rate_works_{sex}_idx{_f}_pi2"] = bool(
            _att2 is not None and _br2 is not None
            and _att2 <= min(_br2, I_REAL_CAP) + 1e-12)
R["viability_any_rate_works_pi2"] = bool(
    any(R[f"viability_any_rate_works_{s}_idx{f}_pi2"] for s in SEX_AGE for f in FORMS))
R["viability_inflation_note"] = (
    f"The unsuffixed per-form keys use pi = {PI_LR:.2%} (MK 2006-2025 "
    f"average, as in results/system.json). The *_pi2 keys use a peg-consistent pi = {PI_PEG:.0%}. The choice moves "
    f"the real risk-free rate from about 0.2% to about 1.3% and therefore moves every "
    f"net margin materially. Both are reported; the peg-consistent one is the more defensible "
    f"for a market-consistent best estimate, because the EUR curve already embeds "
    f"euro-area inflation and the denar is pegged to the euro."
)

R["viability_any_rate_works"] = bool(
    any(R[f"viability_any_rate_works_{s}_idx{f}"] for s in SEX_AGE for f in FORMS))
R["viability_two_sided_failure"] = not R["viability_any_rate_works"]
R["viability_bequest_caveat"] = (
    "A member declining a lower-income annuity is NOT behaving irrationally: the "
    "programmed withdrawal leaves the remaining account to the estate, so it carries a "
    "bequest the annuity does not. This finding is about why a market has not formed "
    "under the current caps, not about members making a mistake."
)

LOWEST_SCENARIO_TAKEUP = 0.30
R["absorbable_lowest_scenario_takeup"] = LOWEST_SCENARIO_TAKEUP
R["absorbable_below_lowest_scenario"] = bool(
    R["absorbable_takeup_full_capital_sf"] < LOWEST_SCENARIO_TAKEUP)
R["absorbable_shortfall_vs_lowest_scenario"] = float(
    R["absorbable_takeup_full_capital_sf"] - LOWEST_SCENARIO_TAKEUP)
R["absorbable_headline"] = (
    "Take-up that would exhaust the entire life-sector capital is below the lowest "
    "modelled scenario of 30%. The sector cannot absorb even the most conservative "
    "case considered, a stronger result than the '3.9 times capital' comparison."
)

_cap_years = legal.get("mapas_mortality_improvement_ceiling_years")
R["mapas_improvement_ceiling_years"] = _cap_years
for sex, x in SEX_AGE.items():
    for y0 in (2026, 2040):
        for age, tag in ((x, f"e{x}"), (65, "e65")):
            _coh = la.ex_curtate(cohort_qx("lc", sex, age, y0)) + 0.5
            _per = la.ex_curtate(period_qx("lc", sex, age)) + 0.5
            R[f"improvement_years_{tag}_{sex}_{y0}"] = float(_coh - _per)
            R[f"ex_complete_cohort_{tag}_{sex}_{y0}"] = float(_coh)
            R[f"ex_complete_period_{tag}_{sex}"] = float(_per)
    if _cap_years is not None:
        _imp40 = R[f"improvement_years_e65_{sex}_2040"]
        R[f"mapas_ceiling_binds_{sex}_2040"] = bool(_imp40 > _cap_years)
        R[f"mapas_ceiling_margin_years_{sex}_2040"] = float(_cap_years - _imp40)
        R[f"mapas_ceiling_binds_{sex}_2026"] = bool(
            R[f"improvement_years_e65_{sex}_2026"] > _cap_years)
if _cap_years is not None:
    R["mapas_ceiling_binds_any_2040"] = bool(
        any(R[f"mapas_ceiling_binds_{s}_2040"] for s in SEX_AGE))
R["improvement_note"] = (
    "Implied improvement = complete e_x on the projected COHORT table for the stated "
    "retirement year minus complete e_x on the static 2023 period table, i.e. exactly "
    "the quantity the МАПАС bylaw caps at three years. Complete = curtate + 0.5 (UDD)."
)

for sex, x in SEX_AGE.items():
    R[f"a12_period_{sex}{x}_2026_r3"] = R[f"a12_{sex}{x}_period_{HEAD}"]
    R[f"a12_cohort_{sex}{x}_2026_r3"] = R[f"a12_{sex}{x}_cohort_{HEAD}"]
    R[f"gap_pct_{sex}{x}_2026_r3"] = R[f"h2_understatement_{sex}_{HEAD}"]
    R[f"dbel_sii_pct_{sex}"] = R[f"bel_shock20_delta_{sex}_{HEAD}"]
    R[f"dbel_var995_pct_{sex}"] = R[f"bel_var995_delta_{sex}_{HEAD}"]
    R[f"var_to_sii_ratio_{sex}"] = 1.0 / R[f"h3_shock_vs_var_ratio_{sex}"]
    R[f"rm_pct_bel_{sex}"] = R[f"risk_margin_pct_bel_{sex}_coc6"]
    R[f"monthly_annuity_per_1m_period_{sex}"] = R[f"monthly_pension_per_1m_mkd_period_{sex}"]
    R[f"monthly_annuity_per_1m_cohort_{sex}"] = R[f"monthly_pension_per_1m_mkd_cohort_{sex}"]

import hashlib as _hl
_inputs = ["qx_central_m.parquet", "qx_central_f.parquet",
           "qx_central_robust_m.parquet", "qx_central_robust_f.parquet",
           "qx_central_coherent_m.parquet", "qx_central_coherent_f.parquet",
           "qx_sims_m.parquet", "qx_sims_f.parquet"]
for _f in _inputs:
    _pth = MORT / _f
    if _pth.exists():
        _h = _hl.md5()
        with open(_pth, "rb") as _fh:
            for _chunk in iter(lambda: _fh.read(1 << 20), b""):
                _h.update(_chunk)
        _key = _f.replace("qx_", "").replace(".parquet", "")
        R[f"input_{_key}_md5"] = _h.hexdigest()
        R[f"input_{_key}_mtime"] = int(_pth.stat().st_mtime)
_mj = READ_RESULTS / "mortality.json"
R["input_mortality_json_mtime"] = int(_mj.stat().st_mtime)
R["input_mortality_json_md5"] = _hl.md5(_mj.read_bytes()).hexdigest()
R["inputs_provenance_note"] = (
    "md5 and mtime of every mortality export this file was computed from. If any of "
    "these differs from what is on disk, results/annuity.json is STALE and "
    "analysis/annuity/value_annuities.py must be re-run."
)

R["mortality_model_main"] = mortality["main_model"]
R["mortality_model_robust"] = mortality["robust_model"]
R["mortality_variant"] = VARIANT
R["cohort_years_beyond_2080_held_flat"] = True
R["cohort_holdflat_max_impact"] = float(max(abs(v) for v in holdflat.values()))
R["qx_monotonicity_violations_from_age70"] = int(sum(v for v, _ in mono_viol.values()))
R["qx_monotonicity_violations_lc_m"] = int(mono_viol[("lc", "m")][0])
R["qx_monotonicity_violations_lc_f"] = int(mono_viol[("lc", "f")][0])
R["qx_monotonicity_worst_drop_lc_m"] = float(mono_viol[("lc", "m")][1])
R["qx_monotonicity_worst_drop_lc_f"] = float(mono_viol[("lc", "f")][1])
R["qx_monotonicity_cells_checked_per_table"] = int(len(YEARS) * (OMEGA - 70))
for _sex, _x in SEX_AGE.items():
    _qi = cohort_qx_iso(_sex, _x, 2026)
    _a = la.a_due_m(_qi, RATES[HEAD][1])
    R[f"mono_iso_a12_{_sex}{_x}_cohort_{HEAD}"] = float(_a)
    R[f"mono_iso_diff_pct_{_sex}"] = float(_a / R[f"a12_{_sex}{_x}_cohort_{HEAD}"] - 1.0)
R["e65_m_2023_rebuilt"] = e65_rebuilt["m"]
R["e65_f_2023_rebuilt"] = e65_rebuilt["f"]
R["e65_complete_m_2023"] = e65_rebuilt["m"]
R["e65_complete_f_2023"] = e65_rebuilt["f"]
for _k in [k for k in list(R) if k.startswith("ex_") and not k.startswith("ex_curtate_")]:
    R["ex_curtate_" + _k[3:]] = R[_k]
    if _k.startswith("ex_cohort") or _k.startswith("ex_period"):
        R["ex_complete_" + _k[3:]] = R[_k] + 0.5
R["ex_convention_note"] = (
    "ex_curtate_* = curtate e_x = sum_k kpx (canonical). ex_* without a suffix are "
    "aliases of the curtate values, retained for sections already rendered. "
    "ex_complete_* and e65_complete_* are curtate + 0.5 (UDD), the convention "
    "results/mortality.json and the published DZS tables use."
)
R["var_basis"] = "run-off (whole-life), not the one-year VaR Solvency II is calibrated on"
try:
    _cmp = json.load(open(READ_RESULTS / "compare.json"))
    _cmp = _cmp.get("compare", _cmp)
    R["var_coverage_rwd_backtest"] = _cmp.get("coverage_pooled_all_rwd")
    R["var_coverage_trendstat_backtest"] = _cmp.get("coverage_pooled_all_trendstat")
except FileNotFoundError:
    R["var_coverage_rwd_backtest"] = None
    R["var_coverage_trendstat_backtest"] = None
R["var_is_lower_bound"] = True
R["var_lower_bound_reason"] = (
    "The run-off VaR is a LOWER BOUND on trend uncertainty, not a prudent figure. The "
    "comparator backtest in results/compare.json projects two 20-year windows on Bulgaria "
    "and Estonia 20 years forward and achieves pooled 95%-interval coverage of "
    f"{R.get('var_coverage_rwd_backtest')} under the random walk and "
    f"{R.get('var_coverage_trendstat_backtest')} under trend-stationarity, against a "
    "nominal 0.95. Both under-cover; the failures come from the central projection, "
    "because a 20-year window estimates a drift precisely and that drift is wrong when "
    "the window spans a regime break. Comparable countries' projections therefore "
    "under-stated realised improvement, so our capital figure understates trend risk "
    "rather than overstating it. It is not a conservative figure."
)
R["trendstat_specification_rejected"] = True
R["trendstat_label"] = (
    "Output of a specification the comparator backtest REJECTS: trend-stationarity "
    f"covers {R.get('var_coverage_trendstat_backtest')} of realised outcomes against a "
    "nominal 0.95, roughly three times worse than the random walk. Retained because it "
    "shows the capital requirement nearly vanishes under mean reversion, which is why "
    "the assumption matters -- NOT as the lower end of a credible range."
)

print("core valuation done")


ONEYEAR_OK = MAIN_MODEL.upper() == "LC"
EPS_GRID = np.linspace(-6.0, 6.0, 4801)
kt = pd.read_csv(MORT / "kt_series.csv")
ONEYEAR: dict = {}

for sex, x in (SEX_AGE.items() if ONEYEAR_OK else []):
    MXc = SURF[("lc", sex)][3]
    lm23 = np.log(MXc[yi[2023], :])
    dlt = np.log(MXc[yi[2024], :]) - lm23
    fit = (ai[80], ai[89] + 1)
    fit_ages = AGES[fit[0]:fit[1]].astype(float)
    xa = fit_ages - fit_ages.mean()
    sxx = (xa ** 2).sum()

    mu = mortality[f"drift_kt_{sex}_{VARIANT}"]
    sig = mortality[f"sigma_kt_{sex}_{VARIANT}"]
    span = int(mortality[f"kt_span_{sex}_{VARIANT}"])

    kan_lo, kan_hi, kan_src = resolve_kannisto_rule(sex)
    kan_winsor = (kan_lo is not None) or (kan_hi is not None)

    _ks = (kt[(kt.sex == sex) & (kt.variant == VARIANT)
              & (kt.model == MAIN_MODEL.lower())]
           .sort_values("year").dropna(subset=["kt"]))
    if len(_ks) >= 2:
        _imp = ((_ks.kt.iloc[-1] - _ks.kt.iloc[0])
                / (_ks.year.iloc[-1] - _ks.year.iloc[0]))
        check(f"kt_series.csv drift agrees with results/mortality.json ({sex})",
              abs(_imp - mu) < 1e-6,
              f"kt_series implies {_imp:.7f}, mortality.json reports {mu:.7f} "
              f"(diff {_imp - mu:+.2e}). The valuation uses mortality.json and the "
              f"estimator identity, so this is an export-sync note for the mortality outputs, not a "
              f"valuation error.", blocking=False)

    def build_cohort(eps: np.ndarray, sigma: float | None = None) -> np.ndarray:
        sd = sig if sigma is None else sigma
        shift = mu + sd * eps
        mu2 = mu + sd * eps / (span + 1)
        n = len(eps)
        ages_d = np.arange(x, OMEGA + 1)
        out = np.empty((n, len(ages_d)))
        for j, a in enumerate(ages_d):
            y = 2026 + j
            g = (shift + (y - 2024) * mu2) / mu
            if a <= 89:
                m = np.exp(lm23[ai[a]] + dlt[ai[a]] * g)
            else:
                lm = lm23[fit[0]:fit[1]][None, :] + np.outer(g, dlt[fit[0]:fit[1]])
                mf = np.exp(lm)
                yv = np.log(mf / (1.0 - mf))
                b = (yv * xa[None, :]).sum(axis=1) / sxx
                if kan_lo is not None or kan_hi is not None:
                    b = np.clip(b, kan_lo if kan_lo is not None else -np.inf,
                                kan_hi if kan_hi is not None else np.inf)
                aa = yv.mean(axis=1) - b * fit_ages.mean()
                z = aa + b * a
                m = np.exp(z) / (1.0 + np.exp(z))
            out[:, j] = m / (1.0 + m / 2.0)
        out[:, -1] = 1.0
        return out

    ctrl = build_cohort(np.zeros(1))[0]
    ref = cohort_qx("lc", sex, x, 2026)
    vref = RATES[HEAD][1]
    a_err = float(la.a_due_m(ctrl, vref) / la.a_due_m(ref, vref) - 1.0)
    q_err = float(np.abs(ctrl[:-1] / ref[:-1] - 1.0).max())
    R[f"oneyear_recon_a12_relerr_{sex}"] = a_err
    R[f"oneyear_recon_qx_maxerr_{sex}"] = q_err
    R[f"oneyear_kannisto_rule_{sex}"] = kan_src
    R[f"oneyear_kannisto_floor_{sex}"] = kan_lo
    R[f"oneyear_kannisto_ceiling_{sex}"] = kan_hi
    if not check(
            f"one-year VaR reconstruction reproduces the central cohort factor ({sex})",
            abs(a_err) < 1e-4,
            f"a12 relative error {a_err:+.2e}; max qx cell error {q_err:.2e}; "
            f"Kannisto rule applied = {R[f'oneyear_kannisto_rule_{sex}']}. "
            f"A failure here means the mortality projection's old-age closure rule changed and the "
            f"replication in build_cohort must be updated to match it."):
        for _lbl in list(QUANT) + ["995"]:
            R[f"oneyear_var{_lbl}_delta_{sex}_{HEAD}"] = None
        for _k in (f"oneyear_var995_equiv_qx_shock_{sex}",
                   f"oneyear_shock_vs_var_ratio_{sex}",
                   f"oneyear_runoff_ratio_{sex}",
                   f"oneyear_var995_delta_{sex}_{HEAD}_varC",
                   f"oneyear_var995_equiv_qx_shock_{sex}_varC"):
            R[_k] = None
        R[f"oneyear_skipped_{sex}"] = (
            "SKIPPED: the reconstruction no longer reproduces the exported central "
            "cohort factor, so the mortality projection's old-age closure rule has changed. Update the "
            "Kannisto replication in build_cohort before republishing.")
        continue

    vfun = RATES[HEAD][1]
    central = la.a_due_m(ref, vfun)

    def a_of_eps(e, sigma=None):
        return la.a_due_m_paths(build_cohort(np.atleast_1d(e), sigma=sigma), vfun)

    eps_grid = EPS_GRID[(EPS_GRID >= -3.0) & (EPS_GRID <= 3.0)]
    a_grid = a_of_eps(eps_grid)
    check(f"one-year VaR map is strictly monotone in eps over [-3,3] ({sex})",
          bool(np.all(np.diff(a_grid) < 0)),
          f"a12 falls from {a_grid[0]:.4f} at eps=-3 to {a_grid[-1]:.4f} at eps=+3; "
          f"max upward step {np.diff(a_grid).max():+.2e}")

    ONEYEAR[sex] = {"grid": EPS_GRID, "a_grid": a_of_eps(EPS_GRID),
                    "central": central, "ref": ref}
    for lbl, p in QUANT.items():
        e_q = float(norm.ppf(1.0 - p))
        R[f"oneyear_var{lbl}_delta_{sex}_{HEAD}"] = float(
            a_of_eps(e_q)[0] / central - 1.0)
    a995 = float(a_of_eps(float(norm.ppf(0.005)))[0])
    R[f"oneyear_var995_delta_{sex}_{HEAD}"] = float(a995 / central - 1.0)
    R[f"oneyear_shock_vs_var_ratio_{sex}"] = float(
        R[f"bel_shock20_delta_{sex}_{HEAD}"] / R[f"oneyear_var995_delta_{sex}_{HEAD}"])
    R[f"oneyear_runoff_ratio_{sex}"] = float(
        R[f"oneyear_var995_delta_{sex}_{HEAD}"] / R[f"bel_var995_delta_{sex}_{HEAD}"])

    R[f"oneyear_var995_equiv_qx_shock_{sex}"] = float(
        1.0 - equiv_multiplier(ref, vfun, a995))

    sig_c = mortality[f"sigma_kt_{sex}_C"]
    a995c = float(a_of_eps(float(norm.ppf(0.005)), sigma=sig_c)[0])
    R[f"oneyear_var995_delta_{sex}_{HEAD}_varC"] = float(a995c / central - 1.0)
    R[f"oneyear_var995_equiv_qx_shock_{sex}_varC"] = float(
        1.0 - equiv_multiplier(ref, vfun, a995c))
    R[f"oneyear_sigma_{sex}_{VARIANT}"] = float(sig)
    R[f"oneyear_sigma_{sex}_C"] = float(sig_c)
    R[f"oneyear_sigma_{sex}_B"] = float(sig)

if ONEYEAR_OK and all(sx in ONEYEAR for sx in SEX_AGE):
    RHO = float(mortality["kt_increment_corr_mf"])
    _grid = EPS_GRID
    _g = {sx: ONEYEAR[sx]["a_grid"] for sx in SEX_AGE}
    for sx, _x in SEX_AGE.items():
        check(f"one-year eps-grid curve is the {sx} table (closure sanity)",
              abs(float(np.interp(0.0, _grid, _g[sx]))
                  / R[f"a12_{sx}{_x}_cohort_{HEAD}"] - 1.0) < 1e-6,
              f"a12 at eps=0 is {float(np.interp(0.0, _grid, _g[sx])):.6f} vs central "
              f"{R[f'a12_{sx}{_x}_cohort_{HEAD}']:.6f}")
    _N1 = 1_000_000
    _rg = np.random.default_rng(SEED)
    _z = _rg.standard_normal((_N1, 2))
    _em = _z[:, 0]
    _ef = RHO * _z[:, 0] + np.sqrt(1.0 - RHO ** 2) * _z[:, 1]
    _am = np.interp(_em, _grid, _g["m"])
    _af = np.interp(_ef, _grid, _g["f"])
    _cm = R[f"a12_mixed_cohort_{HEAD}"]
    _bel1 = W_M * _am + W_F * _af
    R[f"oneyear_var995_delta_mixed_{HEAD}"] = float(
        np.quantile(_bel1, 0.995) / _cm - 1.0)
    R[f"oneyear_var99_delta_mixed_{HEAD}"] = float(
        np.quantile(_bel1, 0.99) / _cm - 1.0)
    _af_i = np.interp(_rg.standard_normal(_N1), _grid, _g["f"])
    R[f"oneyear_var995_delta_mixed_indep_{HEAD}"] = float(
        np.quantile(W_M * _am + W_F * _af_i, 0.995) / _cm - 1.0)
    R["oneyear_mixed_indep_vs_joint_pct"] = float(
        R[f"oneyear_var995_delta_mixed_indep_{HEAD}"]
        / R[f"oneyear_var995_delta_mixed_{HEAD}"] - 1.0)
    R["oneyear_mixed_rho"] = RHO
    R["oneyear_mixed_n_draws"] = _N1
    R[f"oneyear_shock_vs_var_ratio_mixed"] = float(
        R[f"bel_shock20_delta_mixed_{HEAD}"] / R[f"oneyear_var995_delta_mixed_{HEAD}"])

    def _mixed_a12(lam):
        return (W_M * la.a_due_m(la.scale_qx(cohort_qx("lc", "m", SEX_AGE["m"], 2026), lam),
                                 RATES[HEAD][1])
                + W_F * la.a_due_m(la.scale_qx(cohort_qx("lc", "f", SEX_AGE["f"], 2026), lam),
                                   RATES[HEAD][1]))

    for _tag, _tgt in (("oneyear", np.quantile(_bel1, 0.995)),
                       ("runoff", (1 + R[f"bel_var995_delta_mixed_{HEAD}"]) * _cm)):
        R[f"{_tag}_var995_equiv_qx_shock_mixed"] = float(
            1.0 - brentq(lambda l: _mixed_a12(l) - _tgt, 0.20, 1.0, xtol=1e-12))

for sex, x in (SEX_AGE.items() if ONEYEAR_OK else []):
    if R.get(f"oneyear_var995_delta_{sex}_{HEAD}") is None:
        R[f"risk_margin_pct_bel_{sex}_coc6_oneyearscr"] = None
        continue
    q = cohort_qx("lc", sex, x, 2026)
    vfun = RATES[HEAD][1]
    bel = la.a_due_m(q, vfun)
    R[f"risk_margin_pct_bel_{sex}_coc6_oneyearscr"] = float(
        la.risk_margin(q, vfun, R[f"oneyear_var995_delta_{sex}_{HEAD}"] * bel, COC6) / bel)

if not ONEYEAR_OK:
    for sex in SEX_AGE:
        for lbl in list(QUANT) + ["995"]:
            R[f"oneyear_var{lbl}_delta_{sex}_{HEAD}"] = None
        R[f"oneyear_shock_vs_var_ratio_{sex}"] = None
        R[f"oneyear_runoff_ratio_{sex}"] = None
    R["oneyear_var_skipped_reason"] = (
        f"SKIPPED: the one-year reconstruction assumes the Lee-Carter structure "
        f"log m(x,t) = alpha_x + beta_x kappa_t, but results/mortality.json reports "
        f"main_model = {MAIN_MODEL}. Re-derive the mapping before enabling."
    )

if ONEYEAR_OK and all(R.get(f"oneyear_var995_delta_{sx}_{HEAD}") is not None
                      for sx in SEX_AGE):
    _r1 = {sx: R[f"bel_shock20_delta_{sx}_{HEAD}"]
           / R[f"oneyear_var995_delta_{sx}_{HEAD}"] for sx in SEX_AGE}
    _d1 = {sx: ("shock_exceeds_var" if _r1[sx] > 1 else "var_exceeds_shock")
           for sx in _r1}
    for sx in SEX_AGE:
        R[f"h3_shock_vs_var_ratio_oneyear_{sx}"] = float(_r1[sx])
        R[f"h3_direction_{sx}_oneyear"] = _d1[sx]
    R["h3_supported_oneyear"] = bool(
        all(abs(v - 1.0) > H3_THRESHOLD for v in _r1.values()))
    R["h3_direction_oneyear"] = (_d1["m"] if _d1["m"] == _d1["f"] else "mixed")
    R["h3_supported_strict_band_oneyear"] = bool(
        all((v < 0.8) or (v > 1.25) for v in _r1.values()))

R["oneyear_var_method_short"] = "closed form at Phi^-1(0.005); no simulation"
R["oneyear_var_method"] = (
    "Richards, Currie & Ritchie (2014) one-year view, kappa-only implementation: one extra "
    "RWD innovation for 2024, the drift re-estimated by the same (kappa_last - kappa_first)/span "
    "ML estimator on the gapped series (now 21 years), then a deterministic central "
    "re-projection and revaluation. Deaths are not re-simulated and alpha_x/beta_x are not "
    "refitted, so parameter (not process) uncertainty in the age pattern is excluded."
)

pd.DataFrame(checks).to_csv(OUT / "unit_checks.csv", index=False)
R["unit_checks_all_pass"] = bool(all(c["pass"] for c in checks if c["blocking"]))
R["unit_checks_nonblocking_failures"] = int(
    sum(1 for c in checks if not c["pass"] and not c["blocking"]))

R = {k: (float(v) if isinstance(v, (np.floating,)) else
         int(v) if isinstance(v, (np.integer,)) else v) for k, v in R.items()}
with open(RESULTS / "annuity.json", "w", encoding="utf-8") as fh:
    json.dump(R, fh, indent=2, ensure_ascii=False, sort_keys=True)
print(f"results/annuity.json written: {len(R)} keys")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

FIG.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5})
SEXLBL = {"m": f"Мажи, возраст {SEX_AGE['m']}", "f": f"Жени, возраст {SEX_AGE['f']}"}
RATELBL = {"i2": "2%", "i3": "3%", "i4": "4%", "eiopa": "EUR",
           "eiopa_sp100": "EUR\n+100 бп", "dom": "Дом.\n5,2%"}

COL_M = "#0072B2"
COL_F = "#D55E00"
COL_PERIOD = "#7F7F7F"
COL_SHOCK = "#999999"
COL_VAR = "#CC79A7"


def mk(v, nd=3):
    return f"{v:,.{nd}f}".replace(",", "\u2009").replace(".", ",").replace("-", "\u2212")


class MkTickFormatter(matplotlib.ticker.Formatter):

    def __call__(self, v, pos=None):
        locs = list(getattr(self, "locs", [])) or [v]
        nd = next((d for d in range(5)
                   if all(abs(round(x, d) - x) < 1e-9 * max(1.0, abs(x)) for x in locs)), 4)
        return mk(v, nd)


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=300)
    fig.savefig(FIG / f"{name}.svg")
    plt.close(fig)


fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.3), sharey=True, layout="constrained")
keys = list(RATES.keys())
xpos = np.arange(len(keys))
_gap_ymax = max(
    max(R[f"a12_{sx}{SEX_AGE[sx]}_cohort_{k}"] for k in keys) for sx in ("m", "f")
) * 1.22
for ax, sex in zip(axes, ("m", "f")):
    x = SEX_AGE[sex]
    sex_col = COL_M if sex == "m" else COL_F
    per = [R[f"a12_{sex}{x}_period_{k}"] for k in keys]
    coh = [R[f"a12_{sex}{x}_cohort_{k}"] for k in keys]
    ax.bar(xpos - 0.2, per, 0.4, color="white", edgecolor=sex_col, linewidth=1.3,
           hatch="///", label="Периодна таблица (2023, статична)")
    ax.bar(xpos + 0.2, coh, 0.4, color=sex_col, edgecolor="black",
           label="Кохортна таблица (проектирана, LC)")
    for j, k in enumerate(keys):
        g = R[f"h2_understatement_{sex}_{k}"]
        ax.text(xpos[j], max(per[j], coh[j]) * 1.02, "+" + mk(100 * g, 1) + "%",
                ha="center", fontsize=7)
    ax.set_xticks(xpos)
    ax.set_xticklabels([RATELBL[k] for k in keys])
    ax.set_title(SEXLBL[sex])
    ax.grid(True, axis="y", alpha=0.3)
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5))
    ax.yaxis.set_major_formatter(MkTickFormatter())
    ax.set_ylim(0, _gap_ymax)
axes[0].set_ylabel("Ануитетен фактор ä$^{(12)}$")
fig.supxlabel("Дисконтна основа (EUR: безризична крива на ЕИОПА за евро)", fontsize=8.5)
fig.legend(*axes[0].get_legend_handles_labels(), loc="outside upper center", ncol=2)
save(fig, "annuity_gap_by_rate")

fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.3), sharey=True, layout="constrained")
for ax, sex in zip(axes, ("m", "f")):
    x = SEX_AGE[sex]
    sex_col = COL_M if sex == "m" else COL_F
    A = path_a12[sex][HEAD]
    central = R[f"a12_{sex}{x}_cohort_{HEAD}"]
    shock = central * (1 + R[f"bel_shock20_delta_{sex}_{HEAD}"])
    q995 = np.quantile(A, 0.995)
    q99 = np.quantile(A, 0.99)
    counts, _, _ = ax.hist(A, bins=70, color=sex_col, alpha=0.35, edgecolor=sex_col, linewidth=0.4)
    ax.set_ylim(0, max(ax.get_ylim()[1], 1.55 * counts.max()))
    for val, lbl, ls in (
            (central, f"централна (LC): {mk(central)}", "-"),
            (shock, f"шок −20%: {mk(shock)}", "--"),
            (q99, f"99% квантил: {mk(q99)}", ":"),
            (q995, f"99,5% квантил: {mk(q995)}", "-.")):
        ax.axvline(val, color=sex_col, linestyle=ls, linewidth=1.3, label=lbl)
    ax.set_title(SEXLBL[sex])
    ax.set_xlabel("ä$^{(12)}$ по симулирана патека (i = 3%)")
    ax.xaxis.set_major_formatter(MkTickFormatter())
    ax.yaxis.set_major_formatter(MkTickFormatter())
    ax.legend(loc="upper left", handlelength=2.2, framealpha=0.9)
    ax.grid(True, axis="y", alpha=0.3)
axes[0].set_ylabel("Број патеки")
save(fig, "annuity_pv_distribution")

fig, ax = plt.subplots(figsize=(6.3, 3.2), layout="constrained")
labels, bars_p, bars_c, bar_cols = [], [], [], []
for sex in ("m", "f"):
    for sel in (1.0, 0.9, 0.8):
        labels.append(f"{SEXLBL[sex].split(',')[0]}\n×{mk(sel, 1)}")
        bars_p.append(f(sex, "period", HEAD, sel=sel))
        bars_c.append(f(sex, "cohort", HEAD, sel=sel))
        bar_cols.append(COL_M if sex == "m" else COL_F)
xp = np.arange(len(labels))
ax.bar(xp - 0.2, bars_p, 0.4, color="white", edgecolor=bar_cols, linewidth=1.3, hatch="///",
       label="Периодна таблица (2023)")
ax.bar(xp + 0.2, bars_c, 0.4, color=bar_cols, edgecolor="black",
       label="Кохортна таблица (LC)")
ax.set_xticks(xp)
ax.set_xticklabels(labels)
ax.set_ylabel("Ануитетен фактор ä$^{(12)}$ (i = 3%)")
ax.yaxis.set_major_formatter(MkTickFormatter())
ax.set_xlabel("Пол и мултипликатор на смртноста на ануитантите (селекција)")
ax.legend()
ax.grid(True, axis="y", alpha=0.3)
save(fig, "annuity_selection_sensitivity")

print("figures written")

from fig_shock_vs_var import draw as _draw_shock_vs_var
_draw_shock_vs_var(R, FIG)
print("figure 4 written")
