# NFL publish threshold — RESULTS

**Run:** 2026-10-23, on Bryant's explicit approval the same day (part
of the four-test improvement package). **Preregistration:**
`PREREGISTRATION.md` in this directory (frozen before any threshold
results were computed). Runner: `run_nfl_threshold.py`; numbers:
`results.json`; per-game walk-forward rows: `per_game.csv`. Measurement
only — no live model code, constant, generator setting, or site data
was changed. The live publish threshold remains |spread_edge| ≥ 0.5 in
`src/weekly_picks.py` regardless of the verdict below.

## Verdict: KILL

No candidate threshold satisfies the frozen decision rule, so the
current 0.5 threshold stands — not because it was validated, but
because nothing beat it under the rule. The hypothesis that bigger
edges win more is not supported: on discovery, win% *falls* as the
threshold rises; on validation it rises; an effect whose sign flips
between eras is not an effect.

**The frozen decision rule** (a τ* earns an ADOPT recommendation iff
ALL hold): (1) validation (2024–2025) ATS win% ≥ 52.4% (the -110
breakeven); (2) validation plays n ≥ 100; (3) the same τ* shows
discovery (2021–2023) ATS win% ≥ 51.5%.

## The full table — every τ, both splits (as registered)

| τ (pts) | Disc. W-L-P | Disc. ATS% | Disc. ROI | Val. W-L-P | Val. ATS% | Val. ROI |
|---|---|---|---|---|---|---|
| 0.5 ← current | 350-392-23 (n=765) | 47.2% | -9.6% | 253-272-10 (n=535) | 48.2% | -7.9% |
| 1.5 | 289-323-21 (n=633) | 47.2% | -9.5% | 212-242-9 (n=463) | 46.7% | -10.6% |
| 2.5 | 218-268-19 (n=505) | 44.9% | -13.8% | 174-198-8 (n=380) | 46.8% | -10.5% |
| 3.5 | 170-216-16 (n=402) | 44.0% | -15.3% | 147-161-7 (n=315) | 47.7% | -8.7% |
| 4.5 | 128-171-12 (n=311) | 42.8% | -17.6% | 127-129-5 (n=261) | 49.6% | -5.2% |
| 5.5 | 104-133-12 (n=249) | 43.9% | -15.4% | 103-98-1 (n=202) | 51.2% | -2.2% |

ATS% excludes pushes; ROI is flat 1-unit bets at -110 with pushes in
the denominator. Every cell in both splits at every τ has negative
ROI — consistent with the site's long-published position that the
model has no demonstrated betting edge.

## The closest candidate against each bar (τ = 5.5)

τ = 5.5 is the best validation performer and the only τ whose
validation win% clears 50%. It still fails two of the three bars:

- **Bar 1 — validation ATS ≥ 52.4%: FAIL.**
  103-98-1 → 51.24%, which is 1.16 pp short of the -110 breakeven.
  (Every other τ is further away: the next best validation figure is
  49.6% at τ = 4.5.)
- **Bar 2 — validation n ≥ 100: PASS.**
  n = 202 plays. (This bar passes at every τ; volume was never the
  binding constraint.)
- **Bar 3 — discovery ATS ≥ 51.5% at the same τ: FAIL, by 7.6 pp.**
  104-133-12 → 43.88%. Discovery never reaches 51.5% at *any* τ —
  its best is 47.2%, at τ = 0.5 and 1.5 — and its win% declines
  monotonically-ish as τ rises (47.2 → 47.2 → 44.9 → 44.0 → 42.8 →
  43.9), the opposite direction from validation (48.2 → 46.7 → 46.8
  → 47.7 → 49.6 → 51.2). This is exactly the era-dependence the
  consistency bar exists to catch: on 2021–2023 form, publishing only
  the biggest disagreements would have been the *worst* strategy in
  the table.

Since no τ passes all three bars, there is no τ*, and the registered
tie-break (smallest qualifying τ, committed in the runner before the
run) was never invoked.

## Volume implication (descriptive)

Validation spans 44 distinct season-weeks (2024–2025, incl.
playoffs). Plays and winners per week by τ, validation:

| τ | Plays/wk | Winners/wk |
|---|---|---|
| 0.5 (current) | 12.2 | 5.8 |
| 1.5 | 10.5 | 4.8 |
| 2.5 | 8.6 | 4.0 |
| 3.5 | 7.2 | 3.3 |
| 4.5 | 5.9 | 2.9 |
| 5.5 | 4.6 | 2.3 |

Even at the best-percentage τ (5.5), the card would have produced
*fewer* winners per week (2.3 vs 5.8) — the volume loss swamps the
modest win% gain, and the win% gain itself failed the bars above.

## Baseline gate (passed before any threshold was trusted)

1. **Reproduction.** `run_backtest()` exactly as-is returned ATS
   **47.29%** (393-438-29) and margin RMSE **14.131** on **1,107**
   games (2021–2024) — the frozen pins, inside the registered
   tolerances (|ΔATS%| ≤ 0.15 pp, |ΔRMSE| ≤ 0.02).
2. **Per-game replication.** The extended walk-forward's 2021–2024
   rows replicate
   `research/turnover_damping/per_game_robustness_w0.50_qb.csv`:
   1,107 of 1,107 games merge, ATS at |edge| ≥ 1.5 is 393-438-29,
   margin RMSE 14.130860, max |Δ our_margin| = 3.6e-15. The 2025
   extension therefore runs on a verified frame. All 1,392 games
   (2021–2025) were predicted; every game in both splits is scored
   at every τ from the same rows.

## Method notes

1. **Rounded-edge convention.** The live generator rounds
   `spread_edge` to 0.1 *before* thresholding
   (`src/weekly_picks.py`: "Round BEFORE thresholding: published
   edges are 0.1-rounded"), and the preregistration's play definition
   is the generator's. The table therefore thresholds the 0.1-rounded
   edge. `per_game.csv` carries both the raw and rounded edges, so
   either convention can be recomputed; the margins themselves are
   identical under both (replication note 2 above is computed on the
   raw edge, as in the prior harnesses).
2. **Lines.** 2021–2024 closing spreads come from the repo line store
   (spreadspoke via `backtest.closing_home_spread`); 2025 spreads
   from `data/schedules_games.parquet` (`spread_line`) — the ratified
   source from the 2026-10-19 addendum, same as the prior two
   diagnostics. Only the descriptive ROI/ATS arithmetic touches a
   line at all.
3. **Pushes and ROI.** A play pushes when the actual margin equals
   the line exactly (|actual − line| < 0.01). ROI counts pushes in
   the denominator with 0 profit, the standard flat-bet accounting.
4. **What was NOT tried** (per the anti-data-mining clause): no
   cover-probability thresholds, no totals, no per-season τ, no
   τ values outside the frozen six. The disagreement watch
   (checkpoint 2026-12-09) remains a separate, measurement-only
   instrument and was not touched.

## What this does and doesn't mean

It means the 15-25-2 live start is not explained by "we publish too
many small plays": historically, the small plays are not the losing
part — if anything the big-edge tail was worse in 2021–2023. The live
record is what the preregistration's KILL branch said it would be:
variance on a no-edge model, on a play definition that publishes
nearly every disagreement. It does **not** mean thresholds can never
matter — it means these six, on this model, on 2021–2025, did not
clear a breakeven bar with cross-era consistency. Any future
threshold idea is a new preregistration. The live generator,
publishing rules, and parlay construction are unchanged; adoption of
anything remains Bryant's separate decision.
