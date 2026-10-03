"""Margin-adjusted Elo for NBA, ported from the NFL framework in src/ratings.py.

Honesty rules (same as the NFL model):
  - The betting line is NEVER a model input, anywhere. It is only the
    benchmark the backtest compares against.
  - Prediction precedes update: call ``predict_margin`` BEFORE ``update``
    for leakage-safe walk-forward evaluation.
  - Games are processed in chronological order.

Differences from the NFL version:
  - No ties in the NBA (overtime always produces a winner), so the actual
    outcome is 1.0 for a home win and 0.0 for a home loss.
  - No neutral-site flag: the games.csv contract has no neutral column.
    (The 2020 bubble games were played at a neutral site but carry
    arbitrary home/away designations in the source data; see fit_home_edge.)

All constants below were fitted on the Kaggle oddsData.csv history
(seasons 2008-2023, 18,473 regular-season games after dropping the 88
neutral-site 2020 bubble games). Fitting procedure:
  - home_edge: mean home margin, excluding the neutral-site 2020 bubble
    games and the fanless 2020-21 season (see fit_home_edge).
  - k, elo_per_point, carryover: grid search on walk-forward margin RMSE.
    The RMSE surface is very flat (12.517-12.523 across the whole grid),
    so defaults are plateau-center values, not sharp optima.
"""
from __future__ import annotations

import math
import pandas as pd


ELO_START = 1500.0

# Fitted defaults (see module docstring for procedure):
#   HOME_EDGE_PTS  = 2.75  mean home margin excl. bubble + fanless 2020-21
#   K_BASE         = 26.0  plateau center of walk-forward RMSE grid
#   ELO_PER_POINT  = 30.0  ~30 Elo points per predicted point of margin
#   SEASON_CARRYOVER = 0.5  regress halfway to the mean at season rollover
HOME_EDGE_PTS = 2.75
K_BASE = 26.0
ELO_PER_POINT = 30.0
SEASON_CARRYOVER = 0.5


def mov_multiplier(mov: float, elo_diff: float) -> float:
    """Scale K by margin of victory (blowouts mean more than squeakers),
    dampened when the favorite was much stronger (expected blowouts).
    Same FiveThirtyEight-style form as the NFL model."""
    return ((abs(mov) + 3.0) ** 0.8) / (7.5 + 0.006 * abs(elo_diff))


class NBAElo:
    """Margin-adjusted Elo for NBA. Call ``predict_margin`` BEFORE ``update``
    for leakage-safe walk-forward evaluation.

    Constructor params let the backtester experiment:
      home_edge    - home-court edge in points (fitted default 2.75)
      k            - base K-factor (fitted default 26.0)
      carryover    - fraction of rating kept at season rollover (fitted 0.5)
      elo_per_point- Elo points per predicted point of margin (fitted 30.0)
    """

    def __init__(self, home_edge: float = HOME_EDGE_PTS,
                 k: float = K_BASE,
                 carryover: float = SEASON_CARRYOVER,
                 elo_per_point: float = ELO_PER_POINT) -> None:
        self.ratings: dict[str, float] = {}
        self.home_edge = home_edge
        self.k = k
        self.carryover = carryover
        self.elo_per_point = elo_per_point

    def _get(self, team: str) -> float:
        return self.ratings.setdefault(team, ELO_START)

    def predict_margin(self, home: str, away: str) -> float:
        """Predicted home_score - away_score, from ratings as they stand.
        Positive = home favored. Call BEFORE update()."""
        return ((self._get(home) - self._get(away))
                + self.home_edge * self.elo_per_point) / self.elo_per_point

    def update(self, home: str, away: str,
               home_score: float, away_score: float) -> None:
        """Learn from a final score. Call AFTER predict_margin()."""
        home_elo = self._get(home)
        away_elo = self._get(away)
        margin = home_score - away_score
        edge = self.home_edge * self.elo_per_point
        elo_diff = home_elo - away_elo + edge
        expected = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
        # No ties in the NBA: a home win is 1.0, a home loss is 0.0.
        actual = 1.0 if margin > 0 else 0.0
        kk = self.k * mov_multiplier(margin, elo_diff)
        shift = kk * (actual - expected)
        self.ratings[home] = home_elo + shift
        self.ratings[away] = away_elo - shift

    def new_season(self) -> None:
        """Regress every rating toward the mean at a season boundary."""
        for team in self.ratings:
            self.ratings[team] = (self.carryover * self.ratings[team]
                                  + (1.0 - self.carryover) * ELO_START)


def fit_home_edge(games: pd.DataFrame) -> float:
    """Estimate the home-court edge in points from game data.

    Plain mean of (home_score - away_score), excluding games that were not
    played in front of a normal home crowd:
      - the neutral-site 2020 bubble games (2020-07-01..2020-10-31), which
        carry arbitrary home/away designations, and
      - the fanless 2020-21 season (labelled 2021),
    since forward predictions assume normal arenas. Exclusions apply only
    when a ``date`` column is present; otherwise falls back to the raw mean.

    Fitted value on seasons 2008-2023: ~2.75 pts (raw all-game mean 2.62).
    """
    df = games.copy()
    if "date" in df.columns:
        dates = pd.to_datetime(df["date"])
        bubble = ((df["season"] == 2020)
                  & (dates >= "2020-07-01") & (dates <= "2020-10-31"))
        fanless = df["season"] == 2021
        df = df[~(bubble | fanless)]
    margins = df["home_score"].astype(float) - df["away_score"].astype(float)
    return float(margins.mean())


def _walkforward_rmse(games: pd.DataFrame, k: float, carryover: float,
                      home_edge: float = HOME_EDGE_PTS,
                      elo_per_point: float = ELO_PER_POINT) -> float:
    """Walk-forward margin RMSE for one (k, carryover) pair."""
    elo = NBAElo(home_edge=home_edge, k=k, carryover=carryover,
                 elo_per_point=elo_per_point)
    se, n, last_season = 0.0, 0, None
    for row in games.itertuples():
        season = int(row.season)
        if last_season is not None and season != last_season:
            elo.new_season()
        last_season = season
        pred = elo.predict_margin(row.home_team, row.away_team)
        actual = float(row.home_score) - float(row.away_score)
        se += (pred - actual) ** 2
        n += 1
        elo.update(row.home_team, row.away_team,
                   float(row.home_score), float(row.away_score))
    return math.sqrt(se / n) if n else float("nan")


def tune_carryover(games: pd.DataFrame,
                   candidates: tuple[float, ...] = (0.25, 0.5, 2 / 3, 0.75),
                   k: float = K_BASE) -> float:
    """Tune the season-rollover regression factor by walk-forward RMSE on
    the EARLY half of seasons in ``games`` (the later half is left untouched
    for the real backtest, so tuning cannot leak into evaluation).

    Returns the candidate with the lowest walk-forward margin RMSE.
    Fitted on seasons 2008-2023 tuning split: 0.5 (RMSE surface is flat;
    0.5 edged out 2/3 and 0.75 by ~0.002).
    """
    df = games.sort_values("date").reset_index(drop=True)
    seasons = sorted(df["season"].unique())
    tune_seasons = set(seasons[: max(1, len(seasons) // 2)])
    tune = df[df["season"].isin(tune_seasons)]
    best, best_rmse = candidates[0], float("inf")
    for c in candidates:
        rmse = _walkforward_rmse(tune, k=k, carryover=c)
        if rmse < best_rmse:
            best, best_rmse = c, rmse
    return best
