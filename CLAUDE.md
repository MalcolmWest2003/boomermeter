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
- **Build order from the original brief:** ledger + registry → fetch layer → Tier 1 metrics → house style → (later)
  compose/queue/batch review → X posting last.

## Layout

```
bm/config.py          paths, generation definitions, BM_TODAY / BM_DATA_DIR / BM_SITE_DIR overrides
bm/snapshot.py        immutable dated snapshots + sha256 manifest (never overwrite)
bm/ledger.py          append-only record of every displayed number; auto-logs corrections
bm/registry.py        loads/validates registry/metrics.yaml (every metric must be registered)
bm/landmarks.py       multi-window trend crossings -> central date + range
bm/sources/*.py       congress-legislators, Census PEP + projections, Fed DFA
bm/metrics/*.py       headcount (meter), congress, wealth
bm/site/              static site builder, SVG charts, CSS, hover JS
bm/run.py             orchestrator; each source isolated; failures -> run_status.json
METHODS.md            rendered to methods.html; keep in sync with code
tests/                pytest; tests/synthetic.py makes fake files in the expected layouts
data/                 committed by the workflow: snapshots, ledger.jsonl, corrections.jsonl, state/
```

Local preview with fake Census/Fed data (the page shows a PREVIEW banner):
`BM_DATA_DIR=/tmp/d BM_SITE_DIR=/tmp/s python -m bm.run --demo`

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
- **Census ALLDATA** `nc-est{V}-alldata-r-file{NN}.csv`: assumed columns UNIVERSE, MONTH, YEAR, AGE, TOT_POP; AGE 999 =
  total. File names and the 01–14 split came from Census's download page.
- **Census projections** `np2023_d1_{mid,low,hi}.csv`: assumed columns NATIVITY/ORIGIN/RACE/SEX (0 = total), YEAR,
  POP_0…POP_100.
- **Fed DFA** `dfa.zip` → `dfa-generation-levels.csv`: assumed columns Date ("2026:Q2"), Category (one containing
  "boom"), "Net worth", "Real estate", "Corporate equities and mutual fund shares". The parser matches loosely and
  fails with the actual column list if it can't.
- Whether census.gov and federalreserve.gov accept requests from GitHub runners.

Checks after the first real run:
- Boomer headcount for July 1, 2024 should be close to Pew's "about 67 million" (same convention).
- Boomer share of net worth should match the Fed's DFA web page for the latest quarter.
- Look at the site: meter position, landmark placement, no label collisions at phone width.

## Known next steps

1. First real run: fix any layout mismatches above (parsers raise with the real column list).
2. Replace the 78.8M peak constant with a value computed from Census 1990s intercensal single-year-of-age files
   using the same convention (keep the constant as a cross-check).
3. Remaining Tier 1: homeownership rate by age (Census HVS), labor force participation 65+ (BLS).
4. Tier 2: Boomer share of voters vs. share of adults (CPS Voting Supplement), median age of committee chairs.
5. Later: X snapshot images (matplotlib house style with a source footer in the image), batch review queue.

## Working with the owner

- Be direct; push back when reasoning is flawed.
- He doesn't want to maintain docs or adopt check-in routines. Keep this file, METHODS.md and the registry current
  yourself as part of every change.
- Failures should reach him on their own: the workflow fails when a source fails, and GitHub emails him.
