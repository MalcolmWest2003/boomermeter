import datetime as dt
import json

import pytest

from bm import config, landmarks, ledger, stats
from bm.metrics import headcount as hc
from bm.sources import census, congress, fed_dfa
from tests import synthetic


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "SNAPSHOTS", tmp_path / "snapshots")
    monkeypatch.setattr(config, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(config, "CORRECTIONS", tmp_path / "corrections.jsonl")
    monkeypatch.setattr(config, "RECONCILIATION", tmp_path / "reconciliation.jsonl")
    monkeypatch.setattr(config, "STATE", tmp_path / "state")


# --- rounding: never a headcount to the individual
def test_fmt_millions_three_sig_figs():
    assert stats.fmt_millions(68_412_337) == "68.4 million"
    assert stats.fmt_millions(6_234_000) == "6.23 million"
    assert stats.fmt_millions(123_456_789) == "123 million"


def test_median():
    assert stats.median([3, 1, 2]) == 2
    assert stats.median([4, 1, 2, 3]) == 2.5


# --- cohort convention
def test_cohort_july_is_ages_y_minus_1964_to_y_minus_1946():
    ages = {a: 1.0 for a in range(101)}
    ages[60], ages[80] = 100.0, 1000.0  # 2025: ages 61..79 should be in, 60 and 80 out
    assert hc.cohort_on(ages, 2025, 7) == 19.0


def test_cohort_january_splits_edge_ages():
    ages = {a: 0.0 for a in range(101)}
    ages[61], ages[80] = 12.0, 12.0
    # Jan 2026: y_ref=2025, f=0.5 -> half of age 61 and half of age 80
    assert hc.cohort_on(ages, 2026, 1) == pytest.approx(12.0)


def test_band_uses_worst_miss_at_horizon():
    rows = [{"months_ahead": 1, "rel_error": 0.001}, {"months_ahead": 6, "rel_error": -0.004},
            {"months_ahead": 12, "rel_error": 0.002}]
    assert hc.band_halfwidth(rows, 3)[0] == pytest.approx(0.001)
    assert hc.band_halfwidth(rows, 12)[0] == pytest.approx(0.004)
    assert hc.band_halfwidth(rows, 24)[0] == pytest.approx(0.008)  # scaled beyond checked horizon
    assert hc.band_halfwidth([], 10)[0] == pytest.approx(0.005)


# --- parsers against the layouts we expect
def test_alldata_parser_filters_totals_and_reads_months():
    parsed = census.parse_alldata(synthetic.alldata_csv(2025))
    assert (2026, 12) in parsed and 999 not in parsed[(2025, 7)]
    assert len(parsed[(2025, 7)]) == 101


def test_projection_parser_keeps_only_total_rows():
    parsed = census.parse_projection(synthetic.projection_csv(1.0))
    assert set(parsed) == set(range(2022, 2101))


def test_dfa_parser_and_quarters():
    parsed = fed_dfa.parse_levels(synthetic.dfa_csv())
    assert fed_dfa.boomer_label(parsed["generations"]) == "BabyBoom"
    assert fed_dfa.quarter_end("2026:Q2") == dt.date(2026, 6, 30)
    assert fed_dfa.quarter_end("2025:Q4") == dt.date(2025, 12, 31)


def test_dfa_layout_change_fails_loudly():
    with pytest.raises(ValueError, match="columns are"):
        fed_dfa.parse_levels("Date,Group,Stuff\n2026:Q2,x,1\n")


# --- ledger
def test_ledger_appends_only_on_change_and_logs_corrections():
    e = ledger.Entry("m", 1.0, "1.0%", "measured", "2026-06-30", "percent", sources=[{"sha256": "a"}])
    assert ledger.append(e, dt.date(2026, 9, 1))
    assert not ledger.append(e, dt.date(2026, 9, 2))
    revised = ledger.Entry("m", 1.2, "1.2%", "measured", "2026-06-30", "percent", sources=[{"sha256": "b"}])
    assert ledger.append(revised, dt.date(2026, 12, 15))
    c = ledger.corrections()
    assert len(c) == 1 and c[0]["was"] == "1.0%" and c[0]["now"] == "1.2%"


def test_estimates_require_a_range():
    with pytest.raises(ValueError):
        ledger.Entry("m", 1.0, "1", "interpolated", "2026-01-01", "x")


# --- landmarks
def test_trend_crossing_range_brackets_central():
    pts = [(2000 + i, 60 - 2 * i + (0.5 if i % 2 else -0.5)) for i in range(10)]
    r = landmarks.trend_crossing(pts, 33.3, "below", [3, 4, 5, 6], 5, dt.date(2010, 1, 1))
    assert r["status"] == "projected"
    assert r["low"] <= r["central"] <= r["high"]


def test_trend_crossing_detects_already_passed():
    pts = [(2000, 55.0), (2001, 52.0), (2002, 49.0)]
    r = landmarks.trend_crossing(pts, 50, "below", [3], 3, dt.date(2003, 1, 1))
    assert r["status"] == "passed" and r["central"].startswith("2001")


# --- congress
def test_congress_starts():
    starts = dict(congress.congress_starts(dt.date(2026, 1, 1)))
    assert starts[1] == dt.date(1789, 3, 4)
    assert starts[73] == dt.date(1933, 3, 4)
    assert starts[74] == dt.date(1935, 1, 3)
    assert starts[119] == dt.date(2025, 1, 3)


def test_territorial_delegate_excluded_before_statehood():
    t = congress.Term("rep", dt.date(1955, 1, 3), dt.date(1957, 1, 3), "AK", "0")
    assert not congress.is_voting(t, dt.date(1956, 1, 1))
    t2 = congress.Term("rep", dt.date(1961, 1, 3), dt.date(1963, 1, 3), "AK", "0")
    assert congress.is_voting(t2, dt.date(1962, 1, 1))


def test_duplicate_seat_keeps_later_holder():
    old = congress.Member("A", "Old", dt.date(1900, 1, 1),
                          [congress.Term("rep", dt.date(1933, 3, 4), dt.date(1935, 1, 3), "AL", "8")], False)
    new = congress.Member("B", "New", dt.date(1910, 1, 1),
                          [congress.Term("rep", dt.date(1933, 11, 1), dt.date(1935, 1, 3), "AL", "8")], False)
    rows = congress.serving_on([old, new], dt.date(1934, 3, 4))
    assert [m.bioguide for m, _ in rows] == ["B"]


# --- snapshots are immutable and deduplicated
def test_snapshot_dedup(tmp_path):
    from bm import snapshot
    a = snapshot.record("s", "f.csv", "u", b"abc", dt.date(2026, 1, 1))
    b = snapshot.record("s", "f.csv", "u", b"abc", dt.date(2026, 1, 2))
    assert a.sha256 == b.sha256 and b.stored_path == a.stored_path
    lines = (config.SNAPSHOTS / "s" / "manifest.jsonl").read_text().splitlines()
    assert len(lines) == 1
    snapshot.record("s", "f.csv", "u", b"abcd", dt.date(2026, 1, 3))
    assert len((config.SNAPSHOTS / "s" / "manifest.jsonl").read_text().splitlines()) == 2
