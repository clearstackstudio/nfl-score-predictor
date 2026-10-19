# QB recency diagnostic — RESULTS

**Run attempted:** 2026-10-19, on Bryant's explicit approval to run the
diagnostic scoped 2026-10-15. **Preregistration:** `PREREGISTRATION.md`
in this directory. Runner: `run_qb_recency.py`; numbers: `results.json`.

## Outcome: STOPPED at the baseline gate — the test was NOT run

The preregistration's stop rule is explicit: *"reproduce its baseline
first; if the reproduced 2021–24 baseline does not match the published
ATS 47.5% / margin RMSE 14.44, stop and report — do not proceed on a
mismatched baseline."*

Phase 0 ran `src/epa_ratings.run_backtest()` exactly as-is (the harness's
Part A) before anything else:

| Metric (2021–2024, n = 1,107 games) | Published pin | Reproduced today |
|---|---|---|
| ATS (|edge| ≥ 1.5) | 47.5% (399-441-26) | **47.29% (393-438-29)** |
| Our margin RMSE | 14.44 | **14.131** |

Same game set (1,107), different numbers — far outside rounding. The
stop rule fires. No features were built, no regression was fit, and
**no KEEP/KILL verdict exists**. No live model code was touched.

## Why the baseline moved (diagnosed, with evidence)

This is a stale pin in the preregistration, not a code or data failure:

1. The pinned pair (47.5% / 14.44) comes from
   `research/epa_live_backtest/` (2026-10-12), which measured the model
   **before** turnover damping was adopted — it is Arm 0 (w = 1.00) of
   the turnover-damping study.
2. Later the same day, commit `e1056e3` ("Adopt QB-inclusive turnover
   damping (w=0.50) in live EPA ratings", 2026-10-12) changed the live
   ratings: turnover-play EPA is halved in both the team ratings and
   the QB pool (`src/epa_ratings.py`, `TURNOVER_EPA_WEIGHT = 0.50`).
3. The damping study's own robustness arm — w = 0.50 with the QB pool
   damped, i.e. **exactly the adopted configuration** — published
   margin RMSE **14.131** and ATS **47.29% (393-438-29)** on the same
   1,107 games (`research/turnover_damping/RESULTS.md`).
4. Today's reproduction matches that adopted-configuration arm
   digit-for-digit on both gated metrics and the game count
   (393-438-29, 47.29%, 14.131, n = 1,107).

The preregistration (written 2026-10-15) describes the live model
correctly as damped, but pins its stop rule to the pre-damping pair —
the two premises cannot both hold. The live model the test was meant
to run under is the damped one; the pin describes its predecessor.

## Why the pin was not simply corrected and the test run anyway

Re-pinning the baseline mid-run — after seeing the reproduction — is
editing a frozen protocol in light of results, which is what
preregistration exists to prevent. The stop rule is unconditional, so
it was obeyed. The fix is cheap and belongs in the open:

**To unblock** (Bryant's approval, as it was his approval that froze
the original): a short addendum to `PREREGISTRATION.md` that

1. re-pins the baseline gate to the live damped config's reproduced
   pair — ATS 47.29% (393-438-29), margin RMSE 14.131, n = 1,107 —
   leaving everything else (hypothesis, features, splits, bars,
   guardrail) unchanged; and
2. re-bases the runner's internal replication check, which is pinned
   to the same pre-damping artifacts (the harness's `per_game.csv`
   and the 399-441-26 / 14.4439 aggregates) and would halt a re-run
   for the identical reason. The damping study's robustness per-game
   output (`research/turnover_damping/per_game_robustness_w0.50_qb.csv`,
   the adopted configuration) is the natural reference for the
   re-based check.

The runner built for this test (`run_qb_recency.py`: baseline gate →
2021–2025 walk-forward with features computed at each game's cutoff →
frozen verdict logic) then runs with only those two pins changed.

## Secondary finding recorded while stopping (data, for the re-run)

`spreadspoke_scores.csv` (the line store) ends at 2024: it has zero
2025 rows, although 2025 play-by-play and schedules are complete in
the repo. The primary test needs no lines, but the descriptive ATS
split does; the runner already handles this by taking 2025 closing
spreads from `data/schedules_games.parquet` (`spread_line`, verified
against spreadspoke on 2021–2024: same convention, corr 0.996, 66%
identical, mean |diff| 0.24 pts; scores agree 99.9%). Flagged here so
the addendum can ratify or replace that choice before the re-run.
