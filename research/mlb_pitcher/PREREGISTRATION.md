# MLB starting-pitcher layer — can it beat team-only? — PREREGISTRATION

**Written:** 2026-10-23, BEFORE any pitcher-layer results were computed.
**Approved to run:** 2026-10-23 (Bryant, full test package, off-season).
**Background:** `src/mlb/pitcher.py` is a DESIGN-ONLY module: the
historical odds file has no pitcher column, so the shipped backtest
(22,765 games; moneyline ROI -2.5%, totals ROI -2.7%, Brier 0.2444 vs
the line's 0.2402) is deliberately team-level. This test builds the
missing historical dataset and gives the design its first honest trial.

## Hypothesis (one, frozen)

Adding the pitcher adjustment from `pitcher.py` — prior-season
FIP-based `ra9_vs_avg`, workload-regressed, blended at
STARTER_SHARE = 0.6 — to the team-level model improves out-of-sample
win-probability accuracy (Brier) and margin RMSE on the same games.

## Data (leakage discipline is the whole game here)

- Games + closing lines: the repo's existing MLB backtest universe
  (`src/mlb/backtest.py`, `data/mlb/scores_2022_2026.csv` + its odds
  source). Sample: seasons **2023–2026** (2022 is the ratings burn-in
  and the source of prior-season pitcher stats for 2023).
- Probable starters per game: MLB Stats API (free, no key),
  `schedule?sportId=1&date=...&hydrate=probablePitcher`, cached to
  disk under this research dir. If probable-pitcher coverage for a
  season is < 90% of games, that season is dropped and the gap
  reported — no partial-season verdicts.
- Pitcher quality: **prior-season FIP only** (fallback prior-season
  ERA when FIP unavailable), regressed toward league average by
  `IP / (IP + 50)` per the design doc. Prior-season stats are fully
  known before Opening Day — no within-season information, no
  lookahead. Pitchers with no prior-season MLB record get
  `ra9_vs_avg = 0` (league average), per the design's fallback rule.
- STARTER_SHARE frozen at 0.6 (the design's starting point). It is
  NOT fitted on the verdict sample. (A share fitted on 2023–2024 and
  frozen for 2025–2026 may be reported as a secondary descriptive
  line — no verdict power.)

## Splits

- All four seasons are walk-forward for the TEAM model (ratings update
  game by game as in the shipped backtest). The pitcher layer has no
  fitted parameters on this sample (share frozen, quality from prior
  seasons), so the full 2023–2026 sample is the verdict sample;
  per-season results are reported individually as the guardrail.

## Decision rule

**ADOPT recommendation** iff ALL hold: (1) Brier improves vs.
team-only on the same games, paired bootstrap 95% CI entirely below 0
(10,000 game resamples, seed 20261023); (2) margin RMSE does not
worsen (Δ ≤ 0); (3) Brier does not worsen in more than one of the
four seasons individually. Otherwise **KILL** — the design stays a
design, and the live Feb/Mar 2027 build proceeds team-only (or the
verdict is DEFERRED with the exact data gap named, if coverage fails).
Moneyline/totals ROI at closing prices reported descriptively only —
the backtest's lesson (-2.5% ROI at a *worse* Brier than the line) is
that ROI on this sample is not the bar; calibrated accuracy is.
An ADOPT changes nothing live: the pitcher layer ships only inside
the 2027 live build, on Bryant's separate approval.

## Anti-data-mining clause

One quality metric (prior-season FIP), one regression constant (50
IP), one share (0.6), one fallback (league average). No ERA-vs-FIP
shopping on the verdict sample, no per-season shares, no bullpen
term, no lineup/platoon terms. Variants are new preregistrations.

## Honest prior

Moderate — the most favorable of this package. Starting pitching is
the largest single-game factor the team model ignores, the market
moves visibly on pitching announcements, and the design was written
before seeing any of these results. The risk is measurement: if
probable-pitcher history is patchy, the honest answer is DEFERRED,
not a forced verdict. Cost: $0 (Stats API is free); runtime is
API-bound — cache everything.
