"""Long-run indicators of what each generation faced at the same age.

Every indicator is an annual series built from published source series
(mostly BEA, BLS, Census and Freddie Mac data, fetched through FRED). For each
generation and a chosen age A, the "at age A" value is the average over the
calendar years in which that generation's birth years turned A (Boomers at 30
= 1976-1994), and the range is the lowest and highest year in that window.
Averaging over the whole window, rather than picking a year, keeps the
comparison from depending on which year one picks.
"""
from __future__ import annotations

import datetime as dt
import math

from ..ledger import Entry

# Pew birth years. Silent starts at 1928 here (Pew's definition) because the
# comparisons need a closed window.
ERA_GENERATIONS = [
    ("Silent", 1928, 1945),
    ("Boomer", 1946, 1964),
    ("Gen X", 1965, 1980),
    ("Millennial", 1981, 1996),
    ("Gen Z", 1997, 2012),
]
AGES = (25, 30, 35, 40)

# FRED series used, with how each is reduced to calendar years.
FRED_SERIES = {
    "MORTGAGE30US": "mean", "FEDFUNDS": "mean", "MSPUS": "mean", "MEFAINUSA646N": "mean",
    "CPIAUCNS": "mean", "OPHNFB": "mean", "COMPRNFB": "mean", "AHETPI": "mean",
    "A4002E1A156NBEA": "mean", "CP": "mean", "GDP": "mean", "FEDMINNFRWG": "mean",
    "B075RC1Q027SBEA": "mean", "A053RC1Q027SBEA": "mean",
}
DEFAULT_AGE = 30
MIN_YEARS = 3  # fewer observed years than this -> no value for that generation


def at_age(series: dict[int, float], age: int) -> dict[str, dict]:
    """{generation: {mean, low, high, window, observed, complete}}"""
    out = {}
    for gen, first, last in ERA_GENERATIONS:
        y0, y1 = first + age, last + age
        vals = [series[y] for y in range(y0, y1 + 1) if y in series]
        if len(vals) < MIN_YEARS:
            continue
        out[gen] = {"mean": sum(vals) / len(vals), "low": min(vals), "high": max(vals),
                    "window": [y0, y1], "observed": len(vals), "complete": len(vals) == y1 - y0 + 1}
    return out


# --------------------------------------------------------------------------- builders

def mortgage_payment_share(price: float, rate_pct: float, income: float,
                           down: float = 0.20, years: int = 30) -> float:
    """Annual principal-and-interest payment on a fixed-rate loan for the
    median home, as a percent of median family income."""
    loan = price * (1 - down)
    r, n = rate_pct / 100 / 12, years * 12
    monthly = loan * r / (1 - (1 + r) ** -n) if r else loan / n
    return 100 * 12 * monthly / income


def _ratio(a: dict[int, float], b: dict[int, float], scale: float = 1.0) -> dict[int, float]:
    return {y: scale * a[y] / b[y] for y in a if y in b and b[y]}


def _real(nominal: dict[int, float], cpi: dict[int, float], base_year: int) -> dict[int, float]:
    return {y: v * cpi[base_year] / cpi[y] for y, v in nominal.items() if y in cpi}


def _rebase(s: dict[int, float], year: int) -> dict[int, float]:
    return {y: 100 * v / s[year] for y, v in s.items()}


def build(a: dict[str, dict[int, float]], tuition: dict[int, float] | None,
          top_rate: dict[int, float] | None) -> list[dict]:
    """a: annual FRED series by id. Returns indicator dicts in page order."""
    cpi = a["CPIAUCNS"]
    base = max(cpi)
    out = []

    def add(**kw):
        s = kw["series"]
        if not s:
            return
        kw["series"] = {int(y): float(v) for y, v in sorted(s.items())}
        out.append(kw)

    # ---- housing
    add(id="hist_price_to_income", topic="housing",
        title="Median home price ÷ median family income",
        short="Home price to income", unit="ratio", fmt="{:.1f}×", worse="higher",
        series=_ratio(a["MSPUS"], a["MEFAINUSA646N"]),
        inputs=["MSPUS", "MEFAINUSA646N"],
        note="Median sales price of new houses sold (Census/HUD) over median family income (Census CPS). "
             "New-house prices run above existing-house prices, so the level is high; the change over time is the point.")
    p2i = _ratio(a["MSPUS"], a["MEFAINUSA646N"])
    add(id="hist_down_payment_months", topic="housing",
        title="A 20% down payment on the median new home, in months of median family income",
        short="Down payment", unit="months", fmt="{:.1f} mo", worse="higher",
        series={y: 12 * 0.20 * r for y, r in p2i.items()}, inputs=["MSPUS", "MEFAINUSA646N"],
        note="20% of the median new-house price over one month of median family income, before taxes and "
             "with nothing spent. The saving hurdle before the first payment; low rates do not shrink it.")
    pay = {}
    for y, rate in a["MORTGAGE30US"].items():
        if y in a["MSPUS"] and y in a["MEFAINUSA646N"]:
            pay[y] = mortgage_payment_share(a["MSPUS"][y], rate, a["MEFAINUSA646N"][y])
    add(id="hist_mortgage_payment_share", topic="housing",
        title="Mortgage payment on the median home, % of median family income",
        short="Mortgage payment share", unit="pct", fmt="{:.0f}%", worse="higher", series=pay,
        inputs=["MSPUS", "MORTGAGE30US", "MEFAINUSA646N"],
        note="Principal and interest on a 30-year fixed loan at that year's average rate (Freddie Mac PMMS), "
             "20% down, for the median new house. Excludes taxes and insurance. Captures both prices and rates: "
             "Boomers bought at high rates in the early 1980s, and this measure shows it.")
    add(id="hist_mortgage_rate", topic="housing", title="30-year fixed mortgage rate",
        short="Mortgage rate", unit="pct", fmt="{:.1f}%", worse="higher", series=a["MORTGAGE30US"],
        inputs=["MORTGAGE30US"], note="Freddie Mac Primary Mortgage Market Survey, annual average.")

    # ---- work and pay
    out_hr = a["OPHNFB"]
    comp = a["COMPRNFB"]
    base_y = 1948
    add(id="hist_productivity_index", topic="work", title="Output per hour worked (1948 = 100)",
        short="Productivity", unit="index", fmt="{:.0f}", worse=None, series=_rebase(out_hr, base_y),
        inputs=["OPHNFB"], note="BLS, nonfarm business sector.")
    add(id="hist_real_comp_index", topic="work", title="Real hourly compensation, all workers (1948 = 100)",
        short="Real pay incl. benefits", unit="index", fmt="{:.0f}", worse="lower", series=_rebase(comp, base_y),
        inputs=["COMPRNFB"],
        note="BLS, nonfarm business sector. Includes benefits and all earners from clerks to CEOs, and uses BLS's "
             "own price deflator. This is the measure on which the pay gap looks smallest.")
    if "AHETPI" in a:
        real_ahe = _real(a["AHETPI"], cpi, base)
        if 1964 in real_ahe and 1964 in comp:
            anchor = 100 * comp[1964] / comp[base_y]
            add(id="hist_real_wage_index", topic="work",
                title="Real hourly wage, production and nonsupervisory workers (1948 = 100 scale)",
                short="Real wage, typical worker", unit="index", fmt="{:.0f}", worse="lower",
                series={y: anchor * v / real_ahe[1964] for y, v in real_ahe.items()},
                inputs=["AHETPI", "CPIAUCNS"],
                note="BLS average hourly earnings of the ~80% of private workers who are not supervisors, deflated by "
                     "CPI-U, joined to the scale above at 1964 (the series starts then). Wages only, no benefits. "
                     "This is the measure on which the pay gap looks largest.")
    add(id="hist_labor_share", topic="work", title="Employee compensation, % of gross domestic income",
        short="Labor's share", unit="pct", fmt="{:.1f}%", worse="lower", series=a["A4002E1A156NBEA"],
        inputs=["A4002E1A156NBEA"], note="BEA. Wages, salaries and benefits paid to employees, as a share of all income earned in the US.")
    add(id="hist_profit_share", topic="work", title="Corporate profits after tax, % of GDP",
        short="Profits' share", unit="pct", fmt="{:.1f}%", worse="higher", series=_ratio(a["CP"], a["GDP"], 100),
        inputs=["CP", "GDP"], note="BEA. Profits after tax, without inventory valuation and capital consumption adjustments.")
    minw = a["FEDMINNFRWG"]
    add(id="hist_real_min_wage", topic="work", title=f"Federal minimum wage in {base} dollars",
        short="Real minimum wage", unit="usd", fmt="${:.2f}", worse="lower", series=_real(minw, cpi, base),
        inputs=["FEDMINNFRWG", "CPIAUCNS"],
        note="US Department of Labor, deflated by CPI-U. Many states and cities set higher minimums; this is the "
             "national floor.")

    # ---- college
    if tuition:
        # Academic year 1990-91 is keyed as 1990 (the fall it starts).
        hrs = {y: t / minw[y] for y, t in tuition.items() if y in minw}
        add(id="hist_tuition_hours_min_wage", topic="college",
            title="Hours at the federal minimum wage to pay a year of public 4-year tuition and fees",
            short="Tuition in minimum-wage hours", unit="hours", fmt="{:,.0f} h", worse="higher", series=hrs,
            inputs=["NCES-330.10", "FEDMINNFRWG"],
            note="In-state tuition and required fees, public 4-year institutions (NCES Digest table 330.10), "
                 "sticker price before grants. Net price after aid is lower and has risen less; see the college page.")
        add(id="hist_tuition_real", topic="college",
            title=f"Public 4-year tuition and fees, {base} dollars",
            short="Real public tuition", unit="usd", fmt="${:,.0f}", worse="higher", series=_real(tuition, cpi, base),
            inputs=["NCES-330.10", "CPIAUCNS"], note="NCES Digest table 330.10, deflated by CPI-U.")

    # ---- taxes
    add(id="hist_corp_effective_tax", topic="taxes",
        title="Federal corporate income tax, % of corporate profits",
        short="Corporate tax take", unit="pct", fmt="{:.0f}%", worse="lower",
        series=_ratio(a["B075RC1Q027SBEA"], a["A053RC1Q027SBEA"], 100),
        inputs=["B075RC1Q027SBEA", "A053RC1Q027SBEA"],
        note="BEA. Federal taxes on corporate income over corporate profits before tax (book profits, not taxable "
             "income). An aggregate effective rate across all corporations, profitable or not.")
    if top_rate:
        add(id="hist_top_income_tax_rate", topic="taxes", title="Top federal income tax bracket rate",
            short="Top bracket rate", unit="pct", fmt="{:.0f}%", worse="lower", series=top_rate,
            inputs=["IRS-SOI-23"],
            note="IRS Statistics of Income, historical table 23. Statutory rate on the highest bracket; few "
                 "people paid it, and effective rates at the top were always lower. See the published estimates below.")
    add(id="hist_fed_funds", topic="housing", title="Federal funds rate",
        short="Fed funds rate", unit="pct", fmt="{:.1f}%", worse=None, series=a["FEDFUNDS"],
        inputs=["FEDFUNDS"], note="Federal Reserve, annual average.")
    return out


def compute(indicators: list[dict], prov: dict[str, dict], today: dt.date) -> tuple[list[Entry], dict]:
    entries, site = [], {"indicators": [], "generations": [g for g, _, _ in ERA_GENERATIONS],
                         "ages": list(AGES), "default_age": DEFAULT_AGE}
    for ind in indicators:
        s = ind["series"]
        last_y = max(s)
        sources = [prov[i] for i in ind["inputs"] if i in prov]
        fmt = ind["fmt"]
        entries.append(Entry(ind["id"], _round(s[last_y]), fmt.format(s[last_y]), "measured", f"{last_y}-12-31",
                             ind["unit"], method=["annual_mean_of_source"], sources=sources,
                             notes=f"latest year {last_y}"))
        by_age = {age: at_age(s, age) for age in AGES}
        for age, gens in by_age.items():
            for gen, v in gens.items():
                entries.append(Entry(f"{ind['id']}@{gen}@{age}", _round(v["mean"]), fmt.format(v["mean"]),
                                     "measured", f"{v['window'][1]}-12-31", ind["unit"],
                                     low=_round(v["low"]), high=_round(v["high"]),
                                     display_range=f"{fmt.format(v['low'])}–{fmt.format(v['high'])}",
                                     method=["mean_over_generation_window"], sources=sources,
                                     notes=f"{gen} at age {age}: years {v['window'][0]}-{v['window'][1]}, "
                                           f"{v['observed']} observed"))
        site["indicators"].append({
            **{k: ind[k] for k in ("id", "topic", "title", "short", "unit", "fmt", "worse", "note", "inputs")},
            "years": list(s), "values": [_round(v) for v in s.values()],
            "latest": {"year": last_y, "value": s[last_y]},
            "at_age": {str(a): g for a, g in by_age.items()},
            "sources": sources,
        })
    return entries, site


def _round(x: float) -> float:
    if x == 0 or not math.isfinite(x):
        return x
    return round(x, 4 - int(math.floor(math.log10(abs(x)))))
