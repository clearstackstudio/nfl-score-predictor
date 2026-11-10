# NFL publish threshold — do bigger edges actually win more? — PREREGISTRATION

**Written:** 2026-10-23, BEFORE any threshold results were computed.
**Approved to run:** 2026-10-23 (Bryant, as part of the full test package).
**Trigger:** the live 2026 NFL spread-play record is 15-25-2 (38%) through
Week 7. The live generator (`src/weekly_picks.py:438`) publishes a spread
play at |spread_edge| ≥ 0.5 — nearly every disagreement becomes a play, so
the play record ≈ the model's raw record. This test asks whether the
*historical* record justifies publishing fewer, larger-edge plays.

## Hypothesis (one, frozen)

On walk-forward predictions from the LIVE EPA model, ATS win% on
published spread plays rises with the publish threshold τ: at some
τ > 0.5, historical plays clear the -110 breakeven (52.4%) with a
usable volume of plays.

## Data

- Walk-forward rows under the LIVE EPA config (damped turnovers,
  half-life 8), 2021–2025, generated with the QB-recency harness pattern
  (`research/qb_recency/run_qb_recency.py`); per-game rows must first
  pass the baseline gate below.
- Closing lines: 2021–2024 from the repo line store (spreadspoke via
  `backtest.closing_home_spread`); 2025 from
  `data/schedules_games.parquet` (`spread_line`) — the ratified source
  from the 2026-10-19 addendum.
- 2026 excluded entirely (in-progress; it motivated the test and may not
  tune it).
- Splits: discovery 2021–2023, validation 2024–2025. A threshold is
  judged on validation; discovery is the consistency check.

## Baseline gate (stop rule)

`src/epa_ratings.run_backtest()` as-is must return ATS 47.29%
(393-438-29), margin RMSE 14.131, n = 1,107 (2021–2024), tolerances
|ΔATS%| ≤ 0.15 pp, |ΔRMSE| ≤ 0.02. On mismatch: STOP, report, no
re-pinning without a dated addendum approved by Bryant.

## Procedure (frozen)

- Candidate thresholds τ ∈ {0.5 (current), 1.5, 2.5, 3.5, 4.5, 5.5}
  points of |spread_edge|. No other values may be tried.
- For each τ, per split: plays n, ATS W-L-P, ATS win% (pushes excluded),
  and flat-bet ROI at -110.
- Report the full table — every τ, both splits — not just the winner.

## Decision rule

A threshold τ* earns an **ADOPT recommendation** iff ALL hold on
VALIDATION (2024–2025): (1) ATS win% ≥ 52.4%; (2) n ≥ 100 plays;
(3) the same τ* shows ATS win% ≥ 51.5% on DISCOVERY (2021–2023).
Otherwise **KILL** (the current 0.5 threshold stands, and the live
record is what it is: variance on a no-edge model).
An ADOPT verdict changes nothing live — publishing rules change only
on Bryant's separate approval, and the parlay construction (which reads
current picks) must be re-checked against any new threshold before it
ships.

## Anti-data-mining clause

One model (live EPA walk-forward), one play definition (side = sign of
edge, as the generator does), the six frozen τ values, two frozen
splits. No cover-probability thresholds, no totals analysis (different
question), no per-season τ shopping. A different rule is a new
preregistration.

## Honest prior

Low-to-moderate. In the 45-season Elo backtest the model's ATS hovers
at ~47-50% overall; if edge size carried real information, M1's and the
disagreement watch's early reads would likely have hinted at it. But
the play-basis question has never been put to the EPA walk-forward
directly, and the current 0.5 threshold was never itself validated —
it is a default, not a finding. Cost: $0.
