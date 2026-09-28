#!/usr/bin/env python3
"""Fetch Eurostat deaths and population JSON-stat for the comparator countries into data/raw/compare/."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_DIR = os.path.join(REPO, "data", "raw", "compare")
SOURCES = os.path.join(REPO, "data", "raw", "SOURCES.csv")

BASE = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
        "{slug}?format=JSON&geo={geo}&lang=EN")

GEOS = {
    "BG": "Bulgaria",
    "EE": "Estonia",
    "LT": "Lithuania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "HR": "Croatia",
}

DATASETS = {
    "demo_magec": "Deaths by single year of age and sex, annual",
    "demo_pjan": "Population on 1 January by single year of age and sex, annual",
}


def fetch(slug: str, geo: str) -> dict:
    url = BASE.format(slug=slug, geo=geo)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8")), url


def year_span(d: dict) -> str:
    ids = d["id"]
    sizes = d["size"]
    ti = ids.index("time")
    idx = d["dimension"]["time"]["category"]["index"]
    if isinstance(idx, dict):
        codes = [None] * len(idx)
        for c, p in idx.items():
            codes[p] = c
    else:
        codes = list(idx)
    stride = 1
    for s in sizes[ti + 1:]:
        stride *= s
    n_time = sizes[ti]
    val = d["value"]
    keys = (int(k) for k in val.keys()) if isinstance(val, dict) else (
        i for i, v in enumerate(val) if v is not None)
    seen = set()
    for k in keys:
        seen.add((k // stride) % n_time)
    years = sorted(int(codes[i]) for i in seen)
    if not years:
        return "NONE"
    gaps = [y for y in range(years[0], years[-1] + 1) if y not in set(years)]
    s = f"{years[0]}-{years[-1]}"
    if gaps:
        s += " (missing " + ",".join(str(g) for g in gaps) + ")"
    return s


def append_sources(rows: list[dict]) -> None:
    with open(SOURCES, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        header = rdr.fieldnames
        existing = [r for r in rdr]
    new_files = {r["file"] for r in rows}
    kept = [r for r in existing if r["file"] not in new_files]
    for r in rows:
        for k in header:
            r.setdefault(k, "")
    with open(SOURCES, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, quoting=csv.QUOTE_MINIMAL,
                           lineterminator="\n")
        w.writeheader()
        for r in kept + rows:
            w.writerow({k: r.get(k, "") for k in header})


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for geo, cname in GEOS.items():
        for slug, desc in DATASETS.items():
            out = os.path.join(OUT_DIR, f"{slug}_{geo}.json")
            rel = os.path.relpath(out, REPO)
            d, url = fetch(slug, geo)
            with open(out, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False)
            span = year_span(d)
            rows.append({
                "file": rel,
                "organisation": "Eurostat",
                "url": url,
                "accessed_at_utc": now,
                "description": f"{desc}, {cname} ({geo})",
                "granularity": "single year of age (Y_LT1..Y99,Y_OPEN,TOTAL,UNK), sex (M/F/T)",
                "years": span,
                "open_age": "Y_OPEN (~100+)",
                "notes": ("Comparator country for the truncation backtest and regional "
                          "context in analysis/compare/; same dataset, API and definitions "
                          "as data/raw/eurostat/*_MK.json. Exposure for this study is the "
                          "average of 1 January populations for t and t+1 (documented "
                          "deviation from the MAKSTAT mid-year basis used for MK)."),
            })
            print(f"OK {slug} {geo} -> {rel}  years={span}  "
                  f"({os.path.getsize(out)/1024:.0f} KB)")
    append_sources(rows)
    print(f"SOURCES.csv: {len(rows)} rows written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
