# Ratings recency weighting — is the model's memory the right length? — PREREGISTRATION

**Written:** 2026-10-19 ~14:50 PT, BEFORE any recency-weighting sweep
results were computed. **Scope only — running it requires Bryant's
separate explicit approval** (same standing rule as the QB-recency,
team-momentum, and Wild Day jobs-report diagnostics).

**Trigger:** Bryant asked in main chat (2026-10-19) about adding team
momentum to the model, and then chose — on Snoopy's recommendation —
to scope THIS test instead: the ratings-responsiveness sweep that the
repo's own momentum study pointed at a week ago. The team-momentum
test (`research/team_momentum/PREREGISTRATION.md`, scoped earlier
today) stays frozen and is sequenced AFTER this one (see "Sequencing"
below). This document defines ONE sweep, frozen. Nothing in it has
been run.

## Prior work in this repo — read this first

This test exists because a previous test's *interpretation* named it:

- **`research/momentum/` (M1, run 2026-10-12):** a pre-registered test
  of win/loss streaks on the pattern-study Elo replication,
  1980–2024. The streak term PASSED both naive gates (validation slope
  +0.326, z = +5.69; RMSE 13.260 → 13.185) — and was still correctly
  **not shipped**, because mechanism diagnostics showed the closing
  line already owned the signal (streak slope collapsed to −0.009 with
  the line in the regression; ATS flat at 51.3% → 51.1%). M1's recorded
  interpretation: *"streaks are a symptom of our ratings learning too
  slowly — when a team genuinely improves or declines, it strings
  wins/losses together while the walk-forward rating lags behind."*
  Its proposed next test, verbatim in substance: **pre-register a
  ratings-responsiveness sweep on the LIVE NFL model (post–Oct 1 EPA
  version — M1 ran on the Elo replication, so the live model may lag
  differently): vary update speed / recency weighting, walk-forward.**
  This document is that test, scoped against the live code.
- **Corroborating echo (descriptive, not evidence about this model):**
  M1 also noted the NCAAB pattern study found deleting early-season
  down-weighting (faster learning) improved RMSE there — "same
  disease, different symptom." Two sports showing slow-learning
  symptoms is why this question outranked another add-on feature.
- **This morning's neighbors:** the QB-recency diagnostic returned
  KILL (2026-10-19) and the team-momentum registration was frozen the
  same day. Both are "recent form bolted onto the rating" ideas. This
  test is different in kind: it adds no feature. It asks whether the
  rating's own memory — how fast the core number itself learns — is
  set at the right speed. If the memory is wrong, feature tests run
  on top of it are testing against a mis-tuned baseline, which is why
  this test goes first.

## The knob — what "responsiveness" actually is in the live code

Per `src/epa_ratings.py` (the live model; `src/weekly_picks.py` imports
its `adjusted_ratings` and `qb_adjustments` directly):

- Ratings are decay-weighted means of per-game EPA/play over a
  trailing window. The decay is governed by ONE module constant:

      RECENCY_HALF_LIFE = 8        # games
      _RECENCY_DECAY = 0.5 ** (1.0 / RECENCY_HALF_LIFE)

  A game *k* games back in a team's window weighs
  `_RECENCY_DECAY ** k` — i.e., its weight halves every
  `RECENCY_HALF_LIFE` games. At the live value (8), the most recent
  game weighs 1.0, a game 8 back weighs 0.50, a game 16 back 0.25.
- The constant acts in exactly two places, both through the same
  module-level `_RECENCY_DECAY`:
  1. **`adjusted_ratings()`** — the decayed weighted means of
     offensive/defensive EPA/play and pace over the trailing
     `WINDOW_GAMES = 17` window; the same weights drive the
     single-step opponent adjustment, and they determine the
     effective sample size `n_eff` that governs early-season blending
     toward the prior-season rating (below `MIN_GAMES = 4` effective
     games, ratings blend toward the prior).
  2. **`qb_adjustments()` / `_qb_adj_for_team()`** — an incoming
     starter's trailing-form decayed mean EPA, and the game weights
     on the team's window QB EPA, use the same decay.
- This is NOT turnover damping. `TURNOVER_EPA_WEIGHT = 0.50`
  (adopted 2026-10-12) scales the EPA of turnover plays before any
  averaging; it is a separate parameter, already settled by its own
  pre-registered study, and it does not move in this test.

### Entanglements — how this registration handles them (frozen)

- **Shared constant.** There is no separate half-life for the QB
  machinery; the live code has exactly one responsiveness setting,
  consumed by both the team ratings and the QB adjustments. The sweep
  therefore overrides the module constant (and its derived
  `_RECENCY_DECAY`) per arm, so **both consumers move together —
  exactly what editing the live setting would do.** A "ratings-only,
  QB decay held at 8" variant is a different model that does not
  exist in the live code; it is NOT this test and would need its own
  registration.
- **Frozen companions.** Every other constant stays at its live value
  in every arm: `WINDOW_GAMES = 17`, `MIN_GAMES = 4`,
  `CARRYOVER = 0.5`, `TURNOVER_EPA_WEIGHT = 0.50`, `QB_IMPACT = 0.35`,
  `QB_PRIOR_ATT = 150`, `QB_SAME_THRESHOLD = 0.85`,
  `QB_MAX_ADJ = 0.05`, `HOME_EDGE_PTS = 1.8`, `PLAYS_PER_GAME = 63.0`,
  `ADJ_ITERS`. Two of these deserve explicit note:
  - `CARRYOVER` (prior-season ratings enter the next season's prior
    at half weight) and `MIN_GAMES` are *season-start* responsiveness
    knobs — related in spirit, distinct in mechanism. They are held
    fixed. A carryover sweep is a separate pre-registration, not a
    second axis of this one; a two-axis grid is a bigger search space
    and a different honesty problem.
  - `WINDOW_GAMES = 17` caps the window, so at the slowest grid value
    the truncation still binds (at half-life 16, the oldest in-window
    game keeps weight 0.50 — the decay never gets to fade it
    further). The slow end of this sweep therefore means "slowest
    the live window allows." Accepted and stated; widening the
    window jointly would be a different registration.
- **`n_eff` interaction.** At faster settings the decayed effective
  sample shrinks sooner, so early-season blending toward the prior
  engages more strongly. That is a mechanical consequence of the
  live code's construction of the setting — part of what is being
  tested, not a side effect to correct mid-test.

## Hypothesis (frozen)

The live half-life (8 games) may be mis-set in either direction:

- **Too slow:** ratings lag genuine team change (M1's diagnosis on
  the Elo replication) — recent games should weigh more.
- **Too fast:** ratings chase single-game noise — EPA/play in one
  game is a noisy estimate of team quality, and down-weighting
  slightly older games throws away real information.
- H1: some other value in the frozen grid below predicts future
  margins better out-of-sample than 8, by the decision rule's bars.
  The null — 8 is on the plateau and no grid neighbor clears the
  bars — is a perfectly good outcome: it closes the responsiveness
  question for this model the way today's KILL closed QB recency.

## The sweep (the entire search space, frozen)

    RECENCY_HALF_LIFE ∈ {4, 6, 8, 12, 16}     (games)

| Half-life | Weight of a game 8 back | Weight of a game 16 back | Reading |
|---|---|---|---|
| 4 | 0.25 | 0.06 | twice as fast as live |
| 6 | 0.40 | 0.16 | moderately faster |
| **8 (live)** | **0.50** | **0.25** | **current setting — the baseline arm** |
| 12 | 0.63 | 0.40 | moderately slower |
| 16 | 0.71 | 0.50 | twice as slow (window-bound, see above) |

- The five values are roughly geometric around the live value and
  span plausibly-too-fast to plausibly-too-slow. No other values may
  be evaluated under this registration — no interpolation, no
  refinement pass around the winner, no per-season or per-team
  values.
- **Edge rule:** if discovery selects a grid edge (4 or 16), that is
  reported as-is, including the plain statement that the optimum may
  lie off-grid. Extending the grid requires a NEW pre-registration,
  written before any extended results are computed.

## Data and harness

- Play-by-play: `data/play_by_play_{2021..2025}.parquet` (nflverse),
  consumed through the pipeline's own `load_team_games()` /
  `load_qb_plays()` — reuse the constructions, don't redefine them.
- Walk-forward predictions under each arm, generated with the same
  loop structure as `src/epa_ratings.run_backtest()` and the
  QB-recency runner (the runner extends `epa_ratings.PBP_YEARS` to
  2021–2025, as that harness did; per arm it overrides
  `RECENCY_HALF_LIFE` / `_RECENCY_DECAY` and nothing else). Each arm
  produces per-game `our_margin` and `our_total` for every scored
  game, 2021–2025, walk-forward throughout: predict first, then
  learn, exactly as the live loop does.
- Turnover damping stays ON at w = 0.50 in all arms (the live
  configuration being tuned — an arm with damping off is not a
  responsiveness variant).
- **2026 is excluded entirely** (in-progress season; no result from
  it may tune the verdict).
- No new data feeds; cost $0; compute is five walk-forward backtests
  over 2021–2025 (roughly 5× one QB-recency-scale run).

## Baseline gate (stop rule — read before fitting anything)

The 2026-10-19 QB-recency run taught the lesson this gate encodes: a
stale pin silently invalidates everything downstream. The pins below
are the CORRECT ones for the live (damped) configuration, per the
addendum Bryant approved for `research/qb_recency/PREREGISTRATION.md`
the same day, and they certify the BASELINE arm (half-life 8) before
any other arm is trusted.

1. **Reproduction.** Run `src/epa_ratings.run_backtest()` exactly
   as-is (PBP_YEARS 2021–2024). It must return:
   - ATS **47.29%** (record **393-438-29**)
   - Margin RMSE **14.131**
   - n = **1,107** games

   (Tolerances as in the QB-recency runner: |ATS% − 47.29| ≤ 0.15 pp,
   |RMSE − 14.131| ≤ 0.02.)
2. **Per-game replication.** The extended harness's baseline-arm
   2021–2024 rows must replicate
   `research/turnover_damping/per_game_robustness_w0.50_qb.csv`
   exactly, as verified in the QB-recency run: all 1,107 games
   merge, ATS tuple (393, 438, 29), RMSE within 1e-6 of
   14.130860208614187, max |Δ our_margin| < 1e-9.
3. **On any mismatch: STOP and report.** Do not proceed on a
   mismatched baseline, and do not re-pin mid-run. A pin correction
   requires a dated addendum to THIS document, approved by Bryant,
   written before any re-run — the precedent set 2026-10-19.

## Splits and selection (frozen)

- Discovery: 2021–2023 seasons. Validation: 2024–2025 seasons (the
  verdict sample). Walk-forward throughout.
- Each arm is scored on discovery by pooled margin RMSE over all
  games that arm's walk-forward predicts.
- **Selection rule:** the candidate is the arm with the LOWEST
  pooled discovery margin RMSE. Ties (|ΔRMSE| < 0.001 between arms)
  break toward the value closest to the live setting (8) in log₂
  ratio; if still tied, toward the smaller half-life.
- **Degenerate case, stated now:** if discovery selects 8, the
  candidate IS the live setting. The validation difference is then
  identically zero and cannot meet the ADOPT rule below; the verdict
  is KILL (current setting stands), reported as such — no validation
  ceremony for a foregone conclusion.
- The candidate, once selected, is FROZEN. Validation evaluates that
  one candidate against the baseline arm (8). No refitting, no
  re-selection after seeing validation numbers, under any
  circumstance.

## Primary endpoint and decision rule

**Primary endpoint:** pooled validation (2024–2025) margin RMSE,
candidate vs. baseline, on the paired sample (games scored by both
arms — the scored sets are expected to be identical across arms,
since cold-start depends on window presence, not weights; the run
must verify this and report any discrepancy). The difference
Δ = RMSE(candidate) − RMSE(baseline) gets a paired-bootstrap 95% CI:
10,000 resamples of validation games (resampled as games, both arms
scored per resample), percentile interval, **seed frozen at
20261019** — the repo's existing convention (QB-recency run;
team-momentum registration).

**Guardrails (reported, and binding as stated):**

- Per-validation-season margin RMSE: candidate vs. baseline for 2024
  and for 2025 separately.
- Pooled validation **totals RMSE**: the ratings feed predicted
  totals as well as margins (`our_total` from the same loop), so a
  margin win bought with a totals collapse is not a win. Materiality
  bound: the candidate must not worsen pooled validation totals RMSE
  by more than **+0.10** points vs. baseline.

**Decision rule — ADOPT iff ALL THREE hold:**

1. Δ < 0 AND the paired-bootstrap 95% CI on Δ lies entirely below 0
   (excludes 0 on the good side).
2. The candidate does not worsen margin RMSE in EITHER validation
   season individually (Δ_season ≤ 0 for 2024 and for 2025; any
   increase, however small, fails — the strict guardrail the
   team-momentum registration set as house style).
3. Pooled validation totals RMSE Δ ≤ +0.10.

Anything else: **KILL** — the live setting stands at 8.

- An ADOPT verdict changes nothing live. It earns a recommendation
  to Bryant; the live change (editing the constant in
  `src/epa_ratings.py`, which `weekly_picks.py` consumes) happens
  only with his separate explicit approval, followed by the usual
  verification — and by the sequencing consequence below.
- A KILL is written up in `research/recency_weighting/RESULTS.md`
  and published as a tested-and-rejected note alongside the
  QB-recency one (methodology §05), per the standing honesty rule.

## Secondary / context outputs (no verdict power)

- **Full sweep table (descriptive):** all five arms × (discovery,
  validation) margin RMSE and totals RMSE, published in RESULTS.md.
  Transparency about the whole grid is the point of a sweep; the
  verdict, however, is computed ONLY through the frozen
  selection-then-validation path above. No "best on validation"
  reading of this table has any standing.
- **Validation ATS context:** ATS win% at the house convention
  (|our_margin − line_margin| ≥ 1.5, as in `run_backtest`) for the
  baseline and the candidate on validation games. Closing lines:
  2021–2024 from the repo's line store (`spreadspoke_scores.csv`,
  via `backtest.closing_home_spread`); **2025 from
  `data/schedules_games.parquet` (`spread_line`)**, because
  spreadspoke ends at 2024 — the source ratified by the 2026-10-19
  QB-recency addendum (same sign convention, correlation 0.996 vs.
  spreadspoke on 2021–2024). Reported as context only: M1's framing
  mentioned "no ATS degradation," but this registration's decision
  rule is accuracy-based (margin RMSE with its guardrails), per the
  model's stated purpose of prediction accuracy — ATS neither saves
  nor kills a candidate here.
- Sample sizes per arm per split (expected identical across arms;
  report and explain any difference).
- The selected candidate's identity and the discovery margin by
  which it won (including if it won at a grid edge).

## Sequencing (Bryant's decision, 2026-10-19)

- The **team-momentum test runs AFTER this one.** Its registration
  (`research/team_momentum/PREREGISTRATION.md`) is frozen as written,
  with its baseline gate pinned to the current live configuration
  (47.29% / 14.131 / n = 1,107 — numbers produced at half-life 8).
- **Consequence, stated in advance:** if this test ends in ADOPT
  *and* Bryant approves the live change, the momentum
  registration's gate pins describe a model that no longer exists.
  Before the momentum test may run, its pins must be corrected by a
  dated, Bryant-approved addendum to THAT document, re-derived from
  the new live baseline. If this test KILLs, the momentum pins stand
  exactly as written and no addendum is needed.

## What this test cannot show

- Anything about half-lives off the frozen grid (3, 5, 7, 10, 20…):
  the grid is the search space by design, not a first pass.
- Anything about season-start responsiveness (`CARRYOVER`,
  `MIN_GAMES`, the prior blend) or window length (`WINDOW_GAMES`) —
  held fixed; each is its own possible future registration.
- Whether a totals-OPTIMAL half-life differs: totals enter as a
  guardrail, not the objective. A totals-first sweep would be a
  different registration with a different primary endpoint.
- Whether responsiveness should vary by team, week, or season phase
  — one global setting is the live model's design, and this test
  respects it.
- Anything about 2026 or later seasons.

## Honest prior (recorded before running)

Genuinely uncertain — the most open question of the three scoped
today. For "too slow": M1's mechanism finding on the replication, and
the NCAAB echo. Against a big effect: the live EPA model is not the
Elo replication — it already decays at a half-life of 8 games over a
short 17-game window, which is fairly responsive as ratings go, and
the RMSE surface around a setting like this is usually a wide, flat
plateau where neighbors differ by hundredths of a point. That is
exactly why the ADOPT bar is a bootstrap CI that excludes zero, not
a point estimate: if the plateau is flat, the honest verdict is
KILL, the current setting is confirmed rather than merely
unexamined, and the null is published like the others.

## Process

Scope written 2026-10-19 at Bryant's direction. **Not run.** On
Bryant's go-ahead: run the baseline gate, run the five frozen arms
once, apply the frozen selection rule, evaluate the frozen decision
rule once, write `research/recency_weighting/RESULTS.md` (verdict
ADOPT or KILL, the full sweep table, the numbers against each bar,
the guardrails, and the context outputs) with `results.json` and
`per_game.csv` (all arms) alongside, and report in chat. Cost: $0 —
all data already in repo.
