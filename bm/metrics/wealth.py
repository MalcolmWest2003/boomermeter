"""Boomer-headed households' share of wealth, from the Fed DFA."""
from __future__ import annotations

import datetime as dt

from .. import landmarks, stats
from ..ledger import Entry
from ..sources import fed_dfa

METRIC_IDS = {"networth": "wealth_share_networth",
              "equities": "wealth_share_equities",
              "realestate": "wealth_share_realestate"}


def shares(parsed: dict) -> dict[str, dict]:
    """{col: {'boomer': {date: pct}, 'by_generation': {gen: {date: pct}}}}"""
    boom = fed_dfa.boomer_label(parsed["generations"])
    out = {}
    for col, by_gen in parsed["levels"].items():
        per_gen = {g: {} for g in by_gen}
        for q in parsed["quarters"]:
            total = sum(by_gen[g].get(q, 0.0) for g in by_gen)
            if total <= 0:
                continue
            for g in by_gen:
                per_gen[g][q] = 100 * by_gen[g].get(q, 0.0) / total
        out[col] = {"boomer": per_gen[boom], "by_generation": per_gen, "boomer_label": boom}
    return out


# DFA generation labels -> birth years (Pew), for "when the average member was A".
DFA_BIRTH_YEARS = {"Silent": (1928, 1945), "BabyBoom": (1946, 1964), "GenX": (1965, 1980),
                   "Millennial": (1981, 1996)}
# The Fed's own group names: its oldest group is everyone born before 1946 and its
# youngest is everyone born 1981 or later (so it includes Gen Z).
DFA_DISPLAY = {"Silent": "Silent & earlier", "BabyBoom": "Boomer", "GenX": "Gen X",
               "Millennial": "Millennial & younger"}
SAME_AGE = 35
SAME_AGE_HALF_WIDTH = 2  # years either side of the year the average member turned SAME_AGE


def same_age(sh: dict, age: int = SAME_AGE) -> dict[str, dict]:
    """Each generation's own share when its average member (middle birth year)
    was `age`: mean over the quarters within +/-2 years of that point, with the
    min-max as the range. Needs at least 4 quarters of data."""
    out = {}
    # Equities are left out: the DFA's equity holdings for young households are
    # too noisy early on (Boomer holdings quadruple within a year around 1990).
    for col, d in ((c, sh[c]) for c in ("networth", "realestate") if c in sh):
        res = {}
        for label, (b0, b1) in DFA_BIRTH_YEARS.items():
            series = d["by_generation"].get(label, {})
            mid = (b0 + b1) / 2 + age
            vals = [(q, v) for q, v in series.items() if abs(stats.year_frac(q) - mid) <= SAME_AGE_HALF_WIDTH]
            if len(vals) < 4:
                continue
            xs = [v for _, v in vals]
            res[DFA_DISPLAY[label]] = {
                "mean": sum(xs) / len(xs), "low": min(xs), "high": max(xs),
                "centre_year": mid, "from": min(q for q, _ in vals).isoformat(),
                "to": max(q for q, _ in vals).isoformat(), "quarters": len(vals),
                "complete": len(vals) >= 4 * 2 * SAME_AGE_HALF_WIDTH}
        out[col] = res
    return out


def compute(parsed: dict, prov: list[dict], today: dt.date, reg: dict) -> tuple[list[Entry], dict]:
    sh = shares(parsed)
    entries, site = [], {"sources": prov, "series": {}}
    for col, mid in METRIC_IDS.items():
        b = sh[col]["boomer"]
        last_q = max(b)
        val = b[last_q]
        entries.append(Entry(mid, round(val, 1), f"{val:.1f}%", "measured", last_q.isoformat(),
                             "percent", method=["share_from_levels"], sources=prov,
                             notes=f"quarter ending {last_q}"))
        site["series"][col] = {
            "latest_quarter": last_q.isoformat(), "boomer_share": val,
            "boomer": [{"date": q.isoformat(), "value": v} for q, v in sorted(b.items())],
            "by_generation": {g: [{"date": q.isoformat(), "value": v} for q, v in sorted(s.items())]
                              for g, s in sh[col]["by_generation"].items()},
            # dollar levels ($ millions, nominal) by generation, for per-adult comparisons
            "levels": {g: [{"date": q.isoformat(), "value": v} for q, v in sorted(lv.items())]
                       for g, lv in parsed["levels"][col].items()},
            "peak": max(b.items(), key=lambda kv: kv[1]),
        }
        site["series"][col]["peak"] = {"date": site["series"][col]["peak"][0].isoformat(),
                                       "value": site["series"][col]["peak"][1]}

    # Landmark: under half of household net worth.
    b = sh["networth"]["boomer"]
    pts = [(stats.year_frac(q), v) for q, v in sorted(b.items())]
    cfg = reg["landmarks"]["lm_wealth_under_half"]
    lm = landmarks.trend_crossing(pts, cfg["threshold"], "below",
                                  windows=[12, 16, 20, 24, 28], central=20, today=today)
    lm["window_unit"] = "quarters"
    if lm["status"] == "projected":
        lm["band"] = landmarks.band_lines(lm, pts[-1][0],
                                          stats.year_frac(dt.date.fromisoformat(lm["high"])) + 1)
        entries.append(Entry("lm_wealth_under_half", stats.year_frac(dt.date.fromisoformat(lm["central"])),
                             lm["central"][:4], "projected", max(b).isoformat(), "year",
                             low=stats.year_frac(dt.date.fromisoformat(lm["low"])),
                             high=stats.year_frac(dt.date.fromisoformat(lm["high"])),
                             display_range=landmarks.range_label(lm),
                             method=["linear_trend_multiwindow"], sources=prov))
    site["landmark_under_half"] = lm

    sa = same_age(sh)
    site["same_age"] = {"age": SAME_AGE, "half_width": SAME_AGE_HALF_WIDTH, "by_column": sa}
    for col, res in sa.items():
        for gen, v in res.items():
            entries.append(Entry(f"wealth_same_age_{col}@{gen}@{SAME_AGE}", round(v["mean"], 1), f"{v['mean']:.1f}%",
                                 "measured", v["to"], "percent", low=round(v["low"], 1), high=round(v["high"], 1),
                                 display_range=f"{v['low']:.1f}–{v['high']:.1f}%",
                                 method=["share_from_levels", "mean_over_quarters_near_average_age"], sources=prov,
                                 notes=f"{gen} when average member was {SAME_AGE}: {v['from']} to {v['to']}"))
    return entries, site
