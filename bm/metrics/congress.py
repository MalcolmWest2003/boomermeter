"""Congress age metrics: current median ages, generational makeup, the full
history of median age since 1789, and the 'under a third' landmark."""
from __future__ import annotations

import datetime as dt

from .. import config, landmarks, stats
from ..ledger import Entry
from ..sources import congress as src

# One year in: before 1935 the first session often convened in December, so
# early samples miss most members; a year in, nearly every seat is filled.
SAMPLE_OFFSET = dt.timedelta(days=365)


def _is_boomer(m) -> bool:
    return m.birthday is not None and config.BOOMER_FIRST <= m.birthday.year <= config.BOOMER_LAST


def compute(members, prov, today: dt.date, reg: dict) -> tuple[list[Entry], dict]:
    seated = src.current_seated(members, today)
    house = [(m, t) for m, t in seated if t.chamber == "rep"]
    senate = [(m, t) for m, t in seated if t.chamber == "sen"]

    def ages(rows):
        return [stats.age_on(m.birthday, today) for m, _ in rows if m.birthday]

    med_h, med_s = stats.median(ages(house)), stats.median(ages(senate))
    med_all = stats.median(ages(seated))
    gens = {}
    for chamber, rows in (("House", house), ("Senate", senate)):
        counts = {g[0]: 0 for g in config.GENERATIONS}
        for m, _ in rows:
            if m.birthday:
                counts[config.generation_of(m.birthday.year)] += 1
        gens[chamber] = counts
    n_seated = len([1 for m, _ in seated if m.birthday])
    n_boomer = sum(1 for m, _ in seated if _is_boomer(m))
    share = 100 * n_boomer / n_seated

    # History: median age and Boomer share 60 days into each Congress.
    hist = []
    for n, start in src.congress_starts(today):
        on = start + SAMPLE_OFFSET
        if on > today:
            continue
        rows = src.serving_on(members, on)
        with_bday = [m for m, _ in rows if m.birthday]
        if not with_bday:
            continue
        hist.append({
            "congress": n,
            "date": on.isoformat(),
            "median_age": round(stats.median([stats.age_on(m.birthday, on) for m in with_bday]), 2),
            "boomer_share": round(100 * sum(_is_boomer(m) for m in with_bday) / len(with_bday), 2),
            "members": len(rows),
            "with_birthday": len(with_bday),
        })
    record_prior = max(hist[:-1], key=lambda h: h["median_age"]) if len(hist) > 1 else None

    # Landmark: Boomers under a third of Congress.
    peak_i = max(range(len(hist)), key=lambda i: hist[i]["boomer_share"])
    pts = [(stats.year_frac(dt.date.fromisoformat(h["date"])), h["boomer_share"]) for h in hist[peak_i:]]
    pts.append((stats.year_frac(today), share))
    lm_cfg = reg["landmarks"]["lm_congress_under_third"]
    lm = landmarks.trend_crossing(pts, lm_cfg["threshold"], "below",
                                  windows=[3, 4, 5, 6], central=5, today=today)
    lm["points"] = pts
    if lm["status"] == "projected":
        lm["band"] = landmarks.band_lines(lm, pts[-1][0], stats.year_frac(dt.date.fromisoformat(lm["high"])) + 1)

    method_common = ["exclude_nonvoting_delegates"]
    entries = [
        Entry("congress_median_age_house", round(med_h, 1), f"{med_h:.1f}", "measured",
              today.isoformat(), "years", method=method_common + ["exact_age_on_run_date", "median"],
              sources=prov[:1], notes=f"{len(house)} seated"),
        Entry("congress_median_age_senate", round(med_s, 1), f"{med_s:.1f}", "measured",
              today.isoformat(), "years", method=["exact_age_on_run_date", "median"],
              sources=prov[:1], notes=f"{len(senate)} seated"),
        Entry("congress_boomer_share", round(share, 1), f"{share:.1f}%", "measured",
              today.isoformat(), "percent", method=method_common + ["generation_by_birth_year"],
              sources=prov[:1], notes=f"{n_boomer} of {n_seated}"),
        Entry("congress_median_age_history", round(med_all, 1), f"{med_all:.1f}", "measured",
              today.isoformat(), "years",
              method=method_common + ["members_serving_on_date", "drop_missing_birthdates", "median"],
              sources=prov, notes=f"{len(hist)} Congresses sampled"),
    ]
    if lm["status"] == "projected":
        entries.append(Entry("lm_congress_under_third", stats.year_frac(dt.date.fromisoformat(lm["central"])),
                             lm["central"][:4], "projected", today.isoformat(), "year",
                             low=stats.year_frac(dt.date.fromisoformat(lm["low"])),
                             high=stats.year_frac(dt.date.fromisoformat(lm["high"])),
                             display_range=landmarks.range_label(lm),
                             method=["linear_trend_multiwindow"], sources=prov))

    site = {
        "as_of": today.isoformat(),
        "median_age": {"house": med_h, "senate": med_s, "all": med_all},
        "seated": {"house": len(house), "senate": len(senate)},
        "generations": gens,
        "boomer_share": share, "boomer_count": n_boomer, "seated_with_birthday": n_seated,
        "history": hist,
        "record_prior": record_prior,
        "landmark_under_third": lm,
        "sources": prov,
    }
    return entries, site
