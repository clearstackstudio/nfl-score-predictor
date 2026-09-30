# NFL Score Predictor

Can we beat the Vegas line? That's the whole mission.

## The idea

Most "predictors" (including our own v2) cheat: they take the Vegas spread and
total as model inputs, then predict a score. That's circular — the model can
only ever echo the line back. It can never beat it.

This project does it the hard way:

1. **Fundamentals model** — team-strength ratings built from play-by-play data
   (EPA, success rate, etc.), never from the betting line.
2. **Our own lines** — the model generates a predicted spread and total for
   each game.
3. **Compare vs. the market** — edge = where our numbers differ from Vegas.
4. **Honest backtest** — every claim validated against historical closing
   lines with chronological, leakage-safe evaluation. No peeking.

If the backtest shows a real edge, the website publishes the picks with a
fully transparent tracked record. If it doesn't, we say so and keep working.

## Data

- `spreadspoke_scores.csv` — 14,086 NFL games (1966–2024) with final scores.
  Full spread + over/under coverage from 1980 onward: ~12,000 games of
  backtest ground truth.
- `data/` — nflverse play-by-play pulls (not committed; see `src/fetch.py`).

## Layout

- `src/ratings.py` — team strength ratings (Elo baseline, then EPA-based).
- `src/model.py` — margin/total prediction from ratings + matchup features.
- `src/backtest.py` — walk-forward backtest vs. historical closing lines.
- `src/fetch.py` — nflverse data pulls.

## Status

Phase 1 (done): Elo baseline + walk-forward backtest, 1980–2024.
Phase 2 (done): EPA-based ratings from nflverse play-by-play, 2021–2024.
Neither beats the modern line yet — see results below. No edge claimed.

## Backtest results (leakage-safe, predict-before-update, chronological)

Elo, 1980–2024 (11,352 games): margin RMSE 13.67 vs closing line 13.68
(a dead heat), straight-up 63.8%. ATS at >=1.5pt disagreement: 54.0%
overall, but decaying by decade — 56.3% (80s) → 54.0% (90s) → 54.7%
(00s) → 53.1% (10s) → 50.8% (2020s). The market got sharper; the edge
is gone against modern lines.

EPA model, 2021–2024 (1,107 games): straight-up 63.8%, margin RMSE
14.21 vs line 12.73, ATS 48.2%. Totals: RMSE 15.19 vs line 13.08,
over/under picks 48.2%. No edge on spreads or totals.

Next levers: QB-specific adjustments, rest differentials, weather/dome
effects on totals, recency weighting. Tuning on the backtest window is
overfitting — any parameter search must itself be walk-forward.
