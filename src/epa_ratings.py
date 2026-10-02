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

import numpy as np
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
MIN_GAMES = 4              # below this effective sample, blend toward prior-season rating
CARRYOVER = 0.5            # prior season weight at season start
ADJ_ITERS = 25
# Recency: a game's weight halves every RECENCY_HALF_LIFE games. Without
# this, Week 4 ratings are ~80% last season (14 of 17 trailing games) —
# which is how a total like 27.4 happens in a league averaging 46.
RECENCY_HALF_LIFE = 8
_RECENCY_DECAY = 0.5 ** (1.0 / RECENCY_HALF_LIFE)

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


def load_team_games(years: list[int] | None = None) -> pd.DataFrame:
    """One row per team-game: offensive and defensive EPA/play."""
    years = years or PBP_YEARS
    frames = []
    for year in years:
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


def load_qb_plays(years: list[int] | None = None) -> pd.DataFrame:
    """One row per QB dropback (pass attempt or sack), with passer EPA."""
    years = years or PBP_YEARS
    frames = []
    for year in years:
        pbp = pd.read_parquet(
            DATA / f"play_by_play_{year}.parquet",
            columns=["game_id", "week", "season", "posteam", "passer",
                     "passer_id", "pass_attempt", "sack", "epa"],
        )
        q = pbp[pbp["passer_id"].notna() & pbp["epa"].notna()
                & ((pbp["pass_attempt"] == 1) | (pbp["sack"] == 1))]
        frames.append(
            q[["game_id", "week", "season", "posteam", "passer_id", "epa"]])
    qb = pd.concat(frames, ignore_index=True)
    return qb.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


# How much of a QB's EPA edge over the QBs who generated the team's rating
# carries into team offensive EPA/play. Pass plays are ~55% of offense, and
# part of a QB's number is scheme/support, so this is well below 1.
QB_IMPACT = 0.35
# Regression strength for QB EPA/play (dropbacks).
QB_PRIOR_ATT = 150
# If the starter took more than this share of the window's dropbacks,
# treat it as "no change" rather than noise.
QB_SAME_THRESHOLD = 0.85
# Sanity cap: no single QB change is worth more than ~3 points.
QB_MAX_ADJ = 0.05


def _decayed_mean(values, n):
    w = _RECENCY_DECAY ** np.arange(n - 1, -1, -1)
    return float(np.average(values, weights=w))


def qb_adjustments(qb_plays: pd.DataFrame, team_games: pd.DataFrame,
                   upto_idx: int, season: int,
                   matchups: list[tuple]) -> dict:
    """EPA/play bump per team for a QB change.

    matchups: (home_abbr, away_abbr, home_qb_id, away_qb_id). QB ids are
    nflverse GSIS ids (match the schedule's home_qb_id). Returns
    {team_abbr: adj}; 0 when the starter is unknown or effectively unchanged.
    """
    tg = team_games.iloc[:upto_idx]
    # Leakage-safe cutoff: only QB plays from games already in team_games
    # (row-based, like the ratings). A (season, week) cutoff would leak the
    # very game being predicted, since the parquet holds full seasons.
    allowed_games = set(tg["game_id"])
    qp = qb_plays[qb_plays["game_id"].isin(allowed_games)]
    tg = tg[tg["season"] >= season - 1]
    if tg.empty:
        return {}
    lg_mean = float(qp["epa"].mean()) if len(qp) else 0.0

    # Trailing window game_ids per team (same window as the ratings).
    windows: dict[str, list] = {}
    for team, g in tg.groupby("team"):
        g = g.sort_values(["season", "week", "game_id"])
        windows[team] = list(g.tail(WINDOW_GAMES)["game_id"])

    adj: dict[str, float] = {}
    for home, away, home_qb, away_qb in matchups:
        for team, qb_id in ((home, home_qb), (away, away_qb)):
            adj[team] = _qb_adj_for_team(qp, windows.get(team, []), team,
                                         qb_id, lg_mean)
    return adj


def _qb_adj_for_team(qp: pd.DataFrame, game_ids: list, team: str,
                     qb_id, lg_mean: float) -> float:
    if not game_ids or qb_id is None or (isinstance(qb_id, float) and np.isnan(qb_id)):
        return 0.0
    qb_id = str(qb_id)
    # Window dropbacks thrown FOR this team, in these games.
    wq = qp[qp["game_id"].isin(game_ids) & (qp["posteam"] == team)].copy()
    if wq.empty:
        return 0.0
    n_win = len(wq)
    # No change: the starter threw almost all of the window's passes.
    if (wq["passer_id"] == qb_id).mean() >= QB_SAME_THRESHOLD:
        return 0.0
    # Per-game QB EPA/play, decay-weighted BY GAME (consistent with the
    # team ratings). Weighting by dropback would let one bad recent
    # relief appearance dominate the whole window.
    order = {gid: i for i, gid in enumerate(game_ids)}
    wq["gw"] = wq["game_id"].map(
        lambda g: _RECENCY_DECAY ** (len(game_ids) - 1 - order[g]))
    win_epa = float(np.average(wq["epa"], weights=wq["gw"]))
    win_rel = (win_epa - lg_mean) * n_win / (n_win + QB_PRIOR_ATT)

    # Starter's own trailing form (any team), most recent 400 dropbacks.
    sq = qp[qp["passer_id"] == qb_id].sort_values(["season", "week", "game_id"])
    sq = sq.tail(400)
    n_st = len(sq)
    if n_st == 0:
        return 0.0
    st_epa = _decayed_mean(sq["epa"].to_numpy(), n_st)
    st_rel = (st_epa - lg_mean) * n_st / (n_st + QB_PRIOR_ATT)

    adj = QB_IMPACT * (st_rel - win_rel)
    return float(np.clip(adj, -QB_MAX_ADJ, QB_MAX_ADJ))


def adjusted_ratings(team_games: pd.DataFrame, upto_idx: int,
                     season: int, prior: dict) -> tuple[dict, dict, dict]:
    """Opponent-adjusted (off, def) EPA/play per team, relative to league
    average, using only games before upto_idx. Games are time-decayed
    (recent games count more); pace is the similarly-weighted trailing
    offensive plays/game. prior = last season's final ratings for
    season-start blending. Returns (off, deff, pace)."""
    hist = team_games.iloc[:upto_idx]
    hist = hist[hist["season"] >= season - 1]  # current + previous season
    recent = hist.groupby("team").tail(WINDOW_GAMES)
    if recent.empty:
        return {}, {}, {}

    raw_off, raw_def, pace, opps, opp_w = {}, {}, {}, {}, {}
    for team, g in recent.groupby("team"):
        g = g.sort_values(["season", "week", "game_id"])
        n = len(g)
        # most recent game weight 1, older games decay
        w = _RECENCY_DECAY ** np.arange(n - 1, -1, -1)
        raw_off[team] = float(np.average(g["off_epa_play"], weights=w))
        raw_def[team] = float(np.average(g["def_epa_play"], weights=w))
        pace[team] = float(np.average(g["off_plays"], weights=w))
        opps[team] = list(g["opp"])
        opp_w[team] = list(w)
        # Effective sample size shrinks under decay; blend toward the prior
        # when there isn't much (decayed) information yet.
        n_eff = w.sum() ** 2 / (w ** 2).sum()
        if n_eff < MIN_GAMES and team in prior:
            b = n_eff / MIN_GAMES
            raw_off[team] = b * raw_off[team] + (1 - b) * prior[team][0]
            raw_def[team] = b * raw_def[team] + (1 - b) * prior[team][1]

    lg_off = sum(raw_off.values()) / len(raw_off)
    lg_def = sum(raw_def.values()) / len(raw_def)

    # Single-step schedule correction (NOT iterated: iterating lets
    # off/def adjustments feed back into each other and blow up).
    # Opponent contributions use the same time-decay weights.
    off, deff = {}, {}
    for t in raw_off:
        pairs_d = [(raw_def[o] - lg_def, wt)
                   for o, wt in zip(opps[t], opp_w[t]) if o in raw_def]
        pairs_o = [(raw_off[o] - lg_off, wt)
                   for o, wt in zip(opps[t], opp_w[t]) if o in raw_off]
        adj_d = (sum(v * wt for v, wt in pairs_d) / sum(wt for _, wt in pairs_d)
                 if pairs_d else 0.0)
        adj_o = (sum(v * wt for v, wt in pairs_o) / sum(wt for _, wt in pairs_o)
                 if pairs_o else 0.0)
        off[t] = (raw_off[t] - lg_off) - adj_d
        deff[t] = (raw_def[t] - lg_def) - adj_o
    return off, deff, pace


def run_backtest() -> dict:
    team_games = load_team_games()
    qb_plays = load_qb_plays()
    sched_qb = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "home_team", "away_team",
                 "home_qb_id", "away_qb_id"])
    qb_lookup = {(int(r.season), int(r.week), r.home_team, r.away_team):
                 (r.home_qb_id, r.away_qb_id) for r in sched_qb.itertuples()}
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
        off, deff, pace = adjusted_ratings(team_games, cutoff, season, prior)
        if home not in off or away not in off:
            continue  # cold start, skip

        # Expected offensive EPA/play per side. A generous defense (positive
        # deff = allows above-average EPA) ADDS to the opponent's expectation.
        # QB change bump: 0 when the starter is unknown or unchanged.
        hq, aq = qb_lookup.get(key, (None, None))
        qadj = qb_adjustments(qb_plays, team_games, cutoff, season,
                              [(home, away, hq, aq)])
        exp_home_off = off[home] + deff[away] + qadj.get(home, 0.0)
        exp_away_off = off[away] + deff[home] + qadj.get(away, 0.0)
        edge_pts = 0.0 if neutral else HOME_EDGE_PTS
        # Expected pace: average of the two teams' trailing plays/game.
        exp_plays = (pace.get(home, PLAYS_PER_GAME)
                     + pace.get(away, PLAYS_PER_GAME)) / 2
        # Margin ~= net EPA differential: both teams start drives with roughly
        # the same expected points, so drive-start EP cancels out.
        our_margin = (exp_home_off - exp_away_off) * exp_plays + edge_pts
        # Total ~= combined offensive EPA + typical drive-start EP per game.
        # Empirically combined offensive EPA ≈ 0 (both teams' drive-start
        # expected points roughly cancel), so the constant ≈ avg total.
        epa_const = (sum(epa_const_hist) / len(epa_const_hist)) if epa_const_hist else 46.0
        our_total = (exp_home_off + exp_away_off) * exp_plays + epa_const

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
        off2, def2, _pace = adjusted_ratings(team_games, idxs[-1] + 1, season, prior)
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
