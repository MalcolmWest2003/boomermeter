"""Small numeric helpers. No numpy dependency on purpose: every calculation is
short enough to read in full."""
from __future__ import annotations

import datetime as dt
import math


def median(xs: list[float]) -> float:
    s = sorted(xs)
    if not s:
        raise ValueError("median of empty list")
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Least-squares line. Returns (slope, intercept)."""
    n = len(xs)
    if n < 2:
        raise ValueError("need at least two points")
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, my - slope * mx


def crossing(slope: float, intercept: float, level: float) -> float | None:
    """x where the line reaches `level`; None if it never does going forward."""
    if slope == 0:
        return None
    return (level - intercept) / slope


def sig(x: float, n: int = 3) -> float:
    if x == 0:
        return 0.0
    return round(x, -int(math.floor(math.log10(abs(x)))) + (n - 1))


def fmt_millions(people: float, n: int = 3) -> str:
    """68,412,337 -> '68.4 million'. Never shows a headcount to the individual."""
    m = sig(people, n) / 1e6
    return f"{m:.{max(0, n - len(str(int(m))))}f} million"


def year_frac(d: dt.date) -> float:
    start = dt.date(d.year, 1, 1)
    end = dt.date(d.year + 1, 1, 1)
    return d.year + (d - start).days / (end - start).days


def from_year_frac(y: float) -> dt.date:
    year = int(math.floor(y))
    start = dt.date(year, 1, 1)
    end = dt.date(year + 1, 1, 1)
    return start + dt.timedelta(days=round((y - year) * (end - start).days))


def age_on(birth: dt.date, on: dt.date) -> float:
    return year_frac(on) - year_frac(birth)
