# Boomermeter: context for coding sessions

Read this first. It records decisions already made so they don't get relitigated, and what's verified vs. assumed.

## What this is

A public website (GitHub Pages) tracking the handoff of US wealth and political power from the Baby Boom
generation (born 1946–1964). The centerpiece is a meter: the share of the peak Boomer population (78.8M in 1999)
that is gone. Faint landmark markers on the meter link to detail sections. Posting to X comes later and is **out of
scope** until the site is robust.

## Decisions (settled with the owner, Malcolm; don't reopen without cause)

- **US only.**
- **The framing is a countdown, deliberately.** The owner chose it knowing it's provocative. The edge lives in the
  words; the numbers must survive a hostile economist's read. Don't soften the framing; do keep every number
  defensible.
- **Meter denominator = peak living cohort** (78.8M, 1999, Census P25-1141), so the meter only moves one way.
- **Meter = a clean line/edge at today's value.** Landmarks are low-opacity markers on the meter. Each landmark's
  detail section shows a **band** (upper/lower projections), never a single line.
- **Every non-measured number is labeled "est." or "projection" and carries a range.** Ranges are printed on the page,
  not only in footnotes.
- **Population counts are rounded to 3 significant figures.** Never show a headcount to the individual.
- **Shares: y-axis starts at zero.**
- **Congress median age is a core metric.** The finding "the N oldest Congresses in history are the N most recent"
  is computed live (N was 12 as of Sept 2026).
- **Host-agnostic Python.** It runs on GitHub Actions daily. The owner may move it to a Raspberry Pi later; keep it
  runnable with `python -m bm.run` and no cloud-specific code outside `.github/`.
- **Site structure (Sept 2026):** the home page is the meter plus landmarks plus an "explore" grid; each topic has its
  own page (population, wealth, power, housing, work, college, taxes, sources, methods). Topic pages compare
  generations **at the same age** (window = years a generation's birth years turned that age; value = mean over the
  window; range = min–max year), with an age picker (25/30/35/40). This is the house device for "then vs now".
- **Numbers that cut against the framing stay on the page.** E.g. the mortgage *payment* share at 30 was higher for
  Boomers (1980s rates) and the typical worker's real wage at 30 is higher for Millennials. The pages say so and
  point to the measures where the squeeze is real (price-to-income, down payment, labor/profit shares, tuition).
- **Published estimates, not our own, where no official statistic exists** (e.g. billionaire tax rates):
  `registry/literature.yaml`, each with what it measures and the critique beside it.
- **Build order from the original brief:** ledger + registry → fetch layer → Tier 1 metrics → house style → (later)
  compose/queue/batch review → X posting last.

## Layout

```
bm/config.py          paths, generation definitions, BM_TODAY / BM_DATA_DIR / BM_SITE_DIR overrides
bm/snapshot.py        immutable dated snapshots + sha256 manifest (never overwrite)
bm/ledger.py          append-only record of every displayed number; auto-logs corrections
bm/registry.py        loads/validates registry/metrics.yaml (every metric must be registered)
bm/landmarks.py       multi-window trend crossings -> central date + range
bm/sources/*.py       congress-legislators, Census PEP + projections, Fed DFA, FRED, NCES, IRS SOI
bm/metrics/*.py       headcount (meter), congress, wealth, history (generations at the same age)
bm/site/              static site builder (build.py pages, topics.py topic pages), SVG charts, CSS, JS
bm/probe.py           prints what sources return; run on GitHub runners by .github/workflows/probe.yml
registry/literature.yaml  published estimates shown on the taxes page
bm/run.py             orchestrator; each source isolated; failures -> run_status.json
METHODS.md            rendered to methods.html; keep in sync with code
tests/                pytest; tests/synthetic.py makes fake files in the expected layouts
data/                 committed by the workflow: snapshots, ledger.jsonl, corrections.jsonl, state/
```

Local preview with fake Census/Fed data (the page shows a PREVIEW banner):
`BM_DATA_DIR=/tmp/d BM_SITE_DIR=/tmp/s python -m bm.run --demo`

**Cloud sessions can't reach the data hosts** (census.gov, federalreserve.gov, FRED, BLS, NCES, IRS are blocked by the
session's network policy). Work around it with the probe workflow: it runs on every push to a `claude/**` branch and
prints what sources return (`PROBE_ARGS` in `.github/workflows/probe.yml`: `--history` for the history indicators on
live data, a FRED id, or a spreadsheet URL for every row). Read the job log with the GitHub tools. To preview real
data locally, copy `data/` to a temp dir and run `bm.run` against it: failed fetches fall back to saved state.

## Verified vs. assumed (as of the first build, Sept 25, 2026)

Verified against real data:
- **Congress:** fully end to end on the live congress-legislators files. Sanity checks: 433 House + 100 Senate
  seated; historical samples hold about 435 + 100 once filtered.
- **Cross-checked against Pew** (start of the 119th Congress, Jan 2025):
    - House median 57.5 (Pew 57.5). Boomers 169, Gen X 181, Millennials 66 (Pew 170 / 180 / 66).
    - Senate median 64.66 on Jan 6 with 99 seated (Pew 64.7).
    - The Senate median jumps between about 64.7 and 65.4 depending on who's seated that day. That's a real
      property of a 100-member median, not a bug.

Written against file layouts that could **not** be downloaded in the build environment. Check these on the first
Actions run:
- **Census ALLDATA** `nc-est{V}-alldata-r-file{NN}.csv`: columns UNIVERSE, MONTH, YEAR, AGE, TOT_POP (AGE 999 = total)
  confirmed on all 14 V2025 files and 12 V2024 files (Sept 25 runs). April 2020 is coded MONTH 4.1 (census) / 4.2
  (estimates base); the parser skips those, so the monthly series starts May 2020. Boomer headcount July 1, 2024 =
  67.8M (Pew: "about 67 million"); July 1, 2025 = 66.6M.
- **Census projections** `np2023_d1_{mid,low,hi}.csv`: parsed cleanly on the Sept 25 run. Assumed columns NATIVITY/ORIGIN/RACE/SEX (0 = total), YEAR,
  POP_0…POP_100.
- **Fed DFA** `dfa.zip` → `dfa-generation-levels.csv`: parsed cleanly on the first run (Boomer net worth share 52.5%,
  2026 Q2; still to compare with the Fed's web page). Assumed columns Date ("2026:Q2"), Category (one containing
  "boom"), "Net worth", "Real estate", "Corporate equities and mutual fund shares". The parser matches loosely and
  fails with the actual column list if it can't.
- Both census.gov and federalreserve.gov accept requests from GitHub runners (confirmed on the first run).

Verified on GitHub runners via the probe (Sept 25, 2026):
- **FRED** `fredgraph.csv?id=` works without a key; header is `observation_date,<ID>`; missing values are `.`.
  All series in `history.FRED_SERIES` return data (1913–2026 depending on series).
- **NCES table 330.10** (Digest 2024 edition): public 4-year in-state tuition and fees = the column after the
  "Tuition and required fees" header's first column, in the "Public institutions" section. d24 cells are strings like
  "$1,248"; d23 were numbers. 1964–67 are missing in the source.
- **IRS SOI table 23** (`histab23.xls`): highest-bracket rate in column 6 with footnote markers like "[19] 91.0";
  the table ends in 2018 (37%). Later years are a labeled statutory carry-forward.
- **Census HVS table 19** (homeownership by age) exists at `hvs/data/histtab19.xlsx` but starts in 1994; not used yet.

Checks after the first real run:
- Boomer headcount for July 1, 2024 should be close to Pew's "about 67 million" (same convention).
- Boomer share of net worth should match the Fed's DFA web page for the latest quarter.
- Look at the site: meter position, landmark placement, no label collisions at phone width.

## Known next steps

1. Wealth at the same age from the Fed DFA (already fetched): each generation's share of net worth when it averaged
   about 35 (Boomers 1989–90 vs Millennials now), with real dollars. The strongest wealth comparison we can make.
2. Replace the 78.8M peak constant with a value computed from Census 1990s intercensal single-year-of-age files
   using the same convention (keep the constant as a cross-check).
3. Remaining Tier 1: homeownership rate by age (Census HVS table 19, 1994+; earlier years need another source),
   labor force participation 65+ (BLS).
3b. College net price (College Board Trends in College Pricing) next to the sticker-price series; statutory
   corporate rate history next to the effective rate.
4. Tier 2: Boomer share of voters vs. share of adults (CPS Voting Supplement), median age of committee chairs.
5. Later: X snapshot images (matplotlib house style with a source footer in the image), batch review queue.

## Working with the owner

- Be direct; push back when reasoning is flawed.
- He doesn't want to maintain docs or adopt check-in routines. Keep this file, METHODS.md and the registry current
  yourself as part of every change.
- Failures should reach him on their own: the workflow fails when a source fails, and GitHub emails him.
