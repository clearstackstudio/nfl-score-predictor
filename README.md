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

Phase 1: data + baseline ratings model. Nothing claimed yet.
