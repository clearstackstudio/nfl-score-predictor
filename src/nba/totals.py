"""Team offensive/defensive efficiency ratings for NBA totals prediction.

Approach (kept deliberately simple, the NBA equivalent of the NFL model's
"separate effects"):
  - Each team carries two exponentially-weighted moving averages in absolute
    points per game: offensive points scored and defensive points allowed.
  - A league-average EMA tracks points per team-game and drifts with the era
    (league scoring rose from ~200 to ~228 per game over 2008-2023, so a
    fixed league average would be badly wrong).
  - Prediction: expected home score = league_avg + (home_off - league_avg)
    + (away_def - league_avg); symmetrically for the away team. Predicted
    total = expected home score + expected away score.
  - After the game, both teams' off/def EMAs move toward the observed
    points scored/allowed, and the league EMA moves toward the game's
    per-team scoring average.
  - New teams start at the league average (deviation 0); at season rollover
    each team's off/def EMAs regress halfway toward the league average.

No home/away split is modeled: home teams score ~2.6 more but allow ~2.6
fewer than away teams, so the home-court effect nets to ~0 on the total.

Honesty rules (same as elo.py): the line is never an input; predict BEFORE
update; chronological order.

Fitted constants (walk-forward totals RMSE on seasons 2008-2023, 18,473
games; closing-line totals RMSE on the same games is 17.68):
  - TEAM_ALPHA = 0.06   per-game EMA weight for team off/def (grid min:
    0.06 -> 18.264; 0.05 -> 18.284; 0.08 -> 18.299)
  - LEAGUE_ALPHA = 0.005 slow drift for the league average (beat 0.01/0.02)
  - SEASON_CARRYOVER = 0.5 regress halfway to league average at rollover
"""
from __future__ import annotations

import pandas as pd


# Fitted defaults (see module docstring for procedure).
TEAM_ALPHA = 0.06
LEAGUE_ALPHA = 0.005
SEASON_CARRYOVER = 0.5


class NBATotals:
    """Team off/def efficiency -> expected total. Call ``predict_total``
    BEFORE ``update`` for leakage-safe walk-forward evaluation.

    Constructor params let the backtester experiment:
      team_alpha  - per-game EMA weight for team off/def (fitted 0.06)
      league_alpha- per-game EMA weight for league scoring average (0.005)
      carryover   - fraction of team off/def kept at season rollover (0.5)
    """

    def __init__(self, team_alpha: float = TEAM_ALPHA,
                 league_alpha: float = LEAGUE_ALPHA,
                 carryover: float = SEASON_CARRYOVER) -> None:
        self.off: dict[str, float] = {}
        self.deff: dict[str, float] = {}
        self.team_alpha = team_alpha
        self.league_alpha = league_alpha
        self.carryover = carryover
        self.league_avg = 100.0  # sensible prior; EMA converges within weeks

    def _off(self, team: str) -> float:
        return self.off.setdefault(team, self.league_avg)

    def _def(self, team: str) -> float:
        return self.deff.setdefault(team, self.league_avg)

    def predict_total(self, home: str, away: str) -> float:
        """Predicted home_score + away_score, from ratings as they stand.
        Call BEFORE update()."""
        lg = self.league_avg
        exp_home = lg + (self._off(home) - lg) + (self._def(away) - lg)
        exp_away = lg + (self._off(away) - lg) + (self._def(home) - lg)
        return exp_home + exp_away

    def update(self, home: str, away: str,
               home_score: float, away_score: float) -> None:
        """Learn from a final score. Call AFTER predict_total()."""
        a = self.team_alpha
        ho, hd = self._off(home), self._def(home)
        ao, ad = self._off(away), self._def(away)
        self.off[home] = ho + a * (home_score - ho)
        self.deff[home] = hd + a * (away_score - hd)
        self.off[away] = ao + a * (away_score - ao)
        self.deff[away] = ad + a * (home_score - ad)
        game_avg = (home_score + away_score) / 2.0
        self.league_avg += self.league_alpha * (game_avg - self.league_avg)

    def new_season(self) -> None:
        """Regress each team's off/def halfway toward the league average."""
        for team in list(self.off):
            self.off[team] = (self.carryover * self.off[team]
                              + (1.0 - self.carryover) * self.league_avg)
            self.deff[team] = (self.carryover * self.deff[team]
                               + (1.0 - self.carryover) * self.league_avg)
