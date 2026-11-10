# CFB totals — post-adoption audit of TOTAL_SHRINKAGE = 0.7 — RESULTS

**Date:** 2026-10-23 · **Pre-registration:**
`research/cfb_totals_shrinkage/PREREGISTRATION.md` (written and frozen
before any audit numbers were computed; run approved by Bryant
2026-10-23 as part of the model improvement package).
**Measurement only** — nothing outside `research/cfb_totals_shrinkage/`
was written; `cfb/cfb_ratings.py` still has `TOTAL_SHRINKAGE = 0.7`,
the live recalibration curves are untouched, no CFBD calls were made
(quota exhausted until ~Nov 1; everything ran off the in-repo frame).

## Headline

| Question | Verdict |
|---|---|
| Q1 — Do the adopted walk-forward numbers reproduce? | **CONFIRMED**, exactly |
| Q2 — Is s = 0.7 supported on a play basis? | **NOT SUPPORTED** by the frozen rule's letter — on a 0.04 pp wiggle; see the tension note |
| Q3 — Does the recalibration refit earn a RECOMMEND? | **NOT** — out-of-sample Brier is a tie; the bootstrap CI straddles 0 |

Data: `research/cfb_improvement/frame_B.parquet` — the same
chronological walk-forward frame as the adoption study (8,947 games,
2014–2025, FBS). Shrinkage applied post-hoc exactly as in October:
`total' = epa_const + s·(our_total − epa_const)`.

---

## Q1 — Reproduction: **CONFIRMED**

Every recorded adoption number reproduces from frame B at the recorded
rounding:

- **Pooled totals RMSE: s = 1.0 → 18.7317 (recorded 18.73);
  s = 0.7 → 17.7287 (recorded 17.73).**
- All 12 per-season raw (s = 1.0) totals RMSEs match the October
  per-season table to 2 dp.
- The walk-forward selection (grid {1.0, 0.95, 0.9, 0.85, 0.8, 0.7},
  chosen on prior seasons only) again picks **s\* = 0.7 in all 11
  evaluation seasons (2015–2025)**, and the shrunk per-season RMSEs
  match the recorded values to 2 dp in all 11 (e.g. 2025: 18.45 →
  17.25; 2021: 18.45 → 17.24; 2019: 18.13 → 17.17).
- **Shrunk totals beat raw totals in 11 of 11 evaluation seasons** —
  the claim in `cfb/cfb_ratings.py` and the October RESULTS.md is
  accurate as recorded. (Descriptive aside: fixed s = 0.7 also improves
  2014, 19.69 → 18.32, so the fixed-factor comparison is 12/12
  calendar seasons; the recorded claim is the walk-forward 11/11.)

| Season | RMSE s = 1.0 | RMSE s = 0.7 |
|---|---|---|
| 2014 | 19.69 | 18.32 |
| 2015 | 19.42 | 18.52 |
| 2016 | 18.22 | 17.63 |
| 2017 | 19.73 | 18.76 |
| 2018 | 18.62 | 17.76 |
| 2019 | 18.13 | 17.17 |
| 2020 | 18.74 | 17.93 |
| 2021 | 18.45 | 17.24 |
| 2022 | 18.65 | 17.64 |
| 2023 | 18.13 | 17.16 |
| 2024 | 18.62 | 17.48 |
| 2025 | 18.45 | 17.25 |
| **Pooled** | **18.73** | **17.73** |

No mismatch, material or otherwise → no FLAGGED stop. The adoption
evidence was sound.

---

## Q2 — Play basis: **NOT SUPPORTED** (frozen rule), with a tension Bryant should see

The live generator's totals play rule (`cfb/cfb_weekly_picks.py`: a
pick fires at |total edge| ≥ 1.0 and is suppressed above the
TOTAL_CIRCUIT of 8.5) applied to the walk-forward rows, same 8,947
games, each s graded on its own totals:

| | OU record (W-L-P) | Picks | Win% | Distance from 50% |
|---|---|---|---|---|
| s = 1.0 | 2513-2469-62 | 5,044 | 50.44% | 0.442 pp |
| s = 0.7 | 2906-2850-67 | 5,823 | 50.49% | 0.486 pp |

(Both records reproduce the October study's descriptive live-rule
numbers exactly — a second internal-consistency check on the
machinery.)

Frozen decision rule: s = 0.7 is supported on play basis iff its OU
win% is **at least as close to 50%** as s = 1.0's **AND** its totals
RMSE is lower. The RMSE condition passes (17.73 < 18.73, Q1). The
closeness condition **fails**: 0.486 pp > 0.442 pp. Verdict per the
rule as written: **NOT SUPPORTED on play basis.**

The tension, stated with magnitudes so the decision is informed:

- The failing margin is **0.044 percentage points** — about one game
  in ~2,300 decided picks. Both records are coin flips (50.4–50.5%,
  both far under the 52.4% breakeven); there is no play-basis story
  in either direction. Shrinkage did not make totals picks worse in
  any material sense — it made ~15% *more* of them (5,044 → 5,823,
  because compressed edges trip the circuit breaker less often) at
  the same win rate.
- The adoption was justified on forecast accuracy, and Q1 confirms
  that justification in full: the published *numbers* are ~1.0 pt of
  RMSE closer to reality in every season. Reverting s to 1.0 would
  give that back to chase a 0.04 pp play-basis difference that is
  indistinguishable from zero.
- The live 32-46 record that triggered this audit predates the
  adoption (both graded weeks ran s = 1.0-era boards), so it is
  evidence about the old totals, not about s = 0.7. Nothing in the
  2014–2025 walk-forward suggests the post-adoption live play record
  should be expected to differ from ~50% either way.

**Recommendation (per the pre-registration, this is a report of a
tension, not an auto-revert): keep TOTAL_SHRINKAGE = 0.7.** The
play-basis failure is a rounding-scale artifact of a strict
inequality applied to two identical coin flips; the RMSE basis for
adoption is confirmed and material.

---

## Q3 — Recalibration refit: **NOT** recommended

Method (the existing recalibration code's, per the pre-registration):
curve = (bin mean raw prob, empirical hit rate) over the bins
[0.50, 0.55), [0.55, 0.60), [0.60, 0.65), [0.65, 0.70), [0.70, 1.01),
anchored at (0.50, 0.50), piecewise-linear with the 0.50 floor —
exactly `src/recalibration.py`'s semantics (verified: my interpolation
replica matches the live `recalibrate()` bit-for-bit on a grid).
Records are decided (non-push) totals picks under the live rule,
raw prob = Φ(|edge| / 17.72), where 17.72 is the `total_sd` the live
generator loads today (`data/cfb/cfb_backtest.json`, post-shrinkage
restated backtest). Fit on post-shrinkage (s = 0.7) predictions,
2014–2023 (4,724 decided picks); evaluate on 2024–2025 (1,032 decided
picks). Pushes are excluded throughout (a push is neither a hit nor
a miss, matching how OU% is computed everywhere else in this
codebase).

**Refit curve** (what would replace the stale one if adopted):

| Bin | n | Mean raw | Empirical hit rate |
|---|---|---|---|
| 0.50–0.55 | 997 | 0.536 | 0.512 |
| 0.55–0.60 | 1,662 | 0.574 | 0.507 |
| 0.60–0.65 | 1,342 | 0.624 | 0.504 |
| 0.65–0.70 | 723 | 0.666 | 0.510 |
| 0.70+ | 0 | — | — |

Refit points: (0.50, 0.50), (0.536, 0.512), (0.574, 0.507),
(0.624, 0.504), (0.666, 0.510) — essentially **flat at ≈ 0.51**.
Stale points (2026-10-09, pre-shrinkage fit): (0.50, 0.50),
(0.536, 0.493), (0.574, 0.508), (0.624, 0.519), (0.662, 0.527).
Post-shrinkage, the empirical hit rate simply does not rise with the
raw probability any more — shrinkage compressed the edges, and what
little slope the s = 1.0 distribution had is gone.

**Out-of-sample evaluation (2024–2025), Brier on over-probability:**

| | Brier | Calibration intercept | Calibration slope |
|---|---|---|---|
| Raw Φ (no curve) | 0.2629 | −0.021 | −0.031 |
| Stale curves | 0.25035 | −0.027 | −0.018 |
| Refit curves | 0.25030 | −0.005 | −1.75 (see note) |

- Refit − stale Brier = **−0.00005** (paired bootstrap, 10,000
  resamples, seed 20261023: 95% CI **[−0.00078, +0.00067]**). The CI
  is not below 0 → under the frozen rule the refit does **NOT** earn
  a RECOMMEND. The stale curves stay live.
- Context: a constant 0.50 forecast scores Brier exactly 0.2500.
  Both curves sit within 0.0004 of that no-information floor — each
  does its real job (the raw Φ probabilities, at 0.2629, are
  overconfident and both curves fix that), but post-shrinkage totals
  probabilities carry almost no discriminative signal for either
  vintage to exploit, so there is nothing measurable for a refit
  to buy.
- Slope note: the refit's −1.75 calibration slope is an artifact,
  not a finding. The refit curve maps every published probability
  into ≈ [0.49, 0.51], so the predictor is nearly constant and a
  logistic slope fit on it is unstable in sign and magnitude. The
  stale and raw slopes (≈ 0) say the same thing more honestly:
  no ranking signal. The decisional metric is the Brier bootstrap,
  per the pre-registration.
- Fairness note: the comparison was, if anything, tilted *toward*
  the stale curves — the 2026-10-09 fit saw data that includes the
  2024–2025 evaluation seasons (fit on the published 2014–2025
  frame), while the refit is genuinely out-of-sample there. The
  refit tied anyway; a tie does not clear the bar.

**Recommendation: do not refit now.** Keep the 2026-10-09 curves.
The refit points are archived in `results.json` if a future
pre-registration (e.g. after a season or two of post-shrinkage live
data) wants to revisit this; on current evidence a refit would
change published probabilities by ≤ ~0.02 and expected calibration
by nothing measurable.

---

## Data gaps and method notes

- **No material gaps.** All three questions were answered from the
  in-repo frame; zero CFBD calls (the quota was never touched).
  Frame B's 2026 partial rows (276 games) were excluded by design —
  the audit universe is the recorded 2014–2025 adoption universe.
- `game_meta.parquet` was not needed: none of the three frozen
  questions uses conference/FCS/wind metadata.
- Q3 sd choice: raw probabilities use the live generator's current
  total_sd (17.72). The fit-window (2014–2023) s = 0.7 residual SD
  is 17.79; using either moves raw probs by < 0.002 and cannot move
  any verdict. Recorded in `results.json` for the record.
- Q2's "same games" is the same 8,947-game universe; the pick *sets*
  necessarily differ between s values (that is what shrinkage does
  to the rule), which the frozen decision rule anticipates — it
  compares the two play records as published-play records.

## Artifacts

All in `research/cfb_totals_shrinkage/`:
`PREREGISTRATION.md` (frozen, pre-run), `audit.py` (runner;
`--only q1|q2|q3`), `results.json` (all numbers at full precision),
this `RESULTS.md`. Nothing else in the repo was created, modified,
or committed by this audit.
