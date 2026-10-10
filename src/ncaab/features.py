"""Rest-day features for the NCAAB model (kept separate from the core model).

Same role as src/nba/features.py: exposes a candidate adjustment so the
backtest can measure whether it improves walk-forward RMSE and keep it only
if it does. CBB schedules are irregular (MTE tournaments = 3 games in 3
days; exam breaks = 10+ days off), so the effect may differ from the NBA's.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

REST_CAP_DAYS = 10  # long exam/holiday breaks aren't extra rest


def add_rest_days(games: pd.DataFrame) -> pd.DataFrame:
    """Add ``home_rest`` / ``away_rest`` columns: full days off since each
    team's previous game. Back-to-back = 0, one day off = 1, etc.

    Conventions (mirrors src/nba/features.py):
      - Requires ``date``, ``season``, ``home_team``, ``away_team`` columns.
      - A team's first game of a season gets NaN (offseason rest is not
        informative).
      - Rest is capped at REST_CAP_DAYS.
      - Rows are returned in their original order.
    """
    df = games.copy()
    orig_index = df.index
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
                          pts_per_day: float = 0.0) -> float:
    """Candidate margin adjustment: +pts_per_day per day of rest
    differential (home_rest - away_rest). The backtest fits pts_per_day on
    walk-forward residuals and keeps it only if RMSE improves."""
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
                                pts_per_day: float = 0.0,
                                mean_days: float = 3.0) -> float:
    """Candidate totals adjustment: +pts_per_day per combined rest day above
    the mean (home_rest + away_rest - 2*mean_days). Fit before keeping."""
    if home_rest is None or away_rest is None:
        return predicted_total
    if isinstance(home_rest, float) and math.isnan(home_rest):
        return predicted_total
    if isinstance(away_rest, float) and math.isnan(away_rest):
        return predicted_total
    return (predicted_total
            + pts_per_day * ((home_rest + away_rest) - 2.0 * mean_days))
