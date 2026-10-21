# NHL rest-effect add-on test — RESULTS

Run 2026-10-20, exactly per `PREREGISTRATION.md` (committed first,
7dda413, before any rest-model computation touched validation).
Script: `rest_test.py`; machine-readable results: `rest_results.json`.
Bryant approved the run 2026-10-20. **No production change was made —
adoption is Bryant's separate decision.**

## Fit (discovery 2019-20 → 2022-23, n = 4,573)

- **Fitted β = +0.05 goals per rest-day of differential** (d capped
  at ±3, so the largest adjustment is ±0.15 goals, split symmetrically:
  λ_home +β·d, λ_away −β·d, floored at 0.5). Sign is as expected: the
  better-rested team scores more.
- Discovery Brier at β*: **0.2353** vs β=0: **0.2356** (Δ −0.0003).
- The discovery curve is very flat: every β in [+0.03, +0.06] rounds to
  0.2353, and the whole positive half of the grid sits within 0.0003 of
  the minimum. The direction is consistent (all β < 0 are worse than
  β = 0, monotonically), the exact magnitude is loosely pinned.

## Judge (validation 2023-24 → 2025-26, n = 3,935, raw pipeline)

| Metric | Frozen v1 | Rest model (β=+0.05) |
|---|---|---|
| Moneyline Brier (raw) | 0.2401 | **0.2394** |
| SU accuracy (raw) | 57.08% | 57.28% |
| Totals RMSE | 2.327 | 2.327 |

- Per-game Brier difference (v1 − rest): mean **+0.00075**.
- Paired bootstrap (10,000 resamples, seed 20261020): 95% CI
  **[+0.00027, +0.00123]** — excludes 0.
- Totals guardrail: the term is symmetric (±β·d cancels in the total),
  so predicted totals move only where the 0.5 λ-floor binds; RMSE is
  unchanged at 2.327 (limit: ≤ 2.337). Guardrail passes.
- Context: the rest signal is present on less than half the slate —
  47.3% of validation games have d ≠ 0, 12.9% have |d| ≥ 2. Away teams
  played on one day's rest (back-to-back) in 20.0% of games, home
  teams in 10.2%.

## Verdict — ADOPT bar CLEARED (per the frozen criteria)

- (a) Validation Brier improves: 0.2394 < 0.2401 ✓
- (b) Bootstrap 95% CI on the difference excludes 0: [+0.00027, +0.00123] ✓
- Guardrail: totals RMSE unchanged (2.327 ≤ 2.337) ✓

Honest magnitude note: the gain is real but small — about 0.3% relative
on Brier, with SU up 0.2 points. It clears the pre-registered bar as
frozen; it does not change the v1 market verdict (no moneyline edge —
this is a slightly better probability, not an edge claim), and per the
preregistration the production model stays exactly as-is until Bryant
decides on adoption separately.
