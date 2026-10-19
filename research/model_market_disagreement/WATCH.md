# Model-vs-Market Disagreement Watch

**Set up:** 2026-10-19, at Bryant's request ("keep an eye on it").
**Type:** Standing measurement only. This watch **never changes the model** — it
accumulates evidence so a possible pattern can be judged on a season-sized sample.

## Origin

The Week 6 (2026) post-mortem (`~/workspace/goals/nfl-score-prediction-website/files/week6-postmortem-2026-10-19.md`)
found the model's overall margin accuracy was normal (RMSE 12.36 vs its 13.67
45-season baseline) while the closing line had a freakishly sharp week (7.76).
One descriptive thread stood out: the model's two biggest disagreements with
the closing line — NYJ @ NE (our_spread +23.8, disagreement +16.3) and
BAL @ CLE (our_spread −14.1, disagreement −10.6) — were also its two worst
margin errors. One week is an anecdote. This watch tests whether it keeps
happening.

## Hypothesis

On games where the model's spread disagrees strongly with the closing line,
the model's margin error exceeds the line's margin error — i.e., the model's
big reaches underperform the market it is reaching against.

## Metric definitions

All spreads are in **home-margin perspective** (predicted home score − away
score; positive = home favored), the convention of `src/weekly_picks.py` and of
the pick records in `site/data/picks.json` / `site/data/season_2026.json`.

Per graded game:

- `actual_margin` = home_score − away_score (from the merged `result`)
- `disagreement` = our_spread − line_spread
- `model_err` = |our_spread − actual_margin|
- `line_err` = |line_spread − actual_margin|
- `excess` = model_err − line_err  (positive ⇒ the model was worse than the line)

Games are bucketed by |disagreement|: **<3**, **3–6.9**, **7–9.9**, **≥10**.
The decision bucket is **≥7** (the last two combined).

Every graded game is logged — not just the model's published spread plays.
The question is about the model's raw spread on every game, play or no play.

## Protocol

- After each week's games are graded and merged, run `update_log.py`
  (in this directory). It scans `site/data/season_2026.json` (archived weeks)
  plus the current `site/data/picks.json`, appends any graded game not already
  in `log.csv` (idempotent by game identity), and prints the running bucket
  summary. It writes only inside this directory.
- **Assessment checkpoints:** (1) after Week 14 grades are in (mid-December
  2026), and (2) at season end. No conclusions are drawn between checkpoints.
- **Decision rule at a checkpoint:** if the ≥7 bucket shows **mean excess
  error > 0** across a meaningful sample (**n ≥ 25**), the watch graduates to
  a **draft pre-registered diagnostic** (candidate test: shrinking large
  disagreements toward the line) written up for Bryant's approval.
  - The watch itself never changes the model.
  - No diagnostic runs without Bryant's separate approval, and no model
    change happens without a passed pre-registered test + his approval.
  - If the ≥7 bucket's mean excess is ≤ 0, or n < 25 at season end, the watch
    closes as a null: big reaches did not systematically underperform.

## Coverage note (read before citing the log)

Honest Line launched at **Week 4 of the 2026 season** (site v1, 2026-09-30).
Weeks 1–3 were never published — there are no model picks for them anywhere in
this repo, so they cannot be logged and are not estimated or backfilled.
`log.csv` therefore starts at Week 4. Backfilling from Week 4 (the first
graded week in `site/data/season_2026.json`):

- Week 4: 16 games · Week 5: 15 games · Week 6: 13 games (WAS @ SF was still
  pending at setup; it enters the log via `update_log.py` once graded).

Validation: the Week 6 rows reproduce the post-mortem's numbers exactly —
model margin RMSE 12.36, closing-line RMSE 7.76 across the 13 graded games.

## Files

- `WATCH.md` — this protocol.
- `log.csv` — one row per graded game (season, week, matchup, spreads, actual
  margin, disagreement, bucket, both errors, excess).
- `update_log.py` — idempotent weekly append + bucket summary printer.
  Read-only on everything outside this directory.
