#!/usr/bin/env python3
"""Fetch MAKSTAT PX-Web tables with one dimension restricted per request, plus the life-table workbooks."""
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://makstat.stat.gov.mk/PXWeb/api/v1/mk"
OUT_DIR = "data/raw/makstat"
MT_DIR = os.path.join(OUT_DIR, "mortality_tables")
HEADERS = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}


def get_json(url, method="GET", body=None, timeout=30):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_config():
    return {
        "mk": get_json(f"{BASE.replace('/mk','/mk')}/?config"),
    }


NASELENIE_FOLDERS = [
    "VencaniRazvedeni", "Vitalna", "VnatresniMigracii", "NadvoresniMigracii",
    "ProcenkiNaselenie", "PolindikatorNaselenie", "DetPod",
    "PrethodniKavrtalni", "Proekcii", "MortalitetniTablici",
]
NESTED_FOLDERS = [
    "VnatresniMigracii/VnatresniMigraciiTekovni",
    "VnatresniMigracii/VnatresniMig2000.2004",
    "ProcenkiNaselenie/ProcenkiPopis2021",
    "ProcenkiNaselenie/ProcenkiPopis2002Arhiva",
    "ProcenkiNaselenie/ProcenkiPopis2021/Proceni30Juni",
    "ProcenkiNaselenie/ProcenkiPopis2021/Proceni31Dekemvri",
    "ProcenkiNaselenie/ProcenkiPopis2021/Proceni2003_2020Revidirani",
    "DetPod/DetPod1", "DetPod/DetPod2", "DetPod/DetPod3",
    "DetPod/DetPod4", "DetPod/DetPod5",
]


def fetch_tree():
    tree = {"api_limits": None, "folders": {}, "broken_folders": {}}
    tree["api_limits"] = get_json("https://makstat.stat.gov.mk/PXWeb/api/v1/mk/?config")
    time.sleep(1.2)
    tree["api_limits_en"] = get_json("https://makstat.stat.gov.mk/PXWeb/api/v1/en/?config")
    time.sleep(1.2)

    tree["folders"]["Naselenie"] = get_json(f"{BASE}/MakStat/Naselenie")
    time.sleep(1.2)

    for fid in NASELENIE_FOLDERS + NESTED_FOLDERS:
        url = f"{BASE}/MakStat/Naselenie/{fid}"
        try:
            tree["folders"][fid] = get_json(url)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            ok = False
            for alt_url in (url + "/", url.replace("/mk/", "/en/")):
                time.sleep(1.2)
                try:
                    tree["folders"][fid] = get_json(alt_url)
                    ok = True
                    break
                except urllib.error.HTTPError as e2:
                    body = e2.read().decode("utf-8", "replace")
            if not ok:
                tree["broken_folders"][fid] = {
                    "url": url,
                    "http_status": e.code,
                    "body": body,
                }
        time.sleep(1.2)
    return tree


DEATH_CANDIDATES = {
    "125_Vit_mk_Umreni_ml.px": "Vitalna",
    "225_VitStat_Op_UmrVoz_ml.px": "Vitalna",
    "425_VitStat_Reg_UmrPol_ml.px": "Vitalna",
    "525_VitStat_Reg_UmrVozr_ml.px": "Vitalna",
    "670_VitStat_Umr_Etn_Voz_Pol_ml.px": "Vitalna",
    "685_VitStat_Umr_Pol_ops_ml.px": "Vitalna",
    "695_VItStat_Umr_Voz_Pol_Skolo_ml.px": "Vitalna",
    "700_VitStat_Umr_zan_pol_voz_ml.px": "Vitalna",
    "910_VitStat_StapUmren_vozrasni_ml.px": "Vitalna",
}


def fetch_candidate_metadata():
    meta = {}
    for table, folder in DEATH_CANDIDATES.items():
        url = f"{BASE}/MakStat/Naselenie/{folder}/{table}"
        try:
            meta[table] = get_json(url)
        except urllib.error.HTTPError as e:
            meta[table] = {"error": e.code, "body": e.read().decode("utf-8", "replace")}
        time.sleep(1.2)
    return meta


RESTRICTED_DOWNLOADS = [
    (
        "deaths_age_sex_school_national_2010_2025",
        "695_VItStat_Umr_Voz_Pol_Skolo_ml.px",
        {"Школската подготовка": ["10"]},
    ),
    (
        "deaths_age_sex_occupation_national_2010_2025",
        "700_VitStat_Umr_zan_pol_voz_ml.px",
        {"Занимање": ["00"]},
    ),
    (
        "deaths_age_sex_ethnicity_national_2010_2024",
        "670_VitStat_Umr_Etn_Voz_Pol_ml.px",
        {"Етничка припадност": ["00"]},
    ),
]


def fetch_data_restricted(meta, url, restrict):
    query = []
    for v in meta["variables"]:
        if v["code"] in restrict:
            query.append({"code": v["code"], "selection": {"filter": "item", "values": restrict[v["code"]]}})
        else:
            query.append({"code": v["code"], "selection": {"filter": "all", "values": ["*"]}})
    body = {"query": query, "response": {"format": "json-stat2"}}
    return get_json(url, method="POST", body=body, timeout=60)


def fetch_chunked_by_year(meta, url, year_var_code):
    years = next(v["values"] for v in meta["variables"] if v["code"] == year_var_code)
    chunks = {}
    for y in years:
        query = []
        for v in meta["variables"]:
            if v["code"] == year_var_code:
                query.append({"code": v["code"], "selection": {"filter": "item", "values": [y]}})
            else:
                query.append({"code": v["code"], "selection": {"filter": "all", "values": ["*"]}})
        body = {"query": query, "response": {"format": "json-stat2"}}
        chunks[y] = get_json(url, method="POST", body=body, timeout=60)
        time.sleep(1.2)
    return chunks


def run_restricted_downloads():
    for slug, table, restrict in RESTRICTED_DOWNLOADS:
        url = f"{BASE}/MakStat/Naselenie/Vitalna/{table}"
        out_path = os.path.join(OUT_DIR, slug + ".json")
        meta = get_json(url)
        time.sleep(1.2)
        data = fetch_data_restricted(meta, url, restrict)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"OK  {slug} -> {out_path}")
        time.sleep(1.2)


MORTALITETNI_TABLICI = [
    ("MortalitetniTablici2011-2013.xls",), ("MortalitetniTablici2012-2014.xls",),
    ("MortalitetniTablici2013-2015.xls",), ("MortalitetniTablici2014-2016.xls",),
    ("MortalitetniTablici2015-2017.xls",), ("MortalitetniTablici2016-2018.xls",),
    ("MortalitetniTablici2017-2019.xls",), ("MortalitetniTablici2018-2020.xls",),
    ("MortalitetniTablici2019-2021.xls",), ("MortalitetniTablici2020-2022.xlsx",),
    ("MortalitetniTablici2021-2023.xlsx",), ("MortalitetniTablici2022-2024.xlsx",),
    ("MortalitetniTablici2023-2025.xlsx",),
]
RESOURCES_BASE = "https://makstat.stat.gov.mk/PXWeb/Resources/PX/Databases/MakStat/Naselenie/MortalitetniTablici"


def fetch_life_tables():
    os.makedirs(MT_DIR, exist_ok=True)
    for (fname,) in MORTALITETNI_TABLICI:
        out_path = os.path.join(MT_DIR, fname)
        req = urllib.request.Request(f"{RESOURCES_BASE}/{fname}", headers=HEADERS)
        with urllib.request.urlopen(req, timeout=60) as r:
            content = r.read()
        with open(out_path, "wb") as f:
            f.write(content)
        print(f"OK  {fname} ({len(content)} bytes) -> {out_path}")
        time.sleep(1.2)


def main():
    print("== tree ==")
    tree = fetch_tree()
    with open(os.path.join(OUT_DIR, "naselenie_tree.json"), "w", encoding="utf-8") as f:
        json.dump(tree, f, ensure_ascii=False, indent=1)

    print("== candidate metadata ==")
    meta = fetch_candidate_metadata()
    with open(os.path.join(OUT_DIR, "deaths_candidates_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    print("== restricted national deaths downloads ==")
    run_restricted_downloads()

    print("== life tables ==")
    fetch_life_tables()


if __name__ == "__main__":
    main()
