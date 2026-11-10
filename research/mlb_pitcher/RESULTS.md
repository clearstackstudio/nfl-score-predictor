# MLB starting-pitcher layer — can it beat team-only? — RESULTS

**Run:** 2026-10-23, per PREREGISTRATION.md (written and frozen before any
pitcher-layer results were computed).
**Scripts:** `fetch_data.py` (Stats API pull, everything cached under
`cache/`) and `run_test.py` (walk-forward + scoring) in this folder.
**Sample:** 9,718 games, seasons 2023–2026 — the shipped team model's
walk-forward (retrain configuration: alpha=1/40, carryover=0.25, home edge
refit 0.094, sigma=4.135, Platt recalibration as shipped), predictions made
before each update, exactly as in the shipped backtest. Pitcher layer per
`src/mlb/pitcher.py`: prior-season FIP only, regressed IP/(IP+50),
STARTER_SHARE = 0.6 frozen, league-average fallback. No fitted parameters
on the verdict sample.

## Coverage — no season dropped

| Season | Games | Matched to API | Both probables known | Coverage |
|---|---|---|---|---|
| 2023 | 2,430 | 2,430 | 2,429 | 99.96% |
| 2024 | 2,429 | 2,429 | 2,427 | 99.92% |
| 2025 | 2,430 | 2,430 | 2,425 | 99.79% |
| 2026 | 2,429 | 2,429 | 2,427 | 99.92% |

Every game in the scores file matched an API final on (date, teams, score)
— including doubleheaders, disambiguated by score. All four seasons clear
the 90% bar by ~10 points, so the full preregistered sample stands; no
DEFERRED escape was needed. Games missing a probable (10 of 9,718) took
the design's league-average fallback, as a live system would. The layer
actually adjusted 9,482 games (97.6%): mean |starter adj| 0.36 runs,
mean |home−away adj difference| 0.53 runs, max 2.96.

## Pre-registered decision bars — ALL THREE PASS

| Bar | Criterion | Result |
|---|---|---|
| 1 | Brier improves; paired bootstrap 95% CI entirely below 0 (10,000 resamples, seed 20261023) | Δ **−0.000664**, CI **[−0.001200, −0.000135]** ✓ |
| 2 | Margin RMSE does not worsen (Δ ≤ 0) | 4.4851 → 4.4797, Δ **−0.0054** ✓ |
| 3 | Brier worsens in at most 1 of 4 seasons | worsens in **0** of 4 ✓ |

## Numbers

| | Team-only | Pitcher-adjusted | Δ |
|---|---|---|---|
| Brier (9,718 games) | 0.245406 | 0.244742 | **−0.000664** |
| Margin RMSE | 4.4851 | 4.4797 | **−0.0054** |
| Straight-up winners | 5,391 (55.47%) | 5,416 (55.73%) | **+25 winners** |
| Totals RMSE (descriptive) | 4.4919 | 4.4927 | +0.0008 (a wash) |

Per season (Brier team → adjusted):

| Season | Brier Δ | Margin RMSE Δ | SU winners Δ |
|---|---|---|---|
| 2023 | −0.000734 | +0.0038 | +6 |
| 2024 | −0.001220 | −0.0134 | +22 |
| 2025 | −0.000179 | −0.0066 | +5 |
| 2026 | −0.000526 | −0.0056 | −8 |

Brier improves in every season; margin RMSE improves in three of four
(2023 ticks the other way by 0.004, inside noise); the winner count is
net +25, with 2026 the one season where raw flips netted negative (−8)
even though its probabilities still got better calibrated.

**Secondary descriptive (no verdict power, as preregistered):** a share
fitted on 2023–2024 comes out at 0.7, on a flat-bottomed curve (0.5–0.8
all within 0.00008 Brier) — the frozen 0.6 sits inside the sweet spot.
Frozen at 0.7 it would have added Δ −0.000267 Brier on 2025–2026. This
changes nothing: the verdict ran at the frozen 0.6.

**ROI (descriptive only, per preregistration): NOT COMPUTABLE.** No
closing lines for 2023–2026 exist anywhere in the repo — the odds file
(`nba-data/mlb_bonus/oddsDataMLB.csv`) ends 2021-10-03 and the
2022–2026 backfill is scores-only. Rather than invent prices, the ROI
lines are reported as unavailable; the preregistration gives ROI no
verdict power, so the verdict does not rest on it. (Context the sample
cannot change: on 2012–2021, where lines do exist, the team model's
Brier of 0.2444 trailed the line's 0.2402, and a −0.0007 Brier gain does
not close that gap by itself. This test says the pitcher layer makes
the *model* better, not that it beats the market.)

## Verdict

**ADOPT recommendation.** The design in `src/mlb/pitcher.py` — written
before any of these results existed — survives its first honest trial
intact: prior-season FIP, lightly regressed, blended at the frozen 0.6
share, improves win-probability accuracy on 9,718 out-of-sample games
with a bootstrap interval that clears zero, does not cost margin RMSE,
and helps (or at worst ties) in every season individually. The effect
is small — roughly a quarter of the model-vs-line Brier gap from the
2012–2021 study — but it is real, cheap ($0 of data), and mechanically
simple.

Per the preregistration this changes nothing live by itself: the
pitcher layer ships only inside the Feb/Mar 2027 live build, and only
on Bryant's separate approval. Remaining live-build caveats, unchanged
from the design doc: probable-pitcher data must fall back to league
average when TBD (implemented here as the fallback for 10 games), and
the 0.7 fitted-share hint should NOT be adopted on this evidence — the
frozen 0.6 is what was validated; refitting the share is a 2027
validation-logging question, not a finding of this test.

**Data provenance:** MLB Stats API (free, no key), ~1,589 calls, all
cached under `cache/` (735 schedule dates, 734 pitcher season-stat
pulls, 120 team-season league pulls). League FIP constants from exact
aggregation of the 30 clubs' pitching totals (2022: lgERA 3.962, cFIP
+3.106; 2023: 4.326/+3.249; 2024: 4.072/+3.160; 2025: 4.151/+3.128) —
the 2022 constant cross-checks against the published ~3.10.
