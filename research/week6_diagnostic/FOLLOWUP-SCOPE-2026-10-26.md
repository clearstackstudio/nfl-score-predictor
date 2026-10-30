# Week 6 Diagnostic — Follow-Up Scope (2026-10-26)

Status: SCOPING ONLY. Nothing here is approved, nothing has been run, and no
model settings were changed. Prepared after Bryant's "Need to do better"
(2026-10-26) and his approval of the diagnosis-only Week 6 report.

---

## ❄️ FREEZE RECORD — 2026-10-29

Frozen 2026-10-29 by Bryant's approval: **"Run the backup-QB test, drop the
rest candidate"** (options-widget tap, 2026-10-29 20:46 PT).

- **Candidate 2 (backup-QB)**: the Draft pre-registration below is FROZEN
  exactly as written on 2026-10-26 — population (regular-season games
  2021–2025 in the walk-forward frame), leakage-safe mechanical backup
  definition (starter differs from the team's previous-game starter that
  season; season openers excluded; sensitivity cut at ≤ half of prior games),
  primary metric (mean model residual vs market residual, backup-team
  perspective), secondary ATS splits, and the adopt bar (same direction in
  ≥3 of the seasons AND pooled model-vs-market residual gap > 1.0 pt; any
  change still needs a separate implementation test + Bryant's approval;
  Week 6 2026 excluded from confirmation) are all locked. No edits to
  definitions, population, metric, or bar after this point.
- **Candidate 1 (rest)**: DROPPED per Bryant's decision — recorded 2026-10-29.
  It duplicates the 2026-10-02 rest/travel test (same 2021–2024 walk-forward
  frame, no systematic effect, rest/travel taken off the board). Nothing was
  run for it and nothing will be.

## Candidate 1 — Rest disadvantage: MOSTLY ALREADY TESTED. Recommendation: do not re-run.

The diagnostic filed: "multi-season backtest of model ATS record when picking
against a team on ≥13 rest days vs its record otherwise" (Week 6: 0-2 fading
CAR and KC off their byes).

Reconciliation against the project's own history:

- On 2026-10-02 Bryant approved rest/travel work and it was run on the same
  2021–2024 walk-forward frame used for the other NFL tests. Result: no
  systematic effect — rest buckets bounced with no pattern, the one big bucket
  went the wrong way, Thursday short weeks leaned 1.8 pts within noise, long
  travel tilted the wrong direction. Verdict recorded then: rest/travel is
  OFF the board; no adjustment was built. (memory/2026-10-02.md)
- The diagnostic's version is a slightly different question (pick *selection*
  against rested teams, not a rest term in the ratings), but it tests the same
  underlying signal on substantially the same data. Prior after the Oct 2
  result: low.
- Honest options if Bryant still wants it: (a) drop it; (b) fold a purely
  descriptive count (model ATS vs ≥13-day-rested opponents, 2021+) into the
  already-scheduled Nov 1 model-health check — no separate pre-registered run.
  Recommendation: (b) at most. A standalone run would spend a pre-registration
  slot re-asking a killed question.

## Candidate 2 — Backup-QB team-rating level: DISTINCT and FEASIBLE. Draft pre-registration below.

Question: when a team starts a backup QB (its QB adjustment at/near the ~3-pt
cap), does the model's *remaining team rating* systematically overshoot the
market? Week 6 instance: BAL @ CLE — model BAL −14.1 vs market −3.5 with
Huntley starting; the override commit shows the pick was numerically unchanged,
so the exposure was the team rating, not the QB term. Distinct from the killed
QB last-game recency test (that was about recency weighting of QB play; this is
about rating level in backup weeks).

Data feasibility — verified 2026-10-26, no new data or spend needed:
- `data/schedules_games.parquet`: 7,548 games with `home_qb_id`/`away_qb_id`,
  `home_qb_name`/`away_qb_name`, `home_rest`/`away_rest`, `spread_line`.
- `research/nfl_threshold/per_game.csv`: walk-forward model margins, lines and
  actual margins, 2021+ (1,291 plays at |edge| ≥ 0.5; full game frame in the
  same runner) — joinable to schedules on date/home/away.

### DRAFT pre-registration (for Bryant's approval — NOT frozen, NOT run)

- Population: all regular-season games 2021–2025 in the walk-forward frame.
- Backup definition (leakage-safe, mechanical): a team's starting QB
  (per schedules `*_qb_id`) differs from that team's starting QB in its
  previous game that season; first game of a season excluded. Sensitivity cut:
  backup = starter who started ≤ half of the team's prior games that season.
- Primary metric: mean model residual (our_margin − actual_margin, signed
  from the backup team's perspective) in backup-QB games vs non-backup games;
  same computation for the market line. Hypothesis: model residual is more
  pro-backup-team than the market's.
- Secondary: model ATS win% on plays involving a backup-QB team, split by
  backing vs fading the backup team.
- Adopt bar (proposal, mirroring prior tests): the effect must appear in the
  same direction in at least 3 of the seasons, the pooled model-vs-market
  residual gap must exceed 1.0 pt, and any resulting change still requires a
  separate pre-registered implementation test + Bryant's approval. A null or
  sub-bar result closes the question permanently, like threshold/momentum.
- Guardrail: Week 6 2026 is the hypothesis-generating week — it is excluded
  from any "confirmation" claim about this test (the backtest frame predates
  it anyway).

## What this changes about the queue

Nothing runs on either candidate without Bryant's separate yes. The Nov 1
model-health check and the Dec 9 model-vs-market disagreement checkpoint are
unchanged and remain the two scheduled decision points.
