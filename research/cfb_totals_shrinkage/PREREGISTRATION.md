# CFB totals — post-adoption audit of TOTAL_SHRINKAGE = 0.7 — PREREGISTRATION

**Written:** 2026-10-23, BEFORE any audit numbers were computed.
**Approved to run:** 2026-10-23 (Bryant, full test package).
**Trigger:** the live 2026 CFB total-play record is 32-46 (41%), but
both graded weeks predate the shrinkage adoption (2026-10-13), so the
live record cannot judge it. The adoption evidence was walk-forward
totals RMSE (11/11 seasons improved, 18.73 → 17.73, recorded in
`cfb/cfb_ratings.py` and `research/cfb_improvement/`). This audit
checks the adoption from the angles the adoption did not cover.

## Questions (three, frozen)

1. **Reproduction.** Do the adopted walk-forward headline numbers
   reproduce from the research artifacts / a fresh walk-forward run
   (s = 0.7 vs s = 1.0, totals RMSE by season, 2014–2025 FBS)?
2. **Play basis.** On published-play terms (the generator's totals
   play rule applied to walk-forward rows), is the OU record with
   s = 0.7 closer to 50% than with s = 1.0, on the same games? RMSE
   can improve while the play record does not — Bryant experiences
   the play record.
3. **Recalibration refit (the Nov 1 checkpoint, pulled forward).**
   The live recalibration curves are still the 2026-10-09
   pre-shrinkage fit. Refit them on post-shrinkage predictions
   (fit 2014–2023, evaluate 2024–2025): does the refit improve
   totals probability calibration (Brier / calibration slope on
   over-probability) out of sample vs. the stale curves?

## Data

- The CFB walk-forward machinery and frames in `cfb/` +
  `research/cfb_improvement/` (frame_A/B/B8.parquet, game_meta) —
  reuse, don't redefine. Seasons 2014–2025, FBS only, the 8,947-game
  restated universe.
- Splits for Q3: fit 2014–2023, evaluation 2024–2025. Q1–Q2 use the
  full walk-forward (every prediction out of sample by construction).

## Decision rules

- Q1: reproduction within rounding of the recorded numbers →
  CONFIRMED; any material mismatch → FLAGGED, stop, report.
- Q2: report both OU records; s = 0.7 is **supported on play basis**
  iff its OU win% is at least as close to 50% as s = 1.0 AND its
  totals RMSE is lower. A play-basis failure does not auto-revert an
  RMSE-justified adoption — it is reported to Bryant as a tension,
  with a recommendation.
- Q3: the refit earns a **RECOMMEND** (to Bryant, separate approval —
  live curves do not change under this run) iff it improves
  out-of-sample Brier on totals probabilities vs. the stale curves,
  paired bootstrap 95% CI below 0 (10,000 resamples, seed 20261023).

## Anti-data-mining clause

One shrinkage pair (0.7 adopted vs 1.0), no re-sweep of s values
(that was the October package, closed), one play rule (the live
generator's), one refit method (the existing recalibration code's).
Anything else is a new preregistration.

## Honest prior

Q1 confirms (the October work was careful). Q2 is the genuinely open
question — the live pre-adoption play record (32-46 on s = 1.0-era
boards) is the baseline the play-basis comparison must beat, and
RMSE gains concentrated in blowout games may not move play outcomes.
Q3 likely recommends — stale curves fitted to a different totals
distribution are miscalibrated almost by definition. Cost: $0.
