# QB recency — does a QB's most recent game predict next week? — PREREGISTRATION

**Written:** 2026-10-15 ~21:15 PT, BEFORE any recency results were computed.
**Trigger:** SEA @ DEN, Thu 2026-10-15 — Sam Darnold threw 2 INT in a 17–14 OT
loss the model had priced SEA −2.5. Bryant asked that night whether "today's
data" should be factored into the model. The main-chat answer: tonight's game
already enters through the normal weekly pipeline; the open question is whether
an *additional* last-game QB term earns its place. This preregistration states
that question as a testable diagnostic. **Scope only — running it requires
Bryant's separate explicit approval** (same standing rule as the Wild Day
jobs-report diagnostic). The motivating game and the entire 2026 season are
excluded from the test sample, so the anecdote cannot tune the verdict.

## What the model already does (the gap this test must clear)

Per `src/epa_ratings.py`:

- Team ratings are EPA/play over a trailing 17-game window, decay-weighted by
  game (recent games weigh more). A continuing QB's form — including his last
  game — is already inside the team window at the highest decay weight.
- `qb_adjustments` fires ONLY on a QB change: if the listed starter threw
  ≥85% of the window's passes for his team, `qb_adj = 0`. On a change, it
  prices the incoming starter's trailing 400 dropbacks (decay-weighted EPA,
  shrunk vs a 150-attempt prior, QB_IMPACT 0.35, clipped) against the window.
- Turnover signal is deliberately damped (QB-inclusive damping w = 0.50,
  adopted 2026-10-12), and `research/turnover_placebo/` already found raw
  turnover counts carry little forward signal.

So the candidate term must add value ON TOP OF all three. The honest prior is
that it won't — last-game EPA deviation is mostly noise, and INT counts are
the noisiest part of it. The test exists to settle it with data, not vibes.

## Question

For games where BOTH starters are continuing starters (each threw ≥85% of his
team's recent window passes — the `qb_adj = 0` population), does the QB's most
recent game predict the model's margin residual next game, beyond what the
ratings + QB machinery already carry?

## Data

- Play-by-play: `data/play_by_play_{2021..2025}.parquet` (nflverse), QB
  dropbacks = pass plays + sacks + QB scrambles as defined by the existing
  `qb_plays` construction in the ratings pipeline — reuse it, don't redefine.
- Walk-forward predictions under the LIVE EPA config, generated with the
  `research/epa_live_backtest/` harness (reproduce its baseline first; if the
  reproduced 2021–24 baseline does not match the published ATS 47.5% / margin
  RMSE 14.44, stop and report — do not proceed on a mismatched baseline).
- Closing lines from the repo's existing line store, as in prior diagnostics.

## Features (computed strictly from games BEFORE the predicted game)

- For each starting QB: `last_dev` = (EPA/dropback in his most recent game)
  − (his decay-weighted trailing mean EPA/dropback entering that game, the
  same decay as the ratings). Eligibility: ≥15 dropbacks in the last game
  and ≥100 career dropbacks entering the predicted game.
- PRIMARY feature: `qb_form_diff = home last_dev − away last_dev`.
- SECONDARY (descriptive only, NO verdict power): `last_int_diff` = away QB's
  last-game INT count − home QB's (the Darnold anecdote's exact shape; kept
  descriptive because of the turnover-damping/placebo prior work above).

## Splits

- Discovery: 2021–2023 seasons. Validation: 2024–2025 seasons (verdict sample).
- Walk-forward throughout: every feature and rating uses only prior games.
  2026 is excluded entirely (motivating season).

## Primary test

Regress `margin_resid` (= actual margin − our_margin, home perspective) on
`qb_form_diff`.

- Fit slope `b` on DISCOVERY only.
- KEEP the idea (recommend a live-model implementation test, for Bryant's
  approval) iff BOTH hold on VALIDATION:
  1. slope of margin_resid on qb_form_diff > 0 with z ≥ 1.96, AND
  2. applying the discovery-fitted adjustment (our_margin + b·qb_form_diff)
     reduces validation margin RMSE vs the unadjusted model.
- Guardrail: if the adjustment worsens RMSE in BOTH validation seasons
  individually, KILL regardless of the pooled result.
- Otherwise KILL. A null is published in RESULTS.md like every other null.
- No tuning: no alternate deviation definitions, windows, dropback
  thresholds, or a "last-2-games" variant get a second shot at the verdict.
  Anything else is a new preregistration.

## Secondary descriptive outputs (no verdict power)

- The same regression with `last_int_diff`; ATS win% on model picks
  (|spread_edge| ≥ 1.5) split by whether qb_form_diff agrees with the pick.
- Coverage: what share of games meet the both-continuing-starters and
  eligibility criteria (the term can only ever apply to that share).

## What this test cannot show

- Anything about QB *changes* — overrides and `qb_adjustments` already own
  that territory; this test is only about continuing starters.
- A KEEP does not ship anything: it earns a separate implementation test
  against the live generator and Bryant's explicit approval, per house rules.
- A null means last-game QB form adds nothing on top of ratings that already
  decay-weight it — not that "form doesn't matter" in general.
- Bye-week staleness (a "last game" 13+ days old) and mid-game QB injuries in
  the *last* game are noted limitations, not modeled.

## Process

Scope written 2026-10-15 at Bryant's direction. **Not run.** On Bryant's
go-ahead: build features, reproduce the baseline, run the frozen test once,
write `research/qb_recency/RESULTS.md` with the verdict (KEEP or KILL) and
the full numbers, and report in chat. Cost: $0 — all data already in repo.
