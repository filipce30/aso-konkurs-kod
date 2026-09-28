"""Parser for the official MAKSTAT (DZS) rolling 3-year abridged period life tables."""
from __future__ import annotations

import glob
import os
import re

import pandas as pd

SEX_BY_SHEET_ORDER = ["t", "m", "f"]
FIELD_ORDER = ["mx", "qx", "px", "lx", "dx", "Lx", "Tx", "ex"]


def _find_header_cell(df: pd.DataFrame, target: str = "mx"):
    nrow, ncol = df.shape
    for r in range(min(6, nrow)):
        for c in range(ncol):
            v = df.iat[r, c]
            if isinstance(v, str) and v.strip().lower() == target:
                return r, c
    raise ValueError(f"could not find header cell '{target}'")


def read_one_sheet(path: str, sheet_index: int) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_index, header=None)
    r, c = _find_header_cell(df, "mx")
    age_col = c - 1
    data = df.iloc[r + 1 :, age_col : c + len(FIELD_ORDER)].copy()
    data.columns = ["age"] + FIELD_ORDER
    data = data[pd.to_numeric(data["age"], errors="coerce").notna()]
    data["age"] = data["age"].astype(int)
    for col in FIELD_ORDER:
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data[(data["age"] >= 0) & (data["age"] <= 99)]
    return data.reset_index(drop=True)


def read_all_dzs_tables(dirpath: str) -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(os.path.join(dirpath, "MortalitetniTablici*.xls*"))):
        fname = os.path.basename(path)
        m = re.search(r"(\d{4})-(\d{4})", fname)
        y1, y2 = int(m.group(1)), int(m.group(2))
        for sheet_idx, sex in enumerate(SEX_BY_SHEET_ORDER):
            d = read_one_sheet(path, sheet_idx)
            d.insert(0, "sex", sex)
            d.insert(0, "window_end", y2)
            d.insert(0, "window_start", y1)
            d.insert(0, "window", f"{y1}-{y2}")
            rows.append(d)
    return pd.concat(rows, ignore_index=True)


if __name__ == "__main__":
    out = read_all_dzs_tables("data/raw/makstat/mortality_tables")
    print(out.shape)
    print(out.head())
    chk = out[(out.window == "2023-2025") & (out.sex == "m") & (out.age.isin([0, 65]))]
    print(chk)
