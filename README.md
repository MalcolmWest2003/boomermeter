# Boomermeter

Tracking the handoff of US wealth and political power from the Baby Boom generation, with every number sourced and
every estimate labeled.

**Site:** https://malcolmwest2003.github.io/boomermeter/

## What it tracks

- **The meter:** share of the peak Boomer population (78.8 million, 1999) that is no longer living in the US.
  Census estimates, with a range.
- **Wealth:** Boomer-headed households' share of US net worth, stocks and real estate (Federal Reserve DFA).
- **Congress:** median age by chamber, generational makeup, and the median age of every Congress since 1789.
- **Landmarks:** projected dates with ranges for Boomers falling under half of household wealth, under a third of
  Congress, and half the peak population gone.

See [METHODS.md](METHODS.md) for how every number is produced.

## How it runs

A GitHub Actions workflow runs daily. It fetches each source, snapshots the raw files (never overwriting), appends
any changed number to an append-only ledger, rebuilds the static site and publishes it to GitHub Pages. Snapshots,
the ledger, and the corrections log are committed to `data/`.

```
pip install -r requirements.txt
python -m pytest -q
python -m bm.run            # real run (needs internet)
python -m bm.run --demo     # layout preview with synthetic Census/Fed data
```

Data sources: U.S. Census Bureau (Population Estimates Program; 2023 National Population Projections), Federal
Reserve Board (Distributional Financial Accounts), and
[unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators).
