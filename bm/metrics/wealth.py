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
                             display_range=f"{lm['low'][:4]}–{lm['high'][:4]}",
                             method=["linear_trend_multiwindow"], sources=prov))
    site["landmark_under_half"] = lm
    return entries, site
