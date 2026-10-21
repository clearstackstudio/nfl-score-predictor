# NHL rest-effect add-on test — PREREGISTRATION

Frozen 2026-10-20, BEFORE any rest-model computation touches validation
outcomes. Bryant approved the run 2026-10-20 ("Run the rest-effect test
first"). This test was pre-registered as an add-on in the frozen v1 spec
(`~/workspace/goals/honest-line-nhl-prediction-model/files/nhl-build-scope.md`:
"Rest is a test, not an assumption… it ships only if it clears the bar").
This document freezes the exact design. Any deviation voids the test.

## Frozen v1 baseline (unchanged, from backtest-2026-10-20.md)

- Ratings: MoneyPuck xGF/xGA, 20-game half-life, 0.5 prior-season
  carryover, single-step opponent adjustment (`src/nhl/ratings.py`).
- Expected goals: λ_home = lam_h0 + home-ice, λ_away = lam_a, where
  lam_h0/lam_a are the frozen walk-forward outputs stored in
  `data/nhl/backtest_predictions.parquet` (expected_goals clip
  [0.5, 6.5] already applied before home-ice) and home-ice = +0.20
  goals (fitted on discovery).
- Win probability: Poisson goal matrix with OT/shootout resolution
  (`src/nhl/ratings.py::win_prob`), raw pipeline (no calibration map)
  for all comparisons in this test — like-for-like with the published
  raw validation numbers.
- Validation baselines (2023-24 → 2025-26, n = 3,935): moneyline Brier
  raw **0.2401**, totals RMSE **2.327**. Discovery (2019-20 → 2022-23,
  n = 4,573): Brier raw 0.2356. All three reproduced exactly from the
  frozen parquet before this document was written.

## Feature (frozen)

For each regular-season game, from `data/nhl/team_games.parquet`
(regular season only, as built by `src/nhl/data_prep.py`):

- rest_days(team) = calendar days between the game's date and that
  team's previous regular-season game date **within the same season**.
  A team's first game of a season counts as rest_days = 3.
- d = rest_days(home) − rest_days(away), capped to [−3, +3].

## Term (frozen)

- λ_home' = λ_home + β·d
- λ_away' = λ_away − β·d
- Both λ floored at 0.5 after adjustment. Nothing else changes: same
  ratings, same home-ice +0.20, same Poisson matrix, same OT/shootout
  resolution. Predicted total = λ_home' + λ_away'.

## Fit (discovery only, frozen)

- β chosen on DISCOVERY ONLY (seasons 2019-20 → 2022-23) by grid search
  β ∈ [−0.10, +0.10] goals per rest day, in 0.01 steps (21 values),
  minimizing discovery moneyline Brier (raw pipeline).

## Judge (validation, frozen)

Validation = seasons 2023-24 → 2025-26 (n = 3,935), raw pipeline,
like-for-like against frozen v1.

**ADOPT requires BOTH:**
- (a) Validation moneyline Brier of the rest model < 0.2401 (v1's).
- (b) The paired-bootstrap 95% CI on the per-game Brier difference
  (v1 − rest model) excludes 0. Bootstrap: 10,000 resamples of the
  3,935 validation games with replacement, percentile CI, seed 20261020.

**Secondary guardrail:** validation totals RMSE of the rest model must
not worsen by more than 0.01 vs v1's 2.327 (i.e., must be ≤ 2.337).

**Anything else = KILL.** Model unchanged. SU accuracy is reported for
both models (raw pipeline) as context only — it is not part of the bar.

## Scope limits (frozen)

- Research code only, under `research/nhl_rest/`, reusing `src/nhl`
  read-only. No change to production model behavior regardless of
  verdict — adoption, if the bar clears, is Bryant's separate decision.
- No site changes, no methodology edits, no daily-picks changes.
