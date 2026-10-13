# Kicker-change term — walk-forward test of the pre-registered design

**Date:** 2026-10-12 · **Approved by:** Bryant (measurement only; no live code/data changed)
**Pre-registration:** `goals/ultimate-multi-sport-prediction-model/hidden_files/kicker-change-preregistration.md` (written before any run)
**Interpreter:** `.venv-cfb/bin/python` — **Artifacts:** `run_kicker_change.py` (runner, staged: baseline / build / descr / test), `baseline_verification.json`, `build_counts.json`, `descriptives.json`, `metrics.json`, `flags.csv`, `kick_plays.csv`, `flagged_residuals.csv`, `second_game_residuals.csv`, `split_half.csv`, `kicker_seasons.csv`, `per_game_baseline.csv`. No git commit/push.

## Verdict (up front)

**The adoption bar is not met — no kicker-change term. The question is closed**, per the pre-registration's rule for a failed or inconclusive result. Three independent reasons, any one of which is sufficient:

1. **The trait does not persist.** Individual kicker FG-play EPA per attempt barely correlates with itself: split-half r = **+0.09** (45 kickers, ~48 attempts per half), consecutive-season r = **−0.05 / −0.40 / +0.07** (mean **−0.13**). The pre-registration states that if individual kicker quality does not persist, "the personnel hypothesis is dead on arrival" — it does not persist, at kicker level any more than it did at team level (r ≈ +0.12 in the special-teams study).
2. **The hypothesis-carrying split points the wrong way.** Teams whose incoming kicker graded *worse* than the outgoing one should underperform the model if a priceable effect exists. Their mean margin residual is **+0.44** (n=45) — they (insignificantly) *out*performed. The incoming-*better* split is +1.63 (n=59), the predicted sign, but its 95% CI [−1.42, +4.68] includes zero.
3. **Nothing survives the debut.** The second game with the new kicker flips sign: mean margin residual **−1.39** (n=152, CI [−3.65, +0.88]).

The pooled change-game estimate (+0.99, 95% CI **[−0.81, +2.80]**, n=199) straddles zero with roughly the ±2-pt width the pre-registration's power caveat predicted. It is reported as **inconclusive on its own — not rounded into a yes or a no** — but pooled with the wrong-signed direction split and the null persistence descriptives, it gives the hypothesis no support. Nothing here is rescued, and no term is proposed.

## Baseline discipline — PASSED

The test reuses the special-teams study's Arm 0 per-game predictions. Stage `baseline` re-graded that CSV with the baseline runner's own grading functions against `config_a.json`: **1,107 games, margin RMSE 14.444, ATS 399-441-26 = 47.50%, total RMSE 15.169, OU 376-386-13 = 49.34%** — all diffs ≤ 7×10⁻¹⁵ (float rounding). The residual frame is Config A exactly.

## Method

- **Kicker identity:** `kicker_player_id` on `field_goal` and `extra_point` plays in the nflverse PBP (columns verified present in all four parquets; FG plays have zero EPA nulls and zero kicker-id nulls; 6 of 5,120 XP plays have a null kicker id and cannot be attributed — excluded, disclosed in the runner).
- **Primary kicker / change flag / quality direction:** exactly as pre-registered (most FG+XP attempts in the game; change = primary differs from the attempts-majority holder over the previous 4 team-games, ties → most recent game's primary; quality = incoming minus outgoing career-to-date FG-play EPA per attempt entering the game, each requiring ≥ 10 career FG attempts).
- **Residuals:** for each flagged team-game in the 1,107-game frame, margin residual = actual − model margin from that team's perspective; total residual = actual − model total. 95% CIs are t-intervals.
- **Disclosed implementation choices** (where the pre-registration is silent, also documented in the runner): careers are **within the 2021–2024 PBP window** (no pre-2021 play-by-play in `data/`), so veteran kickers' careers are left-truncated at 2021 and early-2021 classifications rest on in-window attempts; the previous-4 window spans season boundaries and includes playoff games; within-game primary ties (1 team-game in four seasons) break by FG attempts then kicker id; consecutive-season persistence requires ≥ 10 FG attempts in both seasons; "second game" = the team's next team-game with the same primary kicker, in-frame, deduplicated (85 of the 152 are themselves flagged change games — the 4-game majority window lags a real change, so consecutive flags of one change are expected under the mechanical definition; 209 flagged team-games = **119 distinct change events**, 114 of them in-frame).

## Descriptives

**Volume.** 1,139 games / 2,278 team-games, 2021–2024. Flag status: 2,009 same, **209 change**, 28 unflaggable (zero FG+XP attempts), 32 unflaggable (no previous primary — exactly each team's 2021 opener). Of the 209 change team-games, 199 are in the graded frame (38 / 47 / 48 / 66 by season); 14 frame games have *both* teams flagged. Quality direction is classifiable for 104 of 199 in-frame (59 incoming-better, 45 incoming-worse); 95 are unclassified because the incoming or outgoing kicker had < 10 career in-window FG attempts. Mean classified quality gap: **0.34 EPA per FG attempt** (better +0.31, worse −0.39) — at ~2.0 FG attempts per team-game, even a fully real gap of that size is worth ≈ 0.7 pts/game before any persistence discount, i.e. below the bar's 1.0-pt scale on its face.

**Persistence (the deciding evidence).** 69 distinct kickers attempted FGs; overall FG-play EPA/attempt = +0.098, with a between-kicker SD of 0.27 EPA/attempt among kickers with ≥ 15 attempts — plenty of *observed* spread. Almost none of it repeats:

| Test | n | r |
|---|---|---|
| Split-half FG EPA/att (first vs second half of career attempts) | 45 kickers | **+0.09** |
| Consecutive seasons 2021→2022 | 30 kickers | −0.05 |
| Consecutive seasons 2022→2023 | 27 kickers | −0.40 |
| Consecutive seasons 2023→2024 | 29 kickers | +0.07 |
| Mean consecutive-season r | | **−0.13** |

FG-play EPA already embeds attempt distance and game situation, so this is the context-adjusted quality measure the pre-registration specified — and period-to-period variation in it is dominated by which distances a kicker happened to attempt and ordinary make/miss variance, not by a durable skill level the model could price a *change* from.

## Results — residuals for kicker-change team-games (in-frame)

Margin residual is from the flagged team's perspective (positive = team beat the model's expectation). Total residual is the game's (positive = game went over the model's total).

| Set | n | Margin residual mean [95% CI] | Total residual mean [95% CI] |
|---|---|---|---|
| (a) All change games pooled | 199 | **+0.99** [−0.81, +2.80] | −2.09 [−4.17, −0.00] |
| (b) Incoming worse | 45 | +0.44 [−3.01, +3.89] | +1.77 [−3.38, +6.91] |
| (b) Incoming better | 59 | +1.63 [−1.42, +4.68] | −5.06 [−8.71, −1.42] |
| (b) Unclassified | 95 | +0.86 [−2.05, +3.77] | −2.07 [−4.93, +0.80] |
| (c) Second game with new kicker | 152 | −1.39 [−3.65, +0.88] | −0.80 [−3.11, +1.51] |

Notes on the totals column (reported because the pre-registration requires it; **not** part of the adoption bar and not a finding): change games ran ~2 pts under the model's total, driven by the incoming-better split (−5.06). There is no kicker mechanism for that pattern — a *better* incoming kicker should if anything add points — and the split more plausibly reflects which teams change kickers and the games they play than any kicking effect. The 14 both-teams-flagged games are also counted twice in the team-game total rows. No totals term is licensed by this test, and none is proposed.

## Adoption-bar scorecard

| Criterion | Requirement | Result |
|---|---|---|
| (1) Magnitude + direction | Pooled or direction-split mean margin residual ≥ 1.0 pt in the predicted direction | **Mixed/fails where it matters.** Incoming-better: +1.63 ✓ in isolation. Incoming-worse (the sharper half of the prediction): +0.44, **wrong sign**. Pooled: +0.99 < 1.0. |
| (2) Significance | That estimate's 95% CI excludes zero | **Fails.** No margin-residual CI excludes zero (pooled [−0.81, +2.80]; better [−1.42, +4.68]; worse [−3.01, +3.89]). |
| (3) Sign consistency | Pooled and direction split agree | **Fails.** Pooled is positive while the worse-split's prediction requires negative; the second-game estimate (−1.39) flips the pooled sign outright. |

**Verdict: bar not met.** Under the pre-registration, a failed *or* inconclusive result both end at the same place: **no kicker-change term, and the question is closed.** The pooled estimate alone would be "inconclusive" (its CI is the ±~2 pts the power caveat forecast); the full pattern — non-persistent trait, wrong-signed key split, sign flip in game two — is a null in every way that matters for a modeling decision. The MNF game that prompted this test (BUF 37 @ LA 34 OT, decided partly by a missed and a blocked Rams FG) remains what the pre-registration said it was: the prompt, not evidence.
