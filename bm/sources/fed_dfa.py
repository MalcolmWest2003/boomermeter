"""Federal Reserve Distributional Financial Accounts (DFA), by generation.

The DFA splits the Financial Accounts' household balance sheet across
generations using the Survey of Consumer Finances. A household belongs to the
generation of its reference person ('head'). Published quarterly, about 11
weeks after each quarter ends; every release can revise back history.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import zipfile

from .. import snapshot

SOURCE = "fed-dfa"
URL = "https://www.federalreserve.gov/releases/z1/dataviz/download/zips/dfa.zip"
LEVELS_FILE = "dfa-generation-levels.csv"

# Column we want -> predicate on the normalized column name.
COLUMNS = {
    "networth": lambda c: c == "net worth",
    "equities": lambda c: c.startswith("corporate equities"),
    "realestate": lambda c: c == "real estate",
}


def _norm(s: str) -> str:
    return " ".join(s.strip().lower().replace("_", " ").split())


def quarter_end(label: str) -> dt.date:
    """'2026:Q2' -> 2026-06-30."""
    y, q = label.replace(" ", "").upper().split(":Q")
    month = int(q) * 3
    nxt = dt.date(int(y) + (month == 12), month % 12 + 1, 1)
    return nxt - dt.timedelta(days=1)


def parse_levels(text: str) -> dict:
    """{'quarters': [date...], 'generations': [...],
        'levels': {col: {gen: {date: value}}}}"""
    reader = csv.DictReader(io.StringIO(text))
    cols = {_norm(c): c for c in reader.fieldnames or []}
    date_col = cols.get("date")
    cat_col = cols.get("category")
    if not date_col or not cat_col:
        raise ValueError(f"DFA layout changed; columns are {list(cols)}")
    picked = {}
    for key, pred in COLUMNS.items():
        match = [orig for n, orig in cols.items() if pred(n)]
        if not match:
            raise ValueError(f"DFA: no column for {key}; columns are {list(cols)}")
        picked[key] = match[0]
    levels = {k: {} for k in picked}
    gens, quarters = [], set()
    for r in reader:
        q = quarter_end(r[date_col])
        g = r[cat_col].strip()
        if g not in gens:
            gens.append(g)
        quarters.add(q)
        for k, col in picked.items():
            val = r[col].strip()
            if val:
                levels[k].setdefault(g, {})[q] = float(val)
    return {"quarters": sorted(quarters), "generations": gens, "levels": levels,
            "columns_used": picked}


def boomer_label(gens: list[str]) -> str:
    hits = [g for g in gens if "boom" in g.lower()]
    if len(hits) != 1:
        raise ValueError(f"cannot identify Boomer category among {gens}")
    return hits[0]


def load() -> tuple[dict, list[dict]]:
    snap = snapshot.fetch(SOURCE, "dfa.zip", URL)
    return parse_zip(snap), [snap.provenance()]


def parse_zip(snap) -> dict:
    with zipfile.ZipFile(io.BytesIO(snap.content)) as z:
        names = z.namelist()
        match = [n for n in names if n.lower().endswith(LEVELS_FILE)]
        if not match:
            raise ValueError(f"{LEVELS_FILE} not in dfa.zip; contains {names}")
        text = z.read(match[0]).decode("utf-8-sig")
    if snap.stored_path is None:
        snapshot.store_extract(snap, LEVELS_FILE, text)
    return parse_levels(text)
