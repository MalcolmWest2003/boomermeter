"""Topic pages built from the history indicators (bm/metrics/history.py):
what each generation faced at the same age, with sources and caveats."""
from __future__ import annotations

import json

from .svg import esc, line_chart

GEN_VARS = {"Silent": "--gen-silent", "Boomer": "--gen-boomer", "Gen X": "--gen-x",
            "Millennial": "--gen-millennial", "Gen Z": "--gen-z"}
GEN_SHORT = {"Silent": "Silent", "Boomer": "Boomers", "Gen X": "Gen X", "Millennial": "Millennials",
             "Gen Z": "Gen Z"}
GEN_PLURAL = {"Silent": "the Silent Generation", "Boomer": "Boomers", "Gen X": "Gen X",
              "Millennial": "Millennials", "Gen Z": "Gen Z"}

# Page structure. Each chart lists indicator ids drawn together; "compare" is
# the indicator whose generation-at-age values are shown under the chart.
TOPICS = {
    "housing": {
        "title": "Housing",
        "lede": "What a first home cost, measured against what a family earned, at the age people usually buy one.",
        "charts": [
            {"ids": ["hist_price_to_income"], "compare": "hist_price_to_income",
             "head": "Home prices against family income"},
            {"ids": ["hist_rent_vs_wage"], "compare": "hist_rent_vs_wage",
             "head": "Rent against pay",
             "text": "Before anyone buys, they rent. This follows rent and the typical worker's hourly pay from the "
                     "same starting point in 1964."},
            {"ids": ["hist_down_payment_months"], "compare": "hist_down_payment_months",
             "head": "Saving for the down payment",
             "text": "The price hurdle shows up first as the down payment: money that has to be saved before the "
                     "first mortgage payment, and that low interest rates do nothing to shrink."},
            {"ids": ["hist_mortgage_payment_share"], "compare": "hist_mortgage_payment_share",
             "head": "The monthly payment, prices and rates together",
             "text": "Here the comparison turns. Mortgage rates reached 18% in 1981, so the monthly payment on the "
                     "median home took a larger share of family income when Boomers were 30 than it has for "
                     "Millennials, even though prices are higher now. Boomers’ housing burden was the payment; "
                     "Millennials’ is the price and the down payment. Rates rose again from 2022, and the share has "
                     "climbed since."},
            {"ids": ["hist_mortgage_rate", "hist_fed_funds"], "compare": "hist_mortgage_rate",
             "head": "Interest rates",
             "text": "High rates hurt buyers and helped savers; the four-decade fall in rates after 1981 raised the "
                     "price of every house, stock and bond that was already owned. People who bought before the fall "
                     "were paid by it."},
        ],
    },
    "work": {
        "title": "Work and pay",
        "lede": "How the income the economy produces has been split between the people who work and the people who own.",
        "charts": [
            {"ids": ["hist_productivity_index", "hist_real_comp_index", "hist_real_wage_index"], "compare": None,
             "head": "Productivity and pay",
             "text": "Economists disagree about how big the gap between productivity and pay is, and the disagreement is "
                     "mostly about measurement: whether to count benefits, whether to include executives, and which "
                     "price index to use. The two pay lines are the two ends of that argument. The gap exists on both."},
            {"ids": ["hist_labor_share"], "compare": "hist_labor_share", "head": "Labor's share of income"},
            {"ids": ["hist_profit_share"], "compare": "hist_profit_share", "head": "Corporate profits' share"},
            {"ids": ["hist_real_min_wage"], "compare": "hist_real_min_wage", "head": "The minimum wage"},
            {"ids": ["hist_teen_unemployment"], "compare": "hist_teen_unemployment", "head": "A first job"},
            {"ids": ["hist_teen_participation"], "compare": "hist_teen_participation",
             "head": "How many teens work"},
        ],
    },
    "college": {
        "title": "College",
        "lede": "The price of a public four-year college, counted in hours of minimum-wage work.",
        "charts": [
            {"ids": ["hist_tuition_hours_min_wage"], "compare": "hist_tuition_hours_min_wage",
             "head": "A year of tuition, in minimum-wage hours",
             "text": "This is the sticker price. Grants and tuition discounts mean the average student pays less, and "
                     "the gap between sticker and net price has grown. The College Board’s Trends in College Pricing "
                     "tracks net price, but not back to the 1960s, so the long comparison has to use sticker price."},
            {"ids": ["hist_tuition_real"], "compare": "hist_tuition_real", "head": "Tuition in today’s dollars"},
        ],
    },
    "taxes": {
        "title": "Taxes at the top",
        "lede": "What the highest earners and the largest companies are asked to pay, and what they actually pay.",
        "charts": [
            {"ids": ["hist_top_income_tax_rate"], "compare": "hist_top_income_tax_rate",
             "head": "The top income tax bracket",
             "text": "The statutory top rate was above 90% through the 1950s, but almost no one paid it: the bracket "
                     "started at incomes equal to several million of today’s dollars, and deductions and shelters "
                     "were widespread. What people at the top actually pay is the harder question, below."},
            {"ids": ["hist_corp_effective_tax"], "compare": "hist_corp_effective_tax",
             "head": "What corporations pay on their profits"},
        ],
    },
}
ORDER = ["housing", "work", "college", "taxes"]

# What each number is, in plain words. Shown above every chart.
MEANING = {
    "hist_price_to_income": "How many years of a typical family's entire income it takes to equal the price of a "
                            "typical new house. Higher means harder to buy.",
    "hist_down_payment_months": "How many months of a typical family's pay you would need to save for a 20% down "
                                "payment, if you spent nothing on rent, food or anything else.",
    "hist_mortgage_payment_share": "How much of a typical family's income the monthly mortgage payment would take, "
                                   "buying the typical new house with 20% down.",
    "hist_mortgage_rate": "The interest rate on a typical 30-year home loan.",
    "hist_productivity_index": "How much more a worker produces in an hour than in 1948, next to how much more "
                               "workers are paid. If pay kept up with output, the lines would move together.",
    "hist_labor_share": "Out of every dollar the economy earns, how many cents go to workers as pay and benefits. "
                        "The rest goes to owners: profits, rent and interest.",
    "hist_profit_share": "Corporate profits after tax, as a slice of everything the economy produces.",
    "hist_real_min_wage": "The federal minimum wage, converted to today's dollars so different years can be compared.",
    "hist_tuition_hours_min_wage": "How many hours at the federal minimum wage it takes to pay one year of in-state "
                                   "tuition at a public university. A full-time job is about 2,000 hours a year.",
    "hist_tuition_real": "One year of in-state tuition and fees at a public university, in today's dollars.",
    "hist_rent_vs_wage": "How much rent has grown compared with an ordinary worker's hourly pay, both starting at "
                         "100 in 1964. At 150, rent has grown half again as fast as pay.",
    "hist_teen_unemployment": "Out of every 100 teenagers (16 to 19) who are looking for work, how many can't find "
                              "a job.",
    "hist_teen_participation": "Out of every 100 people aged 16 to 19, how many have a job or are looking for one.",
    "hist_top_income_tax_rate": "The federal income tax rate on the highest slice of the highest incomes.",
    "hist_corp_effective_tax": "Out of every dollar of corporate profit, how many cents go to the federal government "
                               "as corporate income tax.",
}
GEN_NOUN = {"Silent": "the Silent Generation", "Boomer": "Boomers", "Gen X": "Gen X", "Millennial": "Millennials",
            "Gen Z": "Gen Z"}


def _compare_words(ind: dict, v: float, ref: float) -> str:
    """'about 30% more', '2.4 times as much', '6 points lower', 'about the same'."""
    if ind["unit"] == "pct":
        d = v - ref
        if abs(d) < 0.5:
            return "about the same as"
        return f"{abs(d):.0f} percentage points {'higher' if d > 0 else 'lower'} than"
    r = v / ref if ref else 1
    if r >= 1.95:
        return f"{r:.1f} times"
    if r > 1.05:
        return f"about {round((r - 1) * 100)}% higher than"
    if r < 0.95:
        return f"about {round((1 - r) * 100)}% lower than"
    return "about the same as"


def conclusion(ind: dict, age: int) -> str:
    """A plain sentence comparing the youngest generation with data to Boomers at the same age."""
    gens = ind["at_age"].get(str(age), {})
    boom = gens.get("Boomer")
    young = next((g for g in ("Gen Z", "Millennial", "Gen X") if g in gens), None)
    if not boom or not young:
        return ""
    f, v = ind["fmt"], gens[young]
    words = _compare_words(ind, v["mean"], boom["mean"])
    so_far = " so far" if not v["complete"] else ""
    same = words.startswith("about the same")
    tail = "" if same else f" what Boomers faced ({f.format(boom['mean'])})"
    head = f"At {age}, {GEN_NOUN[young]}{so_far} have faced {f.format(v['mean'])}: "
    if same:
        body = f"about the same as Boomers at {age} ({f.format(boom['mean'])})."
    elif words.endswith("times"):
        body = f"{words}{tail}."
    else:
        body = f"{words}{tail}."
    extra = ""
    if young == "Gen Z" and "Millennial" in gens:
        extra = f" Millennials at {age}: {f.format(gens['Millennial']['mean'])}."
    return f'<p class="concl">{head}{body}{extra}</p>'



def _ind_map(hist: dict) -> dict:
    return {i["id"]: i for i in hist.get("indicators", [])}


GEN_MID = {"Silent": 1936.5, "Boomer": 1955.0, "Gen X": 1972.5, "Millennial": 1988.5, "Gen Z": 2004.5}


def view_picker() -> str:
    return ('<div class="agepick viewpick" role="group" aria-label="Chart view"><span>Show</span>'
            '<button type="button" data-view="age" aria-pressed="true">By age</button>'
            '<button type="button" data-view="year" aria-pressed="false">By year</button></div>')


def by_age_chart(ind: dict, ages: list[int], cid: str, y_ticks: list[float], tick_fmt: str) -> tuple[str, list[str]]:
    """One line per generation: the indicator in the year that generation's
    middle birth year reached each age. Makes the same-age comparison visual."""
    vals = dict(zip(ind["years"], ind["values"]))
    series = []
    for gen, mid in GEN_MID.items():
        pts = [(y - mid, v) for y, v in vals.items() if 0 <= y - mid <= 70]
        if len(pts) >= 3:
            series.append({"name": GEN_SHORT[gen], "points": pts, "color": GEN_VARS[gen], "tt_fmt": ind["fmt"],
                           "width": 2.4 if gen == "Boomer" else 1.8})
    if not series:
        return "", []
    a0 = min(p[0][0] for p in (s["points"] for s in series))
    a1 = max(p[-1][0] for p in (s["points"] for s in series))
    a0, a1 = max(0, int(a0) // 5 * 5), min(70, int(a1) // 5 * 5 + 5)
    marks = [{"x0": a - 0.3, "x1": a + 0.3, "color": "--ink-3", "label": f"age {a}", "age": a, "strong": True} for a in ages]
    svg = line_chart(cid, series=series, x_domain=(a0, a1), y_domain=(0, y_ticks[-1]),
                     x_ticks=[(a, "birth" if a == 0 else str(a)) for a in range((a0 + 9) // 10 * 10, a1 + 1, 10)],
                     y_ticks=y_ticks, y_fmt=tick_fmt, x_fmt=lambda x: f"average age {x:.0f}", windows=marks,
                     height=280, aria=f"{ind['title']}, by the age of each generation's average member")
    names = {v: k for k, v in GEN_SHORT.items()}
    return svg, [names[s["name"]] for s in series]


def gen_legend(gens: list[str]) -> str:
    return '<div class="legend">' + "".join(
        f'<span class="lg"><i style="background:var({GEN_VARS[g]})"></i>{esc(GEN_SHORT[g])}</span>' for g in gens) + "</div>"


def age_picker(ages: list[int], default: int) -> str:
    btns = "".join(f'<button type="button" data-age="{a}" aria-pressed="{str(a == default).lower()}">{a}</button>'
                   for a in ages)
    return (f'<div class="agepick" role="group" aria-label="Compare generations at age">'
            f'<span>Compare generations at age</span>{btns}</div>')


def _delta(ind: dict, v: float, ref: float) -> str:
    """Change relative to Boomers at the same age, in the indicator's own terms."""
    if ind["unit"] == "pct":
        d = v - ref
        return f"{d:+.1f} pts vs Boomers" if abs(d) >= 0.05 else "same as Boomers"
    if ref:
        r = v / ref
        return f"{r:.2f}× Boomers" if abs(r - 1) >= 0.005 else "same as Boomers"
    return ""


def compare_cards(ind: dict, ages: list[int]) -> str:
    f = ind["fmt"]
    this_year = ind["latest"]["year"] + 1
    blocks = []
    for age in ages:
        gens = ind["at_age"].get(str(age), {})
        if not gens:
            blocks.append(f'<div class="cmp" data-age="{age}"><p class="caption">No generation has at least three '
                          f'observed years at age {age} in this series.</p></div>')
            continue
        ref = gens.get("Boomer", {}).get("mean")
        cards = []
        for gen, v in gens.items():
            y0, y1 = v["window"]
            span = y1 - y0 + 1
            cov = ("" if v["complete"] else
                   f' <span class="sofar">so far: {v["observed"]} of {span} years</span>' if y1 >= this_year else
                   f' <span class="sofar">data for {v["observed"]} of {span} years</span>')
            delta = "" if gen == "Boomer" or ref is None else f'<div class="cmp-d">{esc(_delta(ind, v["mean"], ref))}</div>'
            cards.append(
                f'<div class="cmp-card" style="--c:var({GEN_VARS[gen]})">'
                f'<div class="cmp-g">{esc(gen)}</div>'
                f'<div class="cmp-v">{esc(f.format(v["mean"]))}</div>'
                f'<div class="cmp-w">{y0}–{y1}{cov}</div>'
                f'<div class="cmp-r">range {esc(f.format(v["low"]))} – {esc(f.format(v["high"]))}</div>{delta}</div>')
        you = (f'<div class="cmp-card you" style="--c:var(--ink)" data-ind="{esc(ind["id"])}" data-age="{age}" hidden>'
               f'</div>')
        blocks.append(f'<div class="cmp" data-age="{age}">{conclusion(ind, age)}'
                      f'<div class="cmp-row">{"".join(cards)}{you}</div></div>')
    return "".join(blocks)


def _windows(ind: dict, ages: list[int]) -> list[dict]:
    out = []
    for age in ages:
        for gen, v in ind["at_age"].get(str(age), {}).items():
            out.append({"x0": v["window"][0], "x1": v["window"][1] + 1, "color": GEN_VARS[gen],
                        "label": GEN_SHORT[gen], "age": age})
    return out


def _nice_ticks(hi: float) -> list[float]:
    for step in (0.5, 1, 2, 2.5, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000):
        if hi / step <= 6:
            return [i * step for i in range(int(hi // step) + 2)]
    return [0, hi]


SERIES_COLORS = ["--ink", "--series-age", "--accent", "--ink-3"]


def chart_block(spec: dict, inds: dict, ages: list[int], cid: str) -> str:
    present = [inds[i] for i in spec["ids"] if i in inds]
    if not present:
        return ""
    first = present[0]
    x0 = min(i["years"][0] for i in present)
    x1 = max(i["years"][-1] for i in present) + 1
    ymax = max(max(i["values"]) for i in present)
    y_ticks = _nice_ticks(ymax * 1.05)
    y_ticks = [t for t in y_ticks if t <= y_ticks[-1]]
    fmt = first["fmt"]
    tick_fmt = fmt.replace(".1f", ".0f").replace(".2f", ".0f").replace(",.0f", ",.0f")
    series = [{"name": i["short"], "points": [(y + 0.5, v) for y, v in zip(i["years"], i["values"])],
               "color": SERIES_COLORS[k % len(SERIES_COLORS)], "tt_fmt": i["fmt"],
               "width": 2.2 if k == 0 else 1.8, "dash": k == 2}
              for k, i in enumerate(present)]
    compare = inds.get(spec.get("compare") or "")
    svg = line_chart(cid, series=series, x_domain=(x0, x1), y_domain=(0, y_ticks[-1]),
                     x_ticks=[(y, str(y)) for y in range((x0 // 10 + 1) * 10, x1 + 1, 10)],
                     y_ticks=y_ticks, y_fmt=tick_fmt, x_fmt=lambda x: str(int(x)),
                     windows=_windows(compare, ages) if compare else (), height=280, aria=first["title"])
    age_view, gens = by_age_chart(compare, ages, cid + "-age", y_ticks, tick_fmt) if compare else ("", [])
    if age_view:
        svg = (f'<div class="v-age">{gen_legend(gens)}{age_view}<p class="caption">Each line follows one generation: '
               f'the value in the year its average member (middle birth year) reached each age. The marked age is '
               f'the one the cards below compare.</p></div><div class="v-year">{svg}</div>')
    legend = ""
    if len(present) > 1:
        legend = '<div class="legend">' + "".join(
            f'<span class="lg"><i style="background:var({s["color"]})"></i>{esc(i["title"])}</span>'
            for s, i in zip(series, present)) + "</div>"
    notes = "".join(f"<li>{esc(i['note'])}</li>" for i in present)
    srcs = "; ".join(sorted({f'<a href="{esc(s["url"])}">{esc(s["filename"])}</a>'
                             for i in present for s in i.get("sources", []) if s.get("url", "").startswith("http")}))
    latest = f'Latest: <strong>{esc(fmt.format(first["latest"]["value"]))}</strong> ({first["latest"]["year"]}).'
    blob = ""
    if compare:
        data = {"years": compare["years"], "values": compare["values"], "fmt": compare["fmt"]}
        blob = (f'<script type="application/json" class="ind-data" data-id="{esc(compare["id"])}">'
                f'{json.dumps(data, separators=(",", ":"))}</script>')
    return f"""
<section class="chart-block">{blob}
  <h3>{esc(spec["head"])}</h3>
  <p class="chart-title">{esc(first["title"])}. {latest}</p>
  {f'<p class="meaning">{esc(MEANING[first["id"]])}</p>' if first["id"] in MEANING else ""}
  {f'<p>{esc(spec["text"])}</p>' if spec.get("text") else ""}
  {legend}{svg}
  {compare_cards(compare, ages) if compare else ""}
  <details><summary>What this measures, and its limits</summary><ul>{notes}</ul>
  <p class="caption">Source files: {srcs or "see the sources page"}.</p></details>
</section>"""


def topic_page(key: str, hist: dict, extra: str = "") -> str:
    t = TOPICS[key]
    inds = _ind_map(hist)
    ages, default = hist.get("ages", [30]), hist.get("default_age", 30)
    blocks = "".join(chart_block(c, inds, ages, f"c-{key}-{n}") for n, c in enumerate(t["charts"]))
    return f"""
<section class="page-head">
  <p class="kicker"><a href="index.html">Boomermeter</a> / {esc(t["title"])}</p>
  <h1>{esc(t["title"])}</h1>
  <p class="hero-lede">{esc(t["lede"])}</p>
  <div class="you-in"><label>Your birth year <input id="birth-year" type="number" inputmode="numeric"
  min="1928" max="2026" placeholder="e.g. 2001"></label><span class="caption">We’ll show what you faced at each age,
  what things looked like the year you were born, and where they are now. Nothing leaves your browser.</span></div>
  {view_picker()}
  {age_picker(ages, default)}
  <p class="caption">Shaded spans mark the years each generation was turning that age (Boomers, born 1946–64, turned 30
  in 1976–94). Each card is the average over those years; its range is the lowest and highest year. Generations still
  inside their window show how many years are in so far.</p>
</section>
{blocks}
{extra}"""


def headline(key: str, hist: dict) -> str:
    """One-line summary for the index page's explore grid."""
    inds = _ind_map(hist)
    t = TOPICS[key]
    ind = next((inds[c["compare"]] for c in t["charts"] if c.get("compare") in inds), None)
    if not ind:
        return ""
    f = ind["fmt"]
    g = ind["at_age"].get("30", {})
    parts = [f'{esc(ind["short"])}: <strong>{esc(f.format(ind["latest"]["value"]))}</strong> now']
    if "Boomer" in g:
        parts.append(f'{esc(f.format(g["Boomer"]["mean"]))} when Boomers were 30')
    return " · ".join(parts)


def literature_table(lit: list[dict]) -> str:
    rows = []
    for e in lit:
        rng = f'<br><span class="caption">{esc(e["range"])}</span>' if e.get("range") else ""
        note = f'<br><span class="caption">{esc(e["note"])}</span>' if e.get("note") else ""
        rows.append(
            f'<tr><td><strong>{esc(e["value"])}</strong>{rng}</td>'
            f'<td>{esc(e["group"])}<br><span class="caption">{esc(e["period"])}</span></td>'
            f'<td>{esc(e["measure"])}</td>'
            f'<td><a href="{esc(e["url"])}">{esc(e["source"])}</a>{note}</td></tr>')
    return f"""
<section class="chart-block" id="published">
  <h3>What the richest actually pay: published estimates</h3>
  <p>No official statistic answers this, so we don’t compute our own; we report the main published estimates and what
  each one measures. They differ because they answer different questions: which taxes count (income tax only, or
  corporate and estate taxes too), and what counts as income (taxable income, or gains on assets not yet sold).
  The spread between them is the real state of knowledge, and the two studies of the same group and years, 24% and 38%,
  bracket the serious disagreement.</p>
  <div class="scroll"><table class="lit"><thead><tr><th>Estimate</th><th>Who, when</th><th>What it measures</th>
  <th>Source</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
</section>"""
