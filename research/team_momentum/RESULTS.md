# Team momentum — RESULTS

**Run:** 2026-10-23, on Bryant's explicit approval to run the full test
package. **Preregistration:** `PREREGISTRATION.md` in this directory
(frozen 2026-10-19, before any momentum-trajectory results were
computed). Runner: `run_team_momentum.py`; numbers: `results.json`;
per-game rows: `per_game.csv`. Measurement only — no live model code,
constant, config, generator, or site data was changed.

## Verdict: KILL

Per the frozen three-bar rule, ADOPT requires all three bars:

- **Bar 1 — validation slope > 0 with z ≥ 1.96: FAIL.**
  Discovery gamma (2021–2023, n = 649): **γ = -5.3947**
  (SE 3.9207, z = -1.38). On validation
  (2024–2025, n = 442), the slope is **-7.3269**
  (SE 4.2964, z = **-1.71**).
- **Bar 2 — frozen adjustment reduces pooled validation RMSE: PASS.**
  Applying `our_margin + γ · momentum_diff`: validation RMSE
  **13.528 → 13.487** (Δ **-0.042**).
  Paired bootstrap (10,000 game resamples, seed 20261019): 95% CI for
  candidate-minus-baseline RMSE = **[-0.122, +0.040]**.
- **Bar 3 — neither validation season worsens: PASS.**
  2024: 13.412 → 13.383
  (Δ -0.029, n = 221);
  2025: 13.644 → 13.590
  (Δ -0.054, n = 221).

The live model is unchanged. Under the standing honesty rule, this KILL is the tested-and-rejected result for this exact momentum definition; a different window, baseline, or performance series would require a new preregistration before any results are computed.

## Baseline gate (passed before fitting)

1. **Reproduction.** `run_backtest()` exactly as-is returned ATS
   **47.29%** (393-438-29) and margin RMSE **14.131** on **1,107**
   games (2021–2024), matching the frozen pins within tolerances.
2. **Per-game replication.** The extended walk-forward's 2021–2024
   rows replicate
   `research/turnover_damping/per_game_robustness_w0.50_qb.csv`:
   1107 of 1,107
   games merge, ATS tuple (393, 438, 29),
   RMSE 14.130860, and max
   |Δ our_margin| = 3.6e-15.

## Mechanism diagnostic (mandatory; no verdict power)

On the validation eligible sample (n = 442):

- **Momentum slope against the market residual:** regressing
  `actual_margin − line_margin` on `momentum_diff` gives slope
  **-0.9910** (SE 3.9016, z = -0.25).
- **Joint regression with the line:** regressing `margin_resid` on
  both `momentum_diff` and `line_margin` gives a momentum slope of
  **-7.5803** (SE 4.3179,
  z = -1.76); the line coefficient is
  +0.0668 (SE 0.1053,
  z = +0.63).

Read plainly: the market-residual slope is the first check on whether
the closing line already contains the trajectory; the joint regression
is the check on whether any model-residual momentum slope survives
once the line is in the same regression (in M1, it did not).

## Coverage

| Split | Predicted games | Eligible games | Eligible share |
|---|---:|---:|---:|
| Discovery 2021–2023 | 822 | 649 | 79.0% |
| Validation 2024–2025 | 570 | 442 | 77.5% |
| All 2021–2025 | 1392 | 1091 | 78.4% |

Eligible = both teams had played at least four prior games in the
current season. Per-season eligible shares: 2021 82.2%,
2022 77.5%, 2023 77.5%,
2024 77.5%, 2025 77.5%.

## Per-season validation RMSE table

| Season | n | Live model | γ-adjusted | Δ |
|---|---:|---:|---:|---:|
| 2024 | 221 | 13.412 | 13.383 | -0.029 |
| 2025 | 221 | 13.644 | 13.590 | -0.054 |
| Pooled | 442 | 13.528 | 13.487 | -0.042 |

## Secondary descriptive output (no verdict power)

- **Validation ATS on model picks (|edge| ≥ 1.5), eligible games:**
  live model [161, 188, 4] (46.1% on 353
  picks); γ-adjusted model [163, 182, 4] (47.2% on
  349 picks). Each model is scored on its own pick set,
  as in the recency-weighting diagnostic. 2021–2024 lines are the
  spreadspoke closing spreads; 2025 lines are
  `schedules_games.parquet` (`spread_line`), per the ratified
  precedent. The primary test uses no lines.

## Method notes

1. The feature was computed exactly once under the frozen definition:
   net EPA/play from `load_team_games()` (turnover EPA damped at the
   live w = 0.50), one four-game window, one season-to-date baseline,
   one additive `γ · momentum_diff` form. No alternative window,
   weighting, series, split, threshold, or interaction was tried.
2. Cutoff safety follows the pipeline convention: the cutoff is the
   first `team_games` row index for the predicted game, and only team
   rows strictly before that index enter either team's baseline or
   window. Same-week games cannot leak through a (season, week)
   cutoff because no such cutoff is used.
3. The baseline is constant across a team's four-game window, so the
   registered slope of `(p_i − B)` is numerically the slope of `p_i`;
   B is reported per game in `per_game.csv` as the interpretive anchor
   and was not replaced with any pre-window variant.
4. 2026 is excluded entirely. The primary test is margin-only and
   line-free; lines enter only the mandatory mechanism diagnostic and
   the descriptive ATS context.
5. OLS uses an intercept and applies only the fitted slope as the
   adjustment, per the registration and the house convention.
