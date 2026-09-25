"""How far the handoff has gone, and how it compares with earlier generations.

Built from the other sections' results (wealth, headcount, congress), so it
runs after them and needs no fetch of its own.

- Wealth vs. population: each Fed DFA generation group's share of household
  net worth next to its share of US adults (Census), and mean net worth per
  adult. The ratio (wealth share / adult share) is "how many times its
  population share".
- Transfer bars: the share of the Boomer *peak* share that has passed to other
  generations, 100 * (peak - now) / peak, for household net worth (DFA) and
  seats in Congress. 0% = at the peak, 100% = Boomers hold nothing.
- Comparators: the same measure for earlier generations (a) at the same
  average age and (b) the same number of years after their own peak.
"""
from __future__ import annotations

import datetime as dt

from .. import config, stats
from ..ledger import Entry

DFA_LABELS = {"Silent": "Silent & earlier", "BabyBoom": "Boomer", "GenX": "Gen X",
              "Millennial": "Millennial & younger"}
# Middle birth year used to place a group at an "average age". The DFA's oldest
# group also holds everyone born before 1928; the Silent midpoint is used, which
# overstates that group's wealth at any given age (see METHODS.md).
DFA_MID = {"Silent & earlier": 1936.5, "Boomer": 1955.0, "Gen X": 1972.5, "Millennial & younger": 1988.5}
HIST_MID = {g: (a + b) / 2 for g, a, b in config.HIST_GENERATIONS}
POWER_COMPARE = ["Lost", "Greatest", "Silent"]


def _series(points: list[dict]) -> list[tuple[float, float]]:
    return [(stats.year_frac(dt.date.fromisoformat(p["date"])), p["value"]) for p in points]


def _at(pts: list[tuple[float, float]], x: float, max_gap: float = 6.0) -> float | None:
    """Linear interpolation; None outside the data or across a gap > max_gap years."""
    if not pts or x < pts[0][0] or x > pts[-1][0]:
        return None
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            if x1 - x0 > max_gap:
                return None
            return y0 if x1 == x0 else y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return pts[-1][1] if x == pts[-1][0] else None


def _transferred(peak: float, now: float) -> float:
    return 100 * (peak - now) / peak if peak else 0.0


def wealth_vs_population(wealth: dict, headcount: dict) -> dict:
    nw = wealth["series"]["networth"]
    shares = {DFA_LABELS.get(g, g): dict(_series(pts)) for g, pts in nw["by_generation"].items()}
    levels = {DFA_LABELS.get(g, g): {p["date"]: p["value"] for p in pts}
              for g, pts in nw.get("levels", {}).items()}
    rows = {}
    for year, adults in (headcount.get("adults_by_dfa_group") or {}).items():
        q = f"{year}-06-30"  # DFA Q2 ends the day before the Census July 1 estimate
        qx = stats.year_frac(dt.date.fromisoformat(q))
        total = sum(adults.values())
        row = {}
        for g, n in adults.items():
            ws = shares.get(g, {}).get(qx)
            lv = levels.get(g, {}).get(q)
            if ws is None or not n:
                continue
            a_share = 100 * n / total
            row[g] = {"wealth_share": ws, "adult_share": a_share, "ratio": ws / a_share, "adults": n,
                      "per_adult": (lv * 1e6 / n) if lv is not None else None}
        if len(row) == len(adults):
            rows[year] = row
    latest = max(rows) if rows else None
    return {"by_year": rows, "latest_year": latest}


def wealth_transfer(wealth: dict) -> dict:
    by = {DFA_LABELS.get(g, g): _series(p) for g, p in wealth["series"]["networth"]["by_generation"].items()}
    boom = by["Boomer"]
    px, pv = max(boom, key=lambda t: t[1])
    nx, nv = boom[-1]
    age_now = nx - DFA_MID["Boomer"]
    out = {"peak": pv, "peak_date": stats.from_year_frac(px).isoformat(), "now": nv,
           "now_date": stats.from_year_frac(nx).isoformat(), "transferred": _transferred(pv, nv),
           "avg_age_now": age_now, "years_since_peak": nx - px, "comparators": []}
    old = by.get("Silent & earlier", [])
    if old:
        ox, ov = max(old, key=lambda t: t[1])
        first_obs = old[0][0]
        at_age = _at(old, DFA_MID["Silent & earlier"] + age_now)
        if at_age is not None:
            out["comparators"].append({
                "generation": "Silent & earlier", "basis": "same_age", "value": at_age,
                "when": round(DFA_MID["Silent & earlier"] + age_now, 1),
                "transferred": _transferred(ov, at_age), "peak": ov,
                "peak_is_lower_bound": abs(ox - first_obs) < 0.3})
        after = _at(old, ox + (nx - px))
        if after is not None:
            out["comparators"].append({
                "generation": "Silent & earlier", "basis": "years_after_peak", "value": after,
                "when": round(ox + (nx - px), 1), "transferred": _transferred(ov, after), "peak": ov,
                "peak_is_lower_bound": abs(ox - first_obs) < 0.3})
    out["by_age"] = {g: [(round(x - DFA_MID[g], 2), round(v, 2)) for x, v in pts] for g, pts in by.items()}
    return out


def congress_series(congress: dict) -> dict[str, list[tuple[float, float]]]:
    """Each historical generation's share of seats at each Congress sample, plus today."""
    hist = congress.get("history") or []
    gens = [g for g, _, _ in config.HIST_GENERATIONS]
    out = {g: [] for g in gens}
    for h in hist:
        if "gen_share" not in h:
            continue
        x = stats.year_frac(dt.date.fromisoformat(h["date"]))
        for g in gens:
            out[g].append((x, h["gen_share"].get(g, 0.0)))
    if congress.get("gen_share_today"):
        x = stats.year_frac(dt.date.fromisoformat(congress["as_of"]))
        for g in gens:
            if out[g] and x > out[g][-1][0]:
                out[g].append((x, congress["gen_share_today"].get(g, 0.0)))
    return {g: pts for g, pts in out.items() if pts and max(v for _, v in pts) > 0}


def power_transfer(congress: dict) -> dict:
    ser = congress_series(congress)
    boom = ser["Boomer"]
    px, pv = max(boom, key=lambda t: t[1])
    nx, nv = boom[-1]
    age_now = nx - HIST_MID["Boomer"]
    out = {"peak": pv, "peak_date": stats.from_year_frac(px).isoformat(), "now": nv,
           "now_date": stats.from_year_frac(nx).isoformat(), "transferred": _transferred(pv, nv),
           "avg_age_now": age_now, "years_since_peak": nx - px,
           "peak_age": px - HIST_MID["Boomer"], "comparators": [], "peaks": {}}
    for g in POWER_COMPARE:
        pts = ser.get(g)
        if not pts:
            continue
        gx, gv = max(pts, key=lambda t: t[1])
        out["peaks"][g] = {"share": gv, "date": stats.from_year_frac(gx).isoformat(),
                           "avg_age": gx - HIST_MID[g]}
        for basis, x in (("same_age", HIST_MID[g] + age_now), ("years_after_peak", gx + (nx - px))):
            v = _at(pts, x)
            if v is not None:
                out["comparators"].append({"generation": g, "basis": basis, "value": v, "when": round(x, 1),
                                           "transferred": _transferred(gv, v), "peak": gv,
                                           "peak_is_lower_bound": False})
    out["peaks"]["Boomer"] = {"share": pv, "date": out["peak_date"], "avg_age": out["peak_age"]}
    # From what average age have Boomers held more seats than every earlier
    # generation did at the same age (and kept doing so through today)?
    others = {g: ser[g] for g in POWER_COMPARE if g in ser}
    lead_from = None
    for x, v in reversed([pt for pt in boom if pt[0] >= px]):
        age = x - HIST_MID["Boomer"]
        rivals = [_at(pts, HIST_MID[g] + age) for g, pts in others.items()]
        if any(r is None or r >= v for r in rivals):
            break
        lead_from = age
    out["lead_from_age"] = lead_from
    out["by_year"] = ser
    out["by_age"] = {g: [(round(x - HIST_MID[g], 2), v) for x, v in pts] for g, pts in ser.items()}
    peaks = {g: max(pts, key=lambda t: t[1])[0] for g, pts in ser.items()}
    out["since_peak"] = {g: [(round(x - peaks[g], 2), v) for x, v in pts if x >= peaks[g] - 30]
                         for g, pts in ser.items() if g in POWER_COMPARE + ["Boomer"]}
    return out


def compute(wealth: dict | None, headcount: dict | None, congress: dict | None,
            today: dt.date) -> tuple[list[Entry], dict]:
    entries, site = [], {}
    if wealth:
        wt = wealth_transfer(wealth)
        site["wealth_transfer"] = wt
        src = wealth.get("sources", [])
        entries.append(Entry("handoff_wealth_transferred", round(wt["transferred"], 1), f"{wt['transferred']:.1f}%",
                             "measured", wt["now_date"], "percent", method=["share_of_peak_share_given_up"],
                             sources=src, notes=f"peak {wt['peak']:.1f}% on {wt['peak_date']}, now {wt['now']:.1f}%"))
        for c in wt["comparators"]:
            entries.append(Entry(f"handoff_wealth_transferred@{c['generation']}@{c['basis']}",
                                 round(c["transferred"], 1), f"{c['transferred']:.0f}%", "measured",
                                 stats.from_year_frac(c["when"]).isoformat(), "percent",
                                 method=["share_of_peak_share_given_up", c["basis"]], sources=src,
                                 notes=f"share {c['value']:.1f}% vs peak {c['peak']:.1f}%"
                                       + (" (peak is a lower bound: data start)" if c["peak_is_lower_bound"] else "")))
        if headcount:
            wp = wealth_vs_population(wealth, headcount)
            site["wealth_vs_population"] = wp
            if wp["latest_year"]:
                for g, r in wp["by_year"][wp["latest_year"]].items():
                    entries.append(Entry(f"wealth_share_vs_adult_share@{g}", round(r["ratio"], 2), f"{r['ratio']:.1f}×",
                                         "measured", f"{wp['latest_year']}-07-01", "ratio",
                                         method=["dfa_share_over_census_adult_share"],
                                         sources=src + (headcount.get("sources") or []),
                                         notes=f"{r['wealth_share']:.1f}% of net worth, {r['adult_share']:.1f}% of adults"))
    if congress and congress.get("history") and "gen_share" in congress["history"][0]:
        pt = power_transfer(congress)
        site["power_transfer"] = pt
        src = congress.get("sources", [])
        entries.append(Entry("handoff_power_transferred", round(pt["transferred"], 1), f"{pt['transferred']:.1f}%",
                             "measured", pt["now_date"], "percent", method=["share_of_peak_share_given_up"],
                             sources=src, notes=f"peak {pt['peak']:.1f}% on {pt['peak_date']}, now {pt['now']:.1f}%"))
        for c in pt["comparators"]:
            entries.append(Entry(f"handoff_power_transferred@{c['generation']}@{c['basis']}",
                                 round(c["transferred"], 1), f"{c['transferred']:.0f}%", "measured",
                                 stats.from_year_frac(c["when"]).isoformat(), "percent",
                                 method=["share_of_peak_share_given_up", c["basis"]], sources=src,
                                 notes=f"share {c['value']:.1f}% vs peak {c['peak']:.1f}%"))
    return entries, site
