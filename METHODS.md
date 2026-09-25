# Methods

This page explains where every number on Boomermeter comes from, what we do to it, and how sure we are. If a number
on the site can't be traced back through this page, the public ledger and the source files, that's a bug. Please
report it.

[TOC]

## Ground rules

- **US only.** "Baby Boomer" is an American cohort, and every source here is American.
- **Boomers = born 1946–1964.** Other generations follow Pew Research Center: Silent and earlier (≤1945), Gen X
  (1965–1980), Millennials (1981–1996), Gen Z (1997+).
- **Three kinds of number, always labeled:**
    - *Measured*: read directly from a source release (a Fed quarter, a member's birthdate).
    - *Estimate* (**est.**): computed between or after source releases. Always shown with a range.
    - *Projection*: a date or value in the future. Always shown with a range, and in charts as a shaded band.
- **No false precision.** Population counts are rounded to three significant figures. We never show a headcount to
  the individual person.
- **Shares start at zero.** Every chart of a percentage has a y-axis starting at 0%.
- **Everything is kept.** Each source file is snapshotted with its SHA-256 fingerprint on the day we fetched it. Each
  number the site displays is written to an append-only ledger with its source, vintage, method and date. Both live
  in the public repository.

## The meter: share of the peak Boomer population gone

**What it shows:** 1 − (living Boomers in the US today ÷ living Boomers in the US at the 1999 peak).

**The 100% mark** is 78.8 million: the Census Bureau's count of Boomers living in the US in 1999, the most there
have ever been (Census report P25-1141; Pew Research Center cites the same figure). The peak is higher than the
76 million babies born 1946–1964 because immigrants of the same ages joined the cohort. We use the peak rather than
the birth count so the meter only ever moves one way.

**"Gone" means no longer living in the US.** That is mostly deaths, but it also includes Boomers who emigrate. We don't
separate them, and the meter shouldn't be read as a death count.

**Who counts on a given day.** Census counts people by age on July 1. Following Census and Pew, "Boomers in year Y" is
everyone aged Y−1964 through Y−1946 on July 1. That's a fixed group of people, born from roughly mid-1945 to
mid-1964: the same convention the 1999 peak was counted with, so the top and bottom of the fraction match. For
dates other than July 1, the group straddles one extra year of age; we split the two edge ages by how much of the
year has passed since July 1.

**Today's estimate.**

1. Census publishes monthly population estimates by single year of age once a year (the *vintage*). Each vintage's
   file also includes Census's own short-term projections for the following months. Where that file covers today,
   we use it, interpolated to today's date.
2. After Census's last published month, we carry the number forward at the average rate of decline over Census's
   last 12 months.

**The range.** We measure how wrong Census's previous vintage was. For every month after its last July 1, we
compare what the previous vintage said with what the newer vintage now estimates for that same month. The range on
today's number is the worst miss the previous vintage made at the same distance ahead or less. If today is further
ahead than any month we can check, the worst miss is scaled up in proportion. If no comparison is possible, we fall
back to ±0.05% per month past the last July 1 and say so.

**Reconciliation.** When a new Census vintage lands, we compare the number we showed for its July 1 with what Census
now says, and log the difference publicly. A difference over 0.5% becomes a correction on the front page.

**Years under the meter** show where Census's 2023 projections put the meter in each future year. The projections
are scaled so their value matches the latest Census estimate.

## Landmarks

Landmarks are projected dates. On the meter they are faint markers placed where the meter is projected to be on that
date. Each has its own section with the chart it comes from and its range.

| Landmark | Series | How the date is projected | How the range is set |
|---|---|---|---|
| Half the peak gone | Living Boomers | Census 2023 National Population Projections (middle series), scaled to the latest estimate | Census's low- and high-immigration series |
| Boomers under half of household wealth | Fed DFA, quarterly | Straight-line trend over the last 5 years | Earliest and latest crossing using trends fitted over the last 3, 4, 5, 6 and 7 years |
| Boomers under a third of Congress | Boomer share of seats | Straight-line trend over the last 5 measurements (one per Congress since the share peaked, plus today) | Earliest and latest crossing using the last 3–6 measurements |

The trend-based ranges show how much the answer depends on how far back you look. They are not statistical
confidence intervals, and they can't anticipate a crash, a boom or a wave election. The Census-based range covers
immigration assumptions only. Mortality surprises, which matter more for people in their 60s–80s, are not in it.

When some of the fitted trends never reach the threshold (for example because the share has recently been flat or
rising), the range has no upper end, and the page says so ("2028 or later; 2 of 5 trends never get there") rather than
printing the latest finite crossing as if it bounded the answer.

## Wealth

**Source:** Federal Reserve Board, Distributional Financial Accounts (DFA), file `dfa-generation-levels.csv` in
`dfa.zip`, updated quarterly about 11 weeks after each quarter ends.

**Share** = Boomer-generation dollar level ÷ sum of all generations' levels, for that quarter.

What to know:

- **Households are assigned by the generation of the household head.** If a Millennial lives in a home headed by a
  Boomer parent, that household's wealth counts as Boomer wealth. That pushes Boomer shares up somewhat.
- **Net worth** is assets minus liabilities.
- **Stocks & mutual funds** is the DFA's "corporate equities and mutual fund shares": what households hold directly.
  Stocks held through pensions and retirement plans are in a separate DFA category and are not included here.
- **Real estate** is market value, before mortgages. It measures who owns the homes' value, not who owns the equity.
- **Revisions.** The Fed revises back data every quarter. When a quarter we've already displayed changes, the old and
  new values go on the corrections list.

**At the same age.** Each generation's own share of net worth (and of real estate) when its average member was 35,
meaning the year its middle birth year turned 35: Boomers 1990, Gen X 2007.5, Millennials 2023.5. The figure is the
mean of the quarterly shares within two years either side, and the range is the lowest and highest quarter. This
differs from the window method on the other topic pages because the DFA starts in 1989 Q3, when Boomers averaged
about 34; a window average would compare Boomers at older ages than Millennials. Two biases to keep in mind: the
Boomer figure uses only the 10 quarters from 1989 Q3, and head-of-household assignment lowers every young
generation's share (young adults living with parents count in their parents' household), more so recently. Stocks are
left out of this comparison: the DFA's estimates of young households' stock holdings are too noisy in the early
years (Boomer holdings roughly quadruple within a year around 1990).

## Congress

**Source:** [unitedstates/congress-legislators](https://github.com/unitedstates/congress-legislators), a
public-domain dataset of every member of Congress since 1789 with birthdates and terms. We fetch it daily.

- **Voting members only.** Delegates from DC and the territories, and territorial delegates before statehood,
  are excluded using each state's admission date.
- **Median age** is computed from exact birthdates on the date shown.
- **Generations** are assigned by birth year.
- **History (1789 to today)** measures each Congress one year after it began. Before 1935, a new Congress's first
  session often didn't meet until December, so a date closer to the start misses most members.
- **Known data quirks.** A handful of early members have no recorded birthdate; they're left out of the median. The
  dataset doesn't always shorten a term when a member died or resigned, so a seat can briefly show two holders. For
  those seats we keep the member whose term started later.

## The handoff: how far it has gone

**Handed off** = the share of the Boomer *peak* share that other generations now hold:
100 × (peak share − share now) ÷ peak share. 0% means Boomers are at their peak; 100% means they hold nothing.
It is measured for two things:

- **Wealth:** the Boomer share of US household net worth (Fed DFA, quarterly). Peak 2016.
- **Power:** the Boomer share of voting seats in Congress, measured one year into each Congress and today. Peak 2014.

This measures position, not gifts or bequests: a share falls when Boomers pass wealth on, but also when other
generations' wealth grows faster. For wealth it moves with the stock market, which Boomers own more of.

**Against earlier generations.** Each bar is compared with earlier generations in two ways:

- *Same average age:* the generation's handed-off share when its middle birth year was the age Boomers' middle
  birth year (1955) is now.
- *Same years after peak:* the same measure the same number of years after that generation's own peak.

For wealth, the only earlier group in the Fed's data is "Silent and earlier" (born before 1946), which includes the
Greatest Generation. The DFA starts in 1989 Q3 and that group's share was highest at the first observation, so its true
peak was at least that high: its handed-off figures are lower bounds ("at least"). Placing that group at the Silent
Generation's middle birth year also flatters it, because the group includes older people. Both biases make the
comparison conservative: the gap they show between Boomers and the generation before is, if anything, understated.

For Congress, generations are: Missionary 1860–1882 and Lost 1883–1900 (Strauss and Howe), Greatest 1901–1927,
Silent 1928–1945 and later (Pew). Values between Congress samples are interpolated linearly.

## Share of the people, share of the wealth

Each Fed DFA generation group's share of household net worth (Q2) next to its share of US residents aged 18 and over
(Census PEP, July 1 of the same year, same cohort convention as the meter), grouped by the Fed's birth years: before
1946, 1946–1964, 1965–1980, 1981 and later. The ratio is wealth share ÷ adult share. "Mean per adult" is the group's
household net worth divided by its adults.

- Wealth is counted by household head and population by person. Adult children living with Boomer parents add to
  Boomer wealth but Millennial population, which raises the Boomer ratio.
- A mean is pulled up by the richest households. It says how much wealth each generation holds per member, not what a
  typical member has.
- We use the latest July that Census has estimated (not its short-term projection), paired with the Fed's Q2.

## Charts by age

Most charts can be shown **by year** or **by age**. In the by-age view each line follows one generation: the value in
the year its middle birth year reached each age (Boomers: 1955 + age). Reading straight up from an age compares
generations at the same point in life. Lines for the topic pages run from 15 to 70; the wealth and Congress charts use
the full range of the data.

## Then and now: generations at the same age

The housing, work, college and taxes pages compare what each generation faced **at the same age**, because a
comparison between "the 1970s" and "today" silently compares people at different points in life.

- **Windows.** For an age A, a generation's window is the calendar years in which its birth years turned A. Boomers
  (born 1946–1964) turned 30 in 1976–1994; Millennials (1981–1996) turn 30 in 2011–2026. The Silent Generation is
  taken as born 1928–1945 (Pew) so its window is closed.
- **The value** for a generation is the average of the indicator over its window; **the range** printed with it is
  the lowest and highest single year in the window. Averaging over the window keeps the comparison from depending on
  which year one picks.
- **Coverage.** A generation needs at least three observed years in its window. Windows that extend past the latest
  data say "so far: N of M years"; windows that start before a series begins say "data for N of M years".
- **Dollars** are converted to the latest full year's prices with the CPI-U (all items, not seasonally adjusted,
  annual average).
- **What these are.** Every indicator is computed directly from published series, so they are labeled measured.
  Several involve stated assumptions (below); those assumptions are on the page next to the chart.

| Indicator | Built from | Assumptions and limits |
|---|---|---|
| Home price ÷ family income | Median sales price of new houses sold (Census/HUD, MSPUS) over median family income (Census CPS, MEFAINUSA646N) | New houses cost more than existing ones; family income because household income starts only in 1984 |
| Down payment in months of income | 20% of the median new-house price over monthly median family income | Pre-tax income with nothing else spent |
| Mortgage payment, % of income | Principal and interest on a 30-year fixed loan at that year's average Freddie Mac PMMS rate, 20% down, median new house | Excludes property tax and insurance; many first-time buyers put down less |
| Mortgage rate, fed funds rate | Freddie Mac PMMS; Federal Reserve | Annual averages |
| Productivity and pay | BLS output per hour and real hourly compensation, nonfarm business (both 1948 = 100); BLS average hourly earnings of production and nonsupervisory workers, CPI-U deflated, spliced to the compensation index at 1964 | The two pay lines bracket the measurement debate: compensation includes benefits and all earners and uses BLS's output deflator; the wage line excludes benefits and supervisors and uses CPI-U |
| Labor's share | BEA compensation of employees, % of gross domestic income | Proprietors' income, part of which is labor income, is excluded |
| Profits' share | BEA corporate profits after tax (without IVA and CCAdj) over GDP | Book profits |
| Real minimum wage | Federal minimum (Department of Labor), CPI-U deflated | Many states and cities set higher minimums |
| Tuition in minimum-wage hours; real tuition | NCES Digest table 330.10, in-state tuition and required fees at public 4-year institutions (newest Digest edition), over the federal minimum wage | Sticker price before grants; the academic year is keyed to the calendar year it starts in |
| Corporate tax take | BEA federal taxes on corporate income over corporate profits before tax | Book profits, all corporations; excludes state taxes |
| Top bracket rate | IRS Statistics of Income historical table 23 | The table ends in 2018; later years carry the 37% statutory rate (P.L. 115-97, made permanent by P.L. 119-21), marked in the source record |

FRED (Federal Reserve Bank of St. Louis) is used as the delivery channel for the BEA, BLS, Census, Freddie Mac, Labor
Department and Federal Reserve series; the original publisher is named on every chart.

**Published estimates.** For questions no official statistic answers, such as the tax rate the richest households
actually pay, we compute nothing ourselves. The taxes page lists the main published estimates, each with exactly what
it measures and, where one exists, the published critique beside it. The list lives in `registry/literature.yaml`
and every figure in it is logged to the ledger like any other number.

## Corrections policy

If a source revises a number we've already shown, or a Census reconciliation moves the headcount by more than 0.5%,
the old and new values are listed on the Sources page under Corrections with the date and reason. Nothing is
quietly replaced; the full history is in the ledger.

## What this page is not

It's not a forecast of any person's life, any election, or any market. The projections extend recent trends and
official Census assumptions so you can see roughly when landmarks arrive. Every one of them will move as new data
comes in, and the page will show when they do.

## Sources

- U.S. Census Bureau, Population Estimates Program, national monthly estimates by single year of age (NC-EST ALLDATA),
  current and prior vintages.
- U.S. Census Bureau, 2023 National Population Projections, projected population by single year of age (np2023_d1),
  middle, low- and high-immigration series.
- U.S. Census Bureau, *The Baby Boom Cohort in the United States: 2012 to 2060* (P25-1141), for the 1999 peak.
- Federal Reserve Board, Distributional Financial Accounts.
- unitedstates/congress-legislators.
- Federal Reserve Bank of St. Louis, FRED, for series from BEA (national accounts), BLS (productivity, compensation,
  earnings, CPI), Census and HUD (new-house prices, family income), Freddie Mac (mortgage rates), the Department of
  Labor (minimum wage) and the Federal Reserve (federal funds rate).
- National Center for Education Statistics, Digest of Education Statistics, table 330.10.
- Internal Revenue Service, Statistics of Income, historical table 23.
- The published studies listed on the taxes page.
