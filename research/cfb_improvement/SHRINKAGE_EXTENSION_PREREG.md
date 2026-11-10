# Pre-registration — CFB totals shrinkage grid extension (H-T3 follow-up)

Written 2026-10-12 PT, **before** any extension numbers are computed.
Status: awaiting Bryant's go. Nothing here changes the live model.

## Why this exists

H-T3 (see `RESULTS.md`) validated totals shrinkage: walk-forward chose
s = 0.7 in all 11 evaluation seasons and total RMSE improved in 11/11
seasons (18.73 → 17.73). But 0.7 was the smallest factor on the tested
grid and the improvement was still increasing at the boundary — the
true optimum may be lower. Tuning further inside the original study
would break its own rules, so the extension gets its own
pre-registration. This is decision #1 from the 2026-10-12 diagnostic
delivery: adopt 0.7 as validated, or run this extension first.

## Hypothesis

Extending the shrinkage grid below 0.7 finds a factor whose
walk-forward total-RMSE beats fixed s = 0.7 by a margin that survives
the adoption bar. Null: no extended factor clears the bar, and 0.7
stands as the validated choice.

## Fixed design (no changes after seeing results)

- **Frame:** frame B (`frame_B.parquet`), identical to H-T3 — same
  8,947 games, 2014–2025, chronological walk-forward ordering. 2026
  reported separately, never tuned on.
- **Formula (unchanged):** `total' = epa_const + s·(our_total − epa_const)`.
  Margins/spreads untouched.
- **Grid:** s ∈ {0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70}. Fixed
  s = 1.00 (current) and fixed s = 0.70 (H-T3 winner) are the two
  comparison baselines. No values below 0.40 will be tested in this
  study; if the walk-forward piles up at 0.40, that is reported as a
  boundary result, not chased further without a new pre-registration.
- **Walk-forward rule (unchanged from H-T3):** for each evaluation
  season, s is chosen on prior seasons only, minimizing prior-season
  total RMSE over the grid.
- **Primary metric:** total RMSE (pooled and per-season). This is an
  accuracy question, exactly as in H-T3.
- **Reported but not decisional:** OU% under the live rule
  (|edge| ≥ 1.0, circuit breaker as live) at the chosen s vs s = 0.7,
  and live-rule pick volume change. Shrinkage is adopted for accuracy,
  never on an OU% claim.

## Adoption bar (same as the parent study)

A factor replaces 0.7 only if the walk-forward procedure (a) improves
total RMSE over fixed s = 0.7 in a **majority of evaluation seasons
AND overall**, and (b) the pooled gain over s = 0.7 is at least
**0.10 RMSE** — below that, the simpler already-validated 0.7 wins on
parsimony. If the bar is not met, the verdict is "adopt 0.7 as-is"
and this question is closed.

## What each outcome means

- **Extension clears the bar →** bring Bryant the winning s with the
  per-season table; live change still needs his yes.
- **Extension fails →** recommend adopting 0.7 immediately; no further
  grid work on shrinkage.
- **Walk-forward piles at the 0.40 boundary →** report it as-is;
  going lower requires a new pre-registration and Bryant's call.

## Cost / feasibility

Reuses the already-captured frame B — shrinkage is a post-hoc
transform in `analyze_main.py` (H-T3 block), so this is a grid
extension of existing code, minutes of compute, **zero CFBD calls**
(quota-safe while CFBD is exhausted until ~Nov 1). No live files are
touched by the test itself.
