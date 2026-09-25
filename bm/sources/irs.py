"""IRS Statistics of Income historical table 23: lowest and highest regular
income tax bracket rates since 1913.

The IRS table ends in 2018. Later years carry the 37% top rate set by the Tax
Cuts and Jobs Act (P.L. 115-97, 2017), which P.L. 119-21 (2025) made
permanent; those years are marked as statutory carry-forward, not table data.
"""
from __future__ import annotations

import re

from .. import config, snapshot

SOURCE = "irs-soi"
URL = "https://www.irs.gov/pub/irs-soi/histab23.xls"
STATUTORY_TOP_RATE_SINCE_2018 = 37.0


def _num(c) -> float | None:
    if isinstance(c, (int, float)):
        return float(c)
    s = re.sub(r"\[[^\]]*\]|[,\s]", "", str(c or ""))
    try:
        return float(s)
    except ValueError:
        return None


def parse_top_rate(content: bytes) -> dict[int, float]:
    import xlrd
    sh = xlrd.open_workbook(file_contents=content).sheet_by_index(0)
    hdr = " ".join(str(c) for r in range(min(8, sh.nrows)) for c in sh.row_values(r))
    if "Highest bracket" not in hdr:
        raise ValueError("IRS table 23 layout changed: no 'Highest bracket' header")
    out = {}
    for r in range(sh.nrows):
        row = sh.row_values(r)
        y = _num(row[0]) if row else None
        if y is None or not 1913 <= y <= 2100 or len(row) < 7:
            continue
        v = _num(row[6])
        if v is not None and 0 < v < 100:
            out[int(y)] = v
    if len(out) < 100:
        raise ValueError(f"IRS table 23: only {len(out)} years parsed")
    return out


def fetch() -> tuple[dict[int, float], dict]:
    snap = snapshot.fetch(SOURCE, "histab23.xls", URL)
    rates = parse_top_rate(snap.content)
    last = max(rates)
    if last < 2018 or rates[last] != STATUTORY_TOP_RATE_SINCE_2018:
        raise ValueError(f"IRS table 23 ends {last} at {rates[last]}%; carry-forward assumption needs review")
    for y in range(last + 1, config.today().year + 1):
        rates[y] = STATUTORY_TOP_RATE_SINCE_2018
    prov = snap.provenance()
    prov["note"] = f"table data through {last}; {last + 1}+ statutory 37% (P.L. 115-97, made permanent by P.L. 119-21)"
    return rates, prov
