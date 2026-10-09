"""Honest Line MLB model: team-level runs ratings + walk-forward backtest.

Honesty rules (same as the NBA/NFL models):
  - The betting line is NEVER a model input. It is only the benchmark.
  - Prediction precedes update: every game is predicted from ratings built
    ONLY on games already played, then the ratings learn from it.
  - The backtest publishes the real numbers even when the verdict is
    "competent forecaster, no betting edge."

Modules:
  data     - pairs the two rows-per-game CSV into game records, derives
             home/away from the park, flags neutral-site games.
  ratings  - park-adjusted exponential runs ratings (offense/defense),
             season rollover, fitted home edge.
  winprob  - predicted run differential -> win probability (normal CDF,
             sigma fitted on the tuning split).
  pitcher  - DESIGN ONLY: how live picks will use probable pitchers from
             the free MLB Stats API. Not wired into the backtest.
  backtest - walk-forward evaluation vs the closing moneyline/total.
"""
