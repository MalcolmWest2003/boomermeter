"""Synthetic stand-ins for Census and Fed files, written in the same layouts
the real parsers read. Used by tests and by `--demo` layout previews. None of
these numbers are real; demo pages carry a banner saying so."""
from __future__ import annotations

import csv
import datetime as dt
import io
import math

from bm.sources import census as census_src, fed_dfa


def _survival(age: float) -> float:
    a, b = 0.00005, 0.085  # Gompertz hazard
    return math.exp(-(a / b) * (math.exp(b * max(age, 0)) - 1))


def _pop(age: int, when: float, drift: float = 1.0) -> float:
    birth = when - age - 0.5
    births = 4.1e6 if 1946 <= birth < 1965 else 3.2e6 if birth < 1946 else 3.9e6
    return births * _survival(age + 0.5) * drift


def alldata_csv(vintage: int, drift: float = 1.0) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["UNIVERSE", "MONTH", "YEAR", "AGE", "TOT_POP", "TOT_MALE", "TOT_FEMALE"])
    y, m = 2020, 4
    while (y, m) <= (vintage + 1, 12):
        t = y + (m - 1) / 12
        total, rows = 0, []
        for age in range(101):
            p = round(_pop(age, t, drift))
            total += p
            rows.append([age, p])
        rows.append([999, total])
        # Real files code April 2020 as 4.1 (census) and 4.2 (estimates base)
        for mc in ((4.1, 4.2) if (y, m) == (2020, 4) else (m,)):
            for age, p in rows:
                w.writerow(["R", mc, y, age, p, p // 2, p - p // 2])
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return buf.getvalue().encode()


def projection_csv(mult: float) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["NATIVITY", "ORIGIN", "RACE", "SEX", "YEAR", "TOTAL_POP"] + [f"POP_{a}" for a in range(101)])
    for year in range(2022, 2101):
        pops = [round(_pop(a, year + 0.5) * mult ** (year - 2022)) for a in range(101)]
        w.writerow([0, 0, 0, 0, year, sum(pops)] + pops)
        w.writerow([0, 0, 0, 1, year, sum(pops) // 2] + [p // 2 for p in pops])  # a male row, filtered out
    return buf.getvalue().encode()


def census():
    v = 2025
    cur = census_parse(alldata_csv(v))
    prior = census_parse(alldata_csv(v - 1, drift=1.004))
    pep = {"vintage": v, "monthly": cur, "prov": [_prov("nc-est2025-alldata-r-demo.csv")],
           "prior": (v - 1, prior, []), "errors": []}
    proj = {k: census_src.parse_projection(projection_csv(m))
            for k, m in {"mid": 1.0, "low": 0.9995, "high": 1.0005}.items()}
    return pep, proj, [_prov("np2023_d1_demo.csv")]


def census_parse(b: bytes):
    return census_src.parse_alldata(b)


def dfa_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Date", "Category", "Net worth", "Assets", "Real estate",
                "Corporate equities and mutual fund shares", "Liabilities"])
    q = 0
    for year in range(1989, 2027):
        for qq in range(1, 5):
            if (year, qq) < (1989, 3) or (year, qq) > (2026, 2):
                continue
            t = year + (qq - 1) / 4
            boom = 20 + 37 * math.exp(-((t - 2013) / 16) ** 2) - 0.2 * max(0, t - 2013)
            silent = max(2, 55 - 1.6 * (t - 1989))
            genx = max(0.5, min(30, 1.2 * (t - 1995)))
            mill = max(0.1, 0.9 * (t - 2008)) if t > 2008 else 0.1
            tot = boom + silent + genx + mill
            for name, share in (("Silent", silent), ("BabyBoom", boom), ("GenX", genx), ("Millennial", mill)):
                nw = 100_000 * share / tot * (1 + 0.04) ** (t - 1989)
                w.writerow([f"{year}:Q{qq}", name, round(nw), round(nw * 1.15), round(nw * 0.3 * (1.1 if name == "BabyBoom" else 1)),
                            round(nw * 0.25 * (1.15 if name == "BabyBoom" else 1)), round(nw * 0.15)])
            q += 1
    return buf.getvalue()


def dfa():
    return fed_dfa.parse_levels(dfa_csv()), [_prov("dfa-generation-levels-demo.csv")]


def _prov(name):
    return {"source": "synthetic", "filename": name, "url": "about:blank", "sha256": "0" * 64,
            "bytes": 0, "retrieved": dt.date.today().isoformat(), "stored_path": None}


# --- history inputs (shapes only; the demo page is labelled PREVIEW)
def history_inputs():
    yrs = range(1913, 2026)
    def s(fn, start):
        return {y: fn(y) for y in yrs if y >= start}
    cpi = s(lambda y: 10 * 1.032 ** (y - 1913), 1913)
    a = {
        "CPIAUCNS": cpi,
        "MORTGAGE30US": s(lambda y: 7 + 5 * math.exp(-((y - 1981) / 7) ** 2) - 0.07 * max(0, y - 1990), 1971),
        "FEDFUNDS": s(lambda y: max(0.1, 5 + 8 * math.exp(-((y - 1980) / 5) ** 2) - 0.12 * max(0, y - 1990)), 1954),
        "MSPUS": s(lambda y: 18000 * 1.052 ** (y - 1963), 1963),
        "MEFAINUSA646N": s(lambda y: 4200 * 1.046 ** (y - 1953), 1953),
        "OPHNFB": s(lambda y: 20 * 1.021 ** (y - 1947), 1947),
        "COMPRNFB": s(lambda y: 30 * 1.021 ** (y - 1947) if y < 1973 else 30 * 1.021 ** 26 * 1.012 ** (y - 1973), 1947),
        "AHETPI": s(lambda y: 2.5 * cpi[y] / cpi[1964] * (1.02 ** (min(y, 1973) - 1964)), 1964),
        "A4002E1A156NBEA": s(lambda y: 55 - 0.08 * max(0, y - 1970), 1929),
        "CP": s(lambda y: 20 * 1.065 ** (y - 1947), 1947),
        "GDP": s(lambda y: 250 * 1.063 ** (y - 1947), 1947),
        "FEDMINNFRWG": s(lambda y: round(0.25 * 1.045 ** (y - 1938), 2) if y < 2009 else 7.25, 1938),
        "B075RC1Q027SBEA": s(lambda y: 10 * 1.05 ** (y - 1947), 1947),
        "A053RC1Q027SBEA": s(lambda y: 28 * 1.068 ** (y - 1947), 1947),
    }
    tuition = {y: 243 * 1.066 ** (y - 1963) for y in range(1963, 2024) if y not in (1964, 1965, 1966, 1967)}
    top = {y: (91.0 if y < 1964 else 70.0 if y < 1982 else 50.0 if y < 1987 else 39.6 if y < 2018 else 37.0)
           for y in range(1913, 2026)}
    prov = {k: {"source": "demo", "filename": f"{k}.csv", "url": "demo", "sha256": k.ljust(12, "0"),
                "bytes": 0, "retrieved": "demo", "stored_path": None}
            for k in list(a) + ["NCES-330.10", "IRS-SOI-23"]}
    return a, tuition, top, prov


def nces_xlsx() -> bytes:
    """A small workbook in the layout of NCES Digest table 330.10."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Table 330.10. Average undergraduate tuition..."])
    ws.append(["Academic year and control of institution", "Current dollars"])
    ws.append([None, "Total tuition, fees, room, and board", None, None, "Tuition and required fees\\2\\"])
    ws.append([None, "All institutions", "4-year", "2-year", "All institutions", "4-year", "2-year"])
    ws.append(["All institutions"])
    ws.append(["1963-64 ", "$1,248", "$1,286", "$775", "$508", "$553", "$171"])
    ws.append(["Public institutions"])
    for i, y in enumerate(range(1963, 2024)):
        ws.append([f"\n{y}-{(y + 1) % 100:02d}", 900 + i, 930 + i, 630, 234 + i, f"{243 + 10 * i:,}", 97])
    ws.append(["Private institutions"])
    ws.append(["1963-64 ", 2000, 2000, 1000, 1000, 1100, 500])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
