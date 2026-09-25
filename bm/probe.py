"""Print what candidate sources actually return, without storing anything.

Development aid for building parsers from an environment that cannot reach
the data hosts: run it where the network is open (the probe workflow runs it
on GitHub runners) and read the output.

  python -m bm.probe                 # all candidates
  python -m bm.probe MSPUS FEDFUNDS  # just these FRED ids
  python -m bm.probe https://...xlsx  # one spreadsheet, every row
"""
from __future__ import annotations

import io
import sys
import zipfile

from .snapshot import http_get
from .sources import fred

FRED_CANDIDATES = [
    # rates
    "MORTGAGE30US", "FEDFUNDS", "GS10",
    # housing and income
    "MSPUS", "MEFAINUSA646N", "MEHOINUSA646N", "MEHOINUSA672N", "CSUSHPINSA",
    # prices
    "CPIAUCSL", "CPIAUCNS", "CUSR0000SEEB01", "CUUR0000SEEB01",
    # wages, profits, productivity
    "W270RE1A156NBEA", "A4102E1A156NBEA", "CP", "CPATAX", "GDP", "A053RC1Q027SBEA",
    "OPHNFB", "COMPRNFB", "AHETPI", "PRS85006173", "LABSHPUSA156NRUG",
    # taxes
    "FCTAX", "B075RC1Q027SBEA", "A054RC1Q027SBEA",
    # minimum wage
    "FEDMINNFRWG",
    # homeownership
    "RHORUSQ156N",
]

OTHER_CANDIDATES = [
    # NCES Digest table 330.10: average undergraduate tuition, fees, room and board
    "https://nces.ed.gov/programs/digest/d23/tables/xls/tabn330.10.xlsx",
    "https://nces.ed.gov/programs/digest/d24/tables/xls/tabn330.10.xlsx",
    # IRS SOI historical table 23: top and bottom bracket rates since 1913
    "https://www.irs.gov/pub/irs-soi/histab23.xls",
    # Tax Policy Center historical highest marginal rates
    "https://www.taxpolicycenter.org/sites/default/files/historical_highest_marginal_income_tax_rates_2.xlsx",
    # Census HVS: homeownership rate by age of householder
    "https://www.census.gov/housing/hvs/data/histtab19.xlsx",
    "https://www.census.gov/housing/hvs/data/histtabs.xlsx",
]


def show_fred(sid: str) -> None:
    try:
        raw = http_get(fred.URL.format(sid=sid), retries=2, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"== FRED {sid}: FETCH FAILED {e}")
        return
    lines = raw.decode("utf-8-sig", "replace").splitlines()
    print(f"== FRED {sid}: {len(raw)} bytes, {len(lines)} lines")
    for l in lines[:3] + ["..."] + lines[-3:]:
        print("   ", l[:160])
    try:
        obs = fred.parse(raw, sid)
        print(f"    parsed {len(obs)} obs, {min(obs)} .. {max(obs)}")
    except Exception as e:  # noqa: BLE001
        print(f"    PARSE FAILED: {e}")


def show_other(url: str, max_rows: int = 60) -> None:
    try:
        raw = http_get(url, retries=2, timeout=60)
    except Exception as e:  # noqa: BLE001
        print(f"== {url}: FETCH FAILED {e}")
        return
    print(f"== {url}: {len(raw)} bytes, starts {raw[:8]!r}")
    if raw[:2] == b"PK":
        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            for ws in wb.worksheets[:3]:
                print(f"   sheet {ws.title!r}")
                for i, row in enumerate(ws.iter_rows(values_only=True)):
                    if i >= max_rows:
                        break
                    cells = [str(c)[:28] for c in row if c is not None]
                    if cells:
                        print("    ", i, " | ".join(cells)[:220])
        except Exception as e:  # noqa: BLE001
            names = zipfile.ZipFile(io.BytesIO(raw)).namelist()[:10]
            print(f"   not readable as xlsx ({e}); zip entries {names}")
    elif raw[:4] == b"\xd0\xcf\x11\xe0":
        try:
            import xlrd
            book = xlrd.open_workbook(file_contents=raw)
            for sh in book.sheets()[:2]:
                print(f"   sheet {sh.name!r} {sh.nrows}x{sh.ncols}")
                for r in range(min(sh.nrows, max_rows)):
                    cells = [str(c)[:28] for c in sh.row_values(r) if c not in ("", None)]
                    if cells:
                        print("    ", r, " | ".join(cells)[:220])
        except Exception as e:  # noqa: BLE001
            print(f"   legacy .xls, not readable ({e})")
    else:
        print("   ", raw[:600].decode("utf-8", "replace"))


def show_history() -> None:
    """Run the history indicators on live data and print a summary table."""
    import datetime as dt
    import os
    import tempfile
    os.environ.setdefault("BM_DATA_DIR", tempfile.mkdtemp())
    from .metrics import history as h
    from .sources import irs, nces
    annual, prov = {}, {}
    for sid, how in h.FRED_SERIES.items():
        obs, prov[sid] = fred.fetch(sid)
        annual[sid] = fred.annual(obs, how)
    tuition, prov["NCES-330.10"] = nces.fetch()
    top, prov["IRS-SOI-23"] = irs.fetch()
    print("tuition", {y: tuition[y] for y in sorted(tuition)[:3] + sorted(tuition)[-3:]})
    print("top rate", {y: top[y] for y in (1950, 1964, 1981, 1987, 1993, 2013, 2018, max(top))})
    _, site = h.compute(h.build(annual, tuition, top), prov, dt.date.today())
    import json
    print("HISTORY_JSON " + json.dumps(site, separators=(",", ":"), default=str))
    for ind in site["indicators"]:
        f = ind["fmt"]
        ys = dict(zip(ind["years"], ind["values"]))
        sample = ", ".join(f"{y}:{f.format(ys[y])}" for y in (1950, 1965, 1980, 1995, 2010) if y in ys)
        print(f"== {ind['id']}: latest {ind['latest']['year']} {f.format(ind['latest']['value'])} | {sample}")
        for gen, v in ind["at_age"]["30"].items():
            print(f"     at 30 {gen:11s} {f.format(v['mean']):>10s}  range {f.format(v['low'])}-{f.format(v['high'])}"
                  f"  {v['window']} n={v['observed']}")


def main(argv: list[str]) -> None:
    if argv == ["--history"]:
        show_history()
        return
    if argv:
        for a in argv:
            show_other(a, max_rows=10_000) if a.startswith("http") else show_fred(a)
        return
    for sid in FRED_CANDIDATES:
        show_fred(sid)
    for url in OTHER_CANDIDATES:
        show_other(url)


if __name__ == "__main__":
    main(sys.argv[1:])
