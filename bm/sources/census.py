"""U.S. Census Bureau population files.

- PEP 'ALLDATA': monthly resident population by single year of age. Each
  vintage covers April 2020 through December of the following year; months
  after the vintage's July 1 are Census's own short-term projections.
- 2023 National Population Projections: single year of age, 2022-2100, in
  middle, low- and high-immigration series.

File names were taken from Census's download pages (Sept 2026). If Census
renames files, the fetch fails loudly with the URL it tried.
"""
from __future__ import annotations

import csv
import io
import urllib.error

from .. import snapshot

SOURCE_PEP = "census-pep"
SOURCE_PROJ = "census-projections"
PEP_DIR = "https://www2.census.gov/programs-surveys/popest/datasets/2020-{v}/national/asrh/"
PROJ_DIR = "https://www2.census.gov/programs-surveys/popproj/datasets/2023/2023-popproj/"
PROJ_SERIES = {"mid": "np2023_d1_mid.csv", "low": "np2023_d1_low.csv", "high": "np2023_d1_hi.csv"}


def _rows(content: bytes):
    text = content.decode("latin-1")
    return csv.DictReader(io.StringIO(text))


def parse_alldata(content: bytes) -> dict[tuple[int, int], dict[int, float]]:
    """{(year, month): {age: population}} for the resident universe."""
    out: dict[tuple[int, int], dict[int, float]] = {}
    reader = _rows(content)
    need = {"MONTH", "YEAR", "AGE", "TOT_POP"}
    cols = {c.strip().upper(): c for c in reader.fieldnames or []}
    if not need <= set(cols):
        raise ValueError(f"ALLDATA layout changed; columns are {list(cols)}")
    for r in reader:
        if "UNIVERSE" in cols and r[cols["UNIVERSE"]].strip() not in ("R", ""):
            continue
        age = int(r[cols["AGE"]])
        if age > 100:  # 999 = all ages
            continue
        key = (int(r[cols["YEAR"]]), int(r[cols["MONTH"]]))
        out.setdefault(key, {})[age] = float(r[cols["TOT_POP"]])
    return out


def fetch_alldata(vintage: int) -> tuple[dict, list[dict]]:
    """All monthly resident files for a vintage, merged. Raises if none exist."""
    merged, prov = {}, []
    for i in range(1, 40):
        fname = f"nc-est{vintage}-alldata-r-file{i:02d}.csv"
        try:
            snap = snapshot.fetch(SOURCE_PEP, fname, PEP_DIR.format(v=vintage) + fname)
        except RuntimeError as e:
            if i == 1:
                raise
            if "404" in str(e) or "Not Found" in str(e):
                break
            raise
        merged.update(parse_alldata(snap.content))
        prov.append(snap.provenance())
    return merged, prov


def latest_alldata(max_vintage: int, min_vintage: int = 2024):
    """Newest vintage that exists, plus the one before it (for the error band)."""
    errors = []
    for v in range(max_vintage, min_vintage - 1, -1):
        try:
            cur, prov = fetch_alldata(v)
        except RuntimeError as e:
            errors.append(str(e))
            continue
        prior = None
        try:
            prior = (v - 1, *fetch_alldata(v - 1))
        except RuntimeError as e:
            errors.append(f"prior vintage unavailable: {e}")
        return {"vintage": v, "monthly": cur, "prov": prov, "prior": prior, "errors": errors}
    raise RuntimeError("no Census ALLDATA vintage found:\n" + "\n".join(errors))


def parse_projection(content: bytes) -> dict[int, dict[int, float]]:
    """{year: {age: population}} for all races, both sexes, all origins."""
    reader = _rows(content)
    cols = {c.strip().upper(): c for c in reader.fieldnames or []}
    if "YEAR" not in cols or "POP_0" not in cols:
        raise ValueError(f"projection layout changed; columns are {list(cols)[:12]}...")
    filters = [c for c in ("NATIVITY", "ORIGIN", "RACE", "SEX") if c in cols]
    out = {}
    for r in reader:
        if any(int(r[cols[c]]) != 0 for c in filters):
            continue
        out[int(r[cols["YEAR"]])] = {a: float(r[cols[f"POP_{a}"]]) for a in range(0, 101)
                                     if f"POP_{a}" in cols}
    if not out:
        raise ValueError("no all-population rows found in projection file")
    return out


def fetch_projections() -> tuple[dict[str, dict], list[dict]]:
    series, prov = {}, []
    for name, fname in PROJ_SERIES.items():
        snap = snapshot.fetch(SOURCE_PROJ, fname, PROJ_DIR + fname)
        series[name] = parse_projection(snap.content)
        if snap.stored_path is None:
            lines = ["YEAR," + ",".join(f"POP_{a}" for a in range(101))]
            for y, ages in sorted(series[name].items()):
                lines.append(f"{y}," + ",".join(str(int(ages.get(a, 0))) for a in range(101)))
            snapshot.store_extract(snap, fname.replace(".csv", "-total-extract.csv"), "\n".join(lines))
        prov.append(snap.provenance())
    return series, prov
