"""Builds the static site from the pipeline's state. No JS framework: one HTML
page plus a methods page, inline SVG charts, a small hover script."""
from __future__ import annotations

import datetime as dt
import json
import shutil
from pathlib import Path

import markdown

from .. import config, stats
from ..metrics import headcount as hc
from .svg import esc, line_chart, stacked_bar

REPO_URL = "https://github.com/MalcolmWest2003/boomermeter"

GEN_COLORS = [("Silent & earlier", "--gen-silent"), ("Boomer", "--gen-boomer"),
              ("Gen X", "--gen-x"), ("Millennial", "--gen-millennial"), ("Gen Z", "--gen-z")]


def d(s: str) -> dt.date:
    return dt.date.fromisoformat(s[:10])


def nice_date(s: str) -> str:
    x = d(s)
    return f"{x:%b} {x.day}, {x.year}"


def yf(s: str) -> float:
    return stats.year_frac(d(s))


def est_tag(status: str) -> str:
    if status == "measured":
        return ""
    return f'<span class="tag tag-{status}">{"est." if status == "interpolated" else "projection"}</span>'


def stale_note(sec: dict) -> str:
    if not sec.get("stale"):
        return ""
    return (f'<p class="stale">This section could not refresh on the latest run and shows data '
            f'from {nice_date(sec["last_success"])}.</p>')


# --------------------------------------------------------------------------- meter

def landmark_list(state: dict) -> list[dict]:
    out = []
    hcs = state.get("headcount", {}).get("data")
    reg = state["registry"]["landmarks"]
    sources = {
        "lm_wealth_under_half": (state.get("wealth", {}).get("data") or {}).get("landmark_under_half"),
        "lm_congress_under_third": (state.get("congress", {}).get("data") or {}).get("landmark_under_third"),
        "lm_cohort_half_gone": (hcs or {}).get("landmark_half_gone"),
    }
    anchors = {"lm_wealth_under_half": "wealth", "lm_congress_under_third": "congress",
               "lm_cohort_half_gone": "cohort"}
    for lid, lm in sources.items():
        if not lm:
            continue
        cfg = reg[lid]
        item = {"id": lid, "name": cfg["display_name"], "anchor": anchors[lid],
                "status": lm["status"], "caveat": cfg["caveat_line"], "method": cfg["method"]}
        if lm["status"] == "projected":
            item.update(central=lm["central"], low=lm["low"], high=lm["high"])
            if hcs:
                item["pos"] = 50.0 if lid == "lm_cohort_half_gone" else hc.share_gone_at(hcs, d(lm["central"]))
        elif lm["status"] == "passed":
            item["central"] = lm.get("central")
            if hcs and item["central"]:
                item["pos"] = hc.share_gone_at(hcs, d(item["central"]))
        out.append(item)
    out.sort(key=lambda i: i.get("central") or "9999")
    return out


def meter(state: dict, lms: list[dict]) -> str:
    sec = state.get("headcount", {})
    h = sec.get("data")
    if not h:
        return ('<section class="meter pending"><p>The headcount meter is waiting on its first '
                'successful Census data run.</p></section>')
    gone = h["gone"]
    ticks, last_p = [], -100.0
    for y in range(2030, 2081, 10):
        p = hc.share_gone_at(h, dt.date(y, 7, 1))
        if p is None or p > 94 or p - last_p < 7 or p < gone + 3:
            continue
        ticks.append(f'<span class="ytick" style="left:{p:.2f}%">{y}</span>')
        last_p = p
    marks, row_last = [], [-100.0, -100.0]
    for lm in sorted((l for l in lms if l.get("pos") is not None), key=lambda l: l["pos"]):
        row = 0 if lm["pos"] - row_last[0] >= 22 else 1
        row_last[row] = lm["pos"]
        if lm["status"] == "passed":
            title = f'{esc(lm["name"])}: passed around {(lm.get("central") or "")[:4]}'
            year = f'✓ {(lm.get("central") or "")[:4]}'
        else:
            title = f'{esc(lm["name"])}: projected {lm["central"][:4]} (range {lm["low"][:4]}–{lm["high"][:4]})'
            year = lm["central"][:4]
        marks.append(
            f'<a class="landmark row{row} {lm["status"]}" href="#{lm["anchor"]}" style="left:{lm["pos"]:.2f}%" title="{title}">'
            f'<span class="lm-line"></span><span class="lm-label">{year}<span class="lm-nm"><br>{esc(short_name(lm["id"]))}</span></span></a>')
    return f"""
<section class="meter" aria-label="Share of the peak Boomer population gone">
  <div class="meter-head">
    <div class="big">{gone:.1f}<span class="pct">%</span></div>
    <div class="meter-copy">
      <p class="meter-lede">of the Boomer generation at its peak is gone {est_tag('interpolated')}</p>
      <p class="meter-sub">About <strong>{stats.fmt_millions(h['value'])}</strong> Boomers live in the US today,
      down from <strong>78.8 million</strong> at the {h['peak_year']} peak.
      Range: {stats.fmt_millions(h['low'])} – {stats.fmt_millions(h['high'])}.</p>
    </div>
  </div>
  <div class="bar-wrap">
    <div class="bar" role="meter" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{gone:.1f}">
      <div class="fill" style="width:{gone:.2f}%"></div>
      <div class="now" style="left:{gone:.2f}%"><span>Today</span></div>
      {''.join(marks)}
    </div>
    <div class="bar-scale"><span style="left:0">0%</span><span style="left:50%">50%</span><span style="left:100%">100%</span></div>
    <div class="bar-years">{''.join(ticks)}</div>
  </div>
  <p class="caveat">Estimate as of {nice_date(h['as_of'])}. 100% = the 78.8 million Boomers living in the US in 1999
  (Census). “Gone” counts deaths and net emigration together. Faint markers are projected landmarks; click one for
  its range and method. Years under the bar are when Census projections put the meter.</p>
  {stale_note(sec)}
</section>"""


def short_name(lid: str) -> str:
    return {"lm_wealth_under_half": "Wealth under ½",
            "lm_congress_under_third": "Congress under ⅓",
            "lm_cohort_half_gone": "Half gone"}[lid]


def landmark_cards(lms: list[dict]) -> str:
    cards = []
    for lm in lms:
        if lm["status"] == "projected":
            rng = (f'range {lm["low"][:4]}–{lm["high"][:4]}' if lm["low"][:4] != lm["high"][:4]
                   else f'all scenarios land in {lm["low"][:4]}')
            when = f'<div class="lm-year">{lm["central"][:4]}</div><div class="lm-range">{rng}</div>'
        elif lm["status"] == "passed":
            when = f'<div class="lm-year">Passed</div><div class="lm-range">{(lm.get("central") or "")[:4]}</div>'
        else:
            when = '<div class="lm-year">—</div><div class="lm-range">recent trend doesn’t get there</div>'
        cards.append(f'<a class="lm-card" href="#{lm["anchor"]}"><div class="lm-name">{esc(lm["name"])}</div>{when}'
                     f'<div class="lm-cav">{esc(lm["caveat"])}</div></a>')
    return f'<section class="lm-cards"><h2 class="kicker">Landmarks ahead</h2><div class="cards">{"".join(cards)}</div></section>'


# --------------------------------------------------------------------------- sections

def cohort_section(state: dict) -> str:
    sec = state.get("headcount", {})
    h = sec.get("data")
    if not h:
        return ""
    est = [(yf(p["date"]), p["value"] / 1e6) for p in h["monthly"] if not p["projected_by_census"]]
    cen = [(yf(p["date"]), p["value"] / 1e6) for p in h["monthly"] if p["projected_by_census"]]
    if est and cen:
        cen = [est[-1]] + cen
    bands, series = [], []
    proj = h.get("projection", {})
    lm = h.get("landmark_half_gone", {})
    if proj.get("low") and proj.get("high"):
        lo = [(p["year"] + 0.5, p["value"] / 1e6) for p in proj["low"]]
        hi = [(p["year"] + 0.5, p["value"] / 1e6) for p in proj["high"]]
        bands.append({"lower": lo, "upper": hi, "color": "--band", "name": "Census low/high immigration projections"})
        series.append({"name": "Census projection", "points": [(p["year"] + 0.5, p["value"] / 1e6) for p in proj["mid"]],
                       "color": "--ink-3", "dash": True, "width": 1.5, "tt_fmt": "{:.1f}M"})
    series += [{"name": "Census estimate", "points": est, "color": "--gen-boomer", "tt_fmt": "{:.1f}M"},
               {"name": "Census short-term projection", "points": cen, "color": "--gen-boomer", "dash": True,
                "tt_fmt": "{:.1f}M"}]
    x1 = 2070 if proj else 2027.5
    chart = line_chart(
        "c-cohort", series=series, bands=bands, x_domain=(2020, x1), y_domain=(0, 85),
        x_ticks=[(y, str(y)) for y in range(2020, int(x1) + 1, 10 if proj else 1)],
        y_ticks=[0, 20, 40, 60, 80], y_fmt="{:.0f}M",
        x_fmt=lambda x: stats.from_year_frac(x).strftime("%b %Y"),
        hrefs=[{"at": 78.8, "label": "1999 peak: 78.8M"}, {"at": 39.4, "label": "half of peak"}],
        vrefs=[{"at": stats.year_frac(d(h["as_of"])), "label": "today"}],
        aria="Living Boomers in the US, estimate and projection")
    lm_text = ""
    if lm.get("status") == "projected":
        lm_text = (f'<div class="lm-detail"><h3>Landmark: half the peak gone</h3>'
                   f'<p>Census projections put the living Boomer population below 39.4 million — half its peak — in '
                   f'<strong>{lm["central"][:4]}</strong> (range {lm["low"][:4]}–{lm["high"][:4]} across Census’s immigration '
                   f'scenarios). The range does not include surprises in mortality, which matter more than immigration for a '
                   f'group this age; treat the range as a floor on the real uncertainty.</p></div>')
    return f"""
<section id="cohort" class="block">
  <h2>The cohort</h2>
  <p class="lede">Every Boomer born is already born. From here the number only goes one way.</p>
  {chart}
  <p class="caption">Living Boomers in the US, millions. Solid: Census monthly estimates. Dashed orange: Census’s own
  short-term projection. Dashed gray + shaded: Census 2023 projections (middle series; shading spans low- to
  high-immigration), scaled to the latest estimate. Source: Census PEP vintage {h['vintage']}; Census 2023 National
  Population Projections.</p>
  {lm_text}
  <details><summary>How today’s number is estimated</summary>
  <p>Census publishes monthly estimates once a year. For months after its most recent July 1 it publishes its own
  short-term projection; we use those, interpolated to today’s date. The range comes from checking Census’s
  <em>previous</em> short-term projection against what the newer estimates later showed. Today is
  {h['months_past_anchor']:.0f} months past the last July 1 Census actually
  estimated ({nice_date(h['anchor'])}); the worst miss Census’s previous vintage made that far ahead was
  ±{h['band_pct']:.2f}%, and that is the range shown.
  When a new Census vintage lands, the difference between what we showed and what Census now says is logged, and
  anything material becomes a public correction.</p></details>
  {stale_note(sec)}
</section>"""


def wealth_section(state: dict) -> str:
    sec = state.get("wealth", {})
    w = sec.get("data")
    if not w:
        return ('<section id="wealth" class="block"><h2>Wealth</h2><p class="pending">Waiting on the first '
                'successful Federal Reserve data run.</p></section>')
    s = w["series"]
    nw = s["networth"]
    pts = [(yf(p["date"]), p["value"]) for p in nw["boomer"]]
    lm = w.get("landmark_under_half", {})
    bands, series = [], [{"name": "Boomer share of net worth", "points": pts, "color": "--gen-boomer", "tt_fmt": "{:.1f}%"}]
    x1 = pts[-1][0] + 1
    if lm.get("status") == "projected" and lm.get("band"):
        b = lm["band"]
        bands.append({"lower": list(zip(b["x"], b["low"])), "upper": list(zip(b["x"], b["high"])),
                      "color": "--band", "name": "Range of recent-trend projections"})
        x1 = max(x1, b["x"][-1])
    x0 = pts[0][0]
    chart = line_chart(
        "c-networth", series=series, bands=bands, x_domain=(x0, x1), y_domain=(0, 70),
        x_ticks=[(y, str(y)) for y in range(int(x0) + (5 - int(x0) % 5) % 5, int(x1) + 1, 5)],
        y_ticks=[0, 10, 20, 30, 40, 50, 60, 70], y_fmt="{:.0f}%",
        x_fmt=lambda x: f"Q{(stats.from_year_frac(x).month - 1)//3 + 1} {stats.from_year_frac(x).year}",
        hrefs=[{"at": 50, "label": "half"}], aria="Boomer share of household net worth")

    def small(col, title, cid):
        p = [(yf(q["date"]), q["value"]) for q in s[col]["boomer"]]
        return (f'<figure class="small"><figcaption>{title}: <strong>{s[col]["boomer_share"]:.1f}%</strong></figcaption>'
                + line_chart(cid, series=[{"name": title, "points": p, "color": "--gen-boomer", "tt_fmt": "{:.1f}%"}],
                             x_domain=(p[0][0], p[-1][0]), y_domain=(0, 70), height=220,
                             x_ticks=[(y, str(y)) for y in range(1990, int(p[-1][0]) + 1, 10)],
                             y_ticks=[0, 20, 40, 60], y_fmt="{:.0f}%",
                             x_fmt=lambda x: f"Q{(stats.from_year_frac(x).month - 1)//3 + 1} {stats.from_year_frac(x).year}",
                             hrefs=[{"at": 50, "label": ""}], aria=title) + "</figure>")

    if lm.get("status") == "projected":
        lm_text = (f'<p>If the share keeps falling at its recent pace, it drops below half in <strong>{lm["central"][:4]}</strong>. '
                   f'Fitting the trend over the last 3 to 7 years instead gives anywhere from {lm["low"][:4]} to {lm["high"][:4]}; '
                   f'that spread is the shaded band. Stock and housing markets can move this by years in either direction.</p>')
    elif lm.get("status") == "passed":
        lm_text = f'<p>Boomer-headed households fell below half of US household net worth around <strong>{(lm.get("central") or "")[:4]}</strong>.</p>'
    else:
        lm_text = '<p>The recent trend doesn’t reach one half within the projection horizon.</p>'
    peak = nw["peak"]
    return f"""
<section id="wealth" class="block">
  <h2>Wealth</h2>
  <p class="lede">Boomer-headed households hold <strong>{nw['boomer_share']:.1f}%</strong> of all US household net worth,
  as of {nice_date(nw['latest_quarter'])}. Their peak was {peak['value']:.1f}% in {peak['date'][:4]}.</p>
  {chart}
  <p class="caption">Boomer-headed households’ share of US household net worth, quarterly. Shaded: range of recent-trend
  projections. Source: Federal Reserve Board, Distributional Financial Accounts, generation levels; share = Boomer ÷ all
  generations.</p>
  <div class="lm-detail"><h3>Landmark: under half of household wealth</h3>{lm_text}</div>
  <div class="smalls">
    {small('equities', 'Stocks & mutual funds', 'c-eq')}
    {small('realestate', 'Real estate (market value)', 'c-re')}
  </div>
  <p class="caveat">A household counts as Boomer if its head is a Boomer; a Millennial living in a Boomer-headed home
  counts as Boomer wealth. Stocks exclude those held inside pensions. Real estate is market value before mortgages.
  The Fed revises back data every quarter; changes to numbers we’ve shown are logged as corrections.</p>
  {stale_note(sec)}
</section>"""


def congress_section(state: dict) -> str:
    sec = state.get("congress", {})
    c = sec.get("data")
    if not c:
        return ""
    hist = c["history"]
    pts = [(yf(h["date"]), h["median_age"]) for h in hist]
    now_x = stats.year_frac(d(c["as_of"]))
    # How many of the oldest Congresses are also the most recent ones?
    by_age = sorted(hist, key=lambda h: -h["median_age"])
    streak = 0
    recent = [h["congress"] for h in hist[::-1]]
    for i in range(2, len(hist) // 4):  # cap: at i = all Congresses it is trivially true
        if {h["congress"] for h in by_age[:i]} == set(recent[:i]):
            streak = i
    oldest = by_age[0]
    hist_chart = line_chart(
        "c-age-history",
        series=[{"name": "Median age of Congress", "points": pts, "color": "--series-age", "tt_fmt": "{:.1f}"}],
        x_domain=(1789, now_x + 2), y_domain=(35, 65),
        x_ticks=[(y, str(y)) for y in range(1800, int(now_x) + 1, 25)],
        y_ticks=[35, 40, 45, 50, 55, 60, 65], y_fmt="{:.0f}",
        x_fmt=lambda x: f"{stats.from_year_frac(x).year}",
        aria="Median age of Congress since 1789")
    streak_line = (f"The {streak} oldest Congresses in American history are the {streak} most recent."
                   if streak >= 2 else f"The oldest Congress on record was the {ordinal(oldest['congress'])} ({oldest['date'][:4]}).")
    gens = c["generations"]
    bar = stacked_bar([{"label": "House", "counts": gens["House"]}, {"label": "Senate", "counts": gens["Senate"]}],
                      GEN_COLORS)
    legend = "".join(f'<span class="lg"><i style="background:var({v})"></i>{esc(k)}</span>' for k, v in GEN_COLORS)

    lm = c["landmark_under_third"]
    share_pts = [(x, y) for x, y in lm["points"]]
    bands = []
    x1 = now_x + 1
    if lm.get("status") == "projected" and lm.get("band"):
        b = lm["band"]
        bands.append({"lower": list(zip(b["x"], b["low"])), "upper": list(zip(b["x"], b["high"])),
                      "color": "--band", "name": "Range of recent-trend projections"})
        x1 = b["x"][-1]
    share_chart = line_chart(
        "c-congress-share",
        series=[{"name": "Boomer share of Congress", "points": share_pts, "color": "--gen-boomer", "tt_fmt": "{:.1f}%"}],
        bands=bands, x_domain=(share_pts[0][0] - 1, x1), y_domain=(0, 70),
        x_ticks=[(y, str(y)) for y in range(int(share_pts[0][0]) + 1, int(x1) + 1, 4)],
        y_ticks=[0, 10, 20, 30, 40, 50, 60, 70], y_fmt="{:.0f}%",
        x_fmt=lambda x: f"{stats.from_year_frac(x):%b %Y}",
        hrefs=[{"at": 100 / 3, "label": "one third"}], height=260,
        aria="Boomer share of Congress since its peak, with projection")
    lm_text = (f'Boomers hold <strong>{c["boomer_share"]:.1f}%</strong> of seats ({c["boomer_count"]} of {c["seated_with_birthday"]}). '
               f'At the pace of the last few Congresses, that falls below a third in <strong>{lm["central"][:4]}</strong> '
               f'(range {lm["low"][:4]}–{lm["high"][:4]}).' if lm.get("status") == "projected" else
               f'Boomers hold <strong>{c["boomer_share"]:.1f}%</strong> of seats.')
    return f"""
<section id="congress" class="block">
  <h2>Congress</h2>
  <div class="tiles">
    <div class="tile"><div class="tile-n">{c['median_age']['senate']:.1f}</div><div class="tile-l">median age, Senate</div></div>
    <div class="tile"><div class="tile-n">{c['median_age']['house']:.1f}</div><div class="tile-l">median age, House</div></div>
    <div class="tile"><div class="tile-n">{c['boomer_share']:.0f}%</div><div class="tile-l">of seats held by Boomers</div></div>
  </div>
  <h3>Older than it has ever been</h3>
  <p class="lede">{streak_line}</p>
  {hist_chart}
  <p class="caption">Median age of voting members of Congress (House and Senate), measured one year into each Congress,
  1st Congress (1789) through the {ordinal(hist[-1]['congress'])}. Source: unitedstates/congress-legislators.
  Before about 1850 some birthdates are missing; those members are left out of the median.</p>
  <h3>Who holds the seats</h3>
  <div class="legend">{legend}</div>
  {bar}
  <p class="caption">Seated voting members by generation (birth year, Pew definitions), {nice_date(c['as_of'])}.</p>
  <div class="lm-detail"><h3>Landmark: Boomers under a third of Congress</h3><p>{lm_text}</p>
  {share_chart}
  <p class="caption">Boomer share of Congress at each Congress since the share peaked, plus today. Shaded: spread of
  straight-line trends fitted to the last 3 to 6 points. Seats change in elections, not smoothly; this is a trend,
  not a forecast of any race.</p></div>
  {stale_note(sec)}
</section>"""


def ordinal(n: int) -> str:
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf}"


def coming_section() -> str:
    items = [("Voters", "Boomer share of people who actually vote vs. share of adults (Census CPS, every two years)."),
             ("Homeownership", "Ownership rate by age of householder (Census Housing Vacancy Survey, quarterly)."),
             ("Work", "Labor force participation, 65 and over (BLS, monthly)."),
             ("Committee chairs", "Median age of the people who set Congress’s agenda.")]
    lis = "".join(f"<li><strong>{a}.</strong> {b}</li>" for a, b in items)
    return f'<section class="block coming"><h2>Coming next</h2><ul>{lis}</ul></section>'


def corrections_section(state: dict) -> str:
    cs = state.get("corrections", [])
    if not cs:
        body = "<p>None so far. When a source revises a number we’ve shown, the old and new values are listed here.</p>"
    else:
        rows = "".join(f"<tr><td>{esc(c['recorded'])}</td><td>{esc(c['metric_id'])}</td><td>{esc(c['as_of'])}</td>"
                       f"<td>{esc(c['was'])}</td><td>{esc(c['now'])}</td><td>{esc(c['reason'])}</td></tr>" for c in cs)
        body = (f"<table><thead><tr><th>Logged</th><th>Metric</th><th>For date</th><th>Was</th><th>Now</th>"
                f"<th>Why</th></tr></thead><tbody>{rows}</tbody></table>")
    return f'<section id="corrections" class="block"><h2>Corrections</h2>{body}</section>'


def sources_section(state: dict) -> str:
    rows = []
    seen = set()
    for key in ("headcount", "wealth", "congress"):
        data = (state.get(key) or {}).get("data") or {}
        for s in data.get("sources", []) + data.get("projection_sources", []):
            if "sha256" not in s or s["sha256"] in seen:
                continue
            seen.add(s["sha256"])
            rows.append(f"<tr><td><a href=\"{esc(s['url'])}\">{esc(s['filename'])}</a></td>"
                        f"<td>{esc(s['retrieved'])}</td><td><code>{esc(s['sha256'][:12])}</code></td></tr>")
    return (f'<section id="sources" class="block"><h2>Source files behind this page</h2>'
            f'<p>Every file is snapshotted with its fingerprint (SHA-256) and kept in the '
            f'<a href="{REPO_URL}">public repository</a>, along with a ledger of every number this page has shown.</p>'
            f'<div class="scroll"><table><thead><tr><th>File</th><th>Retrieved</th><th>SHA-256</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></section>')


# --------------------------------------------------------------------------- page

def page(title: str, body: str, description: str) -> str:
    css = (Path(__file__).parent / "style.css").read_text()
    js = (Path(__file__).parent / "tooltip.js").read_text()
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{css}</style></head>
<body>
<header class="top"><a class="brand" href="index.html">BOOMERMETER</a>
<nav><a href="index.html#cohort">Cohort</a><a href="index.html#wealth">Wealth</a><a href="index.html#congress">Congress</a><a href="methods.html">Methods</a></nav></header>
<main>{body}</main>
<footer><p>US data only. Every number is sourced; every estimate is labeled. <a href="methods.html">Methods</a> ·
<a href="index.html#corrections">Corrections</a> · <a href="data/latest.json">Data (JSON)</a> ·
<a href="data/ledger.jsonl">Ledger</a> · <a href="{REPO_URL}">Code</a></p></footer>
<div id="tt" class="tt" hidden></div>
<script>{js}</script>
</body></html>"""


def build(state: dict, out: Path = config.SITE_OUT) -> Path:
    if out.exists():
        shutil.rmtree(out)
    (out / "data").mkdir(parents=True)
    lms = landmark_list(state)
    demo = state.get("demo")
    banner = ('<div class="demo">PREVIEW — the Census and Fed numbers on this page are placeholders for layout only. '
              'The live site uses the pipeline’s real data.</div>' if demo else "")
    updated = nice_date(state["run_date"])
    body = f"""{banner}
<section class="hero">
  <h1>The handoff, counted.</h1>
  <p class="hero-lede">The Baby Boom generation has held the center of American wealth and political power longer than
  any generation before it. This page tracks the transfer as it happens — with sources you can check and every
  estimate labeled as one.</p>
  <p class="updated">Updated {updated}</p>
</section>
{meter(state, lms)}
{landmark_cards(lms)}
{cohort_section(state)}
{wealth_section(state)}
{congress_section(state)}
{coming_section()}
{corrections_section(state)}
{sources_section(state)}"""
    (out / "index.html").write_text(page("Boomermeter — the handoff, counted", body,
                                         "Tracking the transfer of US wealth and political power from the Baby Boom generation."))
    methods_md = (config.ROOT / "METHODS.md").read_text()
    methods_html = markdown.markdown(methods_md, extensions=["tables", "toc"])
    (out / "methods.html").write_text(page("Methods — Boomermeter", f'<article class="methods">{methods_html}</article>',
                                           "How every number on Boomermeter is sourced, estimated and labeled."))
    public = {k: v for k, v in state.items() if k != "registry"}
    (out / "data" / "latest.json").write_text(json.dumps(public, indent=1, default=str))
    if config.LEDGER.exists():
        shutil.copy(config.LEDGER, out / "data" / "ledger.jsonl")
    (out / ".nojekyll").write_text("")
    return out
