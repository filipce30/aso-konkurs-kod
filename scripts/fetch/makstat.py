#!/usr/bin/env python3
"""Fetch raw tables from the MAKSTAT (DZS) PX-Web API v1, saved unmodified."""
import json
import urllib.request
import urllib.error
import datetime
import os
import time

OUT_DIR = "data/raw/makstat"
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}

TABLES = [
    (
        "population_revised_1jan_2003_2021",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/ProcenkiNaselenie/ProcenkiPopis2021/Proceni2003_2020Revidirani/125_ProcNasMK01_ml.px",
        "Revised population estimate, 1 January, single year of age 0-100+, by sex, 2003-2021, post-Census-2021 revision",
    ),
    (
        "population_revised_30jun_2003_2020",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/ProcenkiNaselenie/ProcenkiPopis2021/Proceni2003_2020Revidirani/150_ProcNasMK30_ml.px",
        "Revised population estimate, 30 June, single year of age 0-100+, by sex, 2003-2020, post-Census-2021 revision",
    ),
    (
        "population_current_30jun_2021_2025",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/ProcenkiNaselenie/ProcenkiPopis2021/Proceni30Juni/30062021_MKD_Za_PX.px",
        "Current resident population estimate, 30 June, single year of age 0-100+, by sex, 2021-2025, post-Census-2021 base",
    ),
    (
        "population_current_31dec_2021_2025",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/ProcenkiNaselenie/ProcenkiPopis2021/Proceni31Dekemvri/31122021_MKD_Za_PX.px",
        "Current resident population estimate, 31 December, single year of age 0-100+, by sex, 2021-2025, post-Census-2021 base",
    ),
    (
        "population_prerevision_30jun_1994_2020",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/ProcenkiNaselenie/ProcenkiPopis2002Arhiva/114_Popis_RM_1Star_Jun_mk.px",
        "PRE-REVISION (vintage) population estimate per Census 2002, 30 June, single year of age 0-99+, by sex, 1994-2020",
    ),
    (
        "population_prerevision_31dec_1994_2020",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/ProcenkiNaselenie/ProcenkiPopis2002Arhiva/115_Popis_RM_1Star_Dek_mk.px",
        "PRE-REVISION (vintage) population estimate per Census 2002, 31 December, single year of age, by sex, 1994-2020",
    ),
    (
        "population_projections_2022_2070",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/Proekcii/125_Popis_Procenki2070_ml.px",
        "Official population projections 2022-2070, by single year of age and sex",
    ),
    (
        "deaths_by_age_region_2005_2025",
        "https://makstat.stat.gov.mk/PXWeb/api/v1/mk/MakStat/Naselenie/Vitalna/525_VitStat_Reg_UmrVozr_ml.px",
        "Deaths by broad age group (7 groups) and region, 2005-2025. NO sex split, NOT single-year age. Kept only as a coverage cross-check.",
    ),
]


def fetch_metadata(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_data(url, meta):
    query = []
    for v in meta["variables"]:
        query.append({"code": v["code"], "selection": {"filter": "item", "values": v["values"]}})
    body = json.dumps({"query": query, "response": {"format": "json-stat2"}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    rows = []
    now = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    for slug, url, desc in TABLES:
        out_path = os.path.join(OUT_DIR, slug + ".json")
        if os.path.exists(out_path):
            print(f"SKIP {slug} (already fetched)")
            rows.append((out_path, url, desc, "OK (cached)"))
            continue
        attempt = 0
        last_err = None
        while attempt < 4:
            attempt += 1
            try:
                meta = fetch_metadata(url)
                time.sleep(2)
                data = fetch_data(url, meta)
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False)
                print(f"OK  {slug} -> {out_path}")
                rows.append((out_path, url, desc, "OK"))
                last_err = None
                break
            except Exception as e:
                last_err = e
                wait = 10 * attempt
                print(f"retry {slug} after error: {e}; sleeping {wait}s")
                time.sleep(wait)
        if last_err is not None:
            print(f"FAIL {slug}: {last_err}")
            rows.append((out_path, url, desc, f"FAILED: {last_err}"))
        time.sleep(3)
    return rows


if __name__ == "__main__":
    main()
