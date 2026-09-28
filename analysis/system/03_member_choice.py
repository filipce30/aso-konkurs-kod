#!/usr/bin/env python3
"""Member-level payout choice: programmed withdrawal under the MAPAS rules vs a lifetime annuity."""
import csv
import datetime
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import openpyxl
import pandas as pd
import pyarrow.parquet as pq

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "analysis/annuity"))
import lib_annuity as la
RAW = ROOT / "data/raw"
CLEAN = ROOT / "data/clean"
RESULTS = ROOT / "results"
ANALYSIS = ROOT / "analysis/system"
MORT = ROOT / "analysis/mortality"
FIG = ROOT / "figures"

system = json.load(open(RESULTS / "system.json"))
annuity = json.load(open(RESULTS / "annuity.json"))
legal = json.load(open(RESULTS / "legal.json"))

RET_AGE = {"m": legal["retirement_age_m"], "f": legal["retirement_age_f"]}
RET_YEAR = 2026
OMEGA = la.OMEGA
AGE_TAG_PRE = {"m": f"m{RET_AGE['m']}", "f": f"f{RET_AGE['f']}"}

wb = openpyxl.load_workbook(RAW / "nbrsm/nbrm_drzavni_obvrznici_archive.xlsx", data_only=True)
ws = wb[wb.sheetnames[0]]


def _to_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return datetime.datetime.strptime(v, "%d.%m.%Y").date()
        except ValueError:
            return None
    return None


auctions = []
for r in ws.iter_rows(min_row=5, max_row=ws.max_row, values_only=True):
    if r[0] is None:
        continue
    _, settle, maturity, _, _, _, _, _, _, wavg, fixed = r[:11]
    sd, md = _to_date(settle), _to_date(maturity)
    if not (sd and md):
        continue
    tenor = (md - sd).days / 365.25
    rate = wavg if wavg not in (None, 0) else fixed
    if rate is None:
        continue
    auctions.append({"tenor": tenor, "date": sd, "rate": float(rate) / 100.0})

long_auctions = [a for a in auctions if a["tenor"] >= 5.0]
long_auctions.sort(key=lambda a: a["date"])
LAST_LONG = long_auctions[-1]
_window_start = LAST_LONG["date"] - datetime.timedelta(days=365)
_in_window = [a for a in long_auctions if _window_start <= a["date"] <= LAST_LONG["date"]]
RATE_A = sum(a["rate"] for a in _in_window) / len(_in_window)
RATE_B = LAST_LONG["rate"]

UNIT_VALUE_SAVA = {2022: 235.843874, 2023: 254.969666, 2024: 278.518719, 2025: 292.831861}
UNIT_VALUE_KBP = {2022: 246.231776, 2023: 264.141459, 2024: 288.532506, 2025: 303.569101}
_fund_returns = {
    y: ((UNIT_VALUE_SAVA[y] / UNIT_VALUE_SAVA[y - 1] - 1)
        + (UNIT_VALUE_KBP[y] / UNIT_VALUE_KBP[y - 1] - 1)) / 2
    for y in (2023, 2024, 2025)
}
RATE_C = sum(_fund_returns.values()) / 3

NOMINAL_CAP = min(RATE_A, RATE_B, RATE_C)
_infl = [system["inflation_2023"], system["inflation_2024"], system["inflation_2025"]]
COL_MIN = 0.5 * (sum(_infl) / len(_infl))
REAL_CAP = max(0.0, min(NOMINAL_CAP - COL_MIN, 0.80 * NOMINAL_CAP))

PUBLISHED_RATES = {"i2": 0.02, "i3": 0.03, "i4": 0.04}
RATE_KEY = max((k for k, v in PUBLISHED_RATES.items() if v <= REAL_CAP),
               key=lambda k: PUBLISHED_RATES[k])
I_REAL = PUBLISHED_RATES[RATE_KEY]

_lt = pd.read_csv(CLEAN / "lifetables_period.csv")
OFFICIAL_YEAR = int(_lt.year.max())
QX_OFFICIAL = {}
for sex in ("m", "f"):
    s = _lt[(_lt.year == OFFICIAL_YEAR) & (_lt.sex == sex)].sort_values("age")
    q = s.set_index("age").qx.reindex(range(0, OMEGA + 1)).to_numpy(float)
    q[-1] = 1.0
    QX_OFFICIAL[sex] = q


def a_immediate(qx_full, x, i):
    q = qx_full[x:]
    v = 1.0 / (1.0 + i)
    tot, surv = 0.0, 1.0
    for k in range(1, len(q)):
        surv *= (1.0 - q[k - 1])
        tot += v ** k * surv
    return tot


def shift_table_by_years(qx_full, x0, target_gain, i_probe=0.0):
    def ex(factor):
        q = qx_full.copy()
        q[x0:] = np.minimum(q[x0:] * factor, 1.0)
        q[-1] = 1.0
        surv, tot = 1.0, 0.0
        for k in range(x0, OMEGA):
            surv *= (1.0 - q[k])
            tot += surv
        return tot
    base = ex(1.0)
    lo, hi = 0.05, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if ex(mid) - base < target_gain:
            hi = mid
        else:
            lo = mid
    q = qx_full.copy()
    q[x0:] = np.minimum(q[x0:] * ((lo + hi) / 2), 1.0)
    q[-1] = 1.0
    return q


_ws_macro = openpyxl.load_workbook(
    RAW / "nbrsm/Osnovni_makroek_indikatori_mak.xlsx", data_only=True)["MKD"]
_infl_hist = {}
for c in range(1, _ws_macro.max_column + 1):
    yr = _ws_macro.cell(row=5, column=c).value
    if isinstance(yr, int) and _ws_macro.cell(row=6, column=c).value is None:
        v = _ws_macro.cell(row=15, column=c).value
        if v is not None:
            if isinstance(v, str):
                v = v.replace("*", "").replace(",", ".")
                try:
                    v = float(v)
                except ValueError:
                    continue
            _infl_hist[yr] = float(v) / 100.0
INFL_WINDOW = (2006, 2025)
_w = {y: v for y, v in _infl_hist.items() if INFL_WINDOW[0] <= y <= INFL_WINDOW[1]}
INFLATION_LR = sum(_w.values()) / len(_w)

YEAR_MAX_SURF = 2080
_COH_Q = {}
for _sex in ("m", "f"):
    _df = pq.read_table(MORT / f"qx_central_{_sex}.parquet").to_pandas()
    _Q = _df.pivot(index="year", columns="age", values="qx").sort_index()
    _x0 = RET_AGE[_sex]
    _ages = np.arange(_x0, OMEGA + 1)
    _yrs = np.minimum(RET_YEAR + (_ages - _x0), YEAR_MAX_SURF)
    _COH_Q[_sex] = np.array([float(_Q.loc[y, a]) for y, a in zip(_yrs, _ages)])
    _COH_Q[_sex][-1] = 1.0


def a12_cohort(sex, rate):
    return la.a_due_m(_COH_Q[sex], la.flat_discount(rate))


for _sex in ("m", "f"):
    _pub = annuity[f"a12_{AGE_TAG_PRE[_sex]}_cohort_{RATE_KEY}"]
    _mine = a12_cohort(_sex, I_REAL)
    assert abs(_mine / _pub - 1) < 1e-9, (
        f"cohort a12 reimplementation does not match results/annuity.json for {_sex}: "
        f"{_mine} vs {_pub}")
A12_REPRO_ERR = max(abs(a12_cohort(s_, I_REAL) / annuity[f"a12_{AGE_TAG_PRE[s_]}_cohort_{RATE_KEY}"] - 1)
                    for s_ in ("m", "f"))

INDEXATIONS = {
    "idxcpi": None,
    "idx1pct": legal["indexation_min_pct"],
    "idx3pct": legal["indexation_max_pct"],
}


def annuity_rate_for(g):
    if g is None:
        return I_REAL
    return (1.0 + I_REAL) * (1.0 + INFLATION_LR) / (1.0 + g) - 1.0


def annuity_real_factor(g, t):
    if g is None:
        return 1.0
    return ((1.0 + g) / (1.0 + INFLATION_LR)) ** t


BALANCE = {"m": system["avg_balance_at_ret_m_2026_mkd"], "f": system["avg_balance_at_ret_f_2026_mkd"]}
AGE_TAG = AGE_TAG_PRE
MAX_COMMISSION = 0.025

REPORT_AGES = [75, 85, 90]
rows = []
out_keys = {}

for sex in ("m", "f"):
    x0 = RET_AGE[sex]
    bal = BALANCE[sex]

    a_by_age = {x: a_immediate(QX_OFFICIAL[sex], x, I_REAL) for x in range(x0, OMEGA)}
    PAY_ACC = sum((1.0 + I_REAL) ** ((11 - k) / 12.0) for k in range(12)) / 12.0
    acct, pw_monthly = bal, {}
    for x in range(x0, OMEGA):
        ax = a_by_age[x]
        if ax <= 0 or acct <= 0:
            pw_monthly[x] = 0.0
            acct = 0.0
            continue
        annual = acct / ax
        pw_monthly[x] = annual / 12.0
        acct = max(0.0, acct * (1.0 + I_REAL) - annual * PAY_ACC)

    q_ext = shift_table_by_years(QX_OFFICIAL[sex], x0, 3.0)
    pw_first_ext = bal / a_immediate(q_ext, x0, I_REAL) / 12.0

    a12_period = annuity[f"a12_{AGE_TAG[sex]}_period_{RATE_KEY}"]
    ann_first = {}
    ann_real_path = {}
    for tag, g in INDEXATIONS.items():
        j = annuity_rate_for(g)
        a12_j = a12_cohort(sex, j)
        ann_first[tag] = bal / (12.0 * a12_j)
        ann_real_path[tag] = {x: ann_first[tag] * annuity_real_factor(g, x - x0)
                              for x in range(x0, OMEGA)}
    ann_monthly_cohort = ann_first["idxcpi"]
    ann_monthly_period = bal / (12.0 * a12_period)
    ann_monthly_net = ann_first['idxcpi'] * (1 - MAX_COMMISSION)

    kpx_coh = la.kpx(_COH_Q[sex])

    def surv_to(age):
        return float(kpx_coh[age - x0]) if age is not None else float("nan")

    crossover_by_tag, surv_by_tag, never_above_by_tag = {}, {}, {}
    for tag in INDEXATIONS:
        cx = next((x for x in range(x0, OMEGA) if pw_monthly[x] < ann_real_path[tag][x]), None)
        crossover_by_tag[tag] = cx
        surv_by_tag[tag] = surv_to(cx)
        never_above_by_tag[tag] = bool(cx == x0)
    crossover = crossover_by_tag["idxcpi"]
    crossover_surv = surv_by_tag["idxcpi"]

    out_keys[f"pw_monthly_first_year_{sex}_2026"] = pw_monthly[x0]
    for A in REPORT_AGES:
        out_keys[f"pw_monthly_age{A}_{sex}"] = pw_monthly[A]
    out_keys[f"pw_monthly_first_year_{sex}_2026_ex_plus3"] = pw_first_ext
    out_keys[f"annuity_monthly_{sex}_2026"] = ann_monthly_cohort
    out_keys[f"annuity_monthly_{sex}_2026_period_priced"] = ann_monthly_period
    out_keys[f"annuity_monthly_{sex}_2026_after_max_commission"] = ann_monthly_net
    out_keys[f"crossover_age_{sex}"] = crossover
    out_keys[f"crossover_survival_prob_{sex}"] = crossover_surv
    for tag, g in INDEXATIONS.items():
        out_keys[f"crossover_age_{sex}_{tag}"] = crossover_by_tag[tag]
        out_keys[f"crossover_survival_prob_{sex}_{tag}"] = surv_by_tag[tag]
        out_keys[f"annuity_monthly_{sex}_2026_{tag}"] = ann_first[tag]
        out_keys[f"annuity_rate_{sex}_{tag}"] = annuity_rate_for(g)
        out_keys[f"annuity_real_at_85_{sex}_{tag}"] = ann_real_path[tag][85]
        out_keys[f"pw_never_above_annuity_{sex}_{tag}"] = never_above_by_tag[tag]
        out_keys[f"pw_over_annuity_first_year_{sex}_{tag}"] = pw_monthly[x0] / ann_first[tag] - 1
    out_keys[f"pw_decline_by_age90_{sex}"] = pw_monthly[90] / pw_monthly[x0] - 1

    for x in range(x0, 101):
        rows.append({"sex": sex, "age": x, "year": RET_YEAR + (x - x0),
                     "pw_monthly_mkd": pw_monthly[x],
                     "annuity_monthly_mkd_idxcpi": ann_real_path["idxcpi"][x],
                     "annuity_monthly_mkd_idx1pct": ann_real_path["idx1pct"][x],
                     "annuity_monthly_mkd_idx3pct": ann_real_path["idx3pct"][x],
                     "pw_over_annuity_idxcpi": pw_monthly[x] / ann_real_path["idxcpi"][x]})

with open(ANALYSIS / "member_choice_2026.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

PW_SRC = (
    "programmed withdrawal per the payout law art. 16(4)-(6): monthly = balance / (a_x x 12), where a_x is "
    "the annuity-IMMEDIATE annual factor sum_k v^k kp_x, recalculated every 12 months on the new balance and "
    f"age. Mortality basis: the OFFICIAL DZS period life table {OFFICIAL_YEAR} "
    "(data/clean/lifetables_period.csv), which is what the MAPAS bylaw Сл. весник 177/2022 art. 2 prescribes "
    "for pension companies -- NOT this paper's projected table. Interest: a real "
    f"{I_REAL:.1%}, the highest published basis that does not exceed the cap the interest-rate bylaw implies "
    f"({REAL_CAP:.2%}). Roll-forward assumes the fund earns exactly the assumed real return and the table and "
    "rate are unchanged, so the decline shown is the pure no-pooling effect, not a market forecast"
)
ANN_SRC = (
    f"lifetime annuity: balance / (12 x a12_{{m64,f62}}_cohort_{RATE_KEY}) from results/annuity.json -- "
    "the annuity valuation's ä^(12) factor on THIS PAPER'S projected cohort table at the same real "
    f"{I_REAL:.1%}. Flat for life by construction. Gross of insurer expenses; the payout law art. 8 caps "
    "sales commission at 2.5% of premium, reported separately"
)
CROSS_SRC = (
    "first age at which the programmed-withdrawal monthly payment falls below the flat annuity payment, "
    "from analysis/system/member_choice_2026.csv"
)
SURV_SRC = (
    "probability of surviving from the retirement age in 2026 to the crossover age, on THIS PAPER'S projected "
    "cohort table (analysis/mortality/qx_central_{m,f}.parquet, LC central, cohort diagonal from 2026). This "
    "is the only place the paper's own table enters the member comparison"
)


def put(key, value, source, year=None, note=None):
    system[key] = value
    system[f"{key}_source"] = source
    if year is not None:
        system[f"{key}_year"] = year
    if note is not None:
        system[f"{key}_note"] = note


for sex in ("m", "f"):
    put(f"pw_monthly_first_year_{sex}_2026", out_keys[f"pw_monthly_first_year_{sex}_2026"], PW_SRC, year=2026)
    for A in REPORT_AGES:
        put(f"pw_monthly_age{A}_{sex}", out_keys[f"pw_monthly_age{A}_{sex}"],
            PW_SRC + f"; payment in the year the member turns {A}, if alive")
    put(f"pw_monthly_first_year_{sex}_2026_ex_plus3", out_keys[f"pw_monthly_first_year_{sex}_2026_ex_plus3"],
        "same, on a table adjusted so curtate life expectancy at the retirement age is three years higher -- "
        "the maximum adjustment MAPAS bylaw 177/2022 art. 2 PERMITS (it does not require it). Lower, because "
        "a longer expected life spreads the same balance further", year=2026)
    put(f"annuity_monthly_{sex}_2026", out_keys[f"annuity_monthly_{sex}_2026"], ANN_SRC, year=2026)
    put(f"annuity_monthly_{sex}_2026_period_priced", out_keys[f"annuity_monthly_{sex}_2026_period_priced"],
        ANN_SRC.replace("_cohort_", "_period_") + ". HIGHER than the cohort-priced figure because a period "
        "table understates how long the member will live -- that difference is RQ2", year=2026)
    put(f"annuity_monthly_{sex}_2026_after_max_commission",
        out_keys[f"annuity_monthly_{sex}_2026_after_max_commission"],
        "same, after the payout law art. 8 maximum sales commission of 2.5% of premium", year=2026)
    put(f"crossover_age_{sex}", out_keys[f"crossover_age_{sex}"],
        CROSS_SRC + ". Default = the cost-of-living-indexed form (idxcpi); see the _idx* keys for the "
        "fixed-nominal forms the payout law art. 6(1)(b) also allows")
    put(f"crossover_survival_prob_{sex}", out_keys[f"crossover_survival_prob_{sex}"], SURV_SRC)
    for tag, g in INDEXATIONS.items():
        if g is None:
            form = ("annuity adjusted to the cost-of-living index each half-year (payout law art. 6(1)(a)), "
                    "so LEVEL IN REAL TERMS")
        else:
            form = (f"annuity with a FIXED NOMINAL adjustment of {g:.0%} a year, set at purchase and "
                    "unchanged for life (payout law art. 6(1)(b); ASO sets the annual minimum, which by law "
                    "cannot be below 1% or above 3%). Its REAL value then moves at (1+g)/(1+pi), so against "
                    f"the assumed long-run inflation of {INFLATION_LR:.2%} it "
                    + ("falls" if g < INFLATION_LR else "rises") + " over time")
        put(f"crossover_age_{sex}_{tag}", out_keys[f"crossover_age_{sex}_{tag}"],
            CROSS_SRC + ". " + form)
        put(f"crossover_survival_prob_{sex}_{tag}", out_keys[f"crossover_survival_prob_{sex}_{tag}"],
            SURV_SRC + ". " + form)
        put(f"annuity_monthly_{sex}_2026_{tag}", out_keys[f"annuity_monthly_{sex}_2026_{tag}"],
            f"first monthly payment: {form}. Priced as balance / (12 x ä^(12)) on this paper's projected "
            f"cohort table at an effective rate of {out_keys[f'annuity_rate_{sex}_{tag}']:.4%}, which for the "
            "fixed-nominal forms is (1+i_real)(1+pi)/(1+g) - 1", year=2026)
        put(f"annuity_real_at_85_{sex}_{tag}", out_keys[f"annuity_real_at_85_{sex}_{tag}"],
            "the same annuity's REAL monthly value at age 85, in 2026 denars. " + form)
        put(f"pw_never_above_annuity_{sex}_{tag}", out_keys[f"pw_never_above_annuity_{sex}_{tag}"],
            "TRUE means the programmed withdrawal is already below this annuity at the very first payment, "
            "so there is no crossover in the ordinary sense and the matching crossover_age key equals the "
            "retirement age with a survival probability of 1 by construction -- read it as 'the annuity "
            "dominates from day one', not as 'the member has a year of advantage'")
        put(f"pw_over_annuity_first_year_{sex}_{tag}", out_keys[f"pw_over_annuity_first_year_{sex}_{tag}"],
            "how much more (or less) the programmed withdrawal pays than this annuity in the first year. "
            + form)
    put(f"pw_decline_by_age90_{sex}", out_keys[f"pw_decline_by_age90_{sex}"],
        "pw_monthly_age90 / pw_monthly_first_year - 1, in REAL terms (the factor uses a real rate)")

put("member_choice_inflation_lr", INFLATION_LR,
    f"ASSUMPTION, stated as such: long-run inflation, taken as the {INFL_WINDOW[0]}-{INFL_WINDOW[1]} average "
    "of the NBRSM series 'Инфлација (просек, на кумулативна основа)' "
    "(data/raw/nbrsm/Osnovni_makroek_indikatori_mak.xlsx). It enters ONLY the fixed-nominal annuity forms "
    "(payout law art. 6(1)(b)); the programmed withdrawal and the cost-of-living-indexed annuity are both "
    "real quantities and do not depend on it")
put("member_choice_inflation_window", f"{INFL_WINDOW[0]}-{INFL_WINDOW[1]}",
    "the averaging window behind member_choice_inflation_lr")
put("member_choice_a12_reproduction_error", A12_REPRO_ERR,
    "this script recomputes ä^(12) on the projected cohort table with the annuity module's own "
    "lib_annuity.a_due_m so it can price the fixed-nominal forms at rates results/annuity.json does not publish. "
    "At the published rate the reimplementation reproduces a12_{m64,f62}_cohort exactly to this relative "
    "error -- an assertion in the script, not a claim")
put("indexation_min_pct", legal["indexation_min_pct"],
    "results/legal.json, copied through: payout law art. 6(1)(b), the ASO-set minimum fixed nominal "
    "adjustment cannot be below 1% a year")
put("indexation_max_pct", legal["indexation_max_pct"],
    "results/legal.json, copied through: the same minimum cannot be set above 3% a year")
put("member_choice_real_rate", I_REAL,
    f"the real interest rate used for BOTH products, so the comparison is not confounded by the discount "
    f"rate: the highest of the published flat annuity bases (2%/3%/4%) that does not exceed the "
    f"cap implied by MAPAS bylaw Сл. весник 177/2022 on interest rates")
put("member_choice_real_rate_cap", REAL_CAP,
    "cap derived from the bylaw: nominal <= min(average rate on >=5y government paper issued in the year "
    f"before the last such issue = {RATE_A:.3%}; the last issue itself = {RATE_B:.3%}; the average of the "
    f"fund's last three nominal returns = {RATE_C:.3%}) = {NOMINAL_CAP:.3%}; minus a cost-of-living estimate "
    f"of at least 50% of the three-year average CPI = {COL_MIN:.3%}; and capped at 80% of the nominal rate; "
    "floored at zero (arts. 3-7)")
put("member_choice_nominal_rate_cap", NOMINAL_CAP,
    f"min of the bylaw's three art. 5 tests: {RATE_A:.3%} / {RATE_B:.3%} / {RATE_C:.3%}")
put("member_choice_balance_m_mkd", BALANCE["m"],
    "avg_balance_at_ret_m_2026_mkd -- the modelled average balance of a man retiring at 64 in 2026")
put("member_choice_balance_f_mkd", BALANCE["f"],
    "avg_balance_at_ret_f_2026_mkd -- the modelled average balance of a woman retiring at 62 in 2026")
put("longevity_risk_bearer_programmed_withdrawal", "member",
    "Under a programmed withdrawal the member keeps the account and bears the longevity risk personally: "
    "there is no pooling, so no mortality credits from those who die early, and the payment is recalculated "
    "downwards every year the member survives. The account can be exhausted")
put("longevity_risk_bearer_annuity", "insurer",
    "Under a lifetime annuity the balance is a single premium paid to an insurer, which pools the risk across "
    "annuitants and bears it: the payment is fixed for life however long the member lives")

with open(RESULTS / "system.json", "w") as f:
    json.dump(system, f, indent=2, ensure_ascii=False, sort_keys=True)

COL_M, COL_F = "#0072B2", "#D55E00"
plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5})


class MkTickFormatter(matplotlib.ticker.Formatter):

    def __call__(self, v, pos=None):
        locs = list(getattr(self, "locs", [])) or [v]
        nd = next((d for d in range(5)
                   if all(abs(round(x, d) - x) < 1e-9 * max(1.0, abs(x)) for x in locs)), 4)
        return f"{v:.{nd}f}".replace(".", ",").replace("-", "\u2212")


fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.5), sharey=True, layout="constrained")
for ax, sex, col, lbl in ((axes[0], "m", COL_M, "Мажи, пензионирање на 64 год."),
                          (axes[1], "f", COL_F, "Жени, пензионирање на 62 год.")):
    sub = [r for r in rows if r["sex"] == sex]
    xs = [r["age"] for r in sub]
    ax.plot(xs, [r["pw_monthly_mkd"] / 1000 for r in sub], color=col, lw=1.8,
            label="Програмирано повлекување")
    ANN_STYLE = {
        "idxcpi": ("black", "--", "Ануитет, усогласен со трошоците за живот"),
        "idx1pct": ("#009E73", "-.", f"Ануитет, фиксно +{INDEXATIONS['idx1pct']:.0%} (зак. минимум)"),
        "idx3pct": ("#CC79A7", (0, (3, 1, 1, 1, 1, 1)),
                    f"Ануитет, фиксно +{INDEXATIONS['idx3pct']:.0%} (зак. максимум)"),
    }
    for tag, (c, ls, lab) in ANN_STYLE.items():
        ax.plot(xs, [r[f"annuity_monthly_mkd_{tag}"] / 1000 for r in sub],
                color=c, lw=1.5, ls=ls, label=lab)
    seen = {}
    for tag in ("idxcpi", "idx3pct", "idx1pct"):
        cx = out_keys[f"crossover_age_{sex}_{tag}"]
        if cx is None:
            continue
        seen.setdefault(cx, []).append(tag)
    for (cx, tags), (tx, ty) in zip(sorted(seen.items(), reverse=True),
                                    ((0.42, 0.97), (0.42, 0.80), (0.42, 0.63))):
        tag = tags[0]
        pv = next(r[f"annuity_monthly_mkd_{tag}"] for r in sub if r["age"] == cx) / 1000
        ax.plot([cx], [pv], marker="o", ms=4, color=ANN_STYLE[tag][0], zorder=5)
        if out_keys[f"pw_never_above_annuity_{sex}_{tag}"]:
            ann_lbl = "ануитетот е повисок\nод првата исплата"
            tx, ty = 0.04, 0.22
        else:
            ann_lbl = (f"пресек: {cx} год.\nдоживуваат "
                       f"{out_keys[f'crossover_survival_prob_{sex}_{tag}']:.0%}")
        ax.annotate(ann_lbl, xy=(cx, pv), xytext=(tx, ty), textcoords="axes fraction",
                    va="top", fontsize=7, color=ANN_STYLE[tag][0],
                    arrowprops=dict(arrowstyle="->", lw=0.8, color=ANN_STYLE[tag][0]))
    ax.set_title(lbl)
    ax.set_xlabel("Возраст")
    ax.grid(True, alpha=0.3)
    ax.set_axisbelow(True)
    ax.xaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, p: f"{int(v)}"))
    ax.yaxis.set_major_formatter(MkTickFormatter())
axes[0].set_ylabel("Месечна исплата\n(илјади денари, реални)")
fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncol=2)
fig.savefig(FIG / "system_member_choice.png", dpi=300)
fig.savefig(FIG / "system_member_choice.svg")
plt.close(fig)

print(f"real rate cap {REAL_CAP:.3%} (nominal cap {NOMINAL_CAP:.3%}); using i = {I_REAL:.0%}")
for sex in ("m", "f"):
    print(f"{sex}: balance {BALANCE[sex]:,.0f} | PW first {out_keys[f'pw_monthly_first_year_{sex}_2026']:,.0f}"
          f" -> 75 {out_keys[f'pw_monthly_age75_{sex}']:,.0f}"
          f" -> 85 {out_keys[f'pw_monthly_age85_{sex}']:,.0f}"
          f" -> 90 {out_keys[f'pw_monthly_age90_{sex}']:,.0f}"
          f" | annuity {out_keys[f'annuity_monthly_{sex}_2026']:,.0f}")
    for tag in INDEXATIONS:
        print(f"   {tag:8s} first {out_keys[f'annuity_monthly_{sex}_2026_{tag}']:,.0f}"
              f" | real@85 {out_keys[f'annuity_real_at_85_{sex}_{tag}']:,.0f}"
              f" | crossover {out_keys[f'crossover_age_{sex}_{tag}']}"
              f" (p={out_keys[f'crossover_survival_prob_{sex}_{tag}']:.3f})")
