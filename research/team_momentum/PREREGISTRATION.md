# Team momentum — does a team's recent EPA trajectory predict its next game? — PREREGISTRATION

**Written:** 2026-10-19 ~14:45 PT, BEFORE any momentum-trajectory results
were computed. **Scope only — running it requires Bryant's separate
explicit approval** (same standing rule as the QB-recency and Wild Day
jobs-report diagnostics).

**Trigger:** Bryant asked in main chat (2026-10-19) what Snoopy thinks of
adding team momentum to the model. The answer given: the prior is low —
ratings already decay-weight recent games, bettors already over-weight
streaks, and this morning's QB-recency diagnostic (a close cousin: recent
form vs. season baseline) returned KILL on every bar. Bryant chose to have
the team-level version scoped and settled on the record anyway. This
document is that scoping. It defines ONE test, frozen. Nothing in it has
been run.

## Prior work in this repo — read this first

Momentum has been tested here before, under a different definition, and
the precedent shapes this registration:

- **`research/momentum/` (M1, run 2026-10-12):** a pre-registered test of
  win/loss **streaks** on the pattern-study Elo replication, 1980–2024.
  It PASSED both of its naive gates (validation slope +0.326, z = +5.69;
  RMSE 13.260 → 13.185) — and was still correctly **not shipped**,
  because post-hoc mechanism diagnostics showed the signal was the
  market's, not the model's: the streak slope against (actual − closing
  line) was only +0.097, it collapsed to −0.009 (z = −0.14) in a joint
  regression with the line included, and ATS did not improve (51.3% →
  51.1%). Interpretation recorded there: streaks are a symptom of
  ratings learning slowly; the closing line has already moved.
- **This test is not M1.** It differs in definition (a continuous EPA
  trajectory slope, not discrete W/L streaks), in model (the LIVE EPA
  model, post-2026-10-01 configuration with turnover damping — M1 ran on
  the Elo replication, and its own RESULTS.md notes the live model may
  lag differently), and in sample (2021–2025 walk-forward under the live
  config, not 1980–2024). It therefore needs its own registration and
  its own verdict; M1's null does not answer it, and its pass would not
  have either.
- **M1's lesson is built in, not bolted on:** the mechanism diagnostic
  that killed M1's shipping case *after* its gates passed is
  pre-registered below as a mandatory reported output of this test, so
  it cannot be skipped if the gates pass this time.
- M1 also proposed a **ratings-responsiveness sweep** on the live model
  (vary update speed / recency weighting) as the follow-up its result
  actually pointed to. That test remains unscoped and unrun, and this
  registration is NOT it. If Bryant wants that test instead, this
  document is the moment to say so — it costs nothing to redirect
  before anything runs.

## What the model already does (the gap this test must clear)

Per `src/epa_ratings.py`:

- Team ratings are opponent-adjusted EPA/play over a trailing 17-game
  window, **decay-weighted with a half-life of 8 games** — a team's most
  recent games already carry the largest weights in its rating. A
  four-game trajectory is therefore substantially *inside* the current
  rating already; the candidate term must show that the **slope** of
  recent performance adds signal on top of the **level** the rating
  carries.
- Turnover EPA is deliberately damped (w = 0.50, adopted 2026-10-12).
  The per-game series defined below is on the same damped basis the
  ratings consume — no undamped variant gets a shot.
- QB changes are separately priced by `qb_adjustments` and the override
  feed. This test's population is NOT restricted to continuing starters
  (a deliberate difference from `research/qb_recency/`): team momentum
  here is a team-level quantity, defined for every eligible game.
- This morning's QB-recency verdict (KILL, 2026-10-19) found a QB's
  single-game deviation from his own baseline is noise out of sample.
  This test asks the distinct team-level question — a four-game slope,
  not a one-game deviation — but the family resemblance is exactly why
  the honest prior below is low.

## Hypothesis (one, frozen)

A team's recent trajectory — the slope of its per-game performance over
its last 4 games, relative to its own season-to-date baseline — predicts
its next game beyond what the live model's current ratings already
capture. Formally, with `margin_resid = actual_margin − our_margin`
(home perspective):

- H1: the slope of `margin_resid` on `momentum_diff` (defined below) is
  **positive** on out-of-sample games: when the home team's trajectory
  is rising faster than the away team's, the model systematically
  under-predicts the home margin.
- Candidate adjustment, if the hypothesis survives:
  `candidate_margin = our_margin + γ · momentum_diff`, with γ fitted on
  discovery seasons only and frozen for validation.

## Definitions (exact, grounded in the codebase)

**Per-game performance series.** From `load_team_games()` in
`src/epa_ratings.py` — the same per-team-game frame the live ratings
consume. It is built from nflverse play-by-play
(`data/play_by_play_{year}.parquet`), pass and rush plays with non-null
EPA, with turnover plays' EPA scaled by `TURNOVER_EPA_WEIGHT = 0.50`
(the live damping). For each team-game it gives `off_epa_play`
(offensive EPA/play) and `def_epa_play` (EPA/play the team ALLOWED —
opponents' offensive EPA/play against it; higher = worse defense).
Define the team's per-game performance:

    p = off_epa_play − def_epa_play        (net EPA/play for that game)

Positive p = the team outplayed its opponent on a per-play basis. One
definitional constraint forced by the codebase, stated plainly: **p is
not opponent-adjusted.** The ratings' opponent adjustment is a
window-level step applied to decayed averages, not a per-game pipeline
artifact; no per-game opponent-adjusted series exists to reuse.
Four-game windows therefore carry whatever schedule strength they
carry. The test accepts this confound rather than inventing a new
adjustment — inventing one would be a second, unregistered modeling
choice inside the feature.

**Baseline.** Entering a predicted game, a team's baseline B is the
unweighted mean of p over ALL of that team's prior games in the
**current season** (regular season and playoffs are one season, as the
pipeline treats them; prior seasons never enter B or the window).

**Momentum.** Let the team's last 4 games of the current season,
chronologically, have performances p₁, p₂, p₃, p₄ (most recent = p₄).
Momentum is the ordinary-least-squares slope of (pᵢ − B) on game index
i = 1..4:

    momentum = slope of recent trajectory, in EPA/play per game

Frozen honesty note: B is constant across the window, so this slope is
numerically the slope of p itself over the last 4 games. B is the
interpretive anchor the hypothesis is stated against ("trajectory
relative to its own season level"); it does not secretly change the
number, and no variant that would change it (e.g., a baseline computed
only from pre-window games) may be substituted under this registration.

**Differential.** `momentum_diff = home_momentum − away_momentum`
(home perspective, matching `margin_resid`).

**Cutoff safety.** Every input uses only games strictly before the
predicted game, under the pipeline's own leakage-safe convention (the
team-games row-index cutoff used by `run_backtest()` and the QB-recency
runner — NOT a (season, week) cutoff, which would leak same-week games).
"Last 4 games" means last 4 games *played*: bye weeks do not shrink or
reset the window, and a window may span five or six calendar weeks
around a bye. Frozen as stated.

**Eligibility (the cleaner rule, frozen).** A team's momentum is defined
only when it has played **≥ 4 prior games in the current season** (a
full window). Partial windows are not used — a slope over 2 or 3 games
is a different, noisier statistic, and mixing window sizes would make
the feature's meaning vary by week. A game enters the test sample only
if **both** teams have a defined momentum. Consequences, accepted in
advance: Weeks 1–4 of every season are out, as are a team's fifth game
if a bye intervenes oddly; expected coverage is roughly 70–75% of
predicted games (vs. ~22% for the QB-recency test's population), to be
reported exactly when run. Within each split, the live baseline and the
candidate are scored on the **same eligible sample** (paired
comparison), so eligibility cannot manufacture an improvement.

## Data

- Play-by-play: `data/play_by_play_{2021..2025}.parquet` (nflverse),
  consumed through the pipeline's own `load_team_games()` — reuse the
  construction, don't redefine it. (The runner pattern is the
  QB-recency one: extend `epa_ratings.PBP_YEARS` to 2021–2025 in the
  runner, as that harness did.)
- Walk-forward predictions under the LIVE EPA config, generated with
  the same loop structure as `research/qb_recency/run_qb_recency.py`.
- **2026 is excluded entirely** (in-progress season; no result from it
  may tune the verdict).
- No new data feeds; cost $0; compute is a single walk-forward run
  comparable to the QB-recency diagnostic.

## Baseline gate (stop rule — read before fitting anything)

Today's QB-recency run taught the lesson this gate encodes: a stale pin
silently invalidates everything downstream. The pins below are the
CORRECT ones for the live (damped) configuration, per the 2026-10-19
addendum Bryant approved for `research/qb_recency/PREREGISTRATION.md`.

1. **Reproduction.** Run `src/epa_ratings.run_backtest()` exactly as-is
   (PBP_YEARS 2021–2024). It must return:
   - ATS **47.29%** (record **393-438-29**)
   - Margin RMSE **14.131**
   - n = **1,107** games

   (Tolerances as in the QB-recency runner: |ATS% − 47.29| ≤ 0.15 pp,
   |RMSE − 14.131| ≤ 0.02.)
2. **Per-game replication.** The extended walk-forward's 2021–2024 rows
   must replicate `research/turnover_damping/per_game_robustness_w0.50_qb.csv`
   exactly, as verified in the QB-recency run: all 1,107 games merge,
   ATS tuple (393, 438, 29), RMSE within 1e-6 of 14.130860208614187,
   max |Δ our_margin| < 1e-9.
3. **On any mismatch: STOP and report.** Do not proceed on a mismatched
   baseline, and do not re-pin mid-run. A pin correction requires a
   dated addendum to THIS document, approved by Bryant, written before
   any re-run — the precedent set 2026-10-19.

## Splits

- Discovery: 2021–2023 seasons (γ is fitted here, and only here).
- Validation: 2024–2025 seasons (the verdict sample; γ frozen).
- Walk-forward throughout: every rating, baseline, and window uses only
  prior games.

## Primary test and decision rule

Regress `margin_resid` on `momentum_diff` (OLS with intercept, the
house convention from the QB-recency runner; only the slope is ever
applied as an adjustment).

- Fit the slope on DISCOVERY only → γ.
- On VALIDATION, the verdict is **ADOPT** iff ALL THREE hold:
  1. **Slope bar:** the validation regression's slope is > 0 with
     **z ≥ 1.96**.
  2. **Accuracy bar:** applying the frozen adjustment
     (`our_margin + γ · momentum_diff`) **reduces pooled validation
     margin RMSE** vs. the live model on the same eligible sample.
     The paired-bootstrap 95% CI on the RMSE difference must be
     reported alongside: 10,000 resamples of eligible validation
     games (resampled as games, both models scored per resample),
     percentile interval, seed frozen at 20261019.
  3. **Guardrail:** the candidate does **not worsen RMSE in either
     validation season individually** (2024 and 2025 checked
     separately). Worsening in one season kills, even if the pooled
     number improves. (Stricter than the QB-recency guardrail, on
     purpose: a two-season validation split is the whole verdict
     sample, and a one-season effect is not a model feature.)
- Anything else: **KILL.**
- An ADOPT verdict changes nothing live. It earns a recommendation and
  a separate implementation test against the live generator, and any
  live-model change still requires Bryant's separate explicit approval.
- A KILL is written up in `research/team_momentum/RESULTS.md` and
  published as a tested-and-rejected note alongside the QB-recency one
  (methodology §05), per the standing honesty rule.

## Mechanism diagnostic (pre-registered, mandatory to report — no verdict power)

Per the M1 precedent, if the gates pass, the live question becomes
whether the signal is the model's or the market's. Report on the
validation eligible sample, regardless of verdict:

- Slope of (`actual_margin` − `line_margin`) on `momentum_diff` — does
  the closing line already contain the trajectory?
- Joint OLS of `margin_resid` on `momentum_diff` AND `line_margin` —
  does the momentum slope survive with the line in the regression
  (M1's streak slope did not: +0.326 → −0.009)?

These numbers carry no verdict power under the rule above, but they
MUST accompany any ADOPT recommendation to Bryant, labeled as what
they are. A recommendation that omits them violates this registration.

## Secondary descriptive outputs (no verdict power)

- ATS context on validation games: ATS win% on model picks
  (|spread_edge| ≥ 1.5) for the live model vs. the γ-adjusted model,
  on the eligible sample. Closing lines: 2021–2024 from the repo's line
  store (`spreadspoke_scores.csv`, via `backtest.closing_home_spread`),
  as in prior diagnostics; **2025 from `data/schedules_games.parquet`
  (`spread_line`)**, because spreadspoke ends at 2024 — the source
  ratified by the 2026-10-19 QB-recency addendum (same sign convention,
  correlation 0.996 vs. spreadspoke on 2021–2024). The primary test
  uses no lines at all.
- Per-season validation RMSE table (live vs. candidate) — required by
  the guardrail in any case.
- Coverage: eligible share of predicted games by split and season.
- Discovery-fit summary (γ, its SE and z) for the record.

## Anti-data-mining clause

Exactly ONE momentum definition (net EPA/play as above), ONE window
(last 4 in-season games), ONE baseline (season-to-date mean), ONE form
(additive γ · momentum_diff on predicted margin), ONE γ source
(discovery OLS slope). No alternative windows (3, 5, 6 games), no
decay-weighted windows, no win/loss-streak variant (that was M1,
closed), no points-based (margin-of-victory) performance series, no
home/away-split γ, no threshold or interaction variants may be tried
under this registration. A different definition is a new
preregistration, written before its results are computed.

## What this test cannot show

- Anything about totals — the endpoint is margin only.
- Anything about 2026 or later seasons; anything about QB changes
  (owned by `qb_adjustments` and the override feed).
- Whether an opponent-adjusted or decay-weighted trajectory would work
  — different definitions, out of scope by the clause above.
- Whether faster *ratings* adaptation helps — that is M1's proposed
  responsiveness sweep, a separate (still unscoped) test. A KILL here
  does not kill that idea, and an ADOPT here does not substitute for it.

## Honest prior (recorded before running)

Low. The ratings already give the last four games their largest
weights; the market visibly prices streaks and form; the one time a
momentum-flavored signal passed its naive gates in this repo (M1), the
line already owned it; and the closest cousin tested (QB last-game
form) was noise out of sample. The test exists because "the prior is
low" is not a verdict — the same standard applied to every other idea
this repo has settled. If it kills, the null is published like the
others. If it adopts, the mechanism numbers decide what Bryant is
actually being asked to approve.

## Process

Scope written 2026-10-19 at Bryant's direction. **Not run.** On
Bryant's go-ahead: run the baseline gate, build the walk-forward once,
evaluate the frozen rule once, write
`research/team_momentum/RESULTS.md` with the verdict (ADOPT or KILL),
the full numbers against each bar, the mechanism diagnostic, and the
descriptive outputs, and report in chat. Cost: $0 — all data already in
repo.
