# NFL explicit penalty term — pre-registered test results

**Date:** 2026-10-12 · **Approved by:** Bryant (measurement only; no live code/data changed)
**Pre-registration:** `goals/ultimate-multi-sport-prediction-model/hidden_files/penalty-term-preregistration.md` (written before any test was run)
**Interpreter:** `.venv-cfb/bin/python` (pandas 3.0.6 / pyarrow) — system `python3` cannot read the parquet inputs.
**Artifacts:** `run_penalty_term.py` (runner), `metrics.json`, `descriptives.json`, `arm0_verification.json`, `per_game_arm{0,1,2,R}.csv` (1,107 rows each). No git commit/push; `src/` and `data/` untouched.

## Verdict (up front)

**NULL — keep the model as-is. No arm clears the pre-registered adoption bar, and the primary metric moves the wrong way in every treated arm.**

Crediting penalty-only-play EPA to the ratings **worsens overall margin RMSE** at 100% weight (14.511 vs 14.444 baseline, **+0.067**), at 50% weight (14.461, **+0.017**), and in the denominators robustness check (14.539, **+0.095**) — where the bar required an *improvement* of at least 0.05. The consistency leg fails too: Arm 1 worsens margin RMSE in **all 4 seasons**, Arm 2 in 3 of 4. The one metric that does move favorably — ATS, +0.6 to +1.25pp across the treated arms — is (a) not the primary metric, (b) worth ~9 net picks on ~840 decided games (SE ≈ 1.7pp, so indistinguishable from noise), and (c) exactly the kind of single-metric bright spot the pre-registration said to report as a null anyway. Totals get no help either: total RMSE is worse at 100% weight (15.202 vs 15.169) and a dead tie at 50% (15.168 vs 15.169), with OU% flat-to-worse in both.

Interpretation: the blind spot is real but it is mostly **noise, not signal**. A team-game carries ±2.30 EPA of penalty-only plays (sd), while the persistent team-level component is only ~±0.5 EPA/game across a season (see descriptives). Injecting the full per-game quantity into a recency-weighted 17-game window adds variance faster than it adds information — and the measurement says precisely that, in 11 of 12 arm-seasons on the primary metric.

## Frame check (pre-committed, passed)

Arm 0 was run through this study's walk-forward loop with the unmodified `load_team_games()` frame and checked with the baseline study's own `verify_against_a`: **bit-identical to Config A of the 2026-10-12 live-EPA backtest — 0.0 difference on every metric** (games 1,107; SU 62.6%; margin RMSE 14.4439 vs line 12.7259; ATS 399-441-26 = 47.50%; total RMSE 15.1691 vs line 13.0767; OU 376-386-13 = 49.34%). Same graded game set (n = 1,107, identical per-season counts) in all four arms, so every A↔arm difference is attributable to the penalty treatment alone.

## What counted as a "penalty-only play"

Per the pre-registration: a PBP row **not** counted by the current pass/rush filter that carries a penalty, valued at its nflverse `epa`. Operationalized as `play_type == "no_play"` AND `penalty == 1` AND not a pass/rush attempt AND posteam/defteam present — i.e., rows whose only content is the penalty: false starts, delay of game, encroachment, unsportsmanlike, and pass/run plays nullified by a foul (DPI, offensive holding "No Play" rows), where the recorded EPA is the penalty's field-position value.

- **10,115 such plays, 2021–2024** (2,532 / 2,383 / 2,459 / 2,741 per season). The `epa` column is populated on **100%** of them — the pre-registered ep-difference fallback was never needed.
- Attribution (per pre-reg): credited to the possession team's offensive EPA sum and charged to the defense's sum, exactly like a scrimmage play; the EPA sign already encodes who benefited.
- Deliberately **excluded**: 1,174 penalty-carrying rows on punt (674), kickoff (423), extra-point (64), and field-goal (12) plays, plus 1 row with null play_type. On those rows the recorded EPA is dominated by the special-teams play itself (the punt/kick outcome), not the penalty, so they are not "penalty-only" plays under the registered definition. Including them would have been a different intervention (adding special-teams plays to the ratings), not the one Bryant approved testing.

## Results

Line benchmarks are identical in every arm (margin 12.726, total 13.077) — the closing line is never an input.

### Arm 0 — baseline (current code)

Overall: n=1,107 · SU 62.6% · margin RMSE **14.444** · ATS 47.50% · total RMSE 15.169 · OU 49.34%

| Season | n | Margin RMSE (ours / line) | ATS w-l-p | ATS% (picks) | Total RMSE (ours / line) | OU w-l-p | OU% (picks) |
|---|---|---|---|---|---|---|---|
| 2021 | 253 | 16.518 / 13.480 | 88-115-3 | 43.35 (206) | 15.905 / 13.409 | 88-80-3 | 52.38 (171) |
| 2022 | 284 | 12.772 / 11.457 | 96-111-5 | 46.38 (212) | 14.952 / 13.226 | 98-97-2 | 50.26 (197) |
| 2023 | 285 | 14.658 / 13.260 | 106-105-10 | 50.24 (221) | 15.780 / 13.123 | 94-124-3 | 43.12 (221) |
| 2024 | 285 | 13.811 / 12.692 | 109-110-8 | 49.77 (227) | 14.051 / 12.573 | 96-85-5 | 53.04 (186) |
| **All** | **1,107** | **14.444 / 12.726** | **399-441-26** | **47.50 (866)** | **15.169 / 13.077** | **376-386-13** | **49.34 (775)** |

### Arm 1 — penalty EPA at 100%, denominators unchanged

Overall: n=1,107 · SU 62.6% · margin RMSE **14.511** (Δ **+0.067 worse**) · ATS 48.51% · total RMSE 15.202 (Δ +0.033 worse) · OU 48.18%

| Season | n | Margin RMSE (ours / line) | ATS w-l-p | ATS% (picks) | Total RMSE (ours / line) | OU w-l-p | OU% (picks) |
|---|---|---|---|---|---|---|---|
| 2021 | 253 | 16.625 / 13.480 | 88-114-3 | 43.56 (205) | 16.095 / 13.409 | 80-88-3 | 47.62 (171) |
| 2022 | 284 | 12.844 / 11.457 | 99-108-5 | 47.83 (212) | 14.942 / 13.226 | 99-99-2 | 50.00 (200) |
| 2023 | 285 | 14.678 / 13.260 | 104-102-11 | 50.49 (217) | 15.730 / 13.123 | 94-120-3 | 43.93 (217) |
| 2024 | 285 | 13.881 / 12.692 | 115-107-8 | 51.80 (230) | 14.064 / 12.573 | 97-91-5 | 51.60 (193) |
| **All** | **1,107** | **14.511 / 12.726** | **406-431-27** | **48.51 (864)** | **15.202 / 13.077** | **370-398-13** | **48.18 (781)** |

### Arm 2 — penalty EPA at 50%, denominators unchanged

Overall: n=1,107 · SU 62.4% · margin RMSE **14.461** (Δ **+0.017 worse**) · ATS 48.10% · total RMSE 15.168 (Δ −0.001, a tie) · OU 49.15%

| Season | n | Margin RMSE (ours / line) | ATS w-l-p | ATS% (picks) | Total RMSE (ours / line) | OU w-l-p | OU% (picks) |
|---|---|---|---|---|---|---|---|
| 2021 | 253 | 16.547 / 13.480 | 88-111-3 | 44.22 (202) | 15.967 / 13.409 | 88-83-3 | 51.46 (174) |
| 2022 | 284 | 12.796 / 11.457 | 99-109-5 | 47.60 (213) | 14.936 / 13.226 | 99-98-2 | 50.25 (199) |
| 2023 | 285 | 14.657 / 13.260 | 107-105-11 | 50.47 (223) | 15.744 / 13.123 | 95-125-3 | 43.18 (220) |
| 2024 | 285 | 13.826 / 12.692 | 111-112-8 | 49.78 (231) | 14.042 / 12.573 | 95-84-5 | 53.07 (187) |
| **All** | **1,107** | **14.461 / 12.726** | **405-437-27** | **48.10 (869)** | **15.168 / 13.077** | **377-390-13** | **49.15 (780)** |

### Arm R — ROBUSTNESS ONLY (100% + penalty plays added to the denominators; not a candidate)

Overall: n=1,107 · SU 62.5% · margin RMSE **14.539** (Δ +0.095 worse) · ATS 48.75% · total RMSE 15.215 (Δ +0.046 worse) · OU 48.07%

| Season | n | Margin RMSE (ours / line) | ATS w-l-p | ATS% (picks) | Total RMSE (ours / line) | OU w-l-p | OU% (picks) |
|---|---|---|---|---|---|---|---|
| 2021 | 253 | 16.621 / 13.480 | 87-114-3 | 43.28 (204) | 16.101 / 13.409 | 80-89-3 | 47.34 (172) |
| 2022 | 284 | 12.889 / 11.457 | 101-108-5 | 48.33 (214) | 14.971 / 13.226 | 100-100-2 | 50.00 (202) |
| 2023 | 285 | 14.728 / 13.260 | 106-103-11 | 50.72 (220) | 15.721 / 13.123 | 96-124-3 | 43.64 (220) |
| 2024 | 285 | 13.906 / 12.692 | 116-106-8 | 52.25 (230) | 14.093 / 12.573 | 97-90-5 | 51.87 (192) |
| **All** | **1,107** | **14.539 / 12.726** | **410-431-27** | **48.75 (868)** | **15.215 / 13.077** | **373-403-13** | **48.07 (789)** |

(The denominators variant also slightly changes the trailing pace inputs, since pace is averaged from `off_plays` — inherent to the check as registered. It confirms Arm 1's direction is not a denominator artifact: same RMSE worsening, same small ATS uptick.)

## Verdict against the pre-registered adoption bar

Bar: improve overall margin RMSE by ≥ 0.05 **and** improve-or-tie margin RMSE in ≥ 3 of 4 seasons **and** not worsen overall ATS.

| Arm | Overall margin RMSE (need ≤ 14.394) | Seasons improve-or-tie (need ≥ 3/4) | ATS not worse (need ≥ 47.50%) | Verdict |
|---|---|---|---|---|
| Arm 1 (100%) | 14.511 (+0.067) ✗ | 0/4 ✗ | 48.51% ✓ | **Fails** |
| Arm 2 (50%) | 14.461 (+0.017) ✗ | 1/4 ✗ | 48.10% ✓ | **Fails** |
| Arm R (robustness) | 14.539 (+0.095) — | 0/4 — | 48.75% — | Not a candidate; confirms Arm 1 |

**Candidate changes for approval: none.** Per the pre-registration, this is reported as a null: the explicit penalty term is not proposed, at either weight. The gap in the ratings is real (next section) but filling it this way degrades the primary metric, so the model stays as-is.

On the ATS uptick, to be explicit about why it does not rescue the proposal: it appears in all three treated arms (+1.01 / +0.60 / +1.25pp), which is a consistent direction — but it amounts to 7–11 net decided picks against an SE of ≈1.7pp, it comes packaged with *worse* point forecasts (RMSE is what the ratings are for; ATS at a fixed 1.5 threshold is a coarse slice of them), and the pre-registration named margin RMSE as primary precisely so a favorable secondary slice could not carry a change on its own. If a future study wanted to pursue the ATS direction, it would need its own pre-registration and an out-of-sample window; nothing here is tuned on 2025–2026, so that window remains clean for such a test.

## Descriptive context — the size of the blind spot (per pre-registration; not decision inputs)

- **Volume:** 10,115 penalty-only plays across 2,278 team-games — **4.44 per team-game** (median 4, max 16).
- **Magnitude per team-game** (offensive attribution; defensive attribution mirrors the same plays): mean **−0.14 EPA**, median −0.33, **sd 2.30**, 5th–95th percentile **−3.53 to +3.90**. In **17.3%** of team-games the excluded penalty EPA is at least 3 points in one direction. Counting both teams, the average game contains **3.52 points** of absolute penalty-only EPA (p95: 7.5).
- **Spread across teams:** season-mean penalty EPA per game, by team, has a within-season cross-team sd of **0.49–0.58** EPA/game. Extremes: **+1.51 EPA/game (2023 Jacksonville)** and **−1.45 EPA/game (2024 Baltimore)**. So disciplined-vs-flagged team differences persist at roughly ±0.5 EPA/game across a season — about half a point of expected margin — while the game-to-game fluctuation around that (±2.3) is four to five times larger.
- **Reading:** the excluded quantity is not trivially small — it is larger per game than the entire measured effect of several features this project has tested. It fails not because it is tiny but because at the ratings' trailing-window scale it is mostly variance: a team's last 17 games of penalty EPA are a poor estimate of its next game's, and the walk-forward prices that in as worse RMSE in 11 of 12 arm-seasons.

## Method notes and caveats

- The walk-forward loop, QB adjustment, recency weighting, totals formula, EPA-constant calibration, and grading are the baseline study's, unchanged; in each treated arm the EPA-constant calibration uses that arm's offensive EPA (penalties included), consistent with the pre-registered "penalty EPA also feeds the totals via the offensive ratings." Only the team-games frame differs across arms, constructed by folding penalty aggregates into the unmodified `load_team_games()` output (same rows, same order, same opponents — verified by assertion in the runner).
- 2021 remains the burn-in season (no prior-season PBP; 15 cold-start skips inherited from the frame) and is the worst season in every arm, baseline included. The verdict does not hinge on it: excluding 2021, Arm 1 still worsens all three remaining seasons and Arm 2 two of three.
- Nothing in `src/`, `site/`, or `data/` was modified; no commit or push was made. (Process note: an initial combined background run was killed mid-Arm-1 by the VM's process management; each arm was then run individually to completion, and Arm 0's verification passed identically on both occasions.)
