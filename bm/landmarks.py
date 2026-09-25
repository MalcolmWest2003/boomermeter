"""Projected crossing dates for landmarks, with ranges.

Method used for trend-based landmarks: fit a straight line to the most recent
k points for several window sizes k. The central estimate uses one fixed
window (named in the registry); the range is the earliest and latest crossing
among all windows. This makes the range honest about how much the answer
depends on how far back you look, which for these series is the dominant
source of uncertainty.
"""
from __future__ import annotations

import datetime as dt

from . import stats


def trend_crossing(points: list[tuple[float, float]], threshold: float, direction: str,
                   windows: list[int], central: int, today: dt.date,
                   horizon_years: float = 60) -> dict:
    """points: (year_frac, value), ascending. direction: 'below' or 'above'."""
    now = stats.year_frac(today)
    last_x, last_y = points[-1]
    passed = last_y < threshold if direction == "below" else last_y > threshold
    if passed:
        # Find when it was first crossed in the observed data.
        when = None
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            before = y0 >= threshold if direction == "below" else y0 <= threshold
            after = y1 < threshold if direction == "below" else y1 > threshold
            if before and after:
                when = x0 + (x1 - x0) * (threshold - y0) / (y1 - y0) if y1 != y0 else x1
        return {"status": "passed", "central": stats.from_year_frac(when).isoformat() if when else None}

    fits = []
    for k in windows:
        if k > len(points):
            continue
        xs, ys = zip(*points[-k:])
        slope, icpt = stats.ols(list(xs), list(ys))
        moving_toward = slope < 0 if direction == "below" else slope > 0
        x = stats.crossing(slope, icpt, threshold) if moving_toward else None
        if x is not None and (x < last_x or x > now + horizon_years):
            x = None
        fits.append({"window": k, "slope_per_year": slope, "intercept": icpt,
                     "crossing": x})
    crossings = [f["crossing"] for f in fits if f["crossing"] is not None]
    central_fit = next((f for f in fits if f["window"] == central), None)
    if not crossings or central_fit is None or central_fit["crossing"] is None:
        return {"status": "no_trend", "fits": fits,
                "note": "Recent trend does not reach the threshold within the horizon."}
    to_date = lambda x: stats.from_year_frac(x).isoformat()
    return {
        "status": "projected",
        "central": to_date(central_fit["crossing"]),
        "low": to_date(min(crossings)),
        "high": to_date(max(crossings)),
        "fits": fits,
        "windows_without_crossing": [f["window"] for f in fits if f["crossing"] is None],
    }


def range_label(result: dict) -> str:
    """The printed range for a projected landmark. When some trend windows never
    reach the threshold, the range has no upper end and must say so; printing
    the latest finite crossing as the top of the range would overstate how
    settled the date is."""
    lo, hi = result["low"][:4], result["high"][:4]
    missing = result.get("windows_without_crossing") or []
    if missing:
        n = len(result.get("fits") or []) or len(missing)
        return f"{lo} or later; {len(missing)} of {n} trends never get there"
    return f"{lo}–{hi}" if lo != hi else lo


def band_lines(result: dict, x_from: float, x_to: float, steps: int = 40) -> dict:
    """Lower/upper envelope and central line of the fitted trends, for charts."""
    fits = result.get("fits") or []
    if not fits:
        return {}
    xs = [x_from + (x_to - x_from) * i / steps for i in range(steps + 1)]
    lo, hi = [], []
    for x in xs:
        vals = [f["slope_per_year"] * x + f["intercept"] for f in fits]
        lo.append(min(vals))
        hi.append(max(vals))
    return {"x": xs, "low": lo, "high": hi}
