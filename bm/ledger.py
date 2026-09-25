"""Provenance ledger: every number the site has ever displayed.

Append-only JSON lines. A new line is written when a metric's displayed value,
its range, or its source vintage changes, so any number that was ever on the
page can be reconstructed with its source, vintage and method.

If a *measured* value for the same reference date changes (the source revised
it), a correction record is written and the site lists it publicly.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field, asdict

from . import config

STATUSES = ("measured", "interpolated", "projected")


@dataclass
class Entry:
    metric_id: str
    value: float
    display: str
    status: str  # measured | interpolated | projected
    as_of: str  # the date the number describes
    unit: str
    low: float | None = None
    high: float | None = None
    display_range: str | None = None
    method: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f"bad status {self.status}")
        if self.status != "measured" and (self.low is None or self.high is None):
            raise ValueError(f"{self.metric_id}: non-measured values need a range")


def _read(path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def history(metric_id: str | None = None) -> list[dict]:
    rows = _read(config.LEDGER)
    return [r for r in rows if metric_id is None or r["metric_id"] == metric_id]


def latest(metric_id: str) -> dict | None:
    rows = history(metric_id)
    return rows[-1] if rows else None


def _fingerprint(d: dict) -> tuple:
    return (d["display"], d.get("display_range"), d["as_of"], d["status"],
            tuple(s.get("sha256") for s in d.get("sources", [])))


def append(entry: Entry, run_date: dt.date | None = None) -> bool:
    """Append if anything displayed changed. Returns True if written."""
    run_date = run_date or config.today()
    rec = {"recorded": run_date.isoformat(), **asdict(entry)}
    prev_all = history(entry.metric_id)
    prev = prev_all[-1] if prev_all else None
    if prev and _fingerprint(prev) == _fingerprint(rec):
        return False
    # Source revision of an already-published measured value -> public correction.
    if entry.status == "measured":
        for old in reversed(prev_all):
            if (old["as_of"] == entry.as_of and old["status"] == "measured"
                    and old["display"] != entry.display):
                _append_json(config.CORRECTIONS, {
                    "recorded": run_date.isoformat(),
                    "metric_id": entry.metric_id,
                    "as_of": entry.as_of,
                    "was": old["display"],
                    "now": entry.display,
                    "reason": "source revised a previously published value",
                })
                break
    _append_json(config.LEDGER, rec)
    return True


def corrections() -> list[dict]:
    return _read(config.CORRECTIONS)


def _append_json(path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(rec, sort_keys=False) + "\n")


def log_reconciliation(rec: dict) -> None:
    _append_json(config.RECONCILIATION, rec)
