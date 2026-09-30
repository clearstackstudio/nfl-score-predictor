"""EPA-based team ratings, walk-forward backtested against closing lines.

Ratings are built ONLY from play-by-play efficiency (EPA/play), opponent
adjusted, never from the betting line. For each game, in chronological
order: predict first (from games already played), then learn from it.

Prediction:
    pred_margin = ((home_off - away_def) - (away_off - home_def)) * PLAYS
                  + home_edge
    pred_total  = league_avg_total + ((home_off - away_def)
                  + (away_off - home_def)) * PLAYS
where off/def are opponent-adjusted EPA/play relative to league average.
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from backtest import load_games, closing_home_spread, fav_name  # noqa: F401

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

PBP_YEARS = [2021, 2022, 2023, 2024]
PLAYOFF_WEEK = {"Wildcard": 19, "Division": 20, "Conference": 21,
                "Superbowl": 22}


def week_int(w) -> int:
    w = str(w).strip()
    if w in PLAYOFF_WEEK:
        return PLAYOFF_WEEK[w]
    return int(w)
PLAYS_PER_GAME = 63.0
HOME_EDGE_PTS = 1.8
WINDOW_GAMES = 17          # trailing games per team
MIN_GAMES = 4              # below this, blend toward prior-season rating
CARRYOVER = 0.5            # prior season weight at season start
ADJ_ITERS = 25

# nflverse abbr -> spreadspoke full name (2021-2024 era)
ABBR_TO_FULL = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons",
    "BAL": "Baltimore Ravens", "BUF": "Buffalo Bills",
    "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
    "DAL": "Dallas Cowboys", "DEN": "Denver Broncos",
    "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts",
    "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs",
    "LA": "Los Angeles Rams", "LAC": "Los Angeles Chargers",
    "LV": "Las Vegas Raiders", "MIA": "Miami Dolphins",
    "MIN": "Minnesota Vikings", "NE": "New England Patriots",
    "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles",
    "PIT": "Pittsburgh Steelers", "SEA": "Seattle Seahawks",
    "SF": "San Francisco 49ers", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
}


def load_team_games() -> pd.DataFrame:
    """One row per team-game: offensive and defensive EPA/play."""
    frames = []
    for year in PBP_YEARS:
        pbp = pd.read_parquet(
            DATA / f"play_by_play_{year}.parquet",
            columns=["game_id", "week", "season", "posteam", "defteam",
                     "epa", "pass_attempt", "rush_attempt",
                     "home_team", "away_team"],
        )
        plays = pbp[
            ((pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1))
            & pbp["epa"].notna()
            & pbp["posteam"].notna()
        ]
        off = (plays.groupby(["game_id", "week", "season", "posteam",
                              "home_team", "away_team"])["epa"]
               .agg(["sum", "count"]).reset_index())
        off = off.rename(columns={"posteam": "team", "sum": "off_epa",
                                  "count": "off_plays"})
        deff = (plays.groupby(["game_id", "defteam"])["epa"]
                .agg(["sum", "count"]).reset_index())
        deff = deff.rename(columns={"defteam": "team", "sum": "def_epa",
                                    "count": "def_plays"})
        g = off.merge(deff, on=["game_id", "team"], how="outer")
        g["off_epa_play"] = g["off_epa"] / g["off_plays"]
        g["def_epa_play"] = g["def_epa"] / g["def_plays"]
        # opponent = the other team in the game
        g["opp"] = g.apply(
            lambda r: r["away_team"] if r["team"] == r["home_team"]
            else r["home_team"], axis=1)
        frames.append(g)
    tg = pd.concat(frames, ignore_index=True)
    return tg.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def adjusted_ratings(team_games: pd.DataFrame, upto_idx: int,
                     season: int, prior: dict) -> tuple[dict, dict]:
    """Opponent-adjusted (off, def) EPA/play per team, relative to league
    average, using only games before upto_idx. prior = last season's final
    ratings for season-start blending."""
    hist = team_games.iloc[:upto_idx]
    hist = hist[hist["season"] >= season - 1]  # current + previous season
    recent = hist.groupby("team").tail(WINDOW_GAMES)
    if recent.empty:
        return {}, {}

    raw_off, raw_def, opps = {}, {}, {}
    for team, g in recent.groupby("team"):
        raw_off[team] = g["off_epa_play"].mean()
        raw_def[team] = g["def_epa_play"].mean()
        opps[team] = list(g["opp"])
        n = len(g)
        if n < MIN_GAMES and team in prior:
            w = n / MIN_GAMES
            raw_off[team] = w * raw_off[team] + (1 - w) * prior[team][0]
            raw_def[team] = w * raw_def[team] + (1 - w) * prior[team][1]

    lg_off = sum(raw_off.values()) / len(raw_off)
    lg_def = sum(raw_def.values()) / len(raw_def)

    # Single-step schedule correction (NOT iterated: iterating lets
    # off/def adjustments feed back into each other and blow up).
    off, deff = {}, {}
    for t in raw_off:
        opp_d = [raw_def[o] - lg_def for o in opps[t] if o in raw_def]
        opp_o = [raw_off[o] - lg_off for o in opps[t] if o in raw_off]
        off[t] = (raw_off[t] - lg_off) - (sum(opp_d) / len(opp_d) if opp_d else 0)
        deff[t] = (raw_def[t] - lg_def) - (sum(opp_o) / len(opp_o) if opp_o else 0)
    return off, deff


def run_backtest() -> dict:
    team_games = load_team_games()
    games = load_games()
    games = games[games["schedule_season"].isin(PBP_YEARS)].copy()
    games["home_abbr"] = games["team_home"].map(
        {v: k for k, v in ABBR_TO_FULL.items()})
    games["away_abbr"] = games["team_away"].map(
        {v: k for k, v in ABBR_TO_FULL.items()})
    games = games.dropna(subset=["home_abbr", "away_abbr"]).copy()
    games = games.sort_values("schedule_date").reset_index(drop=True)

    # (season, week, home, away) -> team_games row indices, for walk-forward cutoffs
    tg_lookup: dict[tuple, list[int]] = {}
    for i, r in team_games[["season", "week", "home_team", "away_team"]].iterrows():
        tg_lookup.setdefault((int(r["season"]), int(r["week"]),
                              r["home_team"], r["away_team"]), []).append(i)

    prior: dict = {}
    last_season = None
    season_final: dict = {}

    n = su = 0
    our_se = line_se = 0.0
    our_tse = line_tse = 0.0
    ats = [0, 0, 0]  # w, l, push
    ou = [0, 0, 0]

    # trailing calibration: total points minus combined offensive EPA
    epa_const_hist: list[float] = []

    for _, row in games.iterrows():
        season = int(row["schedule_season"])
        if last_season is not None and season != last_season:
            prior = {t: (CARRYOVER * v[0], CARRYOVER * v[1])
                     for t, v in season_final.items()}
        last_season = season

        home, away = row["home_abbr"], row["away_abbr"]
        neutral = bool(row["stadium_neutral"])

        # cutoff: team_games rows strictly before this game
        key = (season, week_int(row["schedule_week"]), home, away)
        idxs = tg_lookup.get(key, [])
        if not idxs:
            continue  # no play-by-play for this game (shouldn't happen)
        cutoff = idxs[0]
        off, deff = adjusted_ratings(team_games, cutoff, season, prior)
        if home not in off or away not in off:
            continue  # cold start, skip

        # Expected offensive EPA/play per side. A generous defense (positive
        # deff = allows above-average EPA) ADDS to the opponent's expectation.
        exp_home_off = off[home] + deff[away]
        exp_away_off = off[away] + deff[home]
        edge_pts = 0.0 if neutral else HOME_EDGE_PTS
        # Margin ~= net EPA differential: both teams start drives with roughly
        # the same expected points, so drive-start EP cancels out.
        our_margin = (exp_home_off - exp_away_off) * PLAYS_PER_GAME + edge_pts
        # Total ~= combined offensive EPA + typical drive-start EP per game,
        # calibrated on trailing games.
        epa_const = (sum(epa_const_hist) / len(epa_const_hist)) if epa_const_hist else 22.0
        our_total = (exp_home_off + exp_away_off) * PLAYS_PER_GAME + epa_const

        actual_margin = float(row["score_home"]) - float(row["score_away"])
        actual_total = float(row["score_home"]) + float(row["score_away"])
        line_margin = closing_home_spread(row)
        line_total = float(row["over_under_line"])

        su += (our_margin > 0) == (actual_margin > 0)
        our_se += (our_margin - actual_margin) ** 2
        line_se += (line_margin - actual_margin) ** 2
        our_tse += (our_total - actual_total) ** 2
        line_tse += (line_total - actual_total) ** 2

        e = our_margin - line_margin
        if abs(e) >= 1.5:
            r = actual_margin - line_margin
            if abs(r) < 0.01:
                ats[2] += 1
            elif (r > 0) == (e > 0):
                ats[0] += 1
            else:
                ats[1] += 1
        et = our_total - line_total
        if abs(et) >= 3.0:
            r = actual_total - line_total
            if abs(r) < 0.01:
                ou[2] += 1
            elif (r > 0) == (et > 0):
                ou[0] += 1
            else:
                ou[1] += 1
        n += 1
        # calibrate the EPA->points constant from this game's combined EPA
        game_epa = team_games.iloc[idxs]["off_epa"].sum()
        epa_const_hist.append(actual_total - game_epa)

        # learn: refresh season-final ratings including this game
        off2, def2 = adjusted_ratings(team_games, idxs[-1] + 1, season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    decided = ats[0] + ats[1]
    ou_dec = ou[0] + ou[1]
    return {
        "games": n,
        "straight_up_pct": su / n,
        "our_margin_rmse": math.sqrt(our_se / n),
        "line_margin_rmse": math.sqrt(line_se / n),
        "ats": tuple(ats),
        "ats_pct": ats[0] / decided if decided else float("nan"),
        "our_total_rmse": math.sqrt(our_tse / n),
        "line_total_rmse": math.sqrt(line_tse / n),
        "ou": tuple(ou),
        "ou_pct": ou[0] / ou_dec if ou_dec else float("nan"),
    }


if __name__ == "__main__":
    r = run_backtest()
    w, l, p = r["ats"]
    ow, ol, op = r["ou"]
    print(f"Games backtested:      {r['games']:,}")
    print(f"Straight-up accuracy:  {r['straight_up_pct']:.1%}")
    print(f"Our margin RMSE:       {r['our_margin_rmse']:.2f}  (line: {r['line_margin_rmse']:.2f})")
    print(f"ATS (>=1.5pt edge):    {w}-{l}-{p}  ({r['ats_pct']:.1%})")
    print(f"Our total RMSE:        {r['our_total_rmse']:.2f}  (line: {r['line_total_rmse']:.2f})")
    print(f"O/U (>=3pt edge):      {ow}-{ol}-{op}  ({r['ou_pct']:.1%})")
