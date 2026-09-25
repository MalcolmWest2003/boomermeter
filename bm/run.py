"""Daily pipeline: fetch -> compute -> ledger -> site.

Each source runs independently. If one fails (a site is down, a file layout
changed), the others still update, the failed section shows its last good
data with a visible 'could not refresh' note, and the run records the failure
so the workflow can fail loudly afterwards (GitHub emails the repo owner).

Usage:
  python -m bm.run            # real run
  python -m bm.run --demo     # synthetic Census/Fed data, for layout previews
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import traceback
from pathlib import Path

from . import config, ledger, registry
from .metrics import congress as congress_m
from .metrics import headcount as headcount_m
from .metrics import history as history_m
from .metrics import wealth as wealth_m
from .site import build as site_build
from .sources import census, congress, fed_dfa, fred, irs, nces


def _save_state(name: str, data: dict, run_date: dt.date) -> dict:
    config.STATE.mkdir(parents=True, exist_ok=True)
    rec = {"data": data, "last_success": run_date.isoformat(), "stale": False}
    (config.STATE / f"{name}.json").write_text(json.dumps(rec, default=str))
    return rec


def _prior_state(name: str) -> dict:
    p = config.STATE / f"{name}.json"
    if not p.exists():
        return {"data": None, "stale": True, "last_success": None}
    rec = json.loads(p.read_text())
    rec["stale"] = True
    return rec


def _check_reconciliation(site: dict, run_date: dt.date) -> None:
    """When a new Census vintage appears, compare what we showed for its July 1
    with what Census now says. >0.5% difference -> public correction."""
    prev = _prior_state("headcount").get("data")
    if not prev or prev.get("vintage") == site["vintage"]:
        return
    anchor = site["anchor"]
    shown = [r for r in ledger.history("boomer_headcount") if r["as_of"] <= anchor]
    new_val = next((m["value"] for m in site["monthly"] if m["date"] == anchor), None)
    if not shown or new_val is None:
        return
    old = shown[-1]
    rel = (old["value"] - new_val) / new_val
    rec = {"recorded": run_date.isoformat(), "metric_id": "boomer_headcount",
           "old_vintage": prev.get("vintage"), "new_vintage": site["vintage"],
           "compared_date": anchor, "we_showed": old["display"], "we_showed_as_of": old["as_of"],
           "census_now": new_val, "relative_difference": rel}
    ledger.log_reconciliation(rec)
    if abs(rel) > 0.005:
        ledger._append_json(config.CORRECTIONS, {
            "recorded": run_date.isoformat(), "metric_id": "boomer_headcount", "as_of": anchor,
            "was": old["display"], "now": f"{new_val/1e6:.1f} million",
            "reason": f"Census vintage {site['vintage']} revised the estimate ({rel*100:+.1f}%)"})


def run(demo: bool = False, congress_dir: Path | None = None) -> dict:
    today = config.today()
    reg = registry.load()
    failures = []
    state = {"run_date": today.isoformat(), "registry": reg, "demo": demo}

    def section(name, fn):
        try:
            entries, data = fn()
            for e in entries:
                # "id@generation@age" entries are per-generation values of a registered metric.
                registry.require(reg, e.metric_id.split("@")[0]) if not e.metric_id.startswith("lm_") else None
                ledger.append(e, today)
            if name == "headcount":
                _check_reconciliation(data, today)
            state[name] = _save_state(name, data, today)
        except Exception as e:  # noqa: BLE001 - isolate each source
            failures.append({"section": name, "error": f"{type(e).__name__}: {e}",
                             "trace": traceback.format_exc()[-2000:]})
            state[name] = _prior_state(name)

    def do_congress():
        members, prov = congress.load(local_dir=congress_dir)
        return congress_m.compute(members, prov, today, reg)

    def do_headcount():
        if demo:
            from tests import synthetic
            pep, proj, pprov = synthetic.census()
        else:
            pep = census.latest_alldata(max_vintage=today.year)
            try:
                proj, pprov = census.fetch_projections()
            except Exception as e:  # projections are optional for the meter itself
                failures.append({"section": "projections", "error": f"{type(e).__name__}: {e}"})
                proj, pprov = None, []
        return headcount_m.compute(pep, proj, pprov, today)

    def do_wealth():
        if demo:
            from tests import synthetic
            parsed, prov = synthetic.dfa()
        else:
            parsed, prov = fed_dfa.load()
        return wealth_m.compute(parsed, prov, today, reg)

    def do_history():
        if demo:
            from tests import synthetic
            annual, tuition, top_rate, prov = synthetic.history_inputs()
        else:
            annual, prov = {}, {}
            for sid, how in history_m.FRED_SERIES.items():
                obs, prov[sid] = fred.fetch(sid)
                annual[sid] = fred.annual(obs, how)
            tuition = top_rate = None
            for key, fetch in (("NCES-330.10", nces.fetch), ("IRS-SOI-23", irs.fetch)):
                try:  # one missing table drops its indicators, not the whole section
                    vals, prov[key] = fetch()
                except Exception as e:  # noqa: BLE001
                    failures.append({"section": f"history:{key}", "error": f"{type(e).__name__}: {e}"})
                    continue
                if key == "NCES-330.10":
                    tuition = vals
                else:
                    top_rate = vals
        return history_m.compute(history_m.build(annual, tuition, top_rate), prov, today)

    def do_literature():
        import re

        import yaml

        from .ledger import Entry
        lit = yaml.safe_load((config.ROOT / "registry" / "literature.yaml").read_text())
        entries = []
        for group, items in lit.items():
            for n, e in enumerate(items):
                missing = [k for k in ("value", "group", "period", "measure", "source", "url") if not e.get(k)]
                if missing:
                    raise ValueError(f"literature {group}[{n}] missing {missing}")
                num = float(re.sub(r"[^0-9.]", "", e["value"]))
                entries.append(Entry(f"lit_published_tax_estimates@{group}@{n}", num, e["value"], "measured",
                                     str(e["period"])[:4] + "-12-31", "percent", method=["as_published"],
                                     sources=[{"url": e["url"], "filename": e["source"]}],
                                     notes=f'{e["group"]}, {e["period"]}'))
        return entries, lit

    section("congress", do_congress)
    section("headcount", do_headcount)
    section("wealth", do_wealth)
    section("history", do_history)
    section("literature", do_literature)
    state["corrections"] = ledger.corrections()
    state["failures"] = [{k: v for k, v in f.items() if k != "trace"} for f in failures]
    site_build.build(state)
    (config.DATA / "run_status.json").write_text(json.dumps(
        {"run_date": today.isoformat(), "failures": failures}, indent=1))
    return state


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--congress-dir", type=Path)
    a = ap.parse_args()
    st = run(demo=a.demo, congress_dir=a.congress_dir)
    for f in st["failures"]:
        print(f"FAILED {f['section']}: {f['error']}")
    print(f"site built for {st['run_date']}; failures: {len(st['failures'])}")


if __name__ == "__main__":
    main()
