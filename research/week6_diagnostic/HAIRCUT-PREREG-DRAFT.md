# Backup-QB Rating Haircut — Implementation Test Pre-Registration

## ⚠️ DRAFT — NOT FROZEN, NOT RUN

Status: **DRAFT ONLY.** Prepared 2026-10-29 after Bryant approved
pre-registering this test ("Pre-register the backup haircut test",
options-widget tap, 2026-10-29 20:58 PT). The adopt-bar numbers in §5 are
**PROPOSED** and marked as such. Nothing in this document is frozen until
Bryant approves the draft as written; nothing has been run; **no model or
code change has been made.** Freezing, when it happens, will be recorded in
a freeze block at the top of this file, as with
`FOLLOWUP-SCOPE-2026-10-26.md`.

Parent diagnostic: `BACKUP-QB-RESULTS.md` (run 2026-10-29 under the frozen
scope in `FOLLOWUP-SCOPE-2026-10-26.md`). Measured effect: in backup-QB
games the model's remaining team rating overshoots the market by a pooled
**+1.11 pts** (same direction in 5 of 5 seasons, 2021–2025; model residual
+1.91 vs market +0.80 from the backup team's perspective; backup-involved
plays went **110 W – 134 L – 7 P** over the five seasons). This test asks
the follow-up question the diagnostic deliberately did not: *does shaving
the backup team's predicted margin by the measured overshoot win more
picks than it loses?*

---

## 1. Intervention spec — a single pre-committed haircut of 1.0 pt

**The intervention:** in any game where a team qualifies as a *backup team*
under the frozen mechanical definition in §2, that team's predicted margin
is reduced by exactly **1.0 points** before edges and play selection are
computed:

- Backup team is home: predicted margin (home − away) decreases by 1.0.
- Backup team is away: predicted margin (home − away) increases by 1.0.
- Both teams qualify (28 of 261 backup-involved games in the diagnostic):
  the haircut applies to each team, so the predicted margin is unchanged
  by construction. These games are reported as their own line in every
  table and are excluded from the "affected plays" winner count in §4
  (the intervention cannot change their plays).

The haircut applies to the **spread margin only**. Totals predictions are
untouched — the diagnostic measured spread margins, and no totals claim is
made or tested here.

**Why a single size, not a grid.** The candidate sizes one might test
(0.5 / 1.0 / 1.5) differ from each other by less than the noise in the
underlying measurement (per-season gap SE ≈ 1.9 pts), and on ~50 affected
plays per season the winner-count difference between adjacent grid points
would be a handful of flipped plays — selecting the "best" grid point on
the same 2021–2025 data would be fitting noise, not measuring an effect.
A grid search would also spend the confirmation value of the diagnostic:
the +1.11 was measured on this exact population, so a size *searched* on
this population is no longer an out-of-sample claim of any kind.

Instead the size is **derived, not searched**: haircut = the measured
pooled overshoot (+1.11), rounded **down** to **1.0 pt** — a deliberate,
pre-declared conservative shrink toward zero, because the +1.11 is itself
a noisy point estimate and because partial correction is the failure mode
that costs nothing if the effect is real but smaller than measured. One
size, committed before the run. If 1.0 fails the bar in §5, the question
closes — there is no re-run at 0.5 or 1.5 under this pre-registration
(any such test would need its own new pre-registration and Bryant's
separate approval, and would carry the burden of being a second bite at
the same data).

## 2. Backup definition — identical to the diagnostic, no changes

A team is a *backup team* in a game if its starting QB (per
`data/schedules_games.parquet` `home_qb_id` / `away_qb_id`) differs from
that team's starting QB in its previous game **that season**. Season
openers are excluded (no previous game). This is the diagnostic's frozen,
leakage-safe mechanical definition, carried over verbatim — the +1.11 was
measured over exactly these appearances (289 appearances in 261 games,
2021–2025), and changing the definition here would sever the link between
the measurement and the intervention.

Consequences of the definition, stated plainly so nothing is a surprise
at results time:

- The haircut fires only on the **first game after a QB change**. If the
  same backup starts consecutive games, later starts do not re-trigger it
  (the starter no longer differs from the previous game's starter) — by
  then the trailing team-rating window has also begun absorbing the
  backup's own games. This matches the diagnostic population exactly.
- A change *back* to the previous starter also fires the definition (it
  is symmetric), including a QB1 returning from a one-game absence. No
  exceptions are carved out: the measured gap was computed over all such
  appearances, return games included.
- The diagnostic's sensitivity population (starter had started ≤ half of
  the team's prior games that season — true fill-ins, 225 appearances,
  gap +1.56) is **not** a second intervention. It is reported as a
  descriptive readout only (§4), under the same single 1.0-pt haircut.

## 3. Composition with the existing QB adjustment — additive, no interaction

The existing QB adjustment (`qb_adjustments()` in `src/epa_ratings.py`)
prices the **QB swap itself**: `QB_IMPACT × (starter's trailing relative
EPA − team's window relative EPA)`, clipped to ±`QB_MAX_ADJ` (0.05
EPA/play, ≈ ±3 pts at expected play volume — the "~3-pt cap"). It is zero
when the starter threw ≥ 85% of the window's dropbacks.

The haircut prices a **different, already-measured quantity**: the
residual overshoot in the *team rating itself* — the rating the rest of
the roster earned, largely with the regular starter — beyond what the
market charges for the same situation and beyond what the capped QB term
already removes. The diagnostic's Week 6 instance is the archetype:
BAL @ CLE, the QB machinery worked as designed and the exposure was the
team-rating level, not the QB term.

**Interaction rule (exact):**

1. The QB adjustment is computed **exactly as today** — same formula, same
   constants (`QB_IMPACT`, `QB_MAX_ADJ`, `QB_SAME_THRESHOLD`,
   `QB_PRIOR_ATT`), whether or not the haircut fires. The haircut does
   not modify, rescale, cap, or gate it.
2. The haircut is a separate, additive, margin-level term applied **after**
   the QB adjustment, whenever the §2 definition fires — regardless of
   whether the QB adjustment for that team is at its cap, partial, or
   zero. There is no conditional ("only when at cap") and no combined
   cap: total QB-related adjustment = QB adjustment (unchanged) − 1.0 pt
   (haircut, backup-team perspective).
3. The haircut fires **once per qualifying team per game**. It never
   stacks with itself and is not scaled by the size of the QB adjustment,
   the number of weeks the backup has started, or any other quantity.

In the walk-forward evaluation (§4) the haircut is applied at the margin
level to the frame's predicted margins, which is exactly where the
diagnostic measured the gap. How an adopted change would be expressed
inside the live ratings code (margin-level term vs EPA/play equivalent)
is an implementation detail for the adoption step, not part of this test.

## 4. Evaluation — walk-forward recount, winner count primary

**Frame and joins:** identical to the diagnostic — the walk-forward frame
behind `research/nfl_threshold/per_game.csv` joined to
`data/schedules_games.parquet`, regular-season games **2021–2025**,
playoff rows (weeks 19–22) excluded, including the diagnostic runner's
join mechanics (the 3 Saturday games joined on the unique matchup key).
One run, by a new runner derived from `run_backup_qb.py`, producing a
results file alongside this pre-registration. No other seasons, no other
data, no in-run adjustments.

**Procedure, per game:** take the frame's predicted margin and closing
line as-is; identify backup teams per §2; subtract the §1 haircut;
recompute the edge; re-run play selection at the model's standing publish
threshold, **|edge| ≥ 0.5** (τ = 0.5, unchanged — the threshold test
killed every alternative). A play may consequently flip side, drop below
threshold, or newly qualify. Pushes count as **non-winners** in every
winner count below.

**Metrics, in declared priority order:**

1. **PRIMARY — winner-count change on affected plays.** "Affected plays"
   = plays in backup-involved games (≥ 1 qualifying team, excluding
   both-backup games per §1) under either the baseline or the haircut
   selection. Report, pooled and per season: plays before/after, W–L–P
   before/after, **net winners gained (W_after − W_before)**, and the
   counts of plays flipped, added, and dropped. Bryant's objective is
   the *number* of winning picks; this is the number the verdict turns
   on. (Baseline to beat, from the diagnostic: 252 backup-involved plays,
   110 winners, five seasons.)
2. **ATS record on backup-involved plays**, before/after, pooled and per
   season, split by backing vs fading the backup team (diagnostic
   baseline: backing 46.1%, fading 42.4%).
3. **Residual gap after the haircut:** pooled model-vs-market residual
   gap on backup appearances, recomputed with the haircut applied.
   Expected to land near +0.11 by construction — this is a *sanity
   check that the haircut was applied as specified*, not independent
   evidence, and will be reported as such.
4. **Overall impact across ALL plays:** total winners and ATS record over
   the full 2021–2025 play set, before/after. The haircut cannot touch a
   non-backup game by construction, so this recount doubles as a leakage
   check: **Δ winners on non-backup-involved plays must be exactly 0**,
   and any nonzero value invalidates the run as an implementation error,
   not a result.
5. **Descriptive only (no bar attached):** the same winner recount
   restricted to the sensitivity population (true fill-ins, §2), and the
   per-season table for both-backup games.

## 5. Adopt bar — PROPOSED numbers (Bryant's approval required to freeze)

All four conditions must hold. These numbers are **PROPOSED**, chosen
against the diagnostic baselines (~50 backup-involved plays and ~22
winners per season), and are not in force until Bryant approves this
draft and it is frozen.

1. **Pooled net winners gained on affected plays ≥ +5** over 2021–2025
   (an average of ≥ +1 winner per season — the smallest gain worth a
   permanent model change, and deliberately above what one lucky flip
   explains).
2. **No season materially worse:** every individual season's net winner
   change ≥ **−2**. (A pooled gain bought with one bad season is the
   signature of noise, not of a real correction.)
3. **Consistency:** net winner change ≥ 0 in at least **3 of 5** seasons.
4. **No cost elsewhere:** total winners across ALL plays does not
   decrease (Δ ≥ 0), with the §4 leakage check (Δ = 0 on non-backup
   plays) passing exactly.

**If the bar clears:** the result returns to Bryant. Adoption still
requires his separate yes (§6) — clearing this bar authorizes nothing by
itself.

**If the bar fails:** verdict KILL. The backup-QB haircut question
closes permanently, like the publish-threshold and team-momentum
questions before it, and the diagnostic's finding is recorded as a known,
accepted limitation of the model (its margins in backup weeks are ~1 pt
optimistic vs the market; we publish anyway). No re-run at a different
haircut size under any re-labeling of this test.

## 6. Guardrails

- **Week 6 2026 stays excluded** from any confirmation claim — it is the
  hypothesis-generating week (via the diagnostic) and the frame predates
  it in any case.
- **No live-model change from this test alone.** Nothing in `src/`
  changes as part of the run. If the bar clears, implementation in the
  live model is a separate step requiring Bryant's explicit adoption
  approval after he sees the results, and the live implementation must
  reproduce the §1–§3 spec exactly (any deviation voids the test's
  authority for that change).
- **One run, as frozen.** If a runner bug is found after results are
  seen, the run is reported as invalid with the bug named — not quietly
  fixed and re-run. A corrected re-run needs Bryant's approval and is
  labeled a re-run in the results file.
- **No new data, no spend.** Same parquet, same frame, same joins as the
  diagnostic.
- The rest candidate stays dropped (Bryant's decision, 2026-10-29) and
  is not revived by anything in this document.
