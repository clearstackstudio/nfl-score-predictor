# Recency-weighting diagnostic — RESULTS

**Run:** 2026-10-19, on Bryant's explicit approval to run the diagnostic
scoped the same day. **Preregistration:** `PREREGISTRATION.md` in this
directory (written and committed before any sweep results were
computed). Runner: `run_recency_weighting.py`; numbers: `results.json`;
per-game rows for all five arms: `per_game.csv`. Measurement only — no
live model code, constant, config, generator, or site data was changed.
The live setting remains `RECENCY_HALF_LIFE = 8` in `src/epa_ratings.py`
regardless of the verdict below.

## Verdict: KILL

At least one bar of the frozen decision rule failed (see the arithmetic below). The live setting stands at RECENCY_HALF_LIFE = 8, unchanged.

**The frozen decision rule** (ADOPT iff ALL THREE hold): (1) pooled
validation margin RMSE Δ < 0 with the paired-bootstrap 95% CI lying
entirely below 0; (2) the candidate worsens margin RMSE in neither
validation season; (3) pooled validation totals RMSE Δ ≤ +0.10.

## Baseline gate (passed before any arm was trusted)

1. **Reproduction.** `run_backtest()` exactly as-is returned ATS
   **47.29%** (393-438-29)
   and margin RMSE **14.131** on **1107**
   games (2021–2024) — matching the corrected damped-config pins
   (47.29% / 14.131 / n = 1,107) within the registered tolerances.
2. **Per-game replication.** The baseline arm's (H = 8) extended
   walk-forward 2021–2024 rows replicate
   `research/turnover_damping/per_game_robustness_w0.50_qb.csv`:
   1107 of 1107 games
   merge, ATS 393-438-29,
   margin RMSE 14.130860, max |Δ our_margin| =
   3.6e-15 — the registered gate criterion, met exactly. (The
   reference file's `our_total` column does not replicate exactly;
   totals were never a gate criterion, and the difference is
   diagnosed in Method note 2.)

## The sweep — all five arms (descriptive table)

| Half-life | Disc. n | Disc. margin RMSE | Disc. totals RMSE | Val. n | Val. margin RMSE | Val. totals RMSE |
|---|---|---|---|---|---|---|
| 4 | 822 | 14.517 | 15.354 | 570 | 13.792 | 14.514 |
| 6 | 822 | 14.367 | 15.282 | 570 | 13.679 | 14.263 |
| 8 ← live (baseline) | 822 | 14.305 | 15.270 | 570 | 13.640 | 14.123 |
| 12 | 822 | 14.245 | 15.261 | 570 | 13.571 | 13.996 |
| 16 ← selected candidate | 822 | 14.201 | 15.264 | 570 | 13.534 | 13.930 |

All five arms scored the identical set of games (1392 games, 2021–2025), as the preregistration expected.

## Selection (frozen rule, applied once)

Lowest pooled discovery (2021–2023) margin RMSE wins. Discovery margin
RMSE by arm: H=4: 14.5173, H=6: 14.3671, H=8: 14.3055, H=12: 14.2446, H=16: 14.2009.
**Selected candidate: H = 16**, winning by 0.0437 RMSE
over the second-best arm. The winner sits on a grid edge; per the frozen edge rule this is reported as-is — the optimum may lie off-grid, and extending the grid requires a new pre-registration.

## Validation — the candidate against each bar

Paired sample: 570 games (2024–2025) scored by both arms.

- **Bar 1 — Δ < 0 with bootstrap CI entirely below 0:
  FAIL.**
  Baseline (H = 8) margin RMSE 13.640 →
  candidate (H = 16) 13.534;
  Δ = -0.1061. Paired bootstrap (10,000 resamples
  of validation games, seed 20261019, percentile interval): 95% CI
  [-0.2365, +0.0216].
- **Bar 2 — neither validation season worsens:
  PASS.**
  2024 (n = 285): 13.615 →
  13.442 (Δ -0.1728);
  2025 (n = 285): 13.666 →
  13.626 (Δ -0.0399).
  Any increase, however small, fails this bar.
- **Bar 3 — pooled validation totals RMSE Δ ≤ +0.10:
  PASS.**
  Baseline totals RMSE 14.123 → candidate
  13.930; Δ = -0.1933
  (bound: +0.10).

## Context (descriptive only — no verdict power)

**Validation ATS** at the house convention (|our_margin − line| ≥ 1.5;
2024 lines from spreadspoke, 2025 lines from
`schedules_games.parquet` `spread_line`, per the ratified precedent):
baseline H = 8: 209-237-9
(46.9% on 455 picks); candidate
H = 16: 222-236-9
(48.5% on 467 picks).

## Method notes

1. The sweep overrides only the module constant `RECENCY_HALF_LIFE`
   (and its derived `_RECENCY_DECAY`) per arm, so both consumers —
   `adjusted_ratings()` and `qb_adjustments()` — move together,
   exactly as a live edit would, per the registration's entanglement
   ruling. Every other constant stayed at its live value in every arm
   (`WINDOW_GAMES = 17`, `MIN_GAMES = 4`, `CARRYOVER = 0.5`,
   `TURNOVER_EPA_WEIGHT = 0.50` — damping ON in all arms — and the QB
   machinery constants).
2. The totals calibration (`epa_const`: trailing mean of actual total
   minus the game's raw combined offensive EPA, appended after each
   prediction — `run_backtest()`'s spec verbatim) is arm-invariant:
   for any given game it is the identical number in all five arms,
   since it depends only on game order and actual totals. Bar 3 is
   therefore a clean cross-arm comparison, and by 2024–2025 the
   calibration history behind it is ~800 games deep.

   **Totals-replication caveat (post-run verification, 2026-10-19):**
   this harness's per-game `our_total` does NOT replicate the damping
   study file's `our_total` column exactly — max |Δ| = 28.05, in the
   opening games of 2021, decaying to ≤ 0.12 by 2024 — and its
   baseline-arm 2021–2024 totals RMSE (14.923) sits 0.038 below
   `run_backtest()`'s own aggregate (14.960) instead of matching
   bit-for-bit the way margins do (identical to 1e-15). The cause is
   the calibration constant itself: as a trailing mean, its early
   values are sensitive to the exact order in which same-date games
   are processed during the warm-up weeks, and the three loops
   (`run_backtest`, the damping study's Part B, this runner) order
   those games slightly differently. Margins are unaffected by that
   ordering. No bar depends on matching any external totals figure:
   bar 3 is a within-harness difference between arms sharing one
   calibration sequence. (The runner's RESULTS.md template
   originally described the totals comparison as "verifying the
   totals calibration"; this note corrects that wording. No number
   in this report changed.)
3. 2026 is excluded entirely, per the registration. No new data, no
   cost. The descriptive sweep table above carries no verdict standing:
   the verdict was computed only through the frozen
   selection-then-validation path.
