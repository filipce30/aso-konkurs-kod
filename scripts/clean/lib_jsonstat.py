"""Minimal dependency-free JSON-stat 2.0 loader that keeps the raw dimension codes."""
from __future__ import annotations

import itertools
import json

import pandas as pd


def load_jsonstat(path: str):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)

    ids = d["id"]
    sizes = d["size"]
    dims = []
    labels = {}
    for dim in ids:
        cat = d["dimension"][dim]["category"]
        index = cat.get("index")
        lbl = cat.get("label", {})
        if index is None:
            codes = list(lbl.keys())
        elif isinstance(index, dict):
            codes = [None] * len(index)
            for code, pos in index.items():
                codes[pos] = code
        else:
            codes = list(index)
        dims.append(codes)
        labels[dim] = lbl

    val = d["value"]
    n = 1
    for s in sizes:
        n *= s
    if isinstance(val, dict):
        values = [None] * n
        for k, v in val.items():
            values[int(k)] = v
    else:
        values = val

    rows = list(itertools.product(*dims))
    df = pd.DataFrame(rows, columns=ids)
    df["value"] = values
    return df, labels
