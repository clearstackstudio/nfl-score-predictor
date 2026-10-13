# M1 — Explicit momentum / win-streak term for the NFL model — PREREGISTRATION

**Written:** 2026-10-12 ~16:45 PT, BEFORE any streak results were computed.
**Trigger:** Bryant asked (2026-10-12, main chat) whether the model can predict
team momentum (win/lose streaks). The main-chat answer said the 2026-10-10
pattern study tested hot/cold streaks across ~100,000 games. Audit of that
study shows the only streak test actually run was NBA *totals* hotness
(trailing-5 offensive EMA vs over-pick loss rate, basketball/findings.md P3 —
flat/null). No NFL, CFB, or MLB test of W/L streaks as a margin/ATS/SU signal
exists in `hidden_files/pattern_study/{nfl,cfb,mlb}/findings.md` (zero mentions).
This test closes that gap properly instead of relying on the generalization.

## Question
Does an explicit win/loss streak term add predictive value to the live NFL
model — i.e., is there momentum signal NOT already captured by the
walk-forward ratings (which update after every game, weighted by opponent
and margin)?

## Data
`~/workspace/goals/ultimate-multi-sport-prediction-model/hidden_files/pattern_study/nfl/nfl_walkforward_1980_2024.csv`
— 11,352 games, 1980–2024, with pre-game walk-forward `our_margin`,
`actual_margin`, `margin_resid`, closing lines and ATS results.

## Features (computed strictly from PRIOR games, chronological per franchise)
- `streak` per team entering the game: +n for n consecutive wins, −n for n
  consecutive losses; a tie (actual_margin = 0) resets to 0. Season boundaries
  do NOT reset (offseason gap noted as a limitation; a within-season variant
  is descriptive only).
- PRIMARY feature: `streak_diff = home_streak − away_streak`.
- SECONDARY (descriptive only, no verdict power): last-3 win% differential.

## Splits (same as the |edge|≥5 retest)
- Discovery: 1980–2014. Validation: 2015–2024 (verdict sample).

## Primary test
Regress `margin_resid` (= actual − our_margin) on `streak_diff`.
If momentum exists beyond the ratings, the slope is positive: the model
systematically under-rates streaking teams.

- Fit slope `b` on DISCOVERY only.
- KEEP the idea (recommend a live-model streak term for Bryant's approval)
  iff BOTH hold on VALIDATION:
  1. slope of margin_resid on streak_diff > 0 with z ≥ 1.96, AND
  2. applying the discovery-fitted adjustment (our_margin + b·streak_diff)
     reduces validation margin RMSE vs the unadjusted model.
- Otherwise KILL — permanently, like the other pattern-study nulls.
- No tuning: no alternate streak definitions, windows, or thresholds get a
  second shot at the verdict. Last-3 win% is reported descriptively only.

## Secondary descriptive outputs (no verdict power)
- ATS win% on model picks (|spread_edge| ≥ 1.5) split by whether streak_diff
  agrees or disagrees with the pick side.
- Straight-up: how often the streak-favored team wins vs the model-favored team.

## What this test cannot show
A null here means streaks add nothing ON TOP OF ratings that already update
every game — not that "form doesn't matter." A positive would still need a
separate live-model implementation test before anything ships (Bryant
approves all live model changes).
