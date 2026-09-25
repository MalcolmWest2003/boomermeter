"""The meter: living Boomers in the US, and the share of the peak now gone.

Cohort convention
-----------------
Census counts people by completed age on July 1. Following Census report
P25-1141 and Pew Research, "Boomers on July 1 of year Y" = everyone aged
Y-1964 through Y-1946. That is a fixed group of people (born roughly
mid-1945 to mid-1964), so year to year it only shrinks by death and net
emigration. The 1999 peak we use as 100% (78.8M, P25-1141) was counted the
same way, so the numerator and denominator match.

For months other than July, the same fixed group straddles one extra age
bin; `cohort_on` weights the two edge bins by the fraction of the year
elapsed since July 1 (assumes birthdays spread evenly within a year of age).

Estimate for today
------------------
1. If Census's monthly file covers the current month, use it (for months
   after the vintage's July 1 those are Census's own short-term projections).
2. After Census's last month, carry the cohort forward at the average
   monthly rate of decline over Census's last 12 months.
Range: how far Census's previous vintage was off, by months ahead, measured
against the newer vintage. The worst miss at today's horizon (or shorter)
sets the +/- band; see band_halfwidth.
"""
from __future__ import annotations

import datetime as dt
import math

from .. import stats
from ..ledger import Entry

PEAK_POPULATION = 78_800_000
PEAK_YEAR = 1999
PEAK_SOURCE = {
    "name": "U.S. Census Bureau, P25-1141, The Baby Boom Cohort in the United States: 2012 to 2060",
    "url": "https://www.census.gov/content/dam/Census/library/publications/2014/demo/p25-1141.pdf",
    "note": "Peak living Boomer population, 78.8 million in 1999 (also cited by Pew Research Center).",
}
FALLBACK_ERROR_PER_MONTH = 0.0005  # 0.05%/month if the prior vintage can't be compared


def cohort_on(ages: dict[int, float], year: int, month: int = 7) -> float:
    """Boomer cohort size from single-year-of-age counts on the 1st of a month."""
    y_ref = year if month >= 7 else year - 1
    f = ((month - 7) % 12) / 12  # fraction of a year since the last July 1
    lo = y_ref - 1964
    total = (1 - f) * ages.get(lo, 0.0)
    total += sum(ages.get(a, 0.0) for a in range(lo + 1, lo + 19))
    total += f * ages.get(lo + 19, 0.0)
    return total


def _monthly_cohort(monthly: dict) -> dict[dt.date, float]:
    return {dt.date(y, m, 1): cohort_on(ages, y, m) for (y, m), ages in sorted(monthly.items())}


def _months_between(a: dt.date, b: dt.date) -> float:
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.4


def prior_vintage_errors(cur: dict[dt.date, float], prior: dict[dt.date, float],
                         prior_anchor: dt.date) -> list[dict]:
    """How far the prior vintage's numbers for months after its last July 1
    were from what the newer vintage now says, by months ahead."""
    rows = []
    for d, old in sorted(prior.items()):
        if d <= prior_anchor or d not in cur:
            continue
        rows.append({"month": d.isoformat(),
                     "months_ahead": round(_months_between(prior_anchor, d), 1),
                     "rel_error": (old - cur[d]) / cur[d]})
    return rows


def band_halfwidth(rows: list[dict], months_ahead: float) -> tuple[float, str]:
    """Relative +/- half-width for an estimate `months_ahead` past Census's
    last July 1: the worst miss the prior vintage made at this horizon or
    shorter. Beyond the longest horizon we can check, the worst miss is
    scaled up in proportion. No comparison available -> 0.05% per month."""
    if not rows:
        return FALLBACK_ERROR_PER_MONTH * max(months_ahead, 1), "fallback 0.05%/month"
    max_h = max(r["months_ahead"] for r in rows)
    within = [abs(r["rel_error"]) for r in rows if r["months_ahead"] <= max(months_ahead, rows[0]["months_ahead"])]
    worst = max(within)
    if months_ahead > max_h:
        worst = max(abs(r["rel_error"]) for r in rows) * months_ahead / max_h
        return worst, f"prior vintage's worst miss, scaled from {max_h:.0f} to {months_ahead:.0f} months ahead"
    return worst, f"prior vintage's worst miss at up to {months_ahead:.0f} months ahead"


def estimate_today(series: dict[dt.date, float], anchor: dt.date, today: dt.date,
                   err_rows: list[dict]) -> dict:
    months = sorted(series)
    first_of_month = today.replace(day=1)
    last = months[-1]
    if first_of_month <= last:
        # interpolate within Census's monthly series to today's day
        base = max(d for d in months if d <= first_of_month)
        nxt = next((d for d in months if d > base), None)
        v = series[base]
        if nxt:
            frac = (today - base).days / (nxt - base).days
            v = series[base] + frac * (series[nxt] - series[base])
        how = "census_monthly_interpolated_to_day"
    else:
        window = [d for d in months if d > last.replace(year=last.year - 1)]
        rate = math.log(series[window[-1]] / series[window[0]]) / _months_between(window[0], window[-1])
        v = series[last] * math.exp(rate * _months_between(last, today))
        how = "extrapolated_past_census_last_month_at_12mo_rate"
    h = max(0.0, _months_between(anchor, today))
    half, basis = band_halfwidth(err_rows, h)
    return {"value": v, "low": v * (1 - half), "high": v * (1 + half),
            "months_past_anchor": h, "how": how, "band_pct": 100 * half, "band_basis": basis}


def project(proj: dict[str, dict], anchor_year: int, anchor_value: float) -> dict[str, dict[int, float]]:
    """Cohort by year in each projection series, scaled to the latest estimate."""
    out = {}
    for name, years in proj.items():
        raw = {y: cohort_on(ages, y) for y, ages in years.items()}
        scale = anchor_value / raw[anchor_year] if anchor_year in raw else 1.0
        out[name] = {y: v * scale for y, v in sorted(raw.items()) if y >= anchor_year}
    return out


def year_reaching(series: dict[int, float], level: float) -> float | None:
    ys = sorted(series)
    for a, b in zip(ys, ys[1:]):
        if series[a] >= level > series[b]:
            return a + (series[a] - level) / (series[a] - series[b]) + 0.5  # July 1 -> mid-year
    return None


def compute(pep: dict, proj: dict | None, proj_prov: list, today: dt.date) -> tuple[list[Entry], dict]:
    v = pep["vintage"]
    anchor = dt.date(v, 7, 1)  # last July 1 that is an estimate, not a projection
    cur = _monthly_cohort(pep["monthly"])
    err_rows = []
    if pep.get("prior"):
        pv, pmonthly, _ = pep["prior"]
        err_rows = prior_vintage_errors(cur, _monthly_cohort(pmonthly), dt.date(pv, 7, 1))
    est = estimate_today(cur, anchor, today, err_rows)
    gone = 100 * (1 - est["value"] / PEAK_POPULATION)
    gone_lo = 100 * (1 - est["high"] / PEAK_POPULATION)
    gone_hi = 100 * (1 - est["low"] / PEAK_POPULATION)

    sources = pep["prov"] + [PEAK_SOURCE]
    entries = [
        Entry("boomer_headcount", round(stats.sig(est["value"], 3)), stats.fmt_millions(est["value"]),
              "interpolated", today.isoformat(), "people",
              low=est["low"], high=est["high"],
              display_range=f"{stats.fmt_millions(est['low'])} – {stats.fmt_millions(est['high'])}",
              method=["boomer_cohort_from_single_year_ages", est["how"], "round_3_sig_figs"],
              sources=pep["prov"], notes=f"Census vintage {v}; ±{est['band_pct']:.2f}% ({est['band_basis']})"),
        Entry("boomer_share_gone", round(gone, 1), f"{gone:.1f}%", "interpolated", today.isoformat(),
              "percent", low=gone_lo, high=gone_hi, display_range=f"{gone_lo:.1f}–{gone_hi:.1f}%",
              method=["one_minus_headcount_over_peak"], sources=sources),
    ]

    site = {
        "as_of": today.isoformat(), "vintage": v, "anchor": anchor.isoformat(),
        "value": est["value"], "low": est["low"], "high": est["high"], "how": est["how"],
        "months_past_anchor": est["months_past_anchor"],
        "gone": gone, "gone_low": gone_lo, "gone_high": gone_hi,
        "peak": PEAK_POPULATION, "peak_year": PEAK_YEAR, "peak_source": PEAK_SOURCE,
        "monthly": [{"date": d.isoformat(), "value": val, "projected_by_census": d > anchor}
                    for d, val in cur.items()],
        "band_pct": est["band_pct"], "band_basis": est["band_basis"], "error_rows": err_rows,
        "sources": sources,
    }

    if proj:
        base_year = v
        projected = project(proj, base_year, cur[anchor])
        half = PEAK_POPULATION / 2
        cross = {k: year_reaching(s, half) for k, s in projected.items()}
        site["projection"] = {k: [{"year": y, "value": val} for y, val in s.items() if y <= 2070]
                              for k, s in projected.items()}
        site["projection_sources"] = proj_prov
        c = [x for x in cross.values() if x is not None]
        if cross.get("mid") and c:
            lm = {"status": "projected",
                  "central": stats.from_year_frac(cross["mid"]).isoformat(),
                  "low": stats.from_year_frac(min(c)).isoformat(),
                  "high": stats.from_year_frac(max(c)).isoformat(),
                  "by_series": cross}
            entries.append(Entry("lm_cohort_half_gone", cross["mid"], lm["central"][:4], "projected",
                                 today.isoformat(), "year", low=min(c), high=max(c),
                                 display_range=f"{lm['low'][:4]}–{lm['high'][:4]}",
                                 method=["census_2023_projection_scaled_to_latest_estimate"],
                                 sources=proj_prov))
        else:
            lm = {"status": "no_trend", "by_series": cross}
        site["landmark_half_gone"] = lm
    return entries, site


def share_gone_at(site: dict, when: dt.date) -> float | None:
    """% of peak gone on a date: from Census monthly figures for past dates,
    from the scaled projection for future ones. None if outside both."""
    x = stats.year_frac(when)
    pts = [(stats.year_frac(dt.date.fromisoformat(m["date"])), m["value"]) for m in site.get("monthly", [])]
    pts += [(p["year"] + 0.5, p["value"]) for p in site.get("projection", {}).get("mid", [])
            if not pts or p["year"] + 0.5 > pts[-1][0]]
    if not pts or x < pts[0][0]:
        return None
    if when <= dt.date.fromisoformat(site["as_of"]) <= when + dt.timedelta(days=31):
        return site["gone"]
    for (x0, v0), (x1, v1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            v = v0 + (v1 - v0) * (x - x0) / (x1 - x0)
            return 100 * (1 - v / site["peak"])
    return None
