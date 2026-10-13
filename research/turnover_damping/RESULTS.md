# Turnover-EPA damping — walk-forward test of the pre-registered arms

**Date:** 2026-10-12 · **Approved by:** Bryant (measurement only; no live code/data changed)
**Pre-registration:** `goals/ultimate-multi-sport-prediction-model/hidden_files/turnover-damping-preregistration.md` (written before any run)
**Interpreter:** `.venv-cfb/bin/python` — **Artifacts:** `run_turnover_damping.py` (runner), `metrics.json`, `per_game_w1.00.csv`, `per_game_w0.50.csv`, `per_game_w0.25.csv`, `per_game_robustness_w0.50_qb.csv`, `run.log` / `run2.log`. No git commit/push.

## Verdict (up front)

**No arm clears the pre-registered adoption bar, so the recommendation is: keep the model as-is.** The bar required all three of (1) overall margin RMSE improves ≥ 0.05, (2) margin RMSE improves or ties in ≥ 3 of 4 seasons, (3) overall ATS does not worsen. Both damped arms pass (1) and (2) decisively — and fail (3): overall ATS slips from 47.50% to 46.92% (w = 0.50) and 46.43% (w = 0.25). The ATS slippage is small and well within sampling noise (SE ≈ 1.7pp), but the bar was written as a point-estimate rule before the run, so it is applied as written. What follows is the full split result so the tension is visible rather than buried:

- **Forecast accuracy improves, monotonically in damping strength.** Margin RMSE: 14.44 (w = 1.00) → 14.14 (w = 0.50) → 14.09 (w = 0.25), better in **all four seasons** at both damped weights. Total RMSE improves too (15.17 → 14.94 → 14.88), and OU% is flat-to-slightly-better.
- **Pick quality at the published threshold does not.** ATS and straight-up% both drift *down* as damping increases (SU 62.6% → 61.8% → 60.9%), and fewer picks qualify (866 → 856 → 828 ATS picks) because damped ratings sit closer together.
- **The luck premise is confirmed in our own data** (descriptives below): turnover plays are only 1.9% of plays but 9.3% of all absolute EPA, the spread of team turnover EPA is large (±2.4 EPA/game SD), and its season-to-season persistence is essentially zero (mean consecutive-season r ≈ +0.08 for net turnover EPA per game; −0.14 for giveaways, +0.10 for takeaways).

Interpretation caution (applies to the RMSE gains): monotone RMSE improvement accompanied by declining SU/ATS is also the signature of *generic shrinkage* — pulling the noisiest rating component toward zero reduces squared error whether or not that component is pure luck. This test, as pre-registered, does not include a placebo arm (damping a matched non-turnover component), so it cannot fully separate "turnover EPA is mostly luck" from "any shrinkage of a noisy component reduces walk-forward MSE." The descriptives (near-zero persistence) support the luck reading; the RMSE table alone would not prove it.

## Method

- **Frame:** identical to the 2026-10-12 live-EPA backtest — walk-forward 2021–2024, closing lines as benchmark only, ATS @ |edge| ≥ 1.5, OU @ |edge| ≥ 3.0, no wind, no circuit. The walk-forward loop is that study's Part B replication loop, with `load_team_games` parametrized by the damping weight.
- **Turnover play:** inside the current pass/rush filter, `interception == 1` or `fumble_lost == 1` in the nflverse PBP (verified present in the parquet files). Its full EPA (including return/defensive-score value) is multiplied by w before the offensive and defensive sums — both derive from the same rows, so the damping is symmetric by construction. Play counts are not scaled. Non-turnover plays untouched.
- **QB adjustment untouched** in the primary arms (the QB EPA pool is loaded exactly as in Config A). One labeled robustness arm additionally damps the QB pool (below).
- **One documented interpretation:** the loop's totals constant (`epa_const`) is calibrated on each completed game's **undamped** combined offensive EPA, exactly as in Config A. The pre-registration scopes damping to the ratings aggregation and holds the totals formula fixed; `epa_const` is part of that formula, not a rating. The primary metrics (margin RMSE, ATS) do not involve `epa_const` at all and are identical under either reading, so the verdict cannot hinge on this choice.
- **Baseline discipline — PASSED.** The damped loader at w = 1.0 produces a frame exactly equal to the baseline loader (`DataFrame.equals` → True; multiplication by 1.0 is exact and the code path short-circuits). Arm 0's walk-forward then reproduced Config A **bit-identical**: 0.0 difference on games, SU%, both margin RMSEs, ATS w-l-p, both total RMSEs, OU w-l-p (verification harness from the EPA backtest study). Arm 0 below *is* Config A.

## Results — overall

Line benchmarks are identical across arms (margin RMSE 12.726, total RMSE 13.077).

| Arm | SU% | Margin RMSE (ours / line) | ATS w-l-p (picks) | ATS% | Total RMSE (ours / line) | OU w-l-p (picks) | OU% |
|---|---|---|---|---|---|---|---|
| w = 1.00 (Arm 0, current model) | 62.6 | **14.444** / 12.726 | 399-441-26 (866) | **47.50** | 15.169 / 13.077 | 376-386-13 (775) | 49.34 |
| w = 0.50 (Arm 1) | 61.8 | **14.144** / 12.726 | 388-439-29 (856) | **46.92** | 14.939 / 13.077 | 364-368-12 (744) | 49.73 |
| w = 0.25 (Arm 2) | 60.9 | **14.091** / 12.726 | 371-428-29 (828) | **46.43** | 14.878 / 13.077 | 359-366-11 (736) | 49.52 |
| Robustness: w = 0.50 + QB pool damped | 62.3 | 14.131 / 12.726 | 393-438-29 (860) | 47.29 | 14.960 / 13.077 | 369-373-12 (754) | 49.73 |

## Results — per season

Margin RMSE (ours / line) and ATS% @ ≥1.5:

| Season | n | w = 1.00 | w = 0.50 | w = 0.25 | Robustness |
|---|---|---|---|---|---|
| 2021 | 253 | 16.518 / 13.480 · ATS 43.3% | 15.860 / 13.480 · 43.8% | 15.678 / 13.480 · 43.6% | 15.840 / 13.480 · 43.6% |
| 2022 | 284 | 12.772 / 11.457 · ATS 46.4% | 12.534 / 11.457 · 46.5% | 12.489 / 11.457 · 46.1% | 12.506 / 11.457 · 49.0% |
| 2023 | 285 | 14.658 / 13.260 · ATS 50.2% | 14.529 / 13.260 · 48.2% | 14.533 / 13.260 · 47.7% | 14.549 / 13.260 · 48.4% |
| 2024 | 285 | 13.811 / 12.692 · ATS 49.8% | 13.642 / 12.692 · 48.9% | 13.655 / 12.692 · 48.2% | 13.615 / 12.692 · 48.0% |

Total RMSE (ours / line) and OU% @ ≥3.0:

| Season | w = 1.00 | w = 0.50 | w = 0.25 | Robustness |
|---|---|---|---|---|
| 2021 | 15.905 / 13.409 · OU 52.4% | 15.664 / 13.409 · 51.0% | 15.641 / 13.409 · 51.0% | 15.683 / 13.409 · 51.3% |
| 2022 | 14.952 / 13.226 · OU 50.3% | 14.809 / 13.226 · 51.8% | 14.772 / 13.226 · 51.3% | 14.901 / 13.226 · 51.3% |
| 2023 | 15.780 / 13.123 · OU 43.1% | 15.465 / 13.123 · 42.9% | 15.349 / 13.123 · 44.1% | 15.406 / 13.123 · 43.1% |
| 2024 | 14.051 / 12.573 · OU 53.0% | 13.832 / 12.573 · 54.2% | 13.767 / 12.573 · 52.5% | 13.871 / 12.573 · 54.4% |

## Adoption-bar scorecard

| Criterion | w = 0
...[truncated 4975 chars]