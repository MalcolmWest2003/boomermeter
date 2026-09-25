"""Views for the handoff: transfer bars, wealth vs. population, and generation
lines for wealth and Congress (by year, by average age, by years since peak)."""
from __future__ import annotations

import datetime as dt

from .. import stats
from .svg import esc, line_chart

GEN_VARS = {"Missionary": "--gen-missionary", "Lost": "--gen-lost", "Greatest": "--gen-greatest",
            "Silent": "--gen-silent", "Silent & earlier": "--gen-silent", "Boomer": "--gen-boomer",
            "Gen X": "--gen-x", "Millennial": "--gen-millennial", "Millennial & younger": "--gen-millennial",
            "Gen Z": "--gen-z"}


def _yr(iso: str) -> str:
    return iso[:4]


def _x(r: float) -> str:
    return f"{r:.1f}×" if r >= 1 else f"{r:.2f}×"


def _money(v: float) -> str:
    return f"${v / 1e6:.2f}M" if v >= 1e6 else f"${v / 1e3:,.0f}k"


def _legend(gens) -> str:
    return '<div class="legend">' + "".join(
        f'<span class="lg"><i style="background:var({GEN_VARS[g]})"></i>{esc(g)}</span>' for g in gens) + "</div>"


def transfer_bar(kind: str, t: dict, href: str | None = None) -> str:
    """0% = Boomers at their peak share; 100% = none left. Markers show earlier
    generations at the same average age."""
    what = {"wealth": "of US household net worth", "power": "of the seats in Congress"}[kind]
    title = {"wealth": "Wealth handed off", "power": "Power handed off"}[kind]
    pct = t["transferred"]
    marks, rows = [], []
    same_age = [c for c in t["comparators"] if c["basis"] == "same_age"]
    after_peak = [c for c in t["comparators"] if c["basis"] == "years_after_peak"]
    for i, c in enumerate(sorted(same_age, key=lambda c: c["transferred"])):
        lb = "≥" if c.get("peak_is_lower_bound") else ""
        marks.append(f'<span class="hb-mark row{i % 2}" style="left:{min(c["transferred"], 100):.1f}%" '
                     f'title="{esc(c["generation"])} at the same average age ({c["when"]:.0f}): {lb}{c["transferred"]:.0f}%">'
                     f'<span class="hb-ml">{esc(c["generation"])} {lb}{c["transferred"]:.0f}%</span></span>')
    for c in same_age:
        lb = "at least " if c.get("peak_is_lower_bound") else ""
        rows.append(f'<li><strong>{esc(c["generation"])}</strong>, when its average member was the same age '
                    f'(around {c["when"]:.0f}): {lb}<strong>{c["transferred"]:.0f}%</strong> handed off '
                    f'({c["value"]:.1f}% held, down from {c["peak"]:.1f}%).</li>')
    for c in after_peak:
        lb = "at least " if c.get("peak_is_lower_bound") else ""
        rows.append(f'<li><strong>{esc(c["generation"])}</strong>, the same number of years after its own peak '
                    f'(around {c["when"]:.0f}): {lb}<strong>{c["transferred"]:.0f}%</strong>.</li>')
    link = f' <a href="{href}">Details →</a>' if href else ""
    return f"""
<div class="hbar" id="handoff-{kind}">
  <div class="hb-head"><span class="hb-title">{title}</span><span class="hb-pct">{pct:.1f}%</span></div>
  <div class="hb-track" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{pct:.1f}"
       aria-label="{title}">
    <div class="hb-fill" style="width:{pct:.2f}%"></div>
    {''.join(marks)}
  </div>
  <div class="hb-scale"><span>Boomer peak, {_yr(t['peak_date'])}</span><span>100%: none left</span></div>
  <p class="hb-sub">Boomers held {t['peak']:.1f}% {what} at their peak in {_yr(t['peak_date'])}; they hold
  {t['now']:.1f}% now. Handed off = the share of that peak now held by other generations.{link}</p>
  <details><summary>Against earlier generations</summary><ul>{''.join(rows)}</ul></details>
</div>"""


def handoff_summary(h: dict) -> str:
    """The two bars together, for the home page."""
    parts = []
    if h.get("wealth_transfer"):
        parts.append(transfer_bar("wealth", h["wealth_transfer"], "wealth.html#handoff"))
    if h.get("power_transfer"):
        parts.append(transfer_bar("power", h["power_transfer"], "power.html#handoff"))
    if not parts:
        return ""
    w, p = h.get("wealth_transfer"), h.get("power_transfer")
    lede = ""
    if w and p:
        wc = next((c for c in w["comparators"] if c["basis"] == "same_age"), None)
        pcs = [c for c in p["comparators"] if c["basis"] == "same_age"]
        if wc and pcs:
            lo = min(c["transferred"] for c in pcs)
            lede = (f'<p class="lede">At an average age of {int(w["avg_age_now"])}, Boomers have handed off '
                    f'<strong>{w["transferred"]:.0f}%</strong> of their peak share of the nation’s wealth. The generation '
                    f'before them had handed off at least <strong>{wc["transferred"]:.0f}%</strong> by the same age. '
                    f'In Congress the gap is smaller: {p["transferred"]:.0f}% handed off, against {lo:.0f}% or more '
                    f'for the {len(pcs)} generations before.</p>').replace("for the 3 generations", "for the three generations")
    return (f'<section class="handoff"><h2 class="kicker">The handoff so far</h2>{lede}'
            f'{"".join(parts)}</section>')


def wealth_vs_population(wp: dict) -> str:
    y = wp.get("latest_year")
    if not y:
        return ""
    rows = wp["by_year"][y]
    order = ["Silent & earlier", "Boomer", "Gen X", "Millennial & younger"]
    top = max(max(r["wealth_share"], r["adult_share"]) for r in rows.values()) / 0.72  # room for labels
    bars = []
    for g in order:
        r = rows.get(g)
        if not r:
            continue
        pa = r["per_adult"]
        bars.append(f"""
  <div class="wp-row" style="--c:var({GEN_VARS[g]})">
    <div class="wp-g">{esc(g)}</div>
    <div class="wp-bars">
      <div class="wp-bar adults" style="width:{100 * r['adult_share'] / top:.1f}%"><span>{r['adult_share']:.1f}% of adults</span></div>
      <div class="wp-bar wealth" style="width:{100 * r['wealth_share'] / top:.1f}%"><span>{r['wealth_share']:.1f}% of wealth</span></div>
    </div>
    <div class="wp-x"><strong>{_x(r['ratio'])}</strong><span>its share of adults</span>
    {f'<span class="wp-pa">{_money(pa)} mean per adult</span>' if pa else ''}</div>
  </div>""")
    b, m = rows.get("Boomer"), rows.get("Millennial & younger")
    lede = ""
    if b and m and m["per_adult"]:
        lede = (f'<p class="lede">Boomers are <strong>{b["adult_share"]:.0f}%</strong> of American adults and hold '
                f'<strong>{b["wealth_share"]:.0f}%</strong> of household wealth. Millennials and everyone younger are '
                f'{m["adult_share"]:.0f}% of adults and hold {m["wealth_share"]:.0f}%. Per adult, the average Boomer '
                f'household wealth is <strong>{b["per_adult"] / m["per_adult"]:.0f} times</strong> the average for '
                f'Millennials and younger.</p>')
    return f"""
<section class="block" id="per-person">
  <h2>Share of the people, share of the wealth</h2>
  {lede}
  <div class="wp">{''.join(bars)}</div>
  <p class="caption">Mid-{y}. Wealth: Federal Reserve Distributional Financial Accounts, household net worth by the
  generation of the household head, Q2 {y}. Adults: Census resident population 18 and over by birth year, July 1, {y}.
  The Fed’s groups are “Silent and earlier” (born before 1946) and “Millennial” (1981 or later, so it includes Gen Z);
  population is grouped the same way. “Mean per adult” divides each group’s household wealth by its adults; it is an
  average pulled up by the richest households, not what a typical person has. Adult children who live with Boomer
  parents count toward Boomer wealth but Millennial population, which raises the Boomer figure somewhat.</p>
</section>"""


def _gen_chart(cid: str, by: dict, gens: list[str], *, x_domain, x_ticks, x_fmt, y_max=None, aria="",
               hrefs=(), vrefs=(), width_boomer=2.6) -> str:
    series = [{"name": g, "points": [tuple(p) for p in by[g]], "color": GEN_VARS[g], "tt_fmt": "{:.1f}%",
               "width": width_boomer if g == "Boomer" else 1.8} for g in gens if by.get(g)]
    top = y_max or max(max(v for _, v in s["points"]) for s in series)
    step = 10 if top <= 80 else 20
    y_top = (int(top // step) + 1) * step
    return line_chart(cid, series=series, x_domain=x_domain, y_domain=(0, y_top),
                      x_ticks=x_ticks, y_ticks=list(range(0, y_top + 1, step)), y_fmt="{:.0f}%",
                      x_fmt=x_fmt, hrefs=hrefs, vrefs=vrefs, height=300, aria=aria)


def wealth_generations(w: dict, h: dict) -> str:
    nw = w["series"]["networth"]
    labels = {"Silent": "Silent & earlier", "BabyBoom": "Boomer", "GenX": "Gen X", "Millennial": "Millennial & younger"}
    by_year = {labels.get(g, g): [(stats.year_frac(dt.date.fromisoformat(p["date"])), p["value"]) for p in pts]
               for g, pts in nw["by_generation"].items()}
    gens = [g for g in ["Silent & earlier", "Boomer", "Gen X", "Millennial & younger"] if g in by_year]
    x0, x1 = min(p[0][0] for p in by_year.values()), max(p[-1][0] for p in by_year.values())
    c_year = _gen_chart("c-wealth-gens", by_year, gens, x_domain=(x0, x1 + 0.5),
                        x_ticks=[(y, str(y)) for y in range(1990, int(x1) + 1, 5)],
                        x_fmt=lambda x: f"Q{(stats.from_year_frac(x).month - 1)//3 + 1} {stats.from_year_frac(x).year}",
                        hrefs=[{"at": 50, "label": "half"}], aria="Share of household net worth by generation")
    wt = (h or {}).get("wealth_transfer") or {}
    by_age = {g: [tuple(p) for p in pts] for g, pts in (wt.get("by_age") or {}).items()}
    c_age = ""
    if by_age:
        a0 = min(p[0][0] for p in by_age.values() if p)
        a1 = max(p[-1][0] for p in by_age.values() if p)
        by_age = {g: [pt for pt in pts if pt[0] >= 15] for g, pts in by_age.items()}
        c_age = _gen_chart("c-wealth-age", by_age, gens, x_domain=(15, a1 + 1),
                           x_ticks=[(a, str(a)) for a in range(20, int(a1) + 1, 10)],
                           x_fmt=lambda x: f"average age {x:.1f}", hrefs=[{"at": 50, "label": "half"}],
                           vrefs=[{"at": wt["avg_age_now"], "label": f"Boomers today, {int(wt['avg_age_now'])}"}],
                           aria="Share of household net worth by generation, by average age")
    return f"""
<section class="block" id="generations">
  <h2>Every generation’s share</h2>
  <div class="agepick viewpick" role="group" aria-label="Chart view"><span>Show</span>
  <button type="button" data-view="age" aria-pressed="true">By average age</button>
  <button type="button" data-view="year" aria-pressed="false">By year</button></div>
  {_legend(gens)}
  <div class="v-age">{c_age}<p class="caption">Each line follows one generation’s share of US household net worth
  against the age of its average member (the middle birth year). Read across at any age to compare generations at
  the same point in life; the vertical line is where Boomers are now. The oldest group includes everyone born before
  1946, which makes its line higher than the Silent Generation alone would be.</p></div>
  <div class="v-year">{c_year}<p class="caption">Share of US household net worth by generation of the household
  head, quarterly since 1989. Source: Federal Reserve Board, Distributional Financial Accounts.</p></div>
</section>"""


def congress_generations(p: dict) -> str:
    order = ["Missionary", "Lost", "Greatest", "Silent", "Boomer", "Gen X", "Millennial"]
    by_year = {g: [tuple(x) for x in pts if x[0] >= 1900] for g, pts in p["by_year"].items() if g in order}
    gens = [g for g in order if by_year.get(g)]
    x1 = max(pt[-1][0] for pt in by_year.values() if pt)
    c_year = _gen_chart("c-cong-gens", by_year, gens, x_domain=(1900, x1 + 1),
                        x_ticks=[(y, str(y)) for y in range(1900, int(x1) + 1, 20)],
                        x_fmt=lambda x: str(int(x)), aria="Share of Congress by generation since 1900")
    cmp = ["Lost", "Greatest", "Silent", "Boomer"]
    by_age = {g: [tuple(x) for x in p["by_age"][g]] for g in cmp if g in p["by_age"]}
    c_age = _gen_chart("c-cong-age", by_age, [g for g in cmp if g in by_age], x_domain=(25, 95),
                       x_ticks=[(a, str(a)) for a in range(30, 95, 10)], x_fmt=lambda x: f"average age {x:.0f}",
                       vrefs=[{"at": p["avg_age_now"], "label": f"Boomers today, {int(p['avg_age_now'])}"}],
                       aria="Share of Congress by generation, by average age")
    since = {g: [tuple(x) for x in p["since_peak"][g]] for g in cmp if g in p["since_peak"]}
    c_peak = _gen_chart("c-cong-peak", since, [g for g in cmp if g in since], x_domain=(-30, 45),
                        x_ticks=[(a, f"{a:+d}" if a else "peak") for a in range(-30, 46, 10)],
                        x_fmt=lambda x: f"{x:+.0f} years from peak",
                        vrefs=[{"at": p["years_since_peak"], "label": "Boomers today"}],
                        aria="Share of Congress by generation, years before and after each generation's peak")
    peaks = p["peaks"]
    lead = ""
    if p.get("lead_from_age") is not None:
        lead = (f" Since their average member was {int(p['lead_from_age'])}, Boomers have held a larger share of "
                f"Congress at every age than any earlier generation held at that age.")
    peak_line = "; ".join(f'{g} {v["share"]:.0f}% in {v["date"][:4]} (average age {v["avg_age"]:.0f})'
                          for g, v in peaks.items())
    return f"""
<section class="block" id="generations">
  <h2>Every generation’s share of Congress</h2>
  <p class="lede">Measured from the top, Boomers are giving up seats at about the pace the generations before them
  did. What sets them apart is when the top came: their share peaked at an average age of
  {int(peaks['Boomer']['avg_age'])}, later than any generation before them.{lead}</p>
  <div class="agepick viewpick" role="group" aria-label="Chart view"><span>Show</span>
  <button type="button" data-view="age" aria-pressed="true">By average age</button>
  <button type="button" data-view="peak" aria-pressed="false">From each peak</button>
  <button type="button" data-view="year" aria-pressed="false">By year</button></div>
  <div class="v-age">{_legend([g for g in cmp if g in by_age])}{c_age}</div>
  <div class="v-peak">{_legend([g for g in cmp if g in since])}{c_peak}</div>
  <div class="v-year">{_legend(gens)}{c_year}</div>
  <p class="caption">Share of voting members of Congress (House and Senate) in each generation, measured one year
  into each Congress, plus today. Peaks: {peak_line}. Generations: Pew for Greatest (1901–27) onward; Strauss and Howe
  for Lost (1883–1900) and Missionary (1860–82). “Average age” is the age of the generation’s middle birth year.</p>
</section>"""
