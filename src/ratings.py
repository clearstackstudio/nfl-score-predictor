"""Team-strength ratings from game results only — never from the betting line.

Baseline: margin-adjusted Elo in the FiveThirtyEight style.
Every update uses only final scores; the line is never an input anywhere.
"""
from __future__ import annotations

import math
import pandas as pd


ELO_START = 1500.0
# Each new season, carry over 2/3 of last year's rating (regress to mean).
SEASON_CARRYOVER = 2.0 / 3.0
HOME_ELO_EDGE = 55.0          # ~2.2 points of home field
ELO_PER_POINT = 25.0          # 25 Elo points ~= 1 predicted point of margin
K_BASE = 20.0


def elo_point_spread(home_elo: float, away_elo: float, neutral: bool = False) -> float:
    """Predicted home-team margin in points. Positive = home favored."""
    edge = 0.0 if neutral else HOME_ELO_EDGE
    return (home_elo - away_elo + edge) / ELO_PER_POINT


def mov_multiplier(mov: float, elo_diff: float) -> float:
    """Scale K by margin of victory (blowouts mean more than squeakers),
    dampened when the favorite was much stronger (expected blowouts)."""
    return ((abs(mov) + 3.0) ** 0.8) / (7.5 + 0.006 * abs(elo_diff))


class EloRatings:
    """Margin-adjusted Elo. Call `game_prediction` BEFORE `record_game`
    for leakage-safe walk-forward evaluation."""

    def __init__(self) -> None:
        self.ratings: dict[str, float] = {}
        self.season: int | None = None

    def _get(self, team: str) -> float:
        return self.ratings.setdefault(team, ELO_START)

    def _roll_season(self, season: int) -> None:
        if self.season is not None and season != self.season:
            for team in self.ratings:
                self.ratings[team] = (
                    SEASON_CARRYOVER * self.ratings[team]
                    + (1 - SEASON_CARRYOVER) * ELO_START
                )
        self.season = season

    def game_prediction(self, home: str, away: str, neutral: bool = False) -> float:
        """Predicted home margin (points) using ratings as they stand."""
        return elo_point_spread(self._get(home), self._get(away), neutral)

    def record_game(self, home: str, away: str, margin_home: float,
                    season: int, neutral: bool = False) -> None:
        """margin_home = score_home - score_away."""
        self._roll_season(season)
        home_elo = self._get(home)
        away_elo = self._get(away)
        edge = 0.0 if neutral else HOME_ELO_EDGE
        elo_diff = home_elo - away_elo + edge
        expected = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
        actual = 1.0 if margin_home > 0 else (0.5 if margin_home == 0 else 0.0)
        k = K_BASE * mov_multiplier(margin_home, elo_diff)
        shift = k * (actual - expected)
        self.ratings[home] = home_elo + shift
        self.ratings[away] = away_elo - shift


def normalize_teams(games: pd.DataFrame) -> pd.DataFrame:
    """Team name/ID cleanup applied identically to every season's games."""
    df = games.copy()
    # spreadspoke uses full names; keep them as-is but strip whitespace.
    for col in ("team_home", "team_away", "team_favorite_id"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df
