#!/usr/bin/env python3
"""Figure annuity_shock_vs_var: Solvency II longevity shock against the 99.5% VaR, one panel per horizon."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HEAD = "i3"
COL_SHOCK = "#999999"
COL_VAR = "#CC79A7"
NAME = "annuity_shock_vs_var"


def mk(v, nd=3):
    return f"{v:,.{nd}f}".replace(",", " ").replace(".", ",").replace("-", "\u2212")


def pct_tick(v, _pos=None):
    x = 100.0 * v
    for nd in (0, 1, 2):
        if abs(x - round(x, nd)) < 1e-9:
            return mk(x, nd) + "%"
    return mk(x, 2) + "%"


def draw(R: dict, fig_dir: Path) -> list[Path]:
    age_m, age_f = int(R["retirement_age_m"]), int(R["retirement_age_f"])
    w_m = R["mixed_weight_m"]

    def eq_oneyear(c):
        return R.get(f"oneyear_var995_equiv_qx_shock_{c}")

    def eq_runoff(c):
        return (R.get("runoff_var995_equiv_qx_shock_mixed") if c == "mixed"
                else R.get(f"var995_equiv_qx_shock_pct_{c}"))

    panels = [
        ("Едногодишен хоризонт (SCR)",
         "Моделски 99,5% VaR",
         lambda c: R.get(f"oneyear_var995_delta_{c}_{HEAD}"), eq_oneyear, None),
        ("До истек на обврската (не е SCR)",
         "Моделски 99,5% VaR",
         lambda c: R[f"bel_var995_delta_{c}_{HEAD}"], eq_runoff,
         lambda c: (R.get(f"bel_var995_delta_{c}_{HEAD}_ci_lo"),
                    R.get(f"bel_var995_delta_{c}_{HEAD}_ci_hi"))),
    ]
    cols = ["m", "f", "mixed"]
    tick = {"m": f"Мажи, {age_m}", "f": f"Жени, {age_f}",
            "mixed": f"Мешан\n(w(м) = {mk(w_m, 3)})"}

    plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 8.5, "axes.titlesize": 8.5,
                         "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5})
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 3.5), sharey=True, layout="constrained")
    for ax, (title, varlbl, varfn, eqfn, cifn) in zip(axes, panels):
        xp = np.arange(len(cols))
        shock = [R[f"bel_shock20_delta_{c}_{HEAD}"] for c in cols]
        var = [varfn(c) for c in cols]
        var = [np.nan if v is None else v for v in var]
        ax.bar(xp - 0.19, shock, 0.36, color=COL_SHOCK, alpha=0.45,
               edgecolor=COL_SHOCK, hatch="///",
               label="Стандарден шок −20% q$_x$")
        err = None
        if cifn is not None:
            lo, hi = [], []
            for c, v in zip(cols, var):
                a, b = cifn(c)
                lo.append(v - a if a is not None else 0.0)
                hi.append(b - v if b is not None else 0.0)
            err = np.array([lo, hi])
        ax.bar(xp + 0.19, var, 0.36, color=COL_VAR, edgecolor="black", label=varlbl,
               yerr=err, capsize=2.5, ecolor="black", error_kw={"linewidth": 0.8})
        for k, c in enumerate(cols):
            ax.text(xp[k] - 0.19, shock[k] + 0.003, mk(100 * shock[k], 1) + "%",
                    ha="center", fontsize=7)
            if np.isnan(var[k]):
                ax.text(xp[k] + 0.19, 0.003, "н/п", ha="center", fontsize=7)
                continue
            top = var[k] + (err[1][k] if err is not None else 0.0)
            ax.text(xp[k] + 0.19, top + 0.003, mk(100 * var[k], 1) + "%",
                    ha="center", fontsize=7)
            eq = eqfn(c)
            if eq is not None:
                ax.text(xp[k] + 0.19, top + 0.011, "екв.\n" + mk(100 * eq, 1) + "%",
                        ha="center", va="bottom", fontsize=7, style="italic", linespacing=0.95)
        ax.set_xticks(xp)
        ax.set_xticklabels([tick[c] for c in cols])
        ax.set_title(title)
        ax.grid(True, axis="y", alpha=0.3)
        ax.yaxis.set_major_locator(mticker.MultipleLocator(0.05))
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(pct_tick))

    axes[0].set_ylabel("ΔBEL, % од најдобрата проценка")
    axes[0].set_ylim(0, max(R[f"bel_var995_delta_m_{HEAD}_ci_hi"],
                            R[f"bel_shock20_delta_m_{HEAD}"]) * 1.42)
    fig.legend(*axes[1].get_legend_handles_labels(), loc="outside lower center", ncol=2)
    fig_dir.mkdir(exist_ok=True)
    out = [fig_dir / f"{NAME}.png", fig_dir / f"{NAME}.svg"]
    fig.savefig(out[0], dpi=300)
    fig.savefig(out[1])
    plt.close(fig)
    return out


if __name__ == "__main__":
    with open(ROOT / "results" / "annuity.json", encoding="utf-8") as fh:
        R = json.load(fh)
    for p in draw(R, ROOT / "figures"):
        print(f"written {p.relative_to(ROOT)}")
