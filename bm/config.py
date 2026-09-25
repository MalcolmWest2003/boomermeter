"""Paths and fixed definitions shared across the pipeline."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ["BM_DATA_DIR"]) if os.environ.get("BM_DATA_DIR") else ROOT / "data"
SNAPSHOTS = DATA / "snapshots"
LEDGER = DATA / "ledger.jsonl"
CORRECTIONS = DATA / "corrections.jsonl"
RECONCILIATION = DATA / "reconciliation.jsonl"
REGISTRY = ROOT / "registry" / "metrics.yaml"
SITE_OUT = Path(os.environ["BM_SITE_DIR"]) if os.environ.get("BM_SITE_DIR") else ROOT / "_site"
STATE = DATA / "state"

# Raw files larger than this are hashed and recorded but not committed;
# only the extract the pipeline actually uses is stored alongside the hash.
MAX_STORED_RAW_BYTES = 5_000_000

# Generation birth-year ranges (Pew Research Center definitions).
GENERATIONS = [
    ("Silent & earlier", None, 1945),
    ("Boomer", 1946, 1964),
    ("Gen X", 1965, 1980),
    ("Millennial", 1981, 1996),
    ("Gen Z", 1997, None),
]
BOOMER_FIRST, BOOMER_LAST = 1946, 1964

# Longer list for historical comparisons (Congress since 1900). Greatest onward
# follow Pew; Lost (1883-1900) and Missionary (1860-1882) follow Strauss & Howe.
HIST_GENERATIONS = [
    ("Missionary", 1860, 1882),
    ("Lost", 1883, 1900),
    ("Greatest", 1901, 1927),
    ("Silent", 1928, 1945),
    ("Boomer", 1946, 1964),
    ("Gen X", 1965, 1980),
    ("Millennial", 1981, 1996),
    ("Gen Z", 1997, 2012),
]


def hist_generation_of(birth_year: int) -> str | None:
    for name, lo, hi in HIST_GENERATIONS:
        if lo <= birth_year <= hi:
            return name
    return None


def today() -> dt.date:
    """Run date. BM_TODAY overrides it for tests and backfills."""
    override = os.environ.get("BM_TODAY")
    return dt.date.fromisoformat(override) if override else dt.date.today()


def generation_of(birth_year: int) -> str:
    for name, lo, hi in GENERATIONS:
        if (lo is None or birth_year >= lo) and (hi is None or birth_year <= hi):
            return name
    raise ValueError(birth_year)
