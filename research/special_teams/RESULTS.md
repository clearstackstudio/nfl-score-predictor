# Special-teams inclusion — walk-forward test of the pre-registered arms

**Date:** 2026-10-12 · **Approved by:** Bryant (measurement only; no live code/data changed)
**Pre-registration:** `goals/ultimate-multi-sport-prediction-model/hidden_files/special-teams-preregistration.md` (written before any run)
**Interpreter:** `.venv-cfb/bin/python` — **Artifacts:** `run_special_teams.py` (runner, staged: descr / arm0 / arm1 / arm2), `metrics.json`, `descriptives.json`, `arm0_verification.json`, `per_game_arm0.csv`, `per_game_arm1.csv`, `per_game_arm2.csv`, `arm1.log` / `arm2.log`. No git commit/push.

## Verdict (up front)

**No arm clears the pre-registered adoption bar, so the recommendation is: keep the model as-is.** The bar required Arm 1 (ST EPA folded into the ratings sums, denominators unchanged) to (1) improve overall margin RMSE by ≥ 0.05, (2) improve or tie margin RMSE in ≥ 3 of 4 seasons, and (3) not worsen overall ATS. Arm 1 fails (1) and (2):

- **Margin RMSE is a near-exact wash, fractionally worse:** 14.444 → **14.452** (+0.008) — against a required improvement of 0.05. Per season it splits 2-2 (better in 2021 and 2022, worse in 2023 and 2024).
- **ATS ticks up slightly** — 47.50% → 47.73%, on more qualifying picks (905 vs 866) — but the bar's primary criterion is margin RMSE, and a ~0.2pp ATS move is far inside noise (SE ≈ 1.7pp). The same discipline applied in the turnover study (where ATS slipped while RMSE improved, and nothing was rescued) applies here in mirror image: a secondary metric moving the "right" way does not rescue a failed primary.
- **Totals get clearly worse:** total RMSE 15.169 → **15.530** (+0.361), OU 49.34% → 49.06%. The robustness arm (ST plays also counted in denominators) is no better on any headline metric (margin RMSE 14.514, ATS 47.27%, total RMSE 15.524).
- **The pre-registered descriptives explain the result.** The favorable prior — kickers/punters are stable personnel — does **not** show up as stable team-level special-teams EPA: season-to-season persistence of team net ST EPA per game is weak and unstable (consecutive-season r = +0.26, −0.05, +0.14; mean ≈ **+0.12**), much closer to the penalty/turnover components (≈ 0) than to a durable trait. And the totals degradation is consistent with the pre-registration's double-counting concern: a punt's EPA embeds the field position the offense left, and a field-goal attempt exists because a drive stalled — folding that context back into the off/def sums re-counts what the scrimmage ratings already carry, and in a 17-game recency window the added variance lands directly in the totals.

## Method

- **Frame:** identical to the live-EPA backtest (Config A) and the penalty/turnover studies — walk-forward 2021–2024, same 1,107 graded games, closing lines as benchmark only, ATS @ |edge| ≥ 1.5, OU @ |edge| ≥ 3.0, no wind, no circuit. The walk-forward loop and grading functions are the penalty study's replication of the baseline runner, imported/shared so grading semantics are identical by construction.
- **Special-teams play:** `play_type` in {punt, kickoff, field_goal, extra_point} with `epa` populated and posteam/defteam present. Verified on the data before running: zero epa/posteam/defteam nulls among ST rows, and **zero overlap with the pass/rush filter** — disjoint by construction, as the pre-registration asserts. The play's full EPA is credited symmetrically (posteam → offensive sum, defteam → defensive sum); a return's value stays inside its play's EPA. 1,173 penalty-flagged ST plays are included once, as ST plays via their EPA (the penalty study excluded them because it was isolating the penalty component; this study does not revisit that).
- **Arms:** Arm 0 baseline; Arm 1 (primary) ST EPA added to the off/def sums with play-count denominators unchanged, mirroring the penalty study's primary construction; Arm 2 (robustness, labeled) additionally counts ST plays in the denominators. QB adjustment pool and formula untouched; no damping weights tested (per pre-reg, a damping follow-up would be a separate study).
- **One documented construction note** (inherited from the penalty study's runner): the loop's `epa_const` calibration uses the passed frame's offensive EPA, i.e. the treated frame in treated arms. The primary metrics (margin RMSE, ATS) do not involve `epa_const` at all, so the verdict cannot hinge on this choice.
- **Baseline discipline — PASSED.** Arm 0 reproduced Config A **bit-identical**: 0.0 difference on games (1,107), SU%, both margin RMSEs, ATS w-l-p (399-441-26), both total RMSEs, and OU w-l-p (376-386-13) — see `arm0_verification.json`.

## Results — overall

Line benchmarks are identical across arms (margin RMSE 12.726, total RMSE 13.077).

| Arm | SU% | Margin RMSE (ours / line) | ATS w-l-p (picks) | ATS% | Total RMSE (ours / line) | OU w-l-p (picks) | OU% |
|---|---|---|---|---|---|---|---|
| Arm 0 (baseline) | 62.6 | **14.444** / 12.726 | 399-441-26 (866) | **47.50** | **15.169** / 13.077 | 376-386-13 (775) | **49.34** |
| Arm 1 (ST in sums) | 61.8 | **14.452** / 12.726 | 420-460-25 (905) | **47.73** | 15.530 / 13.077 | 391-406-11 (808) | 49.06 |
| Arm 2 (ST in sums + denominators) | 61.6 | 14.514 / 12.726 | 416-464-27 (907) | 47.27 | 15.524 / 13.077 | 389-407-13 (809) | 48.87 |

## Results — per season

Margin RMSE (ours / line) and ATS% @ ≥1.5:

| Season | n | Arm 0 | Arm 1 | Arm 2 |
|---|---|---|---|---|
| 2021 | 253 | 16.518 / 13.480 · ATS 43.3% | 16.474 / 13.480 · 43.4% | 16.429 / 13.480 · 44.2% |
| 2022 | 284 | 12.772 / 11.457 · ATS 46.4% | 12.733 / 11.457 · 47.8% | 12.846 / 11.457 · 46.8% |
| 2023 | 285 | 14.658 / 13.260 · ATS 50.2% | 14.703 / 13.260 · 49.8% | 14.797 / 13.260 · 48.2% |
| 2024 | 285 | 13.811 / 12.692 · ATS 49.8% | 13.876 / 12.692 · 49.6% | 13.973 / 12.692 · 49.6% |

Total RMSE (ours / line) and OU% @ ≥3.0:

| Season | Arm 0 | Arm 1 | Arm 2 |
|---|---|---|---|
| 2021 | 15.905 / 13.409 · OU 52.4% | 16.182 / 13.409 · 51.7% | 16.121 / 13.409 · 51.5% |
| 2022 | 14.952 / 13.226 · OU 50.3% | 15.399 / 13.226 · 49.8% | 15.474 / 13.226 · 48.8% |
| 2023 | 15.780 / 13.123 · OU 43.1% | 16.203 / 13.123 · 43.7% | 16.164 / 13.123 · 44.1% |
| 2024 | 14.051 / 12.573 · OU 53.0% | 14.334 / 12.573 · 52.4% | 14.337 / 12.573 · 52.4% |

SU% by season — Arm 0: 57.3 / 63.4 / 61.4 / 67.7; Arm 1: 57.7 / 63.4 / 60.7 / 64.9; Arm 2: 58.9 / 63.0 / 60.4 / 63.9 (2021–2024).

## Adoption-bar scorecard (Arm 1, as pre-registered)

| Criterion | Required | Arm 1 result | Pass? |
|---|---|---|---|
| (1) Overall margin RMSE improves ≥ 0.05 | ≤ 14.394 | 14.452 (+0.008 vs baseline) | **No** |
| (2) Margin RMSE improves or ties in ≥ 3 of 4 seasons | ≥ 3 | 2 of 4 (2021, 2022 better; 2023, 2024 worse) | **No** |
| (3) Overall ATS does not worsen | ≥ 47.50% | 47.73% | Yes |

**Bar verdict: FAIL (2 of 3 criteria missed) → keep the model as-is.** No damping variant was pre-registered for this study, and none is proposed off the back of a null primary: unlike turnovers — where the full-inclusion direction was never in doubt and only the weight was questioned — here full inclusion itself is neutral-to-negative on margins and clearly negative on totals, so there is no obvious follow-up arm the data is asking for.

## Descriptives (pre-registered, reported regardless of outcome)

Computed over the full PBP pool (1,139 games with play-by-play, 2021–2024; the graded frame is 1,107 after the baseline's documented exclusions).

- **Volume:** 30,066 ST plays (2021: 7,496; 2022: 7,487; 2023: 7,535; 2024: 7,548) — **26.40 per game** across both teams, 13.20 per team-game on each attribution. By type: kickoff 11,540; punt 8,952; extra point 5,120; field goal 4,454.
- **Share of |EPA|:** ST plays carry 13,321 of the pool's 151,173 total absolute EPA = **8.8%** (pass/rush: 143,879 plays, |EPA| 137,852). Not a sliver — comparable in mass to the turnover component (9.3%) — but mass is not persistence.
- **Per-game magnitude:** combined absolute ST EPA (both teams, posteam attribution) averages **5.17 EPA/game** (p95 11.60); per team-game |ST EPA| averages 2.58 on each side, and the net (benefit-terms) team-game value has sd 4.61 — game-to-game ST swings are large.
- **Between-team spread:** team-season net ST EPA per game has sd **1.29**, ranging from **−3.50 (SF, 2024)** to **+3.34 (PIT, 2024)** — real team-seasons exist at the extremes.
- **Persistence (the deciding descriptive):** season-to-season correlation of team net ST EPA per game: 2021→2022 **+0.26**, 2022→2023 **−0.05**, 2023→2024 **+0.14**; mean ≈ **+0.12**. Components are no stronger: kicking/punting side (posteam) mean r ≈ +0.16; coverage side (defensive benefit) mean r ≈ +0.27, and that average leans on a single pair (+0.50 for 2023→2024 against +0.26 / +0.04). A trait that does not repeat cannot be priced into a forward rating — the extremes above are mostly one-season variance, the same signature that sank the penalty term (persistence ≈ ±0.5 EPA/game of signal against much larger noise) and motivated the turnover placebo test.

## Interpretation

Special teams was the last untested exclusion from the ratings, and it closes the same way the penalty test did: the plays are numerous and their EPA mass is material, but the *team-level, forward-looking* component is too weak and unstable to survive a 17-game recency-weighted window. Raw inclusion is a wash on margins (slightly negative), mildly positive on ATS by an amount well within noise, and clearly harmful to totals — the one place the pre-registered double-counting concern predicted damage, since ST EPA partially re-states drive outcomes the scrimmage ratings already own. The model stays pass/rush-only. If this question is ever reopened, the descriptives say the only plausible route is a heavily damped, separately-estimated ST unit rating (kicker/punter personnel are stable even if team ST EPA is not) — a different construction that would need its own pre-registration, and on this evidence a low-priority one.
