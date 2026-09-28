#!/usr/bin/env python3
"""Fetch raw Eurostat JSON-stat responses for North Macedonia (geo=MK)."""
import json
import urllib.request
import os

OUT_DIR = "data/raw/eurostat"
os.makedirs(OUT_DIR, exist_ok=True)

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{}?format=JSON&geo=MK&lang=EN"

DATASETS = [
    ("demo_magec", "Deaths by age (single year), sex and NUTS0 (MK), annual"),
    ("demo_pjan", "Population on 1 January by age (single year) and sex (MK), annual"),
    ("demo_mlifetable", "Life tables: probability of death, life expectancy etc. by age (single year) and sex (MK), annual"),
]


def main():
    for slug, desc in DATASETS:
        out_path = os.path.join(OUT_DIR, slug + "_MK.json")
        url = BASE.format(slug)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"OK {slug} -> {out_path}")


if __name__ == "__main__":
    main()
