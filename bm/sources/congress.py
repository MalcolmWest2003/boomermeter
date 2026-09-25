"""unitedstates/congress-legislators: birthdates and terms for every member of
Congress since 1789. Public domain, community maintained, updated within days
of changes in membership."""
from __future__ import annotations

import csv
import datetime as dt
import io
from dataclasses import dataclass

import yaml

from .. import snapshot

BASE = "https://raw.githubusercontent.com/unitedstates/congress-legislators/main/"
SOURCE = "congress-legislators"
# Non-voting delegates and the resident commissioner (used for current members).
NONVOTING = {"DC", "PR", "GU", "VI", "AS", "MP"}

# Date each state was admitted (or ratified the Constitution). A House term
# only counts as a voting seat if its state code is here and the date being
# sampled is on or after admission; this removes territorial delegates
# (e.g. Alaska and Hawaii before 1959, Arizona before 1912, the Philippines,
# Dakota and Orleans territories) from historical samples.
ADMITTED = {k: dt.date.fromisoformat(v) for k, v in {
    "DE": "1787-12-07", "PA": "1787-12-12", "NJ": "1787-12-18", "GA": "1788-01-02",
    "CT": "1788-01-09", "MA": "1788-02-06", "MD": "1788-04-28", "SC": "1788-05-23",
    "NH": "1788-06-21", "VA": "1788-06-25", "NY": "1788-07-26", "NC": "1789-11-21",
    "RI": "1790-05-29", "VT": "1791-03-04", "KY": "1792-06-01", "TN": "1796-06-01",
    "OH": "1803-03-01", "LA": "1812-04-30", "IN": "1816-12-11", "MS": "1817-12-10",
    "IL": "1818-12-03", "AL": "1819-12-14", "ME": "1820-03-15", "MO": "1821-08-10",
    "AR": "1836-06-15", "MI": "1837-01-26", "FL": "1845-03-03", "TX": "1845-12-29",
    "IA": "1846-12-28", "WI": "1848-05-29", "CA": "1850-09-09", "MN": "1858-05-11",
    "OR": "1859-02-14", "KS": "1861-01-29", "WV": "1863-06-20", "NV": "1864-10-31",
    "NE": "1867-03-01", "CO": "1876-08-01", "ND": "1889-11-02", "SD": "1889-11-02",
    "MT": "1889-11-08", "WA": "1889-11-11", "ID": "1890-07-03", "WY": "1890-07-10",
    "UT": "1896-01-04", "OK": "1907-11-16", "NM": "1912-01-06", "AZ": "1912-02-14",
    "AK": "1959-01-03", "HI": "1959-08-21",
}.items()}


def is_voting(t: "Term", on: dt.date) -> bool:
    admitted = ADMITTED.get(t.state)
    return admitted is not None and on >= admitted

try:
    Loader = yaml.CSafeLoader
except AttributeError:  # pragma: no cover
    Loader = yaml.SafeLoader


@dataclass
class Term:
    chamber: str  # rep | sen
    start: dt.date
    end: dt.date
    state: str
    seat: str = ""  # House district number, or Senate class


@dataclass
class Member:
    bioguide: str
    name: str
    birthday: dt.date | None
    terms: list[Term]
    current: bool


def _parse(content: bytes, current: bool) -> list[Member]:
    out = []
    for p in yaml.load(content, Loader=Loader):
        bday = p.get("bio", {}).get("birthday")
        name = p["name"].get("official_full") or f"{p['name'].get('first','')} {p['name'].get('last','')}".strip()
        terms = [Term(t["type"], dt.date.fromisoformat(str(t["start"])),
                      dt.date.fromisoformat(str(t["end"])), t.get("state", ""),
                      str(t.get("district", t.get("class", ""))))
                 for t in p.get("terms", [])]
        out.append(Member(p["id"]["bioguide"], name,
                          dt.date.fromisoformat(str(bday)) if bday else None,
                          terms, current))
    return out


def _extract_csv(members: list[Member]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["bioguide", "name", "birthday", "chamber", "start", "end", "state", "seat"])
    for m in members:
        for t in m.terms:
            w.writerow([m.bioguide, m.name, m.birthday or "", t.chamber, t.start, t.end, t.state, t.seat])
    return buf.getvalue()


def load(fetch: bool = True, local_dir=None) -> tuple[list[Member], list[dict]]:
    """Returns (members, provenance records)."""
    members, prov = [], []
    for fname, current in (("legislators-current.yaml", True),
                           ("legislators-historical.yaml", False)):
        if local_dir is not None:
            content = (local_dir / fname).read_bytes()
            snap = snapshot.record(SOURCE, fname, BASE + fname, content, store_raw=False)
        else:
            # Raw YAML changes often for reasons unrelated to us (IDs, URLs);
            # store only the fields we use, keyed by the raw file's hash.
            snap = snapshot.fetch(SOURCE, fname, BASE + fname, store_raw=False)
        parsed = _parse(snap.content, current)
        if snap.stored_path is None:
            snapshot.store_extract(snap, fname.replace(".yaml", "-extract.csv"), _extract_csv(parsed))
        members += parsed
        prov.append(snap.provenance())
    return members, prov


def serving_on(members: list[Member], on: dt.date, chamber: str | None = None,
               voting_only: bool = True) -> list[tuple[Member, Term]]:
    """Members holding a seat on `on`.

    The historical file does not always shorten a term when a member died or
    resigned, so a seat can briefly show two holders. For districted House
    seats and Senate seats (state + class) we keep only the holder whose term
    started most recently. At-large House seats (district 0) can legitimately
    have several holders and are left as-is.
    """
    rows = []
    for m in members:
        for t in m.terms:
            if t.start <= on <= t.end and (chamber is None or t.chamber == chamber):
                if voting_only and not is_voting(t, on):
                    continue
                rows.append((m, t))
                break
    by_seat: dict[tuple, tuple[Member, Term]] = {}
    out = []
    for m, t in rows:
        if t.chamber == "rep" and t.seat in ("", "0", "-1"):
            out.append((m, t))
            continue
        key = (t.chamber, t.state, t.seat)
        if key not in by_seat or t.start > by_seat[key][1].start:
            by_seat[key] = (m, t)
    return out + list(by_seat.values())


def current_seated(members: list[Member], on: dt.date) -> list[tuple[Member, Term]]:
    """Members in the current file whose latest term covers `on`."""
    out = []
    for m in members:
        if not m.current or not m.terms:
            continue
        t = m.terms[-1]
        if t.start <= on <= t.end and not (t.chamber == "rep" and t.state in NONVOTING):
            out.append((m, t))
    return out


def congress_starts(until: dt.date) -> list[tuple[int, dt.date]]:
    """(Congress number, start date). March 4 of odd years through the 73rd
    Congress; January 3 of odd years from the 74th (1935) on."""
    out = []
    n, year = 1, 1789
    while True:
        start = dt.date(year, 3, 4) if n <= 73 else dt.date(year, 1, 3)
        if start > until:
            break
        out.append((n, start))
        n += 1
        year += 2
    return out
