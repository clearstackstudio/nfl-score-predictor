"""Rest-day features for the NBA model (kept separate from the core model).

The rest adjustment is NOT baked into elo.py / totals.py. These helpers
expose a candidate adjustment so the backtest can measure whether it
improves walk-forward RMSE and keep it only if it does.

Fitted effect (walk-forward Elo residuals vs rest differential, seasons
2008-2023, n=18,201 games with defined rest):
  - margin residual slope on (home_rest - away_rest): +0.58 pts per day
    (95% CI roughly +/-0.17). Monotonic across the core range:
    rest_diff -2 -> -1.77, -1 -> -1.11, 0 -> -0.33, +1 -> +0.82, +2 -> +1.43.
  - total residual slope on combined rest ((home_rest + away_rest) - 2*1.075):
    +0.27 pts per day (small; test before keeping).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


# Fitted defaults (see module docstring).
REST_PTS_PER_DAY = 0.58          # margin points per rest-day differential
REST_TOTAL_PTS_PER_DAY = 0.27   # total points per combined rest-day above mean
REST_MEAN_DAYS = 1.075          # mean full days off between games (fitted)
REST_CAP_DAYS = 7               # long breaks (all-star etc.) aren't extra rest


def add_rest_days(games: pd.DataFrame) -> pd.DataFrame:
    """Add ``home_rest`` / ``away_rest`` columns: full days off since each
    team's previous game. Back-to-back = 0, one day off = 1, etc.

    Conventions:
      - Requires ``date``, ``season``, ``home_team``, ``away_team`` columns.
      - A team's first game of a season gets NaN (offseason rest is not
        informative).
      - Rest is capped at REST_CAP_DAYS; long layoffs are not extra-rested.
      - Rows are returned in their original order (computation is done on
        a date-sorted copy internally).
    """
    df = games.copy()
    orig_index = df.index
    # Stable date sort; remember the permutation so we can restore order.
    sort_pos = df["date"].pipe(pd.to_datetime).argsort(kind="stable").to_numpy()
    sdf = df.iloc[sort_pos].reset_index(drop=True)

    last: dict[tuple[str, int], pd.Timestamp] = {}
    home_rest: list[float] = []
    away_rest: list[float] = []
    dates = pd.to_datetime(sdf["date"])
    for i in range(len(sdf)):
        row = sdf.iloc[i]
        season = int(row["season"])
        for team, out in ((row["home_team"], home_rest),
                          (row["away_team"], away_rest)):
            key = (str(team), season)
            if key in last:
                days_off = (dates.iloc[i] - last[key]).days - 1
                out.append(float(min(max(days_off, -1), REST_CAP_DAYS)))
            else:
                out.append(float("nan"))
            last[key] = dates.iloc[i]

    # Invert the permutation to restore the caller's row order.
    inv = np.empty(len(df), dtype=int)
    inv[sort_pos] = np.arange(len(df))
    df = df.copy()
    df["home_rest"] = [home_rest[i] for i in inv]
    df["away_rest"] = [away_rest[i] for i in inv]
    df.index = orig_index
    return df


def apply_rest_adjustment(predicted_margin: float,
                          home_rest: float | None,
                          away_rest: float | None,
                          pts_per_day: float = REST_PTS_PER_DAY) -> float:
    """Candidate margin adjustment: +pts_per_day per day of rest differential
    (home_rest - away_rest). Positive differential favors the home team.

    Returns the prediction unchanged when either rest value is missing
    (None or NaN), e.g. season openers. The backtest should verify this
    improves walk-forward RMSE before keeping it (fitted value 0.58 on
    2008-2023 walk-forward residuals).
    """
    if home_rest is None or away_rest is None:
        return predicted_margin
    if isinstance(home_rest, float) and math.isnan(home_rest):
        return predicted_margin
    if isinstance(away_rest, float) and math.isnan(away_rest):
        return predicted_margin
    return predicted_margin + pts_per_day * (home_rest - away_rest)


def apply_rest_adjustment_total(predicted_total: float,
                                home_rest: float | None,
                                away_rest: float | None,
                                pts_per_day: float = REST_TOTAL_PTS_PER_DAY,
                                mean_days: float = REST_MEAN_DAYS) -> float:
    """Candidate totals adjustment: +pts_per_day per combined rest day above
    the league mean (home_rest + away_rest - 2*mean_days).

    Fitted slope is small (0.27); test before keeping. Returns the
    prediction unchanged when either rest value is missing.
    """
    if home_rest is None or away_rest is None:
        return predicted_total
    if isinstance(home_rest, float) and math.isnan(home_rest):
        return predicted_total
    if isinstance(away_rest, float) and math.isnan(away_rest):
        return predicted_total
    return (predicted_total
            + pts_per_day * ((home_rest + away_rest) - 2.0 * mean_days))
