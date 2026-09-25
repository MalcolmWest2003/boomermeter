"""NCES Digest of Education Statistics, table 330.10: average undergraduate
tuition, fees, room and board, by control and level of institution, since
1963-64. Tries the newest Digest edition first."""
from __future__ import annotations

import io
import re

from .. import config, snapshot

SOURCE = "nces"
URL = "https://nces.ed.gov/programs/digest/d{yy}/tables/xls/tabn330.10.xlsx"
YEAR = re.compile(r"^\s*(\d{4})\s*-\s*\d{2}")


def _num(c) -> float | None:
    if c is None:
        return None
    if isinstance(c, (int, float)):
        return float(c)
    s = re.sub(r"\\\d+\\|[$,\s]", "", str(c))
    try:
        return float(s)
    except ValueError:
        return None


def parse_public_4yr_tuition(content: bytes) -> dict[int, float]:
    """{fall year of the academic year: in-state tuition and required fees,
    public 4-year institutions, current dollars}."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    rows = [list(r) for r in wb.worksheets[0].iter_rows(values_only=True)]
    # Column layout: year | total (all, 4yr, 2yr) | tuition and fees (all, 4yr, 2yr) | ...
    head = next((r for r in rows[:8] if any("Tuition and required fees" in str(c or "") for c in r)), None)
    if head is None:
        raise ValueError("NCES 330.10 layout changed: no 'Tuition and required fees' header")
    t_col = next(i for i, c in enumerate(head) if "Tuition and required fees" in str(c or "")) + 1
    out, section = {}, None
    for r in rows:
        first = str(r[0] or "").strip()
        if first.lower().startswith(("public institutions", "private", "all institutions", "nonprofit", "for-profit")):
            section = first.lower()
            continue
        m = YEAR.match(first)
        if m and section and section.startswith("public"):
            v = _num(r[t_col]) if t_col < len(r) else None
            if v:
                out[int(m.group(1))] = v
    if len(out) < 40:
        raise ValueError(f"NCES 330.10: only {len(out)} public 4-year rows parsed (column {t_col})")
    return out


def fetch() -> tuple[dict[int, float], dict]:
    errors = []
    for yy in range(config.today().year - 2000, 22, -1):
        url = URL.format(yy=yy)
        try:
            snap = snapshot.fetch(SOURCE, f"d{yy}-tabn330.10.xlsx", url)
        except RuntimeError as e:
            errors.append(str(e))
            continue
        return parse_public_4yr_tuition(snap.content), snap.provenance()
    raise RuntimeError("no NCES table 330.10 found: " + "; ".join(errors))
