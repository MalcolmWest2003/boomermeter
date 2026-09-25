"""FRED (Federal Reserve Bank of St. Louis) time series.

Uses the public graph CSV endpoint, which needs no API key:
  https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES>
Each series is snapshotted like every other source file. FRED is a
redistributor: the registry names the original publisher (BEA, BLS, Census,
Freddie Mac, the Fed) for every series, and the site cites that publisher.
"""
from __future__ import annotations

import csv
import datetime as dt
import io

from .. import snapshot

SOURCE = "fred"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def parse(content: bytes, sid: str) -> dict[dt.date, float]:
    """{observation date: value}. FRED marks missing values with '.'."""
    reader = csv.reader(io.StringIO(content.decode("utf-8-sig")))
    header = next(reader, None)
    if not header or len(header) < 2 or header[1].strip().upper() != sid.upper():
        raise ValueError(f"FRED {sid}: unexpected header {header}")
    out = {}
    for row in reader:
        if len(row) < 2 or row[1].strip() in ("", "."):
            continue
        out[dt.date.fromisoformat(row[0].strip())] = float(row[1])
    if not out:
        raise ValueError(f"FRED {sid}: no observations")
    return out


def fetch(sid: str) -> tuple[dict[dt.date, float], dict]:
    snap = snapshot.fetch(SOURCE, f"{sid}.csv", URL.format(sid=sid))
    return parse(snap.content, sid), snap.provenance()


def annual(obs: dict[dt.date, float], how: str = "mean") -> dict[int, float]:
    """Calendar-year aggregate. Years with fewer observations than the series'
    usual frequency (a partial current year) are dropped for 'mean'."""
    by_year: dict[int, list[float]] = {}
    for d, v in obs.items():
        by_year.setdefault(d.year, []).append(v)
    if not by_year:
        return {}
    full = max(len(v) for v in by_year.values())
    out = {}
    for y, vals in sorted(by_year.items()):
        if how == "mean":
            if len(vals) < full and y == max(by_year):
                continue
            out[y] = sum(vals) / len(vals)
        elif how == "last":
            out[y] = vals[-1]
        else:
            raise ValueError(how)
    return out
