"""Walk-forward backtest: does the ratings model beat the closing line?

Method (leakage-safe):
  - Games processed in chronological order.
  - For each game, the model predicts home margin from ratings built ONLY
    on games already played (prediction precedes update).
  - The Vegas closing spread is used ONLY as the benchmark to beat,
    never as a model input.

Metrics:
  - ATS record: where our predicted margin differs from the closing line by
    >= 1.5 pts, we "bet" the side we favor; record wins/losses/pushes.
  - RMSE of our margin prediction vs actual margin, and the closing line's
    RMSE, on the same games.
"""
from __future__ import annotations

import math
import pandas as pd

from ratings import EloRatings, normalize_teams

from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
CSV = REPO / "spreadspoke_scores.csv"
PICK_THRESHOLD = 1.5   # only "bet" when we differ from the line by this much
BACKTEST_FROM = 1980  # full spread/total coverage starts here


def load_games() -> pd.DataFrame:
    df = pd.read_csv(CSV, parse_dates=["schedule_date"])
    df = normalize_teams(df)
    df = df[df["schedule_season"] >= BACKTEST_FROM].copy()
    df = df.dropna(subset=["spread_favorite", "team_favorite_id"]).copy()
    df = df.sort_values("schedule_date").reset_index(drop=True)
    return df


def fav_name(abbr: str, season: int) -> str | None:
    """Map spreadspoke favorite abbreviations to full team names, season-aware
    for relocated/renamed franchises. Returns None for pick'em games."""
    if abbr == "PICK":
        return None
    plain = {
        "ARI": None,  # handled below by season
        "ATL": "Atlanta Falcons",
        "BAL": None,  # Baltimore Colts pre-1984, Ravens from 1996
        "BUF": "Buffalo Bills",
        "CAR": "Carolina Panthers",
        "CHI": "Chicago Bears",
        "CIN": "Cincinnati Bengals",
        "CLE": "Cleveland Browns",
        "DAL": "Dallas Cowboys",
        "DEN": "Denver Broncos",
        "DET": "Detroit Lions",
        "GB": "Green Bay Packers",
        "HOU": None,  # Oilers pre-1997, Texans from 2002
        "IND": "Indianapolis Colts",
        "JAX": "Jacksonville Jaguars",
        "KC": "Kansas City Chiefs",
        "LAC": None,  # San Diego Chargers pre-2017, LA from 2017
        "LAR": None,  # LA Rams pre-1995, St. Louis 1995-2015, LA from 2016
        "LV": "Las Vegas Raiders",
        "LVR": None,  # Oakland pre-1982, LA 1982-94, Oakland 1995-2019, LV from 2020
        "MIA": "Miami Dolphins",
        "MIN": "Minnesota Vikings",
        "NE": "New England Patriots",
        "NJY": "New York Jets",
        "NO": "New Orleans Saints",
        "NYG": "New York Giants",
        "NYJ": "New York Jets",
        "PHI": "Philadelphia Eagles",
        "PIT": "Pittsburgh Steelers",
        "SEA": "Seattle Seahawks",
        "SF": "San Francisco 49ers",
        "TB": "Tampa Bay Buccaneers",
        "TEN": None,  # Tennessee Oilers 1997-98, Titans from 1999
        "WAS": None,  # Redskins / Football Team / Commanders by season
    }
    if plain.get(abbr):
        return plain[abbr]
    if abbr == "ARI":
        if season <= 1987:
            return "St. Louis Cardinals"
        return "Phoenix Cardinals" if season <= 1993 else "Arizona Cardinals"
    if abbr == "BAL":
        return "Baltimore Colts" if season <= 1983 else "Baltimore Ravens"
    if abbr == "HOU":
        return "Houston Oilers" if season <= 1996 else "Houston Texans"
    if abbr == "TEN":
        if season <= 1996:
            return "Houston Oilers"
        return "Tennessee Oilers" if season <= 1998 else "Tennessee Titans"
    if abbr == "LAC":
        return "San Diego Chargers" if season <= 2016 else "Los Angeles Chargers"
    if abbr == "LAR":
        if season <= 1994:
            return "Los Angeles Rams"
        return "St. Louis Rams" if season <= 2015 else "Los Angeles Rams"
    if abbr == "LVR":
        if season <= 1981:
            return "Oakland Raiders"
        if season <= 1994:
            return "Los Angeles Raiders"
        return "Oakland Raiders" if season <= 2019 else "Las Vegas Raiders"
    if abbr == "WAS":
        if season <= 2019:
            return "Washington Redskins"
        return "Washington Football Team" if season <= 2021 else "Washington Commanders"
    return None


def closing_home_spread(row: pd.Series) -> float:
    """Closing spread expressed as home-team margin (positive = home favored)."""
    favorite = fav_name(str(row["team_favorite_id"]).strip(), int(row["schedule_season"]))
    if favorite is None:  # pick'em
        return 0.0
    spread = float(row["spread_favorite"])  # negative = favorite's edge
    return -spread if favorite == row["team_home"] else spread


def run_backtest() -> dict:
    games = load_games()
    elo = EloRatings()

    n = 0
    ats_w = ats_l = ats_p = 0
    our_se, line_se = 0.0, 0.0
    su_w = 0

    for _, row in games.iterrows():
        home, away = row["team_home"], row["team_away"]
        neutral = bool(row["stadium_neutral"])
        season = int(row["schedule_season"])

        # Predict BEFORE updating: this is the whole honesty of the backtest.
        our_margin = elo.game_prediction(home, away, neutral)
        actual_margin = float(row["score_home"]) - float(row["score_away"])
        line_margin = closing_home_spread(row)

        # Straight-up pick quality.
        su_w += (our_margin > 0) == (actual_margin > 0)

        # Margin prediction error vs line error.
        our_se += (our_margin - actual_margin) ** 2
        line_se += (line_margin - actual_margin) ** 2

        # ATS: pick side where our number beats the line by the threshold.
        # Home covers when actual_margin - line_margin > 0.
        edge = our_margin - line_margin
        if abs(edge) >= PICK_THRESHOLD:
            picked_home = edge > 0
            result = actual_margin - line_margin  # >0 home covers, <0 away covers
            if abs(result) < 0.01:
                ats_p += 1
            elif (result > 0) == picked_home:
                ats_w += 1
            else:
                ats_l += 1
        n += 1

        # NOW learn from the game.
        elo.record_game(home, away, actual_margin, season, neutral)

    decided = ats_w + ats_l
    return {
        "games": n,
        "straight_up_pct": su_w / n,
        "our_margin_rmse": math.sqrt(our_se / n),
        "line_margin_rmse": math.sqrt(line_se / n),
        "ats_record": (ats_w, ats_l, ats_p),
        "ats_win_pct": ats_w / decided if decided else float("nan"),
        "ats_decided": decided,
    }


if __name__ == "__main__":
    r = run_backtest()
    w, l, p = r["ats_record"]
    print(f"Games backtested:      {r['games']:,}")
    print(f"Straight-up accuracy:  {r['straight_up_pct']:.1%}")
    print(f"Our margin RMSE:       {r['our_margin_rmse']:.2f} pts")
    print(f"Closing-line RMSE:     {r['line_margin_rmse']:.2f} pts")
    print(f"ATS record (>=1.5 pt edge): {w}-{l}-{p}  ({r['ats_win_pct']:.1%} on {r['ats_decided']:,} picks)")
