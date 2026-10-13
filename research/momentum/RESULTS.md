# M1 — Momentum / win-streak term (NFL) — RESULTS

**Run:** 2026-10-12, per PREREGISTRATION.md (written before any results).
**Script:** `run_m1.py` (this folder). Data: pattern-study walk-forward CSV,
11,352 games 1980–2024 (discovery 1980–2014 n=8,609; validation 2015–2024 n=2,743).

## Pre-registered gates — BOTH PASSED (against the model)
| Gate | Criterion | Result |
|---|---|---|
| 1 | Validation slope of margin_resid on streak_diff > 0, z ≥ 1.96 | **+0.326 pts/streak-game, z = +5.69** ✓ |
| 2 | Discovery-fitted adjustment (b = +0.261) reduces validation RMSE | 13.260 → 13.185 (**−0.075**) ✓ |

Discovery slope: +0.261 (z = +7.59). Era-stable in every split tested:
1980–94 +0.247 (z 4.31) · 1995–2009 +0.288 (z 5.82) · 2010–14 +0.213 (z 2.45) ·
2015–19 +0.346 (z 4.28) · 2020–24 +0.306 (z 3.77). Within-season streaks
variant (descriptive): even stronger (+0.393, z 6.00 validation).

## Mechanism diagnostics (post-hoc, labeled as such) — the catch
- Streak → (actual − closing line): slope only **+0.097, z = +1.75**.
- Joint regression with line_margin included: streak slope **collapses to
  −0.009 (z = −0.14)**. With our_margin only: survives (+0.239, z = 3.66).
- ATS regrade (validation, |edge| ≥ 1.5, formula verified 100% vs recorded
  ats_win): current **51.3%** (n=1,789) → streak-adjusted **51.1%** (n=1,760).

**Interpretation:** streaks are NOT market-missing momentum. They are a
symptom of our ratings learning too slowly — when a team genuinely improves
or declines, it strings wins/losses together while the walk-forward rating
lags behind; the closing line has already moved. Adding a streak term just
pulls the model toward the market (fewer, duller disagreements), which is
why RMSE improves slightly but ATS does not improve at all.

## Verdict
- **Do NOT ship a streak/momentum term.** It passed the naive gates and
  still isn't an edge — the two-gate pass is exactly why the mechanism
  check matters.
- **The real finding is ratings responsiveness.** This is the second sport
  where "the ratings learn too slowly" shows up: NCAAB section 9 of the
  pattern study found deleting early-season downweighting (faster learning)
  improved RMSE with paired t ≈ 19. Same disease, different symptom.
- **Proposed next test (needs Bryant's yes, per standing rule):** pre-register
  a ratings-responsiveness sweep on the LIVE NFL model (post–Oct 1 EPA
  version — this test ran on the pattern-study Elo replication, so the
  live model may lag differently): vary update speed / recency weighting,
  walk-forward, keep iff RMSE improves with no ATS degradation.
- **Correction to the 2026-10-12 main-chat answer:** the Oct 10 pattern
  study did not test W/L streaks across all sports — only NBA totals
  hotness (flat/null). This M1 test is the first actual NFL momentum test.
