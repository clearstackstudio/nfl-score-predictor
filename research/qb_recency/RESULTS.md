# QB recency diagnostic — RESULTS

**Run:** 2026-10-19, on Bryant's explicit approval to run the diagnostic
scoped 2026-10-15, under the 2026-10-19 addendum he approved after the
first attempt stopped at the stale pre-damping baseline pin (pins only;
protocol otherwise frozen). **Preregistration:** `PREREGISTRATION.md` in
this directory (written before any recency results were computed).
Runner:
`run_qb_recency.py`; numbers: `results.json`; per-game rows:
`per_game.csv`. Measurement only — no live model code was changed.

## Verdict: KILL

Per the frozen decision rule (KEEP iff both validation bars hold, with
the both-seasons-worse guardrail as an automatic KILL):

- **Bar 1 — validation slope > 0 with z ≥ 1.96: FAIL.**
  Validation slope: **+2.537** (SE 3.449, z = +0.74) on n = 106 games (2024–2025).
- **Bar 2 — discovery-fitted adjustment reduces validation margin RMSE: FAIL.**
  Discovery slope (2021–2023, n = 199): -2.407 (SE 2.867, z = -0.84). Applying `our_margin + -2.407 · qb_form_diff`: validation RMSE 13.267 → 13.366 (+0.099).
- **Guardrail — adjustment worsens RMSE in both validation seasons: True.**
  2024: 13.902 → 14.049 (n = 59); 2025: 12.425 → 12.455 (n = 47).

## Baseline reproduction (stop rule — passed)

The live-config baseline was reproduced before anything else was run:
`run_backtest()` exactly as-is returned ATS **47.29%** (393-438-29) and
margin RMSE **14.131** on 1,107 games (2021–2024), matching the gate as
re-pinned by the 2026-10-19 addendum to the preregistration — the live
damped configuration's figures, published as the robustness arm of
`research/turnover_damping/RESULTS.md` (the original pins, 47.5% /
14.44 from `research/epa_live_backtest/`, were pre-damping and halted
the first run attempt). The extended walk-forward's 2021–2024 rows were
then verified bit-for-bit against the damping study's per-game
robustness file (max |Δmargin| = 3.6e-15), so the 2025
extension runs on a verified frame.

## Coverage

| Split | Predicted | Both continuing | Test sample |
|---|---|---|---|
| Discovery 2021–2023 | 822 | 235 (28.6%) | 199 (24.2%) |
| Validation 2024–2025 | 570 | 108 (18.9%) | 106 (18.6%) |
| All 2021–2025 | 1392 | 343 (24.6%) | 305 (21.9%) |

"Both continuing" = each listed starter threw ≥85% of his team's
trailing-window dropbacks (the model's own `qb_adj = 0` criterion,
replicated exactly). "Test sample" adds the feature eligibility rules
(≥15 dropbacks in the QB's last game, ≥100 career dropbacks entering
the game).

## Secondary outputs (descriptive only — no verdict power)

- **Last-game INT differential** (`last_int_diff` = away QB's last-game
  INTs − home QB's; the Darnold anecdote's exact shape):
  discovery slope +0.361 (z = +0.37, n = 199);
  validation slope +0.745 (z = +0.62, n = 106).
- **ATS win% on model picks (|spread_edge| ≥ 1.5), split by whether
  `qb_form_diff` agrees with the pick:**
  validation — agree [24, 22, 0] (52.2%), disagree [14, 24, 0] (36.8%);
  discovery — agree [34, 41, 1] (45.3%), disagree [32, 29, 2] (52.5%).

## Method notes and deviations (all flagged per house rules)

1. **2025 closing lines:** `spreadspoke_scores.csv`, the line store
   used by every prior diagnostic, ends at 2024 — it has no 2025 rows.
   The 2025 game frame, final scores, and closing spread therefore come
   from `data/schedules_games.parquet` (nflverse), a file the harness
   already loads for QB ids and venue. Its `spread_line` was checked
   against the spreadspoke closing spread on 2021–2024 first: same
   convention (positive = home favored), correlation 0.996, 66%
   identical, mean |difference| 0.24 pts; final scores agree 99.9%.
   The PRIMARY test never touches a line (it needs only our_margin and
   the actual margin); only the descriptive ATS split uses lines, and
   only its 2025 rows use the nflverse line.
2. **`last_dev` trailing mean:** the preregistration specifies the
   ratings' decay without specifying a game window for the QB's own
   history. Implemented as: per-game EPA/dropback for each of the QB's
   prior games, weighted by the ratings' per-game decay (half-life 8
   games, most recent = weight 1) via the pipeline's own
   `_decayed_mean`, over all his prior games in the data. Dropbacks and
   EPA are the pipeline's own construction (`load_qb_plays`:
   pass attempts + sacks, turnover-damped EPA) — reused, not redefined.
   A QB's games are his games for any team (as in `qb_adjustments`'
   treatment of a starter's own form).
3. **"Career dropbacks"** are counted within the test data (2021–2025
   play-by-play), the only data the preregistration names; pre-2021
   dropbacks are unobserved, which mainly delays eligibility for some
   veterans early in 2021.
4. OLS is fit with an intercept (the standard reading of "regress Y on
   X"); only the slope is applied as the adjustment, as specified.
5. The motivating 2026 season is excluded entirely, per the
   preregistration.

## What this does and doesn't mean

A KILL means: on the frozen test, a QB's most recent game adds no demonstrated signal on top of ratings that already decay-weight that game and a QB-change machinery that already prices replacement starters. The live model is unchanged. This says nothing about QB *changes* (owned by `qb_adjustments` and the override feed), and it does not mean "form doesn't matter" in general — it means this specific last-game deviation term did not earn its place.

## Supplementary reporting (descriptive — computed from this run's `per_game.csv`; NOT part of the frozen verdict)

### Per-season walk-forward margin RMSE, live vs candidate (test sample)

Candidate = `our_margin + (−2.407) · qb_form_diff` (the discovery-fitted
slope) applied to every season. The 2021–2023 rows are **in-sample** for
that slope (it was fit on them) and are shown for completeness only; the
verdict rests on 2024–2025.

| Season | n | Live RMSE | Candidate RMSE | Δ (cand − live) |
|---|---|---|---|---|
| 2021 (discovery, in-sample) | 105 | 15.965 | 15.867 | −0.098 |
| 2022 (discovery, in-sample) | 47 | 13.562 | 13.738 | +0.176 |
| 2023 (discovery, in-sample) | 47 | 13.146 | 13.111 | −0.035 |
| 2024 (validation) | 59 | 13.902 | 14.049 | +0.148 |
| 2025 (validation) | 47 | 12.425 | 12.455 | +0.030 |
| **Validation pooled** | **106** | **13.267** | **13.366** | **+0.099** |

Paired bootstrap on the pooled validation Δ (resampling games, 10,000
draws, seed 20261019): Δ = **+0.099**, 95% CI **[−0.091, +0.277]** — the
interval straddles zero and only 15.3% of resamples show any improvement,
consistent with bar 2's failure: no demonstrated RMSE gain.

### Fitted β trajectory (descriptive)

OLS slope of `margin_resid` on `qb_form_diff` fit within each season
(test sample), alongside the two fits the protocol uses:

| Fit | β̂ | SE | z |
|---|---|---|---|
| 2021 only | −5.055 | 3.846 | −1.31 |
| 2022 only | +7.679 | 6.185 | +1.24 |
| 2023 only | −1.965 | 6.246 | −0.31 |
| **Discovery pooled 2021–2023 (protocol fit)** | **−2.407** | **2.867** | **−0.84** |
| 2024 only | +4.508 | 4.714 | +0.96 |
| 2025 only | −0.560 | 5.086 | −0.11 |
| **Validation pooled 2024–2025 (bar 1)** | **+2.537** | **3.449** | **+0.74** |

The sign flips season to season and between the discovery and validation
pools, and no fit reaches |z| ≥ 1.32 — the signature of noise, not of a
stable effect the model is missing.

### Per-season ATS context (all predicted games, |spread_edge| ≥ 1.5)

| Season | Predicted | W-L-P | Win% |
|---|---|---|---|
| 2021 | 253 | 89-115-3 | 43.6% |
| 2022 | 284 | 102-106-7 | 49.0% |
| 2023 | 285 | 93-99-11 | 48.4% |
| 2024 | 285 | 109-118-8 | 48.0% |
| 2025 | 285 | 100-119-1 | 45.7% |

(2025 lines from `schedules_games.parquet` per the addendum; 2021–2024
from the spreadspoke closing store, as in the baseline. The 2021–2024
rows pool to the gated 393-438-29 / 47.29%.)
