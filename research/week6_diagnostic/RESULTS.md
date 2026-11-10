# NFL Week 6 (2026) ATS Collapse — Diagnosis-Only Report

**Scope:** Diagnosis only. No model settings were changed, no code was modified,
nothing was committed or pushed. All Week 6 data was reconstructed read-only from
`site/data/season_2026.json` (the graded season log), cross-checked against
`site/data/recaps/2026-10-26.json` (NFL Week 6: 1-12 ATS, 4-3 totals — matches),
`data/schedules_games.parquet` (rest days), the git history of `picks.json`
(Friday Week 6 QB-override commit `26107c1`), and
`research/model_market_disagreement/log.csv` (W4–W6). Grading convention per
`src/grade_week.py`: home-margin terms, cover = actual home margin − line.

## Verdict

**No actionable cluster — correlated variance on a slate-wide bad ratings week.**
The losses did not concentrate in any cut that isn't already explained by the
model's known base rates. Every bucket lost (edge, home/away, favorite/underdog),
the model's raw margin accuracy was only modestly worse than the two prior weeks,
and the model's preferred side covered in just 1 of all 14 Week 6 games — the
signature of a week where the ratings were collectively off, not a selection or
threshold failure. Two small-n curiosities (fading bye-rested teams, the BAL
backup-QB rating) are noted below strictly as candidates for future
pre-registered tests.

## The week in numbers

- 13 ATS plays (the 14th game, TEN @ IND, was totals-only; spread edge 0.4 sat
  below the 0.5 publish threshold). Record: **1-12 ATS**, 4-3 on totals.
- Published cover probabilities were ~0.500–0.502 on every play (flat empirical
  calibration), so published expectation was ~6.5 wins; the model delivered 1.
- Probability of ≤1 win in 13 at a coin flip: ~0.17% (~1 in 585 weeks). At the
  model's own backtest base rate (47.5%, see below): ~0.29% (~1 in 340). Rare
  per week — but weekly picks share one set of ratings, so they are not
  independent trials; a slate-wide ratings miss produces exactly this shape.

## Per-game detail

Model/line in home-margin terms (+ = home favored). "Cover ±" is points the
pick beat (+) or missed (−) the spread by.

| Game | Pick | Model | Line | \|Edge\| | Prob | Final (A–H) | Cover ± | ATS | O/U |
|---|---|---|---|---|---|---|---|---|---|
| SEA @ DEN | SEA −2.5 | −4.5 | −2.5 | 2.0 | .500 | 14–17 | −5.5 | L | — |
| HOU @ JAX | JAX −2.5 | +6.0 | +2.5 | 3.5 | .500 | 34–31 | −5.5 | L | L |
| CHI @ ATL | ATL +1.5 | +4.5 | −1.5 | 6.0 | .502 | 31–23 | −6.5 | L | W |
| BAL @ CLE | BAL −3.5 | −14.1 | −3.5 | 10.6 | .500 | 10–13 | −6.5 | L | W |
| NYJ @ NE | NE −7.5 | +23.8 | +7.5 | 16.3 | .500 | 19–26 | −0.5 | L | L |
| NO @ NYG | NYG +1.5 | −0.1 | −1.5 | 1.4 | .500 | 34–27 | −5.5 | L | — |
| CAR @ PHI | PHI +3.5 | −0.1 | −3.5 | 3.4 | .500 | 25–14 | −7.5 | L | — |
| PIT @ TB | TB +2.5 | +4.2 | −2.5 | 6.7 | .502 | 26–19 | −4.5 | L | — |
| ARI @ LA | LA −12.5 | +18.5 | +12.5 | 6.0 | .502 | 18–16 | −14.5 | L | — |
| LAC @ KC | LAC +7.5 | +4.7 | +7.5 | 2.8 | .500 | 6–22 | −8.5 | L | — |
| BUF @ LV | BUF −5.5 | −12.9 | −5.5 | 7.4 | .500 | 33–30 | −2.5 | L | W |
| DAL @ GB | GB −1.5 | +9.2 | +1.5 | 7.7 | .500 | 13–23 | +8.5 | **W** | — |
| WAS @ SF | SF −7.5 | +19.5 | +7.5 | 12.0 | .500 | 17–23 | −1.5 | L | L |

## Clustering cuts vs long-run base rates

Base rates from the `nfl_threshold` backtest (`per_game.csv`, 2021+,
walk-forward, 1,291 plays at |edge| ≥ 0.5; overall 47.5% excl. pushes). These
are backtest ratings, not the live 2026 ratings — the best in-repo comparison
available, not a perfect one.

| Cut | Week 6 | Backtest base rate | Read |
|---|---|---|---|
| Edge < 2 | 0-1 | 51.6% (163-153, n=316) | n=1, nothing |
| Edge 2–4 | 0-4 | 45.8% (147-174, n=321) | Bad, small n |
| Edge 4+ | 1-7 | 46.4% (288-333, n=621) | Worst bucket, but this bucket is *already* sub-.500 historically |
| Home picks | 1-8 | 48.0% (304-329) | Broad |
| Away picks | 0-4 | 47.0% (294-331) | Broad |
| Favorites | 1-7 | 47.9% (332-361) | Broad |
| Underdogs | 0-5 | 47.1% (266-299) | Broad |

No cut isolates the damage: it is spread across all of them. The one pattern
with any shape is that 8 of 13 plays carried |edge| ≥ 4 and went 1-7 — but the
threshold study already established that win% *falls* as model edge grows and no
publish threshold is profitable; Week 6 sits at the unlucky tail of a property
the model already knows about. It is confirmation of existing evidence, not a
new finding.

## Loss-margin distribution

Miss distances (points by which losing picks failed to cover):
0.5, 1.5, 2.5, 4.5, 5.5, 5.5, 5.5, 6.5, 6.5, 7.5, 8.5, 14.5.
**Mean 5.8, median 5.5.** Only 3 of 12 losses were within a field goal; 9 of 12
were within one score; exactly one was a blowout (ARI @ LA, missed by 14.5 —
model had the Rams by 18.5, they won by 2). This was not a week of coin-flip
photo-finishes: the model was systematically ~a score too high on its own
sides. But its raw margin accuracy was not anomalous — mean absolute margin
error was 11.5 pts in Week 6 vs 9.4 (W4) and 10.6 (W5) per the disagreement
log: same regime, worse week. And the model's side covered in only 1 of all
14 Week 6 games (vs 10/16 in W4, 6/15 in W5) — including the game it declined
to play. Selection didn't fail; the ratings did, for one week.

## Bye weeks, QB override, totals contrast

- **Bye/rest:** Two Week 6 teams came off a bye (14 rest days): CAR and KC.
  The model faded both — PHI +3.5 vs CAR (lost by 7.5) and LAC +7.5 at KC
  (lost by 8.5): **0-2 picking against rested teams.** No pick was *on* a
  rested team. n=2 proves nothing, but it is the cleanest directional signal
  in the week.
- **QB override:** One override game — BAL @ CLE, Tyler Huntley for the
  ruled-out Lamar Jackson (commit `26107c1`). It lost (BAL −3.5, missed by
  6.5). However, the commit record states the re-run left the BAL pick
  *numerically unchanged*: Huntley's trailing EPA hit the same +3.0 QB cap,
  so the override did not create the exposure. The miss was the model's raw
  −14.1 margin on a backup-QB road team vs a −3.5 market line. (Backup QBs
  also appeared in CAR @ PHI — McKee, with a QB adjustment already applied —
  also a loss, via the other side.)
- **Totals went 4-3 the same week** and did not share the collapse: across the
  six games carrying both an ATS and a totals play, totals went 3-3 while ATS
  went 0-6. The totals signal (game scoring level) and the spread signal (team
  margin) decoupled completely — consistent with a team-ratings week, not a
  broken pipeline or bad lines (the market lines themselves graded normally).

## Candidates for future PRE-REGISTERED tests (candidates only — no change implied)

1. **Rest disadvantage:** multi-season backtest of model ATS record when
   picking *against* a team on ≥13 rest days vs its record otherwise. Week 6
   contributes n=2 (0-2); the hypothesis needs the full backtest before it
   means anything.
2. **Backup-QB team ratings:** when a team's QB adjustment is at/near the cap
   (i.e., a backup is starting), does the model's remaining team rating
   systematically overshoot the market? BAL @ CLE is one data point
   (model −14.1 vs market −3.5). Distinct from the already-killed QB
   last-game recency term — this is about rating *level* in backup weeks.

Explicitly **not** candidates: anything about the publish threshold or edge
buckets (already tested to a KILL verdict in `research/nfl_threshold/`), and
totals (4-3, no signal).

## Limitations

- Base rates come from the walk-forward backtest file, whose ratings are
  computed differently from the live in-season ratings; treat bucket
  comparisons as approximate.
- One week, 13 plays: every cut is small-n by construction. This report can
  rule out a *concentrated* failure; it cannot prove the model is healthy —
  only that Week 6's shape matches correlated variance on a bad ratings week.
- Published cover probabilities in the season log are the flat ~0.50 empirical
  values, so no per-play probability signal exists to audit for this week.
