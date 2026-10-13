# Turnover-EPA damping — placebo (specificity) test results

**Date:** 2026-10-12 · **Approved by:** Bryant (measurement only; no live code/data changed)
**Pre-registration:** `goals/ultimate-multi-sport-prediction-model/hidden_files/turnover-placebo-preregistration.md` (written before any placebo run existed)
**Interpreter:** `.venv-cfb/bin/python` — **Artifacts:** `run_turnover_placebo.py` (runner), `metrics.json`, `selection_info.json`, `selection_seed{1101,2202,3303,4404,5505}.json` (saved play IDs per replicate), `per_game_*.csv` for the baseline and all 10 placebo arms. No git commit/push; `src/` and `site/` untouched.

## Verdict (up front)

**SPECIFIC.** Under the pre-registered decision rule at the primary weight (w = 0.50):

- The turnover arm's margin-RMSE improvement over baseline is **0.300** (14.444 → 14.144). The five |EPA|-mass-matched placebo replicates improve by **0.069 to 0.144, mean 0.104**. The turnover improvement exceeds the placebo mean by **0.196**, clearing clause (a)'s ≥ 0.05 margin by nearly 4×.
- The turnover arm beats **5 of 5** replicates individually on margin RMSE (14.144 vs 14.300–14.375), clearing clause (b)'s ≥ 4 of 5.

The secondary weight (w = 0.25) agrees, with a larger margin: turnover improvement 0.353 vs placebo mean 0.135 (excess **0.217**), 5 of 5 replicates beaten.

**What this does and does not mean** (per the pre-registration): the RMSE gain from damping is *not* fully explained by generic shrinkage — roughly two-thirds of it is specific to turnover plays, consistent with the damping study's descriptives (turnover EPA's season-to-season persistence ≈ +0.08). But roughly one-third *is* generic: every placebo replicate also improved on the baseline, so a real ratings over-dispersion component exists alongside the turnover effect. This verdict does **not** adopt turnover damping: the original adoption bar was failed on its ATS clause (47.50% → 46.92% at w = 0.50) and stays failed unless Bryant separately decides to revisit that clause. The question this returns to him is the explicit trade stated in the pre-registration: a turnover-specific ~0.20 margin-RMSE gain (plus a generic ~0.10 available from any shrinkage) against a ~0.6pp ATS slip at the published threshold. The generic component, if pursued, is a different study (global ratings shrinkage) requiring its own pre-registration.

## Baseline discipline — PASSED

The placebo loader at w = 1.0 (seed-1101 selection loaded, scaling short-circuited) produces a team-games frame exactly equal to the baseline loader (`DataFrame.equals` → True), and the Arm 0 walk-forward reproduced Config A of the 2026-10-12 live-EPA backtest **bit-identical**: 0.0 difference on games (1,107), SU%, both margin RMSEs (14.443910 / 12.725944), ATS w-l-p (399-441-26), both total RMSEs (15.169133 / 13.076688), and OU w-l-p (376-386-13). Turnover arms were **not** re-run; their numbers below are the published ones from `research/turnover_damping/metrics.json`.

## Placebo selection (fixed in advance, performed once)

- Pool: the exact filtered pass/rush pool the ratings are built from, 2021–2024: **143,879 plays**, of which **2,777 are turnover plays** with total |EPA| mass **12,839.88**.
- Per seed (1101, 2202, 3303, 4404, 5505): a `RandomState(seed)` permutation of the 141,102 non-turnover plays, accumulated in that order until cumulative |EPA| first reaches the target. Selected sets are ~5.2× the turnover play count — the expected consequence of matching on |EPA| mass rather than count (turnover plays average ~4.6 |EPA|; ordinary plays ~0.88).

| Seed | Plays selected | Achieved |EPA| | Match vs target |
|---|---|---|---|
| 1101 | 14,446 | 12,839.93 | 100.000% |
| 2202 | 14,472 | 12,840.05 | 100.001% |
| 3303 | 14,535 | 12,840.08 | 100.002% |
| 4404 | 14,524 | 12,840.94 | 100.008% |
| 5505 | 14,419 | 12,840.26 | 100.003% |

All five land within ±0.01% of the target — far inside the pre-registered ±2% band. Selected (game_id, play_id) IDs are saved in `selection_seed<seed>.json`; every saved ID was verified to match exactly one pool play before the arms ran (see process note 1).

## Results — overall, w = 0.50 (primary comparison)

Line benchmarks are identical across arms (margin RMSE 12.726, total RMSE 13.077). Improvements are vs the w = 1.00 baseline margin RMSE 14.443910.

| Arm | Margin RMSE | Improvement | ATS w-l-p | ATS% | Total RMSE | OU w-l-p | OU% | SU% |
|---|---|---|---|---|---|---|---|---|
| Baseline (w = 1.00) | **14.444** | — | 399-441-26 | 47.50 | 15.169 | 376-386-13 | 49.34 | 62.6 |
| **Turnover (published)** | **14.144** | **+0.300** | 388-439-29 | 46.92 | 14.939 | 364-368-12 | 49.73 | 61.8 |
| Placebo seed 1101 | 14.338 | +0.106 | 401-445-26 | 47.40 | 15.023 | 374-389-12 | 49.02 | 61.8 |
| Placebo seed 2202 | 14.348 | +0.096 | 399-445-25 | 47.27 | 15.069 | 360-384-13 | 48.39 | 62.2 |
| Placebo seed 3303 | 14.337 | +0.107 | 410-439-26 | 48.29 | 14.976 | 369-383-13 | 49.07 | 62.3 |
| Placebo seed 4404 | 14.375 | +0.069 | 396-434-24 | 47.71 | 15.018 | 363-376-12 | 49.12 | 61.9 |
| Placebo seed 5505 | 14.300 | +0.144 | 402-451-26 | 47.13 | 15.008 | 371-382-13 | 49.27 | 62.2 |
| **Placebo mean** | **14.340** | **+0.104** | — | 47.56 | 15.019 | — | 48.97 | 62.1 |

Descriptive notes (not decision inputs — the rule is RMSE-based): the placebo's RMSE gain comes with **no ATS cost** (replicate ATS 47.13–48.29%, mean 47.56% ≈ the 47.50% baseline), while the turnover arm pays 0.58pp of ATS for its larger RMSE gain. Total RMSE improves under every placebo replicate (14.976–15.069 vs 15.169) but by less than under turnover damping (14.939); OU% is flat-to-slightly-worse under placebos (mean 48.97%) vs slightly better under turnover damping (49.73%).

## Results — overall, w = 0.25 (secondary)

| Arm | Margin RMSE | Improvement | ATS w-l-p | ATS% | Total RMSE | OU w-l-p | OU% | SU% |
|---|---|---|---|---|---|---|---|---|
| Baseline (w = 1.00) | **14.444** | — | 399-441-26 | 47.50 | 15.169 | 376-386-13 | 49.34 | 62.6 |
| **Turnover (published)** | **14.091** | **+0.353** | 371-428-29 | 46.43 | 14.878 | 359-366-11 | 49.52 | 60.9 |
| Placebo seed 1101 | 14.307 | +0.137 | 397-441-27 | 47.37 | 14.975 | 360-386-12 | 48.26 | 61.3 |
| Placebo seed 2202 | 14.321 | +0.123 | 393-453-26 | 46.45 | 15.043 | 359-384-13 | 48.32 | 61.7 |
| Placebo seed 3303 | 14.304 | +0.140 | 418-435-28 | 49.00 | 14.902 | 368-379-12 | 49.26 | 62.2 |
| Placebo seed 4404 | 14.362 | +0.082 | 399-438-24 | 47.67 | 14.963 | 355-376-12 | 48.56 | 61.8 |
| Placebo seed 5505 | 14.249 | +0.195 | 406-449-26 | 47.49 | 14.946 | 373-382-12 | 49.40 | 61.9 |
| **Placebo mean** | **14.309** | **+0.135** | — | 47.60 | 14.966 | — | 48.76 | 61.8 |

## Results — per season

Margin RMSE / ATS% (line margin RMSE in the baseline row's parentheses per season: 13.480 / 11.457 / 13.260 / 12.692):

| Arm | 2021 (n=253) | 2022 (n=284) | 2023 (n=285) | 2024 (n=285) |
|---|---|---|---|---|
| Baseline | 16.518 / 43.3 | 12.772 / 46.4 | 14.658 / 50.2 | 13.811 / 49.8 |
| Turnover w=0.50 | **15.860 / 43.8** | **12.534 / 46.5** | **14.529 / 48.2** | **13.642 / 48.9** |
| Placebo 1101 w=0.50 | 16.288 / 42.3 | 12.706 / 46.7 | 14.578 / 51.2 | 13.771 / 48.9 |
| Placebo 2202 w=0.50 | 16.358 / 43.2 | 12.640 / 48.8 | 14.634 / 47.6 | 13.736 / 49.1 |
| Placebo 3303 w=0.50 | 16.311 / 44.0 | 12.710 / 47.8 | 14.548 / 49.8 | 13.769 / 51.1 |
| Placebo 4404 w=0.50 | 16.408 / 43.6 | 12.741 / 46.6 | 14.610 / 49.5 | 13.727 / 50.9 |
| Placebo 5505 w=0.50 | 16.285 / 43.1 | 12.681 / 46.0 | 14.581 / 49.3 | 13.640 / 49.8 |
| Turnover w=0.25 | **15.678 / 43.6** | **12.489 / 46.1** | **14.533 / 47.7** | **13.655 / 48.2** |
| Placebo 1101 w=0.25 | 16.202 / 43.0 | 12.692 / 46.0 | 14.554 / 51.7 | 13.773 / 48.4 |
| Placebo 2202 w=0.25 | 16.308 / 41.7 | 12.593 / 47.4 | 14.643 / 47.1 | 13.715 / 49.1 |
| Placebo 3303 w=0.25 | 16.243 / 44.1 | 12.696 / 50.0 | 14.507 / 50.2 | 13.762 / 51.1 |
| Placebo 4404 w=0.25 | 16.383 / 44.1 | 12.742 / 45.5 | 14.600 / 48.3 | 13.708 / 52.3 |
| Placebo 5505 w=0.25 | 16.195 / 42.9 | 12.659 / 46.5 | 14.560 / 49.5 | 13.570 / 50.7 |

Total RMSE / OU%:

| Arm | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|
| Baseline | 15.905 / 52.4 | 14.952 / 50.3 | 15.780 / 43.1 | 14.051 / 53.0 |
| Turnover w=0.50 | 15.664 / 51.0 | 14.809 / 51.8 | 15.465 / 42.9 | 13.832 / 54.2 |
| Placebo 1101 w=0.50 | 15.742 / 49.1 | 14.809 / 51.2 | 15.653 / 43.7 | 13.897 / 52.8 |
| Placebo 2202 w=0.50 | 15.782 / 51.6 | 14.900 / 49.2 | 15.703 / 42.2 | 13.895 / 51.9 |
| Placebo 3303 w=0.50 | 15.675 / 50.6 | 14.840 / 48.5 | 15.588 / 43.8 | 13.806 / 55.0 |
| Placebo 4404 w=0.50 | 15.769 / 52.4 | 14.888 / 50.5 | 15.598 / 42.3 | 13.826 / 52.5 |
| Placebo 5505 w=0.50 | 15.743 / 51.2 | 14.758 / 50.3 | 15.680 / 43.9 | 13.852 / 52.8 |
| Turnover w=0.25 | 15.641 / 51.0 | 14.772 / 51.3 | 15.349 / 44.1 | 13.767 / 52.5 |
| Placebo 1101 w=0.25 | 15.695 / 48.2 | 14.761 / 50.0 | 15.610 / 42.4 | 13.841 / 53.5 |
| Placebo 2202 w=0.25 | 15.758 / 51.3 | 14.892 / 50.0 | 15.684 / 41.5 | 13.839 / 51.6 |
| Placebo 3303 w=0.25 | 15.597 / 49.7 | 14.802 / 49.0 | 15.504 / 43.5 | 13.707 / 56.5 |
| Placebo 4404 w=0.25 | 15.723 / 49.7 | 14.872 / 49.5 | 15.529 / 42.1 | 13.734 / 53.8 |
| Placebo 5505 w=0.25 | 15.689 / 50.6 | 14.673 / 49.7 | 15.646 / 44.3 | 13.776 / 53.8 |

Per-season texture (descriptive): the turnover arm's overall edge is concentrated in **2021**, where it beats every placebo replicate by ~0.43–0.55 RMSE (15.860 vs 16.285–16.408 at w = 0.50) — the burn-in season, where ratings lean hardest on the noisiest early evidence. In 2022 the turnover arm also beats all five (12.534 vs 12.640–12.741). In 2023 and 2024 the turnover arm still posts the best or near-best margin RMSE but individual replicates come within ~0.02–0.05 of it. The specificity verdict does not hinge on any single season — the overall rule passes with room — but the effect is not uniform across seasons.

## Decision-rule scorecard (applied exactly as pre-registered)

Primary comparison at w = 0.50, margin RMSE:

| Clause | Required | Observed | Pass |
|---|---|---|---|
| (a) Turnover improvement exceeds placebo-mean improvement by ≥ 0.05 | 0.300 − mean ≥ 0.05 | 0.300224 − 0.104330 = **0.195895** | ✓ |
| (b) Turnover arm beats ≥ 4 of 5 replicates individually | ≥ 4 | **5 of 5** (14.143686 < 14.300295 … 14.374860) | ✓ |

**Classification: SPECIFIC.** Neither "generic" trigger is close: the placebo mean (0.104) is not within 0.05 of the turnover improvement (0.300), and no replicate matches or beats the turnover arm (best replicate: 0.144, seed 5505). The w = 0.25 secondary check points the same way (excess 0.217082, 5 of 5 beaten), so the classification is not weight-sensitive.

Decomposition, stated plainly: of the turnover arm's 0.300 improvement at w = 0.50, ≈ **0.104 (≈ 35%) is generic** — available by shrinking any |EPA|-matched set of ordinary plays — and ≈ **0.196 (≈ 65%) is turnover-specific**. The damping study's premise (turnover EPA is disproportionately luck) is supported for the larger share; a smaller ratings over-dispersion effect is also real and is the subject for a separate, separately-approved global-shrinkage study if Bryant wants it.

## Process notes

1. **Key-format bug, caught and fixed before any placebo number was recorded.** The first rep1101 w = 0.50 run returned margin RMSE exactly equal to baseline (improvement +0.0000) — a no-op. Cause: `play_id` is float64 in the PBP parquets (1.0, 40.0, …), and the loader built match keys from `str(float)` (`…#1.0`) while the saved selection IDs are ints (`…#1530`), so the mask matched zero plays. That bogus metrics block and per-game CSV were deleted, the loader was fixed to build keys from `int(play_id)` (via `round().astype("Int64")`), a hard assertion was added (the stage now aborts unless the number of scaled plays equals the saved selection size), and all five selections were verified to match exactly (14,446 / 14,472 / 14,535 / 14,524 / 14,419 of their saved IDs) before the arms were re-run. Every placebo number in this report comes from a run whose scaled-play count was asserted equal to its selection size.
2. **One stage re-run.** The rep3303 w = 0.25 background process died mid-walk-forward before writing anything (same runtime behavior the damping study hit); the stage was re-run cleanly as its own process. All arms were executed as staged single-arm processes writing incrementally to `metrics.json`, per the prior study's lesson.
3. Nothing in `src/` or `site/` was modified, and nothing was committed or pushed.
