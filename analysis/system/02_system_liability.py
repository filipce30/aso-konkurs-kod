#!/usr/bin/env python3
"""Second-pillar system liability for the cohorts retiring 2026-2040 and Macedonian-economy facts."""
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
RESULTS = ROOT / "results"
FIG = ROOT / "figures"
ANALYSIS = ROOT / "analysis/system"

legal = json.load(open(RESULTS / "legal.json"))
data = json.load(open(RESULTS / "data.json"))

RET_AGE = {"M": legal["retirement_age_m"], "F": legal["retirement_age_f"]}
PILLAR2_START = legal["pillar2_start_year"]
N_LIFE_INSURERS = 6

ANNUITY_AVAILABLE = (RESULTS / "annuity.json").exists()
if not ANNUITY_AVAILABLE:
    raise SystemExit("results/annuity.json not found -- this script now requires the final annuity factors")


def jsonstat_get(d, **sel):
    idx = 0
    stride = 1
    strides = {}
    for dim_id in reversed(d["id"]):
        strides[dim_id] = stride
        stride *= d["size"][d["id"].index(dim_id)]
    flat_index = 0
    for i, dim_id in enumerate(d["id"]):
        code = sel[dim_id]
        cat_index = d["dimension"][dim_id]["category"]["index"][code]
        flat_index += cat_index * strides[dim_id]
    return d["value"][flat_index]


pop_proj = json.load(open(RAW / "makstat/population_projections_2022_2070.json"))
pop_current = json.load(open(RAW / "makstat/population_current_31dec_2021_2025.json"))
gdp_ds = json.load(open(RAW / "system/makstat_gdp_annual_2000_2025.json"))
wage_ds = json.load(open(RAW / "system/makstat_avg_gross_wage_monthly_2005_2026.json"))

SEX_CODE_PROJ = {"T": "0", "M": "1", "F": "2"}
VARIANT_MEDIUM = "1"


def proj_population(sex, year, age):
    return jsonstat_get(
        pop_proj, **{"Пол": SEX_CODE_PROJ[sex], "Година": str(year), "Варијанта": VARIANT_MEDIUM, "Возраст": str(age)}
    )


SEX_CODE_CUR = {"T": "0", "M": "1", "F": "2"}


def current_population(sex, year, age):
    return jsonstat_get(pop_current, **{"Возраст": str(age), "Година": str(year), "Пол": SEX_CODE_CUR[sex]})


def current_population_total(sex, year):
    return jsonstat_get(pop_current, **{"Возраст": "1000", "Година": str(year), "Пол": SEX_CODE_CUR[sex]})


from collections import defaultdict

_months = list(wage_ds["dimension"]["Месец"]["category"]["index"].keys())
_vals = wage_ds["value"]
_yearvals = defaultdict(list)
for m, v in zip(_months, _vals):
    if v is None:
        continue
    _yearvals[int(m[:4])].append(v)
AVG_WAGE_MONTHLY = {y: sum(v) / len(v) for y, v in _yearvals.items() if len(v) == 12}

_gdp_merki_idx = gdp_ds["dimension"]["Мерки"]["category"]["index"]
_gdp_year_idx = gdp_ds["dimension"]["Година"]["category"]["index"]
_gdp_year_lab = gdp_ds["dimension"]["Година"]["category"]["label"]
_n_year = gdp_ds["size"][2]
_gdp_cp_row = gdp_ds["value"][_gdp_merki_idx["CP"] * _n_year:(_gdp_merki_idx["CP"] + 1) * _n_year]
GDP_NOMINAL_MKD = {}
for code, i in _gdp_year_idx.items():
    label = _gdp_year_lab[code].split()[0]
    GDP_NOMINAL_MKD[int(label)] = _gdp_cp_row[i] * 1_000_000

wb_macro = openpyxl.load_workbook(RAW / "nbrsm/Osnovni_makroek_indikatori_mak.xlsx", data_only=True)
ws_macro = wb_macro["MKD"]
_maxc = ws_macro.max_column


def annual_series(row):
    out = {}
    for c in range(1, _maxc + 1):
        yr = ws_macro.cell(row=5, column=c).value
        is_annual = ws_macro.cell(row=6, column=c).value is None
        if isinstance(yr, int) and is_annual:
            v = ws_macro.cell(row=row, column=c).value
            if v is not None:
                if isinstance(v, str):
                    v = v.replace("*", "").replace(",", ".")
                    try:
                        v = float(v)
                    except ValueError:
                        continue
                out[yr] = float(v)
    return out


GDP_REAL_GROWTH = annual_series(7)
INFLATION_AVG = annual_series(15)
INFLATION_EOP = annual_series(11)
UNEMPLOYMENT = annual_series(19)
MKD_EUR_RATE = annual_series(59)

import datetime


def to_date(v):
    if isinstance(v, datetime.datetime):
        return v.date()
    if isinstance(v, str):
        try:
            return datetime.datetime.strptime(v, "%d.%m.%Y").date()
        except ValueError:
            return None
    return None


wb_bonds = openpyxl.load_workbook(RAW / "nbrsm/nbrm_drzavni_obvrznici_archive.xlsx", data_only=True)
ws_bonds = wb_bonds[wb_bonds.sheetnames[0]]
bond_auctions = []
for r in ws_bonds.iter_rows(min_row=5, max_row=ws_bonds.max_row, values_only=True):
    if r[0] is None:
        continue
    auc, settle, maturity, offer, demand, alloc, coupon, minr, maxr, wavg, fixed = r[:11]
    sd, md = to_date(settle), to_date(maturity)
    if not (sd and md):
        continue
    tenor = round((md - sd).days / 365.25)
    rate = wavg if wavg not in (None, 0) else fixed
    if rate is None:
        continue
    bond_auctions.append({"tenor": tenor, "date": sd, "rate": float(rate)})

BOND_YIELDS = {}
for tenor in (5, 10, 15):
    cands = sorted([b for b in bond_auctions if b["tenor"] == tenor], key=lambda b: b["date"])
    if cands:
        BOND_YIELDS[tenor] = cands[-1]

wb_life = openpyxl.load_workbook(RAW / "aso/25q4_agregirani_zivot.xlsx", data_only=True)
ws_bs = wb_life["BS"]
ws_bu = wb_life["BU"]


def bs_row(aop_code):
    for row in ws_bs.iter_rows(values_only=True):
        if row[1] == aop_code:
            return row[2]
    raise KeyError(aop_code)


def bu_row(aop_code):
    for row in ws_bu.iter_rows(values_only=True):
        if row[1] == aop_code:
            return row[2]
    raise KeyError(aop_code)


LIFE_CAPITAL_2025 = float(bs_row("085"))
LIFE_TP_GROSS_2025 = float(bs_row("106"))
LIFE_TP_UNITLINKED_2025 = float(bs_row("113"))
LIFE_TP_TOTAL_2025 = LIFE_TP_GROSS_2025 + LIFE_TP_UNITLINKED_2025
LIFE_GWP_2025 = float(bu_row("202"))

wb_nonlife = openpyxl.load_workbook(RAW / "aso/25q4_agregirani_nezivot.xlsx", data_only=True)
ws_nl_bu = wb_nonlife["BU"]


def nl_bu_row(aop_code):
    for row in ws_nl_bu.iter_rows(values_only=True):
        if row[1] == aop_code:
            return row[2]
    raise KeyError(aop_code)


NONLIFE_GWP_2025 = float(nl_bu_row("202"))
TOTAL_MARKET_GWP_2025 = LIFE_GWP_2025 + NONLIFE_GWP_2025
LIFE_GWP_SHARE = LIFE_GWP_2025 / TOTAL_MARKET_GWP_2025

CONTRIB_RATE = 0.06
PIOSM_RATE_TOTAL_2025 = 0.188
PIOSM_RATE_FIRST_PILLAR_2025 = 0.128

CONTRIB_TOTAL_2025_TABLE56 = 17_481.17
CONTRIB_FEE_TOTAL_2025_TABLE56 = 297.26
CONTRIB_FEE_PCT = CONTRIB_FEE_TOTAL_2025_TABLE56 / CONTRIB_TOTAL_2025_TABLE56
ASSET_FEE_PCT_ANNUAL = 0.0033

PILLAR2_NET_ASSETS_2025_MKD = 188_344.53 * 1_000_000
PILLAR2_MEMBERS_2025 = 630_396
PILLAR2_MANDATORY_2025 = 569_135
PILLAR2_VOLUNTARY_2025 = 61_261

UNIT_VALUE_SAVA = {
    2006: 105.929336, 2007: 115.511364, 2008: 100.155213, 2009: 116.874672, 2010: 125.009646,
    2011: 129.003093, 2012: 139.225567, 2013: 151.117506, 2014: 160.733889, 2015: 170.193521,
    2016: 179.771032, 2017: 189.686331, 2018: 193.113009, 2019: 213.757775, 2020: 220.489334,
    2021: 241.504146, 2022: 235.843874, 2023: 254.969666, 2024: 278.518719, 2025: 292.831861,
}
UNIT_VALUE_KBP = {
    2006: 106.265900, 2007: 115.303221, 2008: 107.116421, 2009: 120.667142, 2010: 129.590887,
    2011: 130.697013, 2012: 142.372582, 2013: 153.757419, 2014: 164.578077, 2015: 174.392410,
    2016: 184.786292, 2017: 195.037486, 2018: 196.706281, 2019: 218.317207, 2020: 227.667060,
    2021: 252.373824, 2022: 246.231776, 2023: 264.141459, 2024: 288.532506, 2025: 303.569101,
}
_years_uv = sorted(UNIT_VALUE_SAVA)
FUND_RETURN = {}
for y in _years_uv[1:]:
    r_sava = UNIT_VALUE_SAVA[y] / UNIT_VALUE_SAVA[y - 1] - 1
    r_kbp = UNIT_VALUE_KBP[y] / UNIT_VALUE_KBP[y - 1] - 1
    FUND_RETURN[y] = (r_sava + r_kbp) / 2

LAST_HIST_YEAR = 2025
WAGE_CAGR = (AVG_WAGE_MONTHLY[2025] / AVG_WAGE_MONTHLY[2006]) ** (1 / (2025 - 2006)) - 1
FUTURE_RETURN_FLAT = sum(FUND_RETURN.values()) / len(FUND_RETURN)
ENTRY_AGE = 20

import csv

chart53 = list(csv.DictReader(open(ANALYSIS / "mapas_chart53_membership.csv")))
BAND_AGE_MID = {
    "65+": 67, "61-64": 62, "56-60": 58, "51-55": 53, "46-50": 48, "41-45": 43,
    "36-40": 38, "31-35": 33, "26-30": 28, "21-25": 23, "<=20": 19,
}

_gap_ds = json.load(open(RAW / "system/makstat_gender_pay_gap_by_age_2010_2024.json"))
_gap_age_idx = _gap_ds["dimension"]["Возрасни групи"]["category"]["index"]
_gap_year_idx = _gap_ds["dimension"]["Година"]["category"]["index"]
_n_gap_year = _gap_ds["size"][1]
GENDER_PAY_GAP_55_64_2024 = _gap_ds["value"][_gap_age_idx["05"] * _n_gap_year + _gap_year_idx["2024"]] / 100
WAGE_SEX_MULT = {"M": 2 / (2 - GENDER_PAY_GAP_55_64_2024)}
WAGE_SEX_MULT["F"] = WAGE_SEX_MULT["M"] * (1 - GENDER_PAY_GAP_55_64_2024)


def annual_wage(year):
    if year in AVG_WAGE_MONTHLY:
        return AVG_WAGE_MONTHLY[year] * 12
    return AVG_WAGE_MONTHLY[LAST_HIST_YEAR] * 12 * (1 + WAGE_CAGR) ** (year - LAST_HIST_YEAR)


def annual_wage_sex(year, sex):
    return annual_wage(year) * WAGE_SEX_MULT[sex]


def fund_return(year):
    if year in FUND_RETURN:
        return FUND_RETURN[year]
    return FUTURE_RETURN_FLAT


def potential_years(birth_year, through_year):
    entry_year_potential = max(PILLAR2_START, birth_year + ENTRY_AGE)
    return max(0, through_year - entry_year_potential + 1)


def _accumulate(birth_year, sex, through_year, credited_years):
    if credited_years <= 0:
        return 0.0
    entry_year_potential = max(PILLAR2_START, birth_year + ENTRY_AGE)
    n_full = math.floor(credited_years)
    frac = credited_years - n_full
    cap_entry_year = through_year - n_full - (1 if frac > 0 else 0) + 1
    entry_year = max(entry_year_potential, cap_entry_year)
    bal = 0.0
    for t in range(entry_year, through_year + 1):
        weight = 1.0
        if frac > 0 and t == entry_year and entry_year == cap_entry_year:
            weight = frac
        contrib = annual_wage_sex(t, sex) * CONTRIB_RATE * (1 - CONTRIB_FEE_PCT) * weight
        bal = (bal + contrib) * (1 + fund_return(t) - ASSET_FEE_PCT_ANNUAL)
    return bal


def _bisect(f, target, lo, hi, tol=1e-6, max_iter=60):
    f_lo, f_hi = f(lo) - target, f(hi) - target
    if f_lo > 0 or f_hi < 0:
        raise SystemExit(f"calibration target outside [{lo},{hi}] bracket: f_lo={f_lo}, f_hi={f_hi}")
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        f_mid = f(mid) - target
        if abs(f_mid) / target < tol:
            return mid
        if f_mid < 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def balance_density(birth_year, sex, through_year, delta):
    return _accumulate(birth_year, sex, through_year, delta * potential_years(birth_year, through_year))


def modelled_assets_density_at(delta, eval_year=2025):
    total = 0.0
    for r in chart53:
        members = int(r["members"])
        if members == 0:
            continue
        birth_year = eval_year - BAND_AGE_MID[r["age_band"]]
        total += balance_density(birth_year, r["sex"], eval_year, delta) * members
    return total


DENSITY = _bisect(modelled_assets_density_at, PILLAR2_NET_ASSETS_2025_MKD, 0.01, 1.0)


def balance_at_retirement_density(birth_year, sex, retirement_year):
    return balance_density(birth_year, sex, retirement_year - 1, DENSITY)


CONTRIB_TOTAL_2025_TABLE52_MKD = 17_481.17 * 1_000_000
CONTRIB_TOTAL_2024_TABLE52_MKD = 15_476.0 * 1_000_000
MEMBERSHIP_GROWTH_2025 = 0.0320
PILLAR2_MEMBERS_2024 = PILLAR2_MEMBERS_2025 / (1 + MEMBERSHIP_GROWTH_2025)


def measured_density(year, contributions_mkd, members):
    return contributions_mkd / (CONTRIB_RATE * annual_wage(year) * members)


DENSITY_MEASURED_2025 = measured_density(2025, CONTRIB_TOTAL_2025_TABLE52_MKD, PILLAR2_MEMBERS_2025)
DENSITY_MEASURED_2024 = measured_density(2024, CONTRIB_TOTAL_2024_TABLE52_MKD, PILLAR2_MEMBERS_2024)
DENSITY_MEASURED = DENSITY_MEASURED_2025
DENSITY_MEASURED_YEAR = 2025
DENSITY_FLOOR = DENSITY
DENSITY_UPPER = 0.70

DENSITY_SCENARIOS = {
    "central": DENSITY_MEASURED,
    "floor": DENSITY_FLOOR,
    "upper": DENSITY_UPPER,
}


def balance_at_retirement(birth_year, sex, retirement_year, scenario="central"):
    return balance_density(birth_year, sex, retirement_year - 1, DENSITY_SCENARIOS[scenario])


BAND_RANGE = {
    "65+": range(65, 80), "61-64": range(61, 65), "56-60": range(56, 61),
    "51-55": range(51, 56), "46-50": range(46, 51), "41-45": range(41, 46),
    "36-40": range(36, 41), "31-35": range(31, 36), "26-30": range(26, 31),
    "21-25": range(21, 26), "<=20": range(15, 21),
}
OBS_YEAR = 2025
MANDATORY_BIRTH_YEAR_CUT = 1967

band_members, band_pop, band_pop_eligible, band_pop_eligible_current = {}, {}, {}, {}
band_coverage_raw, band_coverage, band_coverage_current = {}, {}, {}
for _band, _ages in BAND_RANGE.items():
    for _sex in ("M", "F"):
        band_members[(_band, _sex)] = sum(
            int(r["members"]) for r in chart53 if r["age_band"] == _band and r["sex"] == _sex
        )
        band_pop[(_band, _sex)] = sum(proj_population(_sex, OBS_YEAR, a) for a in _ages)
        band_pop_eligible[(_band, _sex)] = sum(
            proj_population(_sex, OBS_YEAR, a) for a in _ages
            if OBS_YEAR - a >= MANDATORY_BIRTH_YEAR_CUT
        )
        band_pop_eligible_current[(_band, _sex)] = sum(
            current_population(_sex, OBS_YEAR, a) for a in _ages
            if OBS_YEAR - a >= MANDATORY_BIRTH_YEAR_CUT
        )
        band_coverage_raw[(_band, _sex)] = band_members[(_band, _sex)] / band_pop[(_band, _sex)]
        band_coverage[(_band, _sex)] = (
            band_members[(_band, _sex)] / band_pop_eligible[(_band, _sex)]
            if band_pop_eligible[(_band, _sex)] > 0 else 0.0
        )
        band_coverage_current[(_band, _sex)] = (
            band_members[(_band, _sex)] / band_pop_eligible_current[(_band, _sex)]
            if band_pop_eligible_current[(_band, _sex)] > 0 else 0.0
        )


def band_of_age(age):
    for band, ages in BAND_RANGE.items():
        if age in ages:
            return band
    raise KeyError(age)


_calib = json.load(open(ANALYSIS / "mapas_chart53_calibration.json"))
MEMBERS_PER_PX = 20000.0 / _calib["px_per_20000_members"]
DETECT_THRESHOLD_PX = 4
PRE1967_MEMBERS_UB_PER_BAND = 2 * DETECT_THRESHOLD_PX * MEMBERS_PER_PX
PRE1967_COVERAGE = {s_: band_coverage[("61-64", s_)] for s_ in ("M", "F")}
PRE1967_COVERAGE_UB = {
    s_: PRE1967_MEMBERS_UB_PER_BAND / band_pop[("61-64", s_)] for s_ in ("M", "F")
}


def cohort_coverage(birth_year, sex):
    age_2025 = OBS_YEAR - birth_year
    if birth_year >= MANDATORY_BIRTH_YEAR_CUT:
        band = band_of_age(age_2025)
        c = band_coverage[(band, sex)]
        return c, c, band, "post-1967 (mandatory + voluntary)"
    return (PRE1967_COVERAGE[sex], PRE1967_COVERAGE_UB[sex], "61-64",
            "pre-1967 (continuation declaration only)")


band_balances = []
for band, age_mid in BAND_AGE_MID.items():
    birth_year = OBS_YEAR - age_mid
    for sex in ("M", "F"):
        band_balances.append({
            "age_band": band, "sex": sex,
            "members_2025": band_members[(band, sex)],
            "population_2025": band_pop[(band, sex)],
            "population_2025_eligible_post1967": band_pop_eligible[(band, sex)],
            "coverage_2025_raw_full_band": band_coverage_raw[(band, sex)],
            "coverage_2025_eligible": band_coverage[(band, sex)],
            "balance_2025_density_mkd": balance_density(birth_year, sex, OBS_YEAR, DENSITY),
        })
with open(ANALYSIS / "balance_by_age_band_2025.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(band_balances[0].keys()))
    w.writeheader()
    w.writerows(band_balances)

YEARS = list(range(2026, 2041))
cohort_rows = []
for Y in YEARS:
    for S in ("M", "F"):
        age = RET_AGE[S]
        birth_year = Y - age
        pop_Y = proj_population(S, Y, age)
        cov, cov_ub, band_used, legal_cat = cohort_coverage(birth_year, S)
        retiring_members = pop_Y * cov
        retiring_members_ub = pop_Y * cov_ub
        avg_balance = balance_at_retirement(birth_year, S, Y, "central")
        avg_balance_floor = balance_at_retirement(birth_year, S, Y, "floor")
        avg_balance_upper = balance_at_retirement(birth_year, S, Y, "upper")
        cohort_rows.append({
            "year": Y, "sex": S, "birth_year": birth_year,
            "age_at_31_12_2025": OBS_YEAR - birth_year,
            "population_at_retirement": pop_Y,
            "chart53_band_used": band_used,
            "legal_category": legal_cat,
            "coverage_rate": cov,
            "coverage_rate_upper_bound": cov_ub,
            "retiring_members": retiring_members,
            "retiring_members_upper_bound": retiring_members_ub,
            "density_central_measured": DENSITY_MEASURED,
            "avg_balance_mkd": avg_balance,
            "avg_balance_mkd_floor": avg_balance_floor,
            "avg_balance_mkd_upper": avg_balance_upper,
            "cohort_balance_mkd": retiring_members * avg_balance,
            "cohort_balance_mkd_floor": retiring_members * avg_balance_floor,
            "cohort_balance_mkd_upper": retiring_members * avg_balance_upper,
        })

with open(ANALYSIS / "cohorts_2026_2040.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(cohort_rows[0].keys()))
    w.writeheader()
    w.writerows(cohort_rows)

retiring_total_2026_2040 = sum(r["retiring_members"] for r in cohort_rows)
retiring_by_year_sex = {(r["year"], r["sex"]): r["retiring_members"] for r in cohort_rows}
retiring_m_2026 = retiring_by_year_sex[(2026, "M")]
retiring_f_2026 = retiring_by_year_sex[(2026, "F")]
retiring_2026_ub = sum(r["retiring_members_upper_bound"] for r in cohort_rows if r["year"] == 2026)
avg_balance_m_2026 = [r for r in cohort_rows if r["year"] == 2026 and r["sex"] == "M"][0]["avg_balance_mkd"]
avg_balance_f_2026 = [r for r in cohort_rows if r["year"] == 2026 and r["sex"] == "F"][0]["avg_balance_mkd"]
first_year_m = min((r["year"] for r in cohort_rows if r["sex"] == "M" and r["retiring_members"] > 0),
                   default=None)
first_year_f = min((r["year"] for r in cohort_rows if r["sex"] == "F" and r["retiring_members"] > 0),
                   default=None)

modelled_assets_2025 = modelled_assets_density_at(DENSITY, eval_year=2025)
calibration_error_assets = (modelled_assets_2025 - PILLAR2_NET_ASSETS_2025_MKD) / PILLAR2_NET_ASSETS_2025_MKD

annuity = json.load(open(RESULTS / "annuity.json"))
AGE_SUFFIX = {"M": 64, "F": 62}


def ae_period(sex, curve="3pct"):
    if curve == "3pct":
        return annuity[f"annuity_factor_{sex.lower()}_{AGE_SUFFIX[sex]}_period_3pct"]
    return annuity[f"a12_{sex.lower()}{AGE_SUFFIX[sex]}_period_{curve}"]


def ae_cohort(sex, year, curve="3pct"):
    if curve == "3pct":
        key = f"annuity_factor_{sex.lower()}_{AGE_SUFFIX[sex]}_cohort_3pct_{year}"
        return annuity[key] if key in annuity else annuity[f"annuity_factor_{sex.lower()}_{AGE_SUFFIX[sex]}_cohort_3pct"]
    base = annuity[f"a12_{sex.lower()}{AGE_SUFFIX[sex]}_cohort_eiopa"]
    y2030 = annuity[f"a12_{sex.lower()}{AGE_SUFFIX[sex]}_cohort_eiopa_2030"]
    y2035 = annuity[f"a12_{sex.lower()}{AGE_SUFFIX[sex]}_cohort_eiopa_2035"]
    if year <= 2030:
        return base + (y2030 - base) * (year - 2026) / (2030 - 2026)
    if year <= 2035:
        return y2030 + (y2035 - y2030) * (year - 2030) / (2035 - 2030)
    return y2035 + (y2035 - y2030) / (2035 - 2030) * (year - 2035)


PERIOD_VINTAGE_YEAR = 2026
gap_pct_cohort_vs_period = {S: ae_cohort(S, PERIOD_VINTAGE_YEAR) / ae_period(S) - 1 for S in ("M", "F")}
gap_pct_cohort_vs_period_eiopa = {
    S: ae_cohort(S, PERIOD_VINTAGE_YEAR, "eiopa") / ae_period(S, "eiopa") - 1 for S in ("M", "F")
}

gap_pct_total_by_year_sex = {}
gap_pct_cvp_by_year_sex = {}
gap_pct_stale_by_year_sex = {}
gap_pct_eiopa_by_year_sex = {}
implied_period_factor_by_year_sex = {}
for Y in YEARS:
    for S in ("M", "F"):
        tot = ae_cohort(S, Y) / ae_period(S) - 1
        cvp = gap_pct_cohort_vs_period[S]
        gap_pct_total_by_year_sex[(Y, S)] = tot
        gap_pct_cvp_by_year_sex[(Y, S)] = cvp
        gap_pct_stale_by_year_sex[(Y, S)] = tot - cvp
        implied_period_factor_by_year_sex[(Y, S)] = ae_cohort(S, Y) / (1 + cvp)
        gap_pct_eiopa_by_year_sex[(Y, S)] = gap_pct_cohort_vs_period_eiopa[S]
gap_pct_by_year_sex = gap_pct_cvp_by_year_sex

TAKEUPS = {"0": 0.00, "30": 0.30, "60": 0.60, "100": 1.00}

DISC_RATE = 0.03
PV_BASE_YEAR = 2025


def pv_factor_i3(year):
    return (1.0 + DISC_RATE) ** (-(year - PV_BASE_YEAR))


def load_eiopa_eur_spot(zip_path):
    import io
    import zipfile
    z = zipfile.ZipFile(zip_path)
    name = [n for n in z.namelist() if n.endswith("Term_Structures.xlsx")][0]
    wb = openpyxl.load_workbook(io.BytesIO(z.read(name)), read_only=True, data_only=True)
    ws = wb["RFR_spot_no_VA"]
    out = {}
    for r in ws.iter_rows(min_row=1, max_row=200, max_col=3, values_only=True):
        if isinstance(r[1], int) and r[1] >= 1 and r[2] is not None:
            out[int(r[1])] = float(r[2])
    return out


EIOPA_SPOT = load_eiopa_eur_spot(RAW / "eiopa/EIOPA_RFR_20260831.zip")
EIOPA_CURVE_DATE = "2026-08-31"


def pv_factor_eiopa(year):
    t = year - PV_BASE_YEAR
    if t <= 0:
        return 1.0
    return (1.0 + EIOPA_SPOT[min(t, max(EIOPA_SPOT))]) ** (-t)


flow_balance_mkd = {y: sum(r["cohort_balance_mkd"] for r in cohort_rows if r["year"] == y) for y in YEARS}
flow_balance_m_mkd = {
    y: sum(r["cohort_balance_mkd"] for r in cohort_rows if r["year"] == y and r["sex"] == "M") for y in YEARS
}
flow_balance_f_mkd = {
    y: sum(r["cohort_balance_mkd"] for r in cohort_rows if r["year"] == y and r["sex"] == "F") for y in YEARS
}
flow_balance_floor_mkd = {
    y: sum(r["cohort_balance_mkd_floor"] for r in cohort_rows if r["year"] == y) for y in YEARS
}
flow_balance_upper_mkd = {
    y: sum(r["cohort_balance_mkd_upper"] for r in cohort_rows if r["year"] == y) for y in YEARS
}
flow_gap_mkd = {
    y: sum(r["cohort_balance_mkd"] * gap_pct_cvp_by_year_sex[(y, r["sex"])]
           for r in cohort_rows if r["year"] == y) for y in YEARS
}
flow_gap_total_mkd = {
    y: sum(r["cohort_balance_mkd"] * gap_pct_total_by_year_sex[(y, r["sex"])]
           for r in cohort_rows if r["year"] == y) for y in YEARS
}
flow_gap_stale_mkd = {
    y: sum(r["cohort_balance_mkd"] * gap_pct_stale_by_year_sex[(y, r["sex"])]
           for r in cohort_rows if r["year"] == y) for y in YEARS
}
flow_gap_eiopa_mkd = {
    y: sum(r["cohort_balance_mkd"] * gap_pct_eiopa_by_year_sex[(y, r["sex"])]
           for r in cohort_rows if r["year"] == y) for y in YEARS
}

balances_pv2025_mkd = sum(flow_balance_mkd[y] * pv_factor_i3(y) for y in YEARS)
balances_pv2025_eiopa_mkd = sum(flow_balance_mkd[y] * pv_factor_eiopa(y) for y in YEARS)
balances_pv2025_floor_mkd = sum(flow_balance_floor_mkd[y] * pv_factor_i3(y) for y in YEARS)
balances_pv2025_upper_mkd = sum(flow_balance_upper_mkd[y] * pv_factor_i3(y) for y in YEARS)
gap_pv2025_mkd = sum(flow_gap_mkd[y] * pv_factor_i3(y) for y in YEARS)
gap_pv2025_total_mkd = sum(flow_gap_total_mkd[y] * pv_factor_i3(y) for y in YEARS)
gap_pv2025_stale_mkd = sum(flow_gap_stale_mkd[y] * pv_factor_i3(y) for y in YEARS)
gap_pv2025_eiopa_mkd = sum(flow_gap_eiopa_mkd[y] * pv_factor_eiopa(y) for y in YEARS)

liability_pv2025 = {k: balances_pv2025_mkd * v for k, v in TAKEUPS.items()}
liability_pv2025_eiopa = {k: balances_pv2025_eiopa_mkd * v for k, v in TAKEUPS.items()}
liability_pv2025_floor = {k: balances_pv2025_floor_mkd * v for k, v in TAKEUPS.items()}
liability_pv2025_upper = {k: balances_pv2025_upper_mkd * v for k, v in TAKEUPS.items()}
flow_2040_pv2025_mkd = flow_balance_mkd[2040] * pv_factor_i3(2040)
reserve_gap_pv2025 = {k: gap_pv2025_mkd * v for k, v in TAKEUPS.items()}
reserve_gap_pv2025_total = {k: gap_pv2025_total_mkd * v for k, v in TAKEUPS.items()}
reserve_gap_pv2025_stale = {k: gap_pv2025_stale_mkd * v for k, v in TAKEUPS.items()}
reserve_gap_pv2025_eiopa = {k: gap_pv2025_eiopa_mkd * v for k, v in TAKEUPS.items()}
gap_share_cohort_vs_period = gap_pv2025_mkd / balances_pv2025_mkd
gap_share_stale_table = gap_pv2025_stale_mkd / balances_pv2025_mkd
gap_share_total = gap_pv2025_total_mkd / balances_pv2025_mkd
gap_share_of_liability = gap_share_cohort_vs_period

GDP_LATEST_YEAR = max(GDP_NOMINAL_MKD)
GDP_LATEST_MKD = GDP_NOMINAL_MKD[GDP_LATEST_YEAR]

BEL_VAR995_DELTA_MIXED_I3 = annuity["bel_var995_delta_mixed_i3"]
system_var995_capital_pv2025_mkd = BEL_VAR995_DELTA_MIXED_I3 * liability_pv2025["100"]
system_var995_capital_pv2025_pct_life_capital = system_var995_capital_pv2025_mkd / LIFE_CAPITAL_2025

OBS_NEW_OLDAGE_2025 = 51
OBS_OLDAGE_IN_PAYMENT_2025 = 116
OBS_DISABILITY_EXITS_2025 = 91
OBS_SURVIVOR_EXITS_2025 = 263
OBS_INHERITANCE_PAYOUTS_2025 = 126
OBS_LUMPSUM_PAYOUTS_2025 = 2
OBS_RECIPIENTS_2024 = legal["n_pillar2_old_age_pensioners_programmed_withdrawal_2024"]
OBS_NEW_RECIPIENTS_PER_YEAR = float(OBS_NEW_OLDAGE_2025)

modelled_retirees_2026 = retiring_m_2026 + retiring_f_2026
validation_ratio_2026 = modelled_retirees_2026 / OBS_NEW_OLDAGE_2025
validation_ratio_2026_ub = retiring_2026_ub / OBS_NEW_OLDAGE_2025
modelled_retirees_2026_2028 = sum(r["retiring_members"] for r in cohort_rows if r["year"] <= 2028)
modelled_retirees_2026_2028_ub = sum(
    r["retiring_members_upper_bound"] for r in cohort_rows if r["year"] <= 2028
)

MISSED_YEARS = [y for y in YEARS if (y - RET_AGE["M"]) < MANDATORY_BIRTH_YEAR_CUT
                or (y - RET_AGE["F"]) < MANDATORY_BIRTH_YEAR_CUT]
missed_flow_mkd = {}
missed_members_by_year = {}
for Y in MISSED_YEARS:
    rows_Y = [r for r in cohort_rows if r["year"] == Y]
    pre67 = [r for r in rows_Y if r["birth_year"] < MANDATORY_BIRTH_YEAR_CUT]
    pop_tot = sum(r["population_at_retirement"] for r in pre67)
    tot, mem = 0.0, 0.0
    for r in pre67:
        share = r["population_at_retirement"] / pop_tot if pop_tot else 0.0
        n = OBS_NEW_OLDAGE_2025 * share
        mem += n
        tot += n * r["avg_balance_mkd"]
    missed_flow_mkd[Y] = tot
    missed_members_by_year[Y] = mem
missed_pv2025_mkd = sum(missed_flow_mkd[y] * pv_factor_i3(y) for y in MISSED_YEARS)
missed_members_total = sum(missed_members_by_year.values())


def oadr(year, source="current"):
    if source == "current":
        pop65 = sum(current_population("T", year, a) for a in list(range(65, 100)) ) + current_population("T", year, "100+")
        pop1564 = sum(current_population("T", year, a) for a in range(15, 65))
    else:
        pop65 = sum(proj_population("T", year, a) for a in range(65, 80)) + proj_population("T", year, "80+")
        pop1564 = sum(proj_population("T", year, a) for a in range(15, 65))
    return pop65 / pop1564


OADR_2025 = oadr(2025, "current")
OADR_2050 = oadr(2050, "projection")

CENSUS_POP_2021 = current_population_total("T", 2021)
POP_2025 = current_population_total("T", 2025)

out = {}

def src(key, value, source, year=None, note=None):
    out[key] = value
    out[f"{key}_source"] = source
    if year is not None:
        out[f"{key}_year"] = year
    if note is not None:
        out[f"{key}_note"] = note


_cov_source = (
    "member count in the cohort's OWN Chart-5.3 age band at 31.12.2025 (mandatory + voluntary pooled), "
    "divided by the MAKSTAT PROJECTION population (medium fertility) of the legally eligible birth years "
    "in that band (born from 1967), same sex and date; for cohorts born before 1.1.1967 the 61-64 band is "
    "used instead, because it is the only purely pre-1967 band in the chart and the 245/2018 amendments "
    "removed that whole legal category from the pillar in 2019 "
    "(analysis/system/mapas_chart53_membership.csv x data/raw/makstat/population_projections_2022_2070.json; "
    "data/raw/system/mapas_soopstenie_2019_kriterium_zadolzitelni_chlenovi.html). The projection series is "
    "used for BOTH the ratio and the retirement-year population so the two are on one basis"
)
_ret_source = (
    "MAKSTAT population_projections_2022_2070.json (medium-fertility variant), population at the statutory "
    "retirement age in that year, x " + _cov_source
)

for _y in YEARS:
    src(f"retiring_m_{_y}", retiring_by_year_sex[(_y, "M")], _ret_source, year=_y)
    src(f"retiring_f_{_y}", retiring_by_year_sex[(_y, "F")], _ret_source, year=_y)
src("retiring_total_2026_2040", retiring_total_2026_2040,
    "sum of modelled retiring members 2026-2040, both sexes; see analysis/system/cohorts_2026_2040.csv")
src("retiring_first_year_m", first_year_m,
    "first projection year in which any man reaches 64 with a second-pillar account: the 1967 birth cohort, "
    "the oldest cohort the 2019 reform left in the pillar. NOTE the model's zero before this year is "
    "contradicted by the data for the pre-1967 continuation-declaration residue -- see validation_residual_note")
src("retiring_first_year_f", first_year_f,
    "first projection year in which any woman reaches 62 with a second-pillar account (1967 birth cohort); "
    "same caveat as retiring_first_year_m")
src("avg_balance_at_ret_m_2026_mkd", avg_balance_m_2026,
    "documented accumulation model at the MEASURED contribution density (analysis/system/"
    "02_system_liability.py); scenario analysis, not a forecast. "
    "Note: the modelled number of men reaching 64 with an account in 2026 is zero, so this is a per-member "
    "figure with no members behind it")
src("avg_balance_at_ret_f_2026_mkd", avg_balance_f_2026, out["avg_balance_at_ret_m_2026_mkd_source"])

_flow_source = (
    "sum over both sexes of retiring_members x modelled average balance at retirement, in THAT year's "
    "denars (not discounted, not added across years); analysis/system/cohorts_2026_2040.csv"
)
for _y in YEARS:
    src(f"balances_flow_mkd_{_y}", flow_balance_mkd[_y], _flow_source, year=_y)
    for _k, _v in TAKEUPS.items():
        src(f"liability_flow_takeup{_k}_mkd_{_y}", flow_balance_mkd[_y] * _v,
            f"balances_flow_mkd_{_y} x take-up rate {_v:.0%} -- the part of that year's balances that would "
            f"become an INSURANCE liability. At the observed take-up of 0% it is zero", year=_y)
src("liability_flow_2040_takeup100_mkd", flow_balance_mkd[2040] * TAKEUPS["100"],
    "single-year 2040 balance flow at 100% take-up, in 2040 denars -- the representative mature year",
    year=2040)
src("liability_flow_2040_pct_gdp2025", flow_balance_mkd[2040] / GDP_LATEST_MKD,
    f"liability_flow_2040_takeup100_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR}. CAVEAT: the numerator is in "
    f"2040 denars and the denominator in {GDP_LATEST_YEAR} denars; no nominal-GDP projection to 2040 exists "
    "in data/raw, so this ratio OVERSTATES the 2040 burden relative to 2040 GDP", year=2040)
src("liability_flow_2040_pv2025_mkd", flow_2040_pv2025_mkd,
    "the single-year 2040 flow at 100% take-up, discounted to 31.12.2025 at i = 3% -- the like-for-like "
    "figure to set against a 2025 capital or GDP base", year=2040)
src("liability_flow_2040_pv2025_pct_life_capital", flow_2040_pv2025_mkd / LIFE_CAPITAL_2025,
    "liability_flow_2040_pv2025_mkd / life_capital_2025_mkd -- both in 2025 denars. LEAD WITH THIS rather "
    "than the nominal ratio. Still one future cohort-year against today's sector capital")
src("liability_flow_2040_pv2025_pct_gdp", flow_2040_pv2025_mkd / GDP_LATEST_MKD,
    f"liability_flow_2040_pv2025_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR} -- both in {GDP_LATEST_YEAR} denars")
src("liability_flow_2040_nominal_pct_life_capital_2025", flow_balance_mkd[2040] / LIFE_CAPITAL_2025,
    "UNDISCOUNTED 2040 flow / life_capital_2025_mkd. CAVEAT: 2040 denars over 2025 denars, NOT like-for-like; "
    "use liability_flow_2040_pv2025_pct_life_capital instead")

_pv_source = (
    "present value at 31.12.2025 of the 2026-2040 annual flow of second-pillar balances reaching "
    "retirement age, discounted at i = 3% -- the same flat rate used for the annuity factors in "
    "results/annuity.json. This is a SAVINGS quantity: it becomes an insurance liability only to the "
    "extent it is annuitised (see the take-up keys)"
)
src("pv_balances_2026_2040_mkd", balances_pv2025_mkd, _pv_source)
src("balances_pv2025_2026_2040_mkd", balances_pv2025_mkd, "TWIN of pv_balances_2026_2040_mkd. " + _pv_source)
src("pv_balances_pct_gdp", balances_pv2025_mkd / GDP_LATEST_MKD,
    f"pv_balances_2026_2040_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR}")
src("pv_balances_pct_pillar2_assets_2025", balances_pv2025_mkd / PILLAR2_NET_ASSETS_2025_MKD,
    "pv_balances_2026_2040_mkd / pillar2_net_assets_2025_mkd -- THE MOST INFORMATIVE DENOMINATOR: the "
    "2026-2040 retirement flow expressed against the pillar's existing stock of net assets. It says what "
    "share of today's second-pillar savings reaches retirement age in the next fifteen years, without "
    "dressing savings up as insurance exposure")
src("pv_balances_2026_2040_mkd_floor", balances_pv2025_floor_mkd,
    "same PV on the FLOOR density scenario (the stock calibration, which embeds the 2006-2025 enrolment "
    "ramp and therefore understates cohorts that have been in the pillar most of its life)")
src("pv_balances_2026_2040_mkd_upper", balances_pv2025_upper_mkd,
    f"same PV on the ASSUMED upper density of {DENSITY_UPPER:.2f} -- retained only for comparability with "
    "an earlier calibration; it is 24% above the only measured value and is not used as the main figure")
src("pv_balances_pct_gdp_floor", balances_pv2025_floor_mkd / GDP_LATEST_MKD,
    f"pv_balances_2026_2040_mkd_floor / gdp_nominal_mkd_{GDP_LATEST_YEAR}")
src("pv_balances_pct_gdp_upper", balances_pv2025_upper_mkd / GDP_LATEST_MKD,
    f"pv_balances_2026_2040_mkd_upper / gdp_nominal_mkd_{GDP_LATEST_YEAR}")

for _k, _v in TAKEUPS.items():
    _tk = (f"the ANNUITISED share at a take-up rate of {_v:.0%}"
           + (" -- the OBSERVED base case: every second-pillar old-age payout to date has been a programmed "
              "withdrawal and no insurer holds the annuity licence (results/legal.json "
              "annuity_licence_exists)" if _v == 0 else ""))
    src(f"liability_pv2025_takeup{_k}_mkd", balances_pv2025_mkd * _v,
        f"pv_balances_2026_2040_mkd x {_tk}. This IS an insurance liability, unlike pv_balances_*")
    src(f"liability_pv2025_takeup{_k}_mkd_eiopa", balances_pv2025_eiopa_mkd * _v,
        f"same, discounted on the EIOPA EUR risk-free curve at {EIOPA_CURVE_DATE} (no VA); sensitivity only")
    src(f"liability_takeup{_k}_mkd", balances_pv2025_mkd * _v,
        f"ALIAS of liability_pv2025_takeup{_k}_mkd (present value at 31.12.2025, i = 3%)")
    src(f"liability_takeup{_k}_pv2025_mkd", balances_pv2025_mkd * _v,
        f"TWIN of liability_takeup{_k}_mkd under an unambiguous name")
    for _suffix, _den, _dlabel in (
        ("pct_gdp", GDP_LATEST_MKD, f"gdp_nominal_mkd_{GDP_LATEST_YEAR}"),
        ("pct_life_tp", LIFE_TP_TOTAL_2025, "life_tech_provisions_2025_mkd"),
        ("pct_life_capital", LIFE_CAPITAL_2025, "life_capital_2025_mkd"),
        ("pct_pillar2_assets", PILLAR2_NET_ASSETS_2025_MKD, "pillar2_net_assets_2025_mkd"),
    ):
        src(f"liability_takeup{_k}_{_suffix}", balances_pv2025_mkd * _v / _den,
            f"liability_pv2025_takeup{_k}_mkd / {_dlabel}")
        src(f"liability_takeup{_k}_pv2025_{_suffix}", balances_pv2025_mkd * _v / _den,
            f"TWIN of liability_takeup{_k}_{_suffix}")
src("liability_pv2025_takeup100_pct_gdp", balances_pv2025_mkd / GDP_LATEST_MKD,
    f"liability_pv2025_takeup100_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR}")
src("liability_pv2025_takeup100_pct_life_tp", balances_pv2025_mkd / LIFE_TP_TOTAL_2025,
    "liability_pv2025_takeup100_mkd / life_tech_provisions_2025_mkd")
src("liability_pv2025_takeup100_pct_life_capital", balances_pv2025_mkd / LIFE_CAPITAL_2025,
    "liability_pv2025_takeup100_mkd / life_capital_2025_mkd")
src("takeup_observed", 0.0,
    "the realised annuity take-up rate: zero. All old-age second-pillar payouts to date are programmed "
    "withdrawals (MAPAS 2025 report Sec. 5.8, Табела 5.12) and no insurer holds the class-24 licence "
    "(results/legal.json). The 30/60/100% cases are counterfactuals conditional on the market opening",
    year=2025)

_ae_source_desc = (
    "results/annuity.json (annuity valuation, i=3%, annuity_factor_{m,f}_{64,62}_{period,cohort}_3pct[_YYYY])"
)
_gap_interim = (
    "INTERIM METHOD: results/annuity.json holds only a 2026-vintage period factor, so the cohort-vs-period "
    "component is computed by holding the 2026 relative gap constant across retirement years (exact in 2026) "
    "and attributing the residual to base-table staleness. Replace with a12_{m,f}_period_i3_<year> when the "
    "annuity valuation supplies them"
)
for _k, _v in TAKEUPS.items():
    src(f"reserve_gap_pv2025_mkd_t{_k}", reserve_gap_pv2025[_k],
        f"Main longevity reserve gap: per cohort, balance x take-up {_v:.0%} x (ae_cohort/ae_period - 1) "
        f"measured against the period table CURRENT IN THE RETIREMENT YEAR, discounted to 31.12.2025 at "
        f"i = 3% and summed over 2026-2040, from {_ae_source_desc}. {_gap_interim}")
    src(f"reserve_gap_pv2025_mkd_t{_k}_total", reserve_gap_pv2025_total[_k],
        f"the same gap measured against a FROZEN 2026 period table: cohort-vs-period mispricing PLUS "
        f"base-table staleness. Larger, but an insurer pricing in 2040 would not incur the staleness part")
    src(f"reserve_gap_pv2025_mkd_t{_k}_stale_table", reserve_gap_pv2025_stale[_k],
        "the base-table-staleness component alone (total minus the main component)")
    src(f"reserve_gap_pv2025_mkd_t{_k}_eiopa", reserve_gap_pv2025_eiopa[_k],
        f"main component on the EIOPA EUR curve ({EIOPA_CURVE_DATE})")
    src(f"reserve_gap_mkd_t{_k}", reserve_gap_pv2025[_k],
        f"Alias of reserve_gap_pv2025_mkd_t{_k} (main component, PV at 31.12.2025, i = 3%)")
    src(f"reserve_gap_mkd_t{_k}_eiopa", reserve_gap_pv2025_eiopa[_k],
        f"ALIAS of reserve_gap_pv2025_mkd_t{_k}_eiopa")
    for _suffix, _den, _dlabel in (
        ("pct_gdp", GDP_LATEST_MKD, f"gdp_nominal_mkd_{GDP_LATEST_YEAR}"),
        ("pct_life_tp", LIFE_TP_TOTAL_2025, "life_tech_provisions_2025_mkd"),
        ("pct_life_capital", LIFE_CAPITAL_2025, "life_capital_2025_mkd"),
    ):
        src(f"reserve_gap_{_suffix}_t{_k}", reserve_gap_pv2025[_k] / _den,
            f"reserve_gap_pv2025_mkd_t{_k} / {_dlabel}")
        src(f"reserve_gap_pv2025_{_suffix}_t{_k}", reserve_gap_pv2025[_k] / _den,
            f"TWIN of reserve_gap_{_suffix}_t{_k}")
src("reserve_gap_share_cohort_vs_period", gap_share_cohort_vs_period,
    "Main relative gap: reserve_gap_pv2025_mkd_t100 / pv_balances_2026_2040_mkd. The cost of pricing on "
    "the period table CURRENT IN THE RETIREMENT YEAR instead of the cohort table. This is RQ2's quantity and "
    f"reconciles with it (RQ2 gap_pct_m64_2026_r3 = {gap_pct_cohort_vs_period['M']:.4f}, "
    f"gap_pct_f62_2026_r3 = {gap_pct_cohort_vs_period['F']:.4f}). Take-up cancels out. " + _gap_interim)
src("reserve_gap_share_stale_table", gap_share_stale_table,
    "the additional relative gap that comes purely from valuing 2027-2040 cohorts against a 2026-vintage "
    "period table. It is a measurement artefact of the available annuity factors, NOT a cost an insurer "
    "pricing in the retirement year would face, and must not be reported as part of the mispricing")
src("reserve_gap_share_total", gap_share_total,
    "reserve_gap_share_cohort_vs_period + reserve_gap_share_stale_table -- the figure earlier "
    "reported as a single 'gap'")
src("reserve_gap_share_of_liability", gap_share_cohort_vs_period,
    "Alias of reserve_gap_share_cohort_vs_period (the main component only)")
src("gap_pct_cohort_vs_period_m", gap_pct_cohort_vs_period["M"],
    "ae_cohort(M,2026)/ae_period(M) - 1, from results/annuity.json; equals RQ2's gap_pct_m64_2026_r3")
src("gap_pct_cohort_vs_period_f", gap_pct_cohort_vs_period["F"],
    "ae_cohort(F,2026)/ae_period(F) - 1, from results/annuity.json; equals RQ2's gap_pct_f62_2026_r3")
out["reserve_gap_note"] = (
    "Note (interim method in place): results/annuity.json has no year-vintage period annuity "
    "factors (a12_{m,f}_period_i3_<year>). Until the annuity valuation adds them, the split between "
    "cohort-vs-period mispricing and base-table staleness rests on the documented assumption that the "
    "relative cohort-vs-period gap is constant across retirement years. Re-run this script once the keys "
    "exist; only the SPLIT depends on it, not the total."
)

for _tu in ("30", "60"):
    src(f"system_var995_capital_pv2025_takeup{_tu}_mkd",
        BEL_VAR995_DELTA_MIXED_I3 * liability_pv2025[_tu],
        f"bel_var995_delta_mixed_i3 x liability_pv2025_takeup{_tu}_mkd; capital scales linearly with take-up")
src("system_var995_capital_pv2025_mkd", system_var995_capital_pv2025_mkd,
    "results/annuity.json bel_var995_delta_mixed_i3 (mixed-book 99.5% run-off VaR relative BEL increase) x "
    "liability_pv2025_takeup100_mkd -- i.e. the capital needed IF the whole 2026-2040 flow were annuitised. "
    "At the observed take-up of 0% the required capital is zero")
src("system_var995_capital_pv2025_pct_life_capital", system_var995_capital_pv2025_pct_life_capital,
    "system_var995_capital_pv2025_mkd / life_capital_2025_mkd. CAVEAT: a FIFTEEN-YEAR book against the life "
    "sector's capital as it stands TODAY -- a statement about current capacity, not future solvency")
src("system_var995_capital_mkd", system_var995_capital_pv2025_mkd,
    "ALIAS of system_var995_capital_pv2025_mkd")
src("system_var995_capital_pct_life_capital", system_var995_capital_pv2025_pct_life_capital,
    "ALIAS of system_var995_capital_pv2025_pct_life_capital")
src("bel_var995_delta_mixed_i3", BEL_VAR995_DELTA_MIXED_I3,
    "results/annuity.json, copied through unchanged")

_p58 = "MAPAS izvestaj-kfpo-2025.pdf, Sec. 5.8 (p.66) and Табела 5.12"
src("validation_observed_new_oldage_recipients_2025", OBS_NEW_OLDAGE_2025,
    _p58 + ": 51 members began receiving an old-age second-pillar pension in 2025, all via programmed "
    "withdrawal (САВАз 20 / КБПз 31 / ТРИГЛАВз 0). A true annual FLOW", year=2025)
src("validation_observed_oldage_in_payment_2025", OBS_OLDAGE_IN_PAYMENT_2025,
    _p58 + ": 116 retired members were being paid an old-age second-pillar pension during 2025, including "
    "those who started in earlier years. A STOCK", year=2025)
src("validation_observed_disability_exits_2025", OBS_DISABILITY_EXITS_2025,
    _p58 + ": 91 disability pensions in 2025. On a disability claim the ACCOUNT IS TRANSFERRED to the ПИОСМ "
    "Fund and the pension is paid from the first pillar -- an EXIT from the pillar, not a payout from it",
    year=2025)
src("validation_observed_survivor_exits_2025", OBS_SURVIVOR_EXITS_2025,
    _p58 + ": 263 survivor pensions in 2025, same transfer mechanism -- also EXITS", year=2025)
src("validation_new_recipients_per_year_observed", OBS_NEW_RECIPIENTS_PER_YEAR,
    "= validation_observed_new_oldage_recipients_2025, the report's own 2025 flow. Replaces the secondary "
    "news figure (147 recipients at 30.06.2026) used earlier")
src("validation_observed_new_recipients_per_year", OBS_NEW_RECIPIENTS_PER_YEAR,
    "TWIN of validation_new_recipients_per_year_observed")
src("validation_modelled_retirees_2026_vs_observed", validation_ratio_2026,
    "modelled members reaching a statutory retirement age in 2026 with a second-pillar account (men + women) "
    "divided by the 51 new old-age recipients MAPAS reports for 2025. Flow against flow. The model returns "
    "zero and is therefore contradicted by the data for this group -- see validation_residual_note", year=2026)
src("validation_modelled_retirees_2026_upper_bound", retiring_2026_ub,
    "upper bound on a Chart-5.3 bar too short for the extractor to see (4 px x "
    f"{MEMBERS_PER_PX:.1f} members/px x 2 categories, over the 61-64 band population)", year=2026)
src("validation_modelled_retirees_2026_ub_vs_observed_not_comparable", validation_ratio_2026_ub,
    "upper bound / 51. Both are now annual flows, but the bound is a detection threshold rather than an "
    "estimate, so the ratio is a scale check only", year=2026)
src("validation_modelled_retirees_2026_2028", modelled_retirees_2026_2028,
    "modelled members reaching retirement age with an account, 2026-2028 (central estimate): zero")
src("validation_modelled_retirees_2026_2028_upper_bound", modelled_retirees_2026_2028_ub,
    "same on the chart-resolution upper bound")
src("validation_modelled_new_retirees_per_year_2026_2028", modelled_retirees_2026_2028 / 3.0,
    "modelled annual flow 2026-2028, directly comparable with the observed 51")
src("validation_modelled_new_retirees_per_year_2026_2028_upper_bound", modelled_retirees_2026_2028_ub / 3.0,
    "same on the resolution bound")
src("validation_missed_pv2025_mkd", missed_pv2025_mkd,
    "PV at 31.12.2025 (i = 3%) of the retirements the model misses by setting the pre-1967 cohorts to zero: "
    f"the observed 2025 flow of {OBS_NEW_OLDAGE_2025} a year carried into {MISSED_YEARS[0]}-{MISSED_YEARS[-1]} "
    "(the years in which a pre-1967 cohort still reaches a statutory age), split by sex in proportion to the "
    "projected population at the two retirement ages and valued at the central modelled balance. A "
    "documented rule, not a fit, and deliberately generous")
src("validation_missed_pv_pct_of_headline", missed_pv2025_mkd / balances_pv2025_mkd,
    "validation_missed_pv2025_mkd / pv_balances_2026_2040_mkd -- the size of the missed flow relative to "
    "the main figure")
src("validation_missed_members_total", missed_members_total,
    "total members behind validation_missed_pv2025_mkd")
out["validation_residual_note"] = (
    "The model's zero for 2026-2028 is contradicted by the data. "
    f"MAPAS's 2025 report records {OBS_NEW_OLDAGE_2025} members beginning an old-age second-pillar "
    f"pension in 2025 and {OBS_OLDAGE_IN_PAYMENT_2025} in payment during the year, every one of them at "
    "least 62 and therefore born before about 1964 -- exactly the pre-1967 group this model sets to zero. "
    "The pre-1967 residue of continuation declarations is real; it is simply below the resolution of Chart "
    f"5.3 (a bar under about {DETECT_THRESHOLD_PX * MEMBERS_PER_PX:,.0f} members is invisible). Carrying the "
    "observed flow forward through the last year a pre-1967 cohort can reach a statutory age puts the "
    f"missed present value at {missed_pv2025_mkd:,.0f} MKD, "
    f"{missed_pv2025_mkd / balances_pv2025_mkd:.2%} of the main figure (pv_balances_2026_2040_mkd) -- relevant to the claim, "
    "immaterial for the magnitude. What the model gets right is the shape: a near-zero flow at the statutory "
    f"ages until the 1967 cohort arrives in {first_year_f} (women) and {first_year_m} (men), then a steep "
    "rise. Disability and survivor claims are not a residual inflow: the report states that on "
    "such a claim the account is transferred to the ПИОСМ Fund and the pension is paid from the first "
    f"pillar, so the {OBS_DISABILITY_EXITS_2025} disability and {OBS_SURVIVOR_EXITS_2025} survivor cases of "
    "2025 are exits from the pillar."
)

src("balances_method", "model",
    "MAPAS does not publish average account balance by age (see results/data_availability.json); documented "
    "accumulation model")
src("accumulation_model_variant", "measured_density",
    "central scenario uses the density MEASURED from the report's own 2025 contribution flow; the "
    "stock-calibrated value is the documented floor and 0.70 an upper sensitivity")
src("accumulation_model_density", DENSITY,
    "STOCK-CALIBRATED composite enrolment-and-payment factor delta in (0,1]: credited contribution years = "
    "delta x the cohort's age-implied potential years, calibrated by bisection so modelled 2025 assets equal "
    "MAPAS's reported aggregate. Because it is fitted to a STOCK it averages the whole 2006-2025 enrolment "
    "ramp into one number, so it is a LOWER BOUND for cohorts that have been in the pillar most of its life. "
    "Used for the 2025 cross-section and the floor scenario, not for the central forward estimate")
src("accumulation_model_density_measured", DENSITY_MEASURED,
    "CENTRAL forward density, MEASURED not assumed: contributions paid in the year divided by (6% x average "
    "gross annual wage x members). MAPAS izvestaj-kfpo-2025.pdf Табела 5.2/5.6 "
    f"({CONTRIB_TOTAL_2025_TABLE52_MKD / 1e6:,.2f}m MKD of contributions in 2025), MAKSTAT average gross "
    f"monthly wage x 12 ({annual_wage(2025):,.0f} MKD), and {PILLAR2_MEMBERS_2025:,} members at 31.12.2025 "
    "(p.34). Consistent with the report's own footnote 8 that only about 70% of members made at least one "
    "payment in 2025", year=DENSITY_MEASURED_YEAR)
src("accumulation_model_density_measured_year", DENSITY_MEASURED_YEAR,
    "the year of the contribution flow used for accumulation_model_density_measured")
src("accumulation_model_density_measured_2024", DENSITY_MEASURED_2024,
    f"the same measurement one year earlier ({CONTRIB_TOTAL_2024_TABLE52_MKD / 1e6:,.0f}m MKD of "
    f"contributions, {PILLAR2_MEMBERS_2024:,.0f} members derived from the report's stated 3.20% membership "
    "growth in 2025). Flat against 2025, so the measured density is a level, not a trend", year=2024)
src("contributions_total_2025_mkd", CONTRIB_TOTAL_2025_TABLE52_MKD,
    "MAPAS izvestaj-kfpo-2025.pdf, Табела 5.2 'Вкупно' 2025 column (17,481 m MKD); equals the 'Придонеси' "
    "row of Табела 5.6 to the decimal -- an internal transcription cross-check", year=2025)
src("contributions_total_2024_mkd", CONTRIB_TOTAL_2024_TABLE52_MKD,
    "MAPAS izvestaj-kfpo-2025.pdf, Табела 5.2 'Вкупно 2024' column (15,476 m MKD)", year=2024)
src("avg_gross_annual_wage_2025_mkd", annual_wage(2025),
    "MAKSTAT average gross monthly wage 2025 x 12; the denominator of the measured density", year=2025)
src("pillar2_members_2024_derived", PILLAR2_MEMBERS_2024,
    "630,396 members at 31.12.2025 divided by 1.0320, using the report's own statement (p.34) that "
    "membership grew 3.20% in 2025. Derived, not published directly", year=2024)
src("accumulation_model_density_upper_assumption", DENSITY_UPPER,
    "ASSUMED upper sensitivity only. It is 24% above the measured value and is contradicted by the flat "
    "2024-25 reading, so it is never used as the main figure")
src("density_sensitivity_liability_pv2025_takeup100_mkd", balances_pv2025_upper_mkd,
    f"pv_balances at the ASSUMED upper density {DENSITY_UPPER:.2f}; legacy key name, upper sensitivity")
src("density_sensitivity_ratio", balances_pv2025_upper_mkd / balances_pv2025_mkd,
    "upper-density PV / central PV")
src("density_floor_ratio", balances_pv2025_floor_mkd / balances_pv2025_mkd,
    "floor-density (stock-calibrated) PV / central PV")
src("calibration_error_assets", calibration_error_assets,
    "(modelled 2025 total pillar-2 assets at the stock-calibrated delta) / MAPAS's reported aggregate net "
    "assets 2025 - 1. Near zero BY CONSTRUCTION: one free parameter tuned to one target is not independent "
    "validation")
src("pillar2_modelled_assets_2025_mkd", modelled_assets_2025,
    "sum over MAPAS Chart 5.3 age/sex/category cells of (stock-calibrated per-member balance) x members")
src("chart53_members_per_pixel", MEMBERS_PER_PX,
    "20,000 members / the measured pixel distance between Chart 5.3 gridlines at 400 dpi")
src("chart53_extraction_error", _calib["error_pct"],
    "extracted total members vs the report's own text total")
src("gender_pay_gap_55_64_2024", GENDER_PAY_GAP_55_64_2024,
    "MAKSTAT gender pay gap by age band, Structure of Earnings Survey 2024 wave, '55-64' band; used to split "
    "the economy-wide average wage into sex-specific sub-series")

for _band in ("61-64", "56-60", "51-55", "46-50", "41-45", "36-40"):
    for _sex in ("M", "F"):
        _tag = _band.replace("-", "_").replace("+", "p")
        src(f"coverage_{_sex.lower()}_band_{_tag}", band_coverage[(_band, _sex)],
            "THE RATIO USED IN THE MODEL: Chart 5.3 members (mandatory + voluntary) / MAKSTAT PROJECTION "
            "population of the legally eligible birth years in that band (born from 1967), same sex, "
            "31.12.2025", year=2025)
        src(f"coverage_{_sex.lower()}_band_{_tag}_raw_full_band", band_coverage_raw[(_band, _sex)],
            "same numerator over the FULL band projection population, including birth years the 245/2018 "
            "amendments removed; diluted, shown for transparency only", year=2025)
        src(f"coverage_{_sex.lower()}_band_{_tag}_current_series", band_coverage_current[(_band, _sex)],
            "robustness: the same eligible-denominator ratio computed on the DZS CURRENT population "
            "estimates instead of the projection series", year=2025)
src("coverage_max_observed", max(band_coverage_raw[(b, s_)] for b in BAND_RANGE for s_ in ("M", "F")),
    "the largest members/population ratio anywhere in Chart 5.3. Values this close to 1 are implausible as "
    "true coverage and are the direct evidence that the numerator (a REGISTRY stock of members, which "
    "includes emigrants and people who never contributed) does not match the denominator (a RESIDENT "
    "population). See member_count_uncertainty_*", year=2025)
_unc_lo, _unc_hi = 0.10, 0.15
src("member_count_uncertainty_lo", _unc_lo,
    "lower end of the judgemental band on modelled member counts implied by the registry-versus-resident "
    "mismatch; a stated bound, not a measurement")
src("member_count_uncertainty_hi", _unc_hi,
    "upper end of the same band")
src("pv_balances_pct_gdp_uncertainty_pp_lo", balances_pv2025_mkd * _unc_lo / GDP_LATEST_MKD,
    "pv_balances_pct_gdp x member_count_uncertainty_lo -- how much of GDP the main figure moves for a 10% "
    "error in member counts. Larger than the whole longevity reserve gap")
src("pv_balances_pct_gdp_uncertainty_pp_hi", balances_pv2025_mkd * _unc_hi / GDP_LATEST_MKD,
    "pv_balances_pct_gdp x member_count_uncertainty_hi")
src("chart53_members_in_retiring_cohorts", sum(
        band_members[(b, s_)] for b in ("56-60", "51-55", "46-50") for s_ in ("M", "F")),
    "members Chart 5.3 places in the bands that supply the 2026-2040 retirements. Comparing this with "
    "retiring_total_2026_2040 shows the implicit decrement the method already embeds", year=2025)


for yr in (2023, 2024, GDP_LATEST_YEAR):
    if yr in GDP_NOMINAL_MKD:
        src(f"gdp_nominal_mkd_{yr}", GDP_NOMINAL_MKD[yr],
            "MAKSTAT BDP/BDPTrimesecni/.../175_NacSmA_Mk_04RasGod_01_ml.px (expenditure method, current prices); "
            "data/raw/system/makstat_gdp_annual_2000_2025.json", year=yr)
    if yr in GDP_REAL_GROWTH:
        src(f"gdp_real_growth_{yr}", GDP_REAL_GROWTH[yr] / 100,
            "NBRSM Osnovni_makroek_indikatori_mak.xlsx, row 'БДП (стапки на реален пораст)'", year=yr)
out["gdp_year"] = GDP_LATEST_YEAR
out["gdp_year_note"] = f"{GDP_LATEST_YEAR} figure is DZS/NBRSM preliminary (marked '2)' in the MAKSTAT table)"

for yr in (2023, 2024, 2025):
    if yr in INFLATION_AVG:
        src(f"inflation_{yr}", INFLATION_AVG[yr] / 100,
            "NBRSM Osnovni_makroek_indikatori_mak.xlsx, row 'Инфлација (просек, на кумулативна основа)'", year=yr)
    if yr in INFLATION_EOP:
        src(f"inflation_eop_{yr}", INFLATION_EOP[yr] / 100,
            "NBRSM Osnovni_makroek_indikatori_mak.xlsx, row 'Инфлација (крај на период)'", year=yr)
    if yr in UNEMPLOYMENT:
        src(f"unemployment_rate_{yr}", UNEMPLOYMENT[yr] / 100,
            "NBRSM Osnovni_makroek_indikatori_mak.xlsx, row 'Стапка на невработеност'", year=yr)

for yr in (2023, 2024, 2025):
    if yr in AVG_WAGE_MONTHLY:
        src(f"avg_gross_wage_mkd_{yr}", AVG_WAGE_MONTHLY[yr],
            "MAKSTAT PazarNaTrud/Plati/.../125_PazTrud_Mk_bruto_ml.px, sector 'Вкупно', annual average of the "
            "monthly series; figure is a MONTHLY wage in MKD (standard MK reporting convention), not annual",
            year=yr, note="monthly wage, MKD")

src("life_tech_provisions_2025_mkd", LIFE_TP_TOTAL_2025,
    "ASO 25q4_agregirani_zivot.xlsx, sheet BS, АОП 106 (Бруто технички резерви) + АОП 113 (unit-linked, "
    "risk on policyholder); full year 2025", year=2025)
src("life_tech_provisions_traditional_2025_mkd", LIFE_TP_GROSS_2025,
    "ASO 25q4_agregirani_zivot.xlsx, sheet BS, АОП 106", year=2025)
src("life_tech_provisions_unitlinked_2025_mkd", LIFE_TP_UNITLINKED_2025,
    "ASO 25q4_agregirani_zivot.xlsx, sheet BS, АОП 113", year=2025)
src("life_capital_2025_mkd", LIFE_CAPITAL_2025,
    "ASO 25q4_agregirani_zivot.xlsx, sheet BS, АОП 085 (Капитал и резерви)", year=2025)
src("life_gwp_2025_mkd", LIFE_GWP_2025,
    "ASO 25q4_agregirani_zivot.xlsx, sheet BU, АОП 202 (Бруто полисирана премија), full year 2025", year=2025)
src("nonlife_gwp_2025_mkd", NONLIFE_GWP_2025,
    "ASO 25q4_agregirani_nezivot.xlsx, sheet BU, АОП 202, full year 2025", year=2025)
src("total_market_gwp_2025_mkd", TOTAL_MARKET_GWP_2025, "life_gwp_2025_mkd + nonlife_gwp_2025_mkd", year=2025)
src("life_gwp_share", LIFE_GWP_SHARE, "life_gwp_2025_mkd / total_market_gwp_2025_mkd", year=2025)
src("insurance_penetration", TOTAL_MARKET_GWP_2025 / GDP_LATEST_MKD,
    f"total_market_gwp_2025_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR}", year=2025)
src("life_insurance_penetration", LIFE_GWP_2025 / GDP_LATEST_MKD,
    f"life_gwp_2025_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR}", year=2025)
src("insurance_density_mkd", TOTAL_MARKET_GWP_2025 / POP_2025,
    "total_market_gwp_2025_mkd / population_2025_mkstat (premium per capita, 31.12.2025 MAKSTAT current "
    "population estimate, NOT the 2021 census figure -- see population_2025 for which was used)", year=2025)
src("n_life_insurers", N_LIFE_INSURERS,
    "results/legal.json annuity_licence_exists_source (aso.mk life-insurer register, fetched 2026-09-22): "
    "6 licensed life insurers", year=2026)

src("pillar2_net_assets_2025_mkd", PILLAR2_NET_ASSETS_2025_MKD,
    "MAPAS izvestaj-kfpo-2025.pdf, Табела 5.6, 'ВКУПНОз' row, 31.12.2025 column (188,344.53m MKD)", year=2025)
src("pillar2_members_2025", PILLAR2_MEMBERS_2025,
    "MAPAS izvestaj-kfpo-2025.pdf p.34: total members + temporarily distributed insured, 31.12.2025", year=2025)
src("pillar2_mandatory_members_2025", PILLAR2_MANDATORY_2025, out["pillar2_members_2025_source"], year=2025)
src("pillar2_voluntary_members_2025", PILLAR2_VOLUNTARY_2025, out["pillar2_members_2025_source"], year=2025)
src("pillar2_assets_pct_gdp", PILLAR2_NET_ASSETS_2025_MKD / GDP_LATEST_MKD,
    f"pillar2_net_assets_2025_mkd / gdp_nominal_mkd_{GDP_LATEST_YEAR}; cross-checks MAPAS's own stated 18.04% "
    "(computed against DZS's Q4-2025 GDP estimate) to within 0.1pp", year=2025)
src("contribution_rate_pillar2", CONTRIB_RATE,
    "MAPAS izvestaj-kfpo-2025.pdf p.42: 6% of gross wage, transferred to the mandatory fund, unchanged since "
    "2012; total PIO contribution 18.8% of gross wage in 2025, of which 12.8pp remains in the first pillar. "
    "Matches the 12.8%/6% split cross-checked by IOPS (2020) in research/literature/notes.md", year=2025)
src("contribution_rate_pillar1_2025", PIOSM_RATE_FIRST_PILLAR_2025, out["contribution_rate_pillar2_source"], year=2025)
src("contribution_fee_pct_of_contributions_2025", CONTRIB_FEE_PCT,
    "MAPAS izvestaj-kfpo-2025.pdf Табела 5.6, 2025 column: total contribution fees / total contributions "
    "(297.26 / 17,481.17 million MKD)", year=2025)
src("asset_fee_pct_annual_2025", ASSET_FEE_PCT_ANNUAL,
    "MAPAS izvestaj-kfpo-2025.pdf p.65 text: '0,33% надоместоци од средства' (2025)", year=2025)

for tenor in (5, 10, 15):
    if tenor in BOND_YIELDS:
        b = BOND_YIELDS[tenor]
        src(f"bond_yield_{tenor}y_latest", b["rate"] / 100,
            "NBRSM nbrm_drzavni_obvrznici_archive.xlsx (auction results); weighted-average or fixed tender rate")
        out[f"bond_yield_{tenor}y_date"] = b["date"].isoformat()
if BOND_YIELDS.get(10) and BOND_YIELDS[10]["date"].year < 2023:
    out["bond_yield_10y_note"] = (
        "stale: no 10-year MKD government bond auctioned since "
        f"{BOND_YIELDS[10]['date'].isoformat()}; recent issuance has concentrated in 5y and 15y tenors"
    )

src("mkd_eur_rate_2025", MKD_EUR_RATE.get(2025),
    "NBRSM Osnovni_makroek_indikatori_mak.xlsx, row 'Просечен девизен курс МКД/ЕУР', 2025 annual average",
    year=2025)
src("denar_euro_peg", True,
    "NBRSM's own monetary-policy page (data/raw/system/nbrm_monetarna_politika.html, fetched 2026-09-22): "
    "'Народната банка од септември 1995 година спроведува монетарна стратегија на таргетирање на девизниот "
    "курс на денарот, прво кон германската марка, а од 2001 година кон еврото.' (exchange-rate-targeting "
    "strategy vs the German mark since Sept 1995, vs the euro since 2001)")

src("oadr_2025", OADR_2025,
    "MAKSTAT population_current_31dec_2021_2025.json, 31.12.2025: population 65+ / population 15-64", year=2025)
src("oadr_2050", OADR_2050,
    "MAKSTAT population_projections_2022_2070.json, medium-fertility variant, 2050: population 65+ / 15-64",
    year=2050)
src("census_population_2021", CENSUS_POP_2021,
    "MAKSTAT population_current_31dec_2021_2025.json, total population 31.12.2021 (post-Census-2021 base). "
    "The census-day (5-30.9.2021) figure widely reported is 1,836,713; this is the year-end estimate "
    "on the same revised base, not the census-day count itself.", year=2021)
src("population_2025", POP_2025,
    "MAKSTAT population_current_31dec_2021_2025.json, total population 31.12.2025 (used as the insurance-"
    "density denominator)", year=2025)

out["e65_m_2023"] = data["e65_m_2023"]
out["e65_f_2023"] = data["e65_f_2023"]
out["e65_gain_m_2003_2023"] = data["e65_gain_m_2003_2023"]
out["e65_gain_f_2003_2023"] = data["e65_gain_f_2003_2023"]
out["e65_trend_source"] = "results/data.json (scripts/clean/build_matrices.py); not recomputed here"

out["piosm_transfer_pct_gdp"] = None
out["piosm_transfer_pct_gdp_note"] = (
    "Note: no primary Буџет на РСМ / Државен завод за ревизија document in data/raw; "
    "research/institutional/brief.md flags only secondary press figures (32.6-43.6% of Fund revenue "
    "2014-2024, journalistic). Not computed to avoid citing an unverified number."
)
out["n_pillar1_pensioners"] = None
out["n_pillar1_pensioners_note"] = "Note: no primary PIOSM pensioner-count file in data/raw."

RESULTS.mkdir(exist_ok=True)
with open(RESULTS / "system.json", "w") as f:
    json.dump(out, f, indent=2, ensure_ascii=False, sort_keys=True)

FIG.mkdir(exist_ok=True)

import numpy as np

COL_M = "#0072B2"
COL_F = "#D55E00"
COL_TAKEUP = {"100": "#0072B2", "60": "#009E73", "30": "#E69F00", "0": "#000000"}


def mk_mkd(v, nd=1):
    s = f"{v:,.{nd}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "\u2212")


class MkTickFormatter(matplotlib.ticker.Formatter):

    def __call__(self, v, pos=None):
        locs = list(getattr(self, "locs", [])) or [v]
        nd = next((d for d in range(5)
                   if all(abs(round(x, d) - x) < 1e-9 * max(1.0, abs(x)) for x in locs)), 4)
        return mk_mkd(v, nd)


plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
                     "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5})

m_vals = [retiring_by_year_sex[(y, "M")] for y in YEARS]
f_vals = [retiring_by_year_sex[(y, "F")] for y in YEARS]
x = np.arange(len(YEARS))
w = 0.4

fig, ax = plt.subplots(figsize=(6.3, 3.3), layout="constrained")
ax.bar(x - w / 2, m_vals, w, color=COL_M, edgecolor="black", linewidth=0.6, label="Мажи (64 год.)")
ax.bar(x + w / 2, f_vals, w, color=COL_F, edgecolor="black", linewidth=0.6, hatch="///",
       label="Жени (62 год.)")
ax.set_xticks(x)
ax.set_xticklabels([str(y) for y in YEARS])
ax.set_xlabel("Година на пензионирање")
ax.set_ylabel("Број на членови")
ax.yaxis.set_major_formatter(MkTickFormatter())
ax.grid(True, axis="y", alpha=0.3)
ax.set_axisbelow(True)
_ymax = max(max(m_vals), max(f_vals))
ax.set_ylim(0, _ymax * 1.32)
ax.axvspan(-0.5, YEARS.index(2028) + 0.5, color="0.93", zorder=0)
_if = YEARS.index(first_year_f)
_im = YEARS.index(first_year_m)
ax.annotate("прва кохорта 1967:\nжени на 62 год. (" + str(first_year_f) + ")",
            xy=(_if + w / 2, f_vals[_if]), xytext=(_if - 0.4, _ymax * 0.78),
            ha="center", fontsize=7,
            arrowprops=dict(arrowstyle="->", lw=0.8, color="black"))
ax.annotate("прва кохорта 1967:\nмажи на 64 год. (" + str(first_year_m) + ")",
            xy=(_im - w / 2, m_vals[_im]), xytext=(_im + 2.3, _ymax * 0.86),
            ha="center", fontsize=7,
            arrowprops=dict(arrowstyle="->", lw=0.8, color="black"))
ax.text(1.0, _ymax * 0.22, "нула 2026-2028\n(двата пола)\nи 2026-2030\n(мажи): родените\n"
        "пред 1.1.1967 се\nвратени во\nпрвиот столб",
        fontsize=7, va="bottom", ha="center")
ax.legend(loc="upper left")
fig.savefig(FIG / "system_cohorts_retiring.png", dpi=300)
fig.savefig(FIG / "system_cohorts_retiring.svg")
plt.close(fig)

flow_bn = [flow_balance_mkd[y] / 1e9 for y in YEARS]
cum_pv = {k: [] for k in TAKEUPS}
_run = {k: 0.0 for k in TAKEUPS}
for y in YEARS:
    for k, v in TAKEUPS.items():
        _run[k] += flow_balance_mkd[y] * v * pv_factor_i3(y)
        cum_pv[k].append(_run[k] / 1e9)

fig, ax = plt.subplots(figsize=(6.3, 3.5), layout="constrained")
h_bar = ax.bar(x, flow_bn, 0.62, color="0.85", edgecolor="black", linewidth=0.6,
               label="Годишен тек на салда при пензионирање\n(денари од таа година)")
h100, = ax.plot(x, cum_pv["100"], color=COL_TAKEUP["100"], linestyle="-", marker="o", markersize=3.5,
                label="100%")
h60, = ax.plot(x, cum_pv["60"], color=COL_TAKEUP["60"], linestyle="--", marker="s", markersize=3.5,
               label="60%")
h30, = ax.plot(x, cum_pv["30"], color=COL_TAKEUP["30"], linestyle=":", marker="^", markersize=3.5,
               label="30%")
h0, = ax.plot(x, cum_pv["0"], color=COL_TAKEUP["0"], linestyle="-.", linewidth=1.5,
              label="0% (набљудувана состојба)")
ax.set_xticks(x)
ax.set_xticklabels([str(y) for y in YEARS])
ax.set_xlabel("Година на пензионирање")
ax.set_ylabel("Милијарди денари")
ax.yaxis.set_major_formatter(MkTickFormatter())
ax.grid(True, axis="y", alpha=0.3)
ax.set_axisbelow(True)
_leg = ax.legend(handles=[h100, h60, h30, h0], loc="upper left", alignment="left",
                 title="Кумулативна сегашна вредност на\n31.12.2025 (i = 3%), прифаќање:",
                 title_fontsize=7.5)
ax.add_artist(_leg)
ax.legend(handles=[h_bar], loc="upper center", bbox_to_anchor=(0.62, 1.0))
fig.savefig(FIG / "system_liability_takeup.png", dpi=300)
fig.savefig(FIG / "system_liability_takeup.svg")
plt.close(fig)

print("done. calibration_error_assets =", f"{calibration_error_assets:+.2%}")
print("retiring_total_2026_2040        =", f"{retiring_total_2026_2040:,.0f}")
print("first year with retirees (m/f)  =", first_year_m, "/", first_year_f)
print("flow 2040 (100% take-up, MKD)   =", f"{flow_balance_mkd[2040]:,.0f}",
      f"= {flow_balance_mkd[2040] / GDP_LATEST_MKD:.2%} of {GDP_LATEST_YEAR} GDP")
print("liability_pv2025_takeup100_mkd  =", f"{liability_pv2025['100']:,.0f}",
      f"= {liability_pv2025['100'] / GDP_LATEST_MKD:.2%} of {GDP_LATEST_YEAR} GDP")
print("reserve_gap_pv2025_mkd_t100     =", f"{reserve_gap_pv2025['100']:,.0f}",
      f"({gap_share_of_liability:.2%} of liability)")
print("system_var995_capital_pv2025    =", f"{system_var995_capital_pv2025_mkd:,.0f}",
      f"= {system_var995_capital_pv2025_pct_life_capital:.1%} of life capital")
print("coverage 56-60 elig. (m/f)      =", f"{band_coverage[('56-60','M')]:.2%}",
      "/", f"{band_coverage[('56-60','F')]:.2%}",
      f"(raw full band {band_coverage_raw[('56-60','M')]:.2%}/{band_coverage_raw[('56-60','F')]:.2%})")
print("flow 2040 PV2025                =", f"{flow_2040_pv2025_mkd:,.0f}",
      f"= {flow_2040_pv2025_mkd / LIFE_CAPITAL_2025:.2f}x life capital")
print("validation: observed inflow/yr  =", f"{OBS_NEW_RECIPIENTS_PER_YEAR:.1f}",
      "| modelled 2026-2028/yr =", f"{modelled_retirees_2026_2028 / 3.0:,.0f}",
      "| resolution cap/yr =", f"{modelled_retirees_2026_2028_ub / 3.0:,.0f}")
