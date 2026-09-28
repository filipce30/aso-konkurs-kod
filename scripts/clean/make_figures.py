#!/usr/bin/env python3
"""Data figures (log m heatmaps, e65 series, census revision effect) from data/clean/*.csv."""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CLEAN = os.path.join(ROOT, "data", "clean")
FIGURES = os.path.join(ROOT, "figures")
os.makedirs(FIGURES, exist_ok=True)

YEAR_LO, YEAR_HI = 2003, 2023
FIT_LO, FIT_HI = 55, 89

COL_M = "#0072B2"
COL_F = "#D55E00"


def mk_num(v, nd=2):
    s = f"{v:,.{nd}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "\u2212")


class MkTickFormatter(mticker.Formatter):

    def __call__(self, v, pos=None):
        locs = list(getattr(self, "locs", [])) or [v]
        nd = next((d for d in range(5)
                   if all(abs(round(x, d) - x) < 1e-9 * max(1.0, abs(x)) for x in locs)), 4)
        if abs(v) < 0.5 * 10 ** (-nd):
            v = 0.0
        return mk_num(v, nd)


def mk_int_year(v, _pos=None):
    return f"{int(round(v))}"


YEARFMT = mticker.FuncFormatter(mk_int_year)


def _save(fig, name):
    fig.savefig(os.path.join(FIGURES, f"{name}.png"), dpi=300)
    fig.savefig(os.path.join(FIGURES, f"{name}.svg"))


def load_rates_raw():
    out = {}
    for sex in ("m", "f"):
        df = pd.read_csv(os.path.join(CLEAN, f"rates_mxt_{sex}.csv"), index_col="age")
        df.columns = [int(c) for c in df.columns]
        out[sex] = df
    return out


def make_figures():
    plt.rcParams.update({"font.size": 8.5, "axes.labelsize": 8.5, "xtick.labelsize": 8,
                         "ytick.labelsize": 8, "legend.fontsize": 8})
    rates_raw = load_rates_raw()
    lifetables_period = pd.read_csv(os.path.join(CLEAN, "lifetables_period.csv"))
    census_bias_df = pd.read_csv(os.path.join(CLEAN, "census_bias_delta.csv"))

    for sex, fname in [("m", "data_heatmap_logm_m"), ("f", "data_heatmap_logm_f")]:
        mat = np.log(rates_raw[sex]).loc[FIT_LO:FIT_HI, YEAR_LO:YEAR_HI]
        age_mean = mat.mean(axis=1, skipna=True)
        dev = mat.sub(age_mean, axis=0)
        cmax = float(np.nanmax(np.abs(dev.values)))
        fig, ax = plt.subplots(figsize=(6.3, 3.5), layout="constrained")
        im = ax.imshow(dev.values, aspect="auto", cmap="RdBu_r", vmin=-cmax, vmax=cmax,
                        extent=[YEAR_LO - 0.5, YEAR_HI + 0.5, FIT_HI + 0.5, FIT_LO - 0.5])
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Отстапување на log m$_x$\nод просекот по возраст")
        cbar.ax.yaxis.set_major_formatter(MkTickFormatter())
        ax.set_xlabel("Година")
        ax.set_ylabel("Возраст (x)")
        ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
        ax.xaxis.set_major_formatter(YEARFMT)
        ax.axvspan(2019.5, 2021.5, facecolor="none", edgecolor="black", linewidth=1.1, linestyle="--")
        ax.text(2020.5, FIT_LO + 4.2, "ковид\n2020-2021", ha="center", va="top", fontsize=7.5,
                color="black", clip_on=True,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
        ax.axvline(2020.5, color="black", linewidth=0.8, linestyle=":")
        ax.text(2020.5, FIT_HI - 1.6, "именител: попис 2021", ha="center", va="bottom", fontsize=7.5,
                color="black", rotation=90, clip_on=True,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
        ax.axvline(2022, color="white", linewidth=7)
        ax.axvline(2022, color="black", linewidth=0.6, linestyle=":")
        ax.text(2022, FIT_LO + 0.5, "2022: н/д", ha="center", va="top", fontsize=7, color="black", rotation=90,
                clip_on=True, bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.7))
        _save(fig, fname)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.3, 3.0), layout="constrained")
    for sex, col, marker, label in [("m", COL_M, "o", "мажи (e65)"), ("f", COL_F, "s", "жени (e65)")]:
        sub = lifetables_period[(lifetables_period.sex == sex) & (lifetables_period.age == 65)].sort_values("year")
        ax.plot(sub["year"], sub["ex"], linestyle="-" if sex == "m" else "--", marker=marker,
                markersize=4, color=col, label=label)
    ax.set_xlabel("Година")
    ax.set_ylabel("e$_{65}$ (години)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(YEARFMT)
    ax.yaxis.set_major_formatter(MkTickFormatter())
    ax.legend(loc="upper left")
    ax.grid(True, linewidth=0.3, alpha=0.5)
    _save(fig, "data_e65_series")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.3, 3.0), layout="constrained")
    cb = census_bias_df[census_bias_df.metric == "e65"].copy()
    for sex, col, marker, label in [("m", COL_M, "o", "мажи"), ("f", COL_F, "s", "жени")]:
        sub = cb[cb.sex == sex].sort_values("year")
        ax.plot(sub["year"], sub["delta_e65_revised_minus_prerevision"], linestyle="-" if sex == "m" else "--",
                marker=marker, markersize=4, color=col, label=label)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_xlabel("Година")
    ax.set_ylabel(r"$\Delta e_{65}$ (години)")
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.xaxis.set_major_formatter(YEARFMT)
    ax.yaxis.set_major_formatter(MkTickFormatter())
    ax.legend()
    ax.grid(True, linewidth=0.3, alpha=0.5)
    _save(fig, "data_census_delta_e65")
    plt.close(fig)

    print("Figures written: data_heatmap_logm_m/f (ages 55-89, deviation), data_e65_series, "
          "data_census_delta_e65 (PNG 300dpi + SVG)")


if __name__ == "__main__":
    make_figures()
