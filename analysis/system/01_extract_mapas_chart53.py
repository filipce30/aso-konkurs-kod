#!/usr/bin/env python3
"""Extract MAPAS 2025 Chart 5.3 membership by age band, sex and category from the rendered PDF page."""
import json
import subprocess
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "data/raw/mapas/izvestaj-kfpo-2025.pdf"
OUT_CSV = ROOT / "analysis/system/mapas_chart53_membership.csv"
OUT_CAL = ROOT / "analysis/system/mapas_chart53_calibration.json"
TMP_DIR = ROOT / "analysis/system"

PAGE = 36
DPI = 400
REPORT_TOTAL_MEMBERS = 630_396
REPORT_MANDATORY = 569_135
REPORT_VOLUNTARY = 61_261

COLORS = {
    "m_mand": (198, 217, 241),
    "f_mand": (204, 193, 218),
    "m_vol": (0, 0, 128),
    "f_vol": (96, 74, 123),
}
CATEGORY_OF = {"m_mand": "mandatory", "f_mand": "mandatory", "m_vol": "voluntary", "f_vol": "voluntary"}
SEX_OF = {"m_mand": "M", "f_mand": "F", "m_vol": "M", "f_vol": "F"}

X0, X1 = 738, 2657
Y0, Y1 = 2450, 3820

EMPTY_TOP_BANDS = ["65+", "61-64"]
BANDS_WITH_DATA = ["56-60", "51-55", "46-50", "41-45", "36-40", "31-35", "26-30", "21-25", "<=20"]
PATTERN = [3, 3, 3, 3, 2, 2, 2, 2, 2]
assert len(BANDS_WITH_DATA) == len(PATTERN)


def render_page() -> Path:
    prefix = TMP_DIR / "_tmp_chart53"
    subprocess.run(
        ["pdftoppm", "-png", "-r", str(DPI), "-f", str(PAGE), "-l", str(PAGE), str(PDF), str(prefix)],
        check=True,
    )
    candidates = sorted(TMP_DIR.glob("_tmp_chart53-*.png"))
    if not candidates:
        raise SystemExit("pdftoppm did not produce the expected page image")
    return candidates[0]


def classify_exact(rgb):
    for name, c in COLORS.items():
        if rgb == c:
            return name
    return None


def find_gridlines(px, y_probe, x0, x1):
    cols = []
    for x in range(x0, x1):
        r, g, b = px[x, y_probe]
        if abs(r - g) < 8 and abs(g - b) < 8 and 100 < r < 220:
            cols.append(x)
    groups, cur = [], [cols[0]]
    for x in cols[1:]:
        if x - cur[-1] <= 2:
            cur.append(x)
        else:
            groups.append(cur)
            cur = [x]
    groups.append(cur)
    return [sum(g) / len(g) for g in groups]


def main():
    png_path = render_page()
    im = Image.open(png_path).convert("RGB")
    px = im.load()

    grid_x = find_gridlines(px, y_probe=2850, x0=0, x1=im.size[0])
    if len(grid_x) != 11:
        raise SystemExit(f"expected 11 gridlines (borders + 0/20k/40k/60k/80k x2), found {len(grid_x)}: {grid_x}")
    center_x = grid_x[5]
    px_per_20000 = (grid_x[9] - grid_x[1]) / 8.0
    value_per_px = 20000.0 / px_per_20000

    rowcount = {}
    for y in range(Y0, Y1):
        c = 0
        for x in range(X0, X1):
            if classify_exact(px[x, y]) is not None:
                c += 1
        rowcount[y] = c

    runs, state, start, prev = [], False, None, None
    for y in range(Y0, Y1):
        s = rowcount[y] > 3
        if s and not state:
            start = y
        if (not s) and state:
            runs.append((start, prev))
        state = s
        prev = y
    if state:
        runs.append((start, prev))

    n_expected = sum(PATTERN)
    if len(runs) != n_expected:
        raise SystemExit(
            f"expected {n_expected} pixel sub-runs for the {len(BANDS_WITH_DATA)} data-bearing age "
            f"bands, found {len(runs)}. PDF rendering may have changed; inspect manually. runs={runs}"
        )

    rows = []
    for band in EMPTY_TOP_BANDS:
        for cat in COLORS:
            rows.append((band, SEX_OF[cat], CATEGORY_OF[cat], 0))

    i = 0
    for band, n in zip(BANDS_WITH_DATA, PATTERN):
        ymin, ymax = runs[i][0], runs[i + n - 1][1]
        i += n
        for cat, color in COLORS.items():
            xs = [x for y in range(ymin, ymax + 1) for x in range(X0, X1) if px[x, y] == color]
            if xs:
                xmin, xmax = min(xs), max(xs)
                if xmax <= center_x + 2:
                    length_px = center_x - xmin
                elif xmin >= center_x - 2:
                    length_px = xmax - center_x
                else:
                    length_px = max(center_x - xmin, xmax - center_x)
                members = round(length_px * value_per_px)
            else:
                members = 0
            rows.append((band, SEX_OF[cat], CATEGORY_OF[cat], members))

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w") as f:
        f.write("age_band,sex,category,members\n")
        for band, sex, cat, members in rows:
            f.write(f"{band},{sex},{cat},{members}\n")

    total = sum(r[3] for r in rows)
    mandatory = sum(r[3] for r in rows if r[2] == "mandatory")
    voluntary = sum(r[3] for r in rows if r[2] == "voluntary")

    calib = {
        "method": f"pixel measurement of Chart 5.3, izvestaj-kfpo-2025.pdf p.{PAGE}, rendered at {DPI} dpi",
        "extracted_total": total,
        "report_total_members_31_12_2025": REPORT_TOTAL_MEMBERS,
        "error_pct": round((total - REPORT_TOTAL_MEMBERS) / REPORT_TOTAL_MEMBERS, 4),
        "extracted_mandatory": mandatory,
        "report_mandatory": REPORT_MANDATORY,
        "mandatory_error_pct": round((mandatory - REPORT_MANDATORY) / REPORT_MANDATORY, 4),
        "extracted_voluntary": voluntary,
        "report_voluntary": REPORT_VOLUNTARY,
        "voluntary_error_pct": round((voluntary - REPORT_VOLUNTARY) / REPORT_VOLUNTARY, 4),
        "px_per_20000_members": round(px_per_20000, 2),
    }
    with open(OUT_CAL, "w") as f:
        json.dump(calib, f, indent=2, ensure_ascii=False)
    print(json.dumps(calib, indent=2, ensure_ascii=False))

    for p in TMP_DIR.glob("_tmp_chart53-*.png"):
        p.unlink()


if __name__ == "__main__":
    main()
