"""PPA-based college football team ratings, walk-forward vs closing lines.

Same architecture as the NFL EPA model, adapted for college:

- Efficiency = PPA/play (garbage time excluded at the source), because
  college pace varies wildly (60-90 plays/game). Totals would lie.
- Opponent-adjusted exactly like the NFL model; the betting line is NEVER
  an input, only the benchmark.
- FBS-vs-FBS only. Neutral-site games get no home edge.
- Walk-forward: for each game in chronological order, predict from games
  already played, then learn from it.

College-specific parameters (empirically tunable, documented honestly):
    PLAYS_PER_GAME = 72   (college pace > NFL's 63)
    HOME_EDGE_PTS  = 2.8  (campus home fields > NFL's 1.8; calibrate below)
    WINDOW_GAMES   = 12   (about one college season of trailing games)
    CARRYOVER      = 0.4  (portal-era roster turnover -> less prior weight
                           than the NFL's 0.5)
"""
from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "cfb"

PLAYS_PER_GAME = 72.0
HOME_EDGE_PTS = 2.8
WINDOW_GAMES = 12
MIN_GAMES = 4
CARRYOVER = 0.4


def load_team_games() -> pd.DataFrame:
    """One row per team-game: offensive/defensive PPA per play.

    CFBD's PPA "overall" is already per-play (verified 2026-10-01), so no
    division by play count. home_plays/away_plays are kept only as a
    completeness filter: a team-game with no parsed plays is dropped."""
    g = pd.read_parquet(DATA / "cfb_games.parquet")
    rows = []
    for _, r in g.iterrows():
        for side, opp_side in (("home", "away"), ("away", "home")):
            off = r[f"{side}_off_ppa"]
            dfn = r[f"{side}_def_ppa"]
            plays = r[f"{side}_plays"]
            if pd.isna(off) or pd.isna(dfn) or not plays:
                continue
            rows.append({
                "game_id": r["game_id"],
                "season": int(r["season"]),
                "week": int(r["week"]) if pd.notna(r["week"]) else 99,
                "date": r["date"],
                "team": r[f"{side}_team"],
                "opp": r[f"{opp_side}_team"],
                "off_ppa_play": float(off),
                "def_ppa_play": float(dfn),
                "neutral": bool(r["neutral"]),
            })
    tg = pd.DataFrame(rows)
    return tg.sort_values(["season", "week", "date", "game_id"]).reset_index(drop=True)


def adjusted_ratings(team_games: pd.DataFrame, upto_idx: int,
                     season: int, prior: dict) -> tuple[dict, dict]:
    """Opponent-adjusted (off, def) PPA/play per team vs league average,
    using only games before upto_idx. prior = last season's final ratings."""
    hist = team_games.iloc[:upto_idx]
    hist = hist[hist["season"] >= season - 1]
    recent = hist.groupby("team").tail(WINDOW_GAMES)
    if recent.empty:
        return {}, {}

    raw_off, raw_def, opps = {}, {}, {}
    for team, gg in recent.groupby("team"):
        raw_off[team] = gg["off_ppa_play"].mean()
        raw_def[team] = gg["def_ppa_play"].mean()
        opps[team] = list(gg["opp"])
        n = len(gg)
        if n < MIN_GAMES and team in prior:
            w = n / MIN_GAMES
            raw_off[team] = w * raw_off[team] + (1 - w) * prior[team][0]
            raw_def[team] = w * raw_def[team] + (1 - w) * prior[team][1]

    lg_off = sum(raw_off.values()) / len(raw_off)
    lg_def = sum(raw_def.values()) / len(raw_def)

    # Single-step schedule correction (same reasoning as the NFL model:
    # iterating lets off/def adjustments feed back and blow up).
    off, deff = {}, {}
    for t in raw_off:
        opp_d = [raw_def[o] - lg_def for o in opps[t] if o in raw_def]
        opp_o = [raw_off[o] - lg_off for o in opps[t] if o in raw_off]
        off[t] = (raw_off[t] - lg_off) - (sum(opp_d) / len(opp_d) if opp_d else 0)
        deff[t] = (raw_def[t] - lg_def) - (sum(opp_o) / len(opp_o) if opp_o else 0)
    return off, deff


def predict(off: dict, deff: dict, home: str, away: str,
            neutral: bool, epa_const: float) -> tuple[float, float] | None:
    if home not in off or away not in off:
        return None
    exp_home_off = off[home] + deff[away]
    exp_away_off = off[away] + deff[home]
    edge = 0.0 if neutral else HOME_EDGE_PTS
    our_margin = (exp_home_off - exp_away_off) * PLAYS_PER_GAME + edge
    our_total = (exp_home_off + exp_away_off) * PLAYS_PER_GAME + epa_const
    return our_margin, our_total


def run_backtest(seasons: list[int] | None = None) -> dict:
    team_games = load_team_games()
    games = pd.read_parquet(DATA / "cfb_games.parquet")
    if seasons:
        games = games[games["season"].isin(seasons)].copy()
    games = games.dropna(subset=["line_spread", "line_total"]).copy()
    games = games.sort_values(["season", "week", "date"]).reset_index(drop=True)

    # game_id -> first team_games row index for that game (walk-forward cutoff)
    gid_first: dict[int, int] = {}
    for i, r in team_games.iterrows():
        gid_first.setdefault(int(r["game_id"]), i)

    prior: dict = {}
    last_season = None
    season_final: dict = {}
    seasons: dict[int, dict] = {}

    n = su = 0
    our_se = line_se = 0.0
    our_tse = line_tse = 0.0
    ats = [0, 0, 0]
    ou = [0, 0, 0]
    epa_const_hist: list[float] = []

    for _, row in games.iterrows():
        season = int(row["season"])
        if last_season is not None and season != last_season:
            prior = {t: (CARRYOVER * v[0], CARRYOVER * v[1])
                     for t, v in season_final.items()}
        last_season = season

        home, away = row["home_team"], row["away_team"]
        cutoff = gid_first.get(int(row["game_id"]))
        if cutoff is None:
            continue
        s = seasons.setdefault(season, {
            "games": 0, "su": 0, "our_se": 0.0, "line_se": 0.0,
            "our_tse": 0.0, "line_tse": 0.0,
            "w": 0, "l": 0, "p": 0, "ow": 0, "ol": 0, "op": 0,
        })
        off, deff = adjusted_ratings(team_games, cutoff, season, prior)
        epa_const = (sum(epa_const_hist) / len(epa_const_hist)
                     if epa_const_hist else 58.0)  # college totals > NFL
        pr = predict(off, deff, home, away, bool(row["neutral"]), epa_const)
        if pr is None:
            continue
        our_margin, our_total = pr

        actual_margin = float(row["home_score"]) - float(row["away_score"])
        actual_total = float(row["home_score"]) + float(row["away_score"])
        # Stored line_spread is a HOME margin (positive = home favored).
        # Verified 2026-10-01 against completed CFBD games: raw CFBD spread
        # is an away margin, negated once at ingestion in fetch_cfb.py.
        line_margin = float(row["line_spread"])
        line_total = float(row["line_total"])

        su += (our_margin > 0) == (actual_margin > 0)
        our_se += (our_margin - actual_margin) ** 2
        line_se += (line_margin - actual_margin) ** 2
        our_tse += (our_total - actual_total) ** 2
        line_tse += (line_total - actual_total) ** 2
        s["games"] += 1
        s["su"] += (our_margin > 0) == (actual_margin > 0)
        s["our_se"] += (our_margin - actual_margin) ** 2
        s["line_se"] += (line_margin - actual_margin) ** 2
        s["our_tse"] += (our_total - actual_total) ** 2
        s["line_tse"] += (line_total - actual_total) ** 2

        e = our_margin - line_margin
        if abs(e) >= 1.5:
            r = actual_margin - line_margin
            if abs(r) < 0.01:
                ats[2] += 1
                s["p"] += 1
            elif (r > 0) == (e > 0):
                ats[0] += 1
                s["w"] += 1
            else:
                ats[1] += 1
                s["l"] += 1
        et = our_total - line_total
        if abs(et) >= 3.0:
            r = actual_total - line_total
            if abs(r) < 0.01:
                ou[2] += 1
                s["op"] += 1
            elif (r > 0) == (et > 0):
                ou[0] += 1
                s["ow"] += 1
            else:
                ou[1] += 1
                s["ol"] += 1
        n += 1
        # Calibrate the PPA->points constant as the trailing average total:
        # combined offensive PPA/play is relative to league average (~0),
        # so the constant carries the sport's scoring level.
        epa_const_hist.append(actual_total)

        off2, def2 = adjusted_ratings(team_games, cutoff + 2, season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    decided = ats[0] + ats[1]
    ou_dec = ou[0] + ou[1]
    resid = math.sqrt(our_se / n) if n else float("nan")
    per_season = []
    for yr in sorted(seasons):
        s = seasons[yr]
        dec = s["w"] + s["l"]
        odec = s["ow"] + s["ol"]
        per_season.append({
            "season": yr,
            "games": s["games"],
            "straight_up_pct": round(s["su"] / s["games"], 4) if s["games"] else None,
            "our_rmse": round(math.sqrt(s["our_se"] / s["games"]), 2) if s["games"] else None,
            "line_rmse": round(math.sqrt(s["line_se"] / s["games"]), 2) if s["games"] else None,
            "ats_w": s["w"], "ats_l": s["l"], "ats_p": s["p"],
            "ats_pct": round(s["w"] / dec, 4) if dec else None,
            "ou_w": s["ow"], "ou_l": s["ol"], "ou_p": s["op"],
            "ou_pct": round(s["ow"] / odec, 4) if odec else None,
        })
    return {
        "games": n,
        "straight_up_pct": su / n if n else float("nan"),
        "our_margin_rmse": resid,
        "line_margin_rmse": math.sqrt(line_se / n) if n else float("nan"),
        "ats": tuple(ats),
        "ats_pct": ats[0] / decided if decided else float("nan"),
        "our_total_rmse": math.sqrt(our_tse / n) if n else float("nan"),
        "line_total_rmse": math.sqrt(line_tse / n) if n else float("nan"),
        "ou": tuple(ou),
        "ou_pct": ou[0] / ou_dec if ou_dec else float("nan"),
        "margin_sd": resid,  # reuse as probability calibrator
        "total_sd": math.sqrt(our_tse / n) if n else float("nan"),
        "seasons": per_season,
    }


if __name__ == "__main__":
    import sys
    seasons = None
    if len(sys.argv) > 1:
        a, b = sys.argv[1].split("-")
        seasons = list(range(int(a), int(b) + 1))
    r = run_backtest(seasons)
    w, l, p = r["ats"]
    ow, ol, op = r["ou"]
    print(f"Games backtested:      {r['games']:,}")
    print(f"Straight-up accuracy:  {r['straight_up_pct']:.1%}")
    print(f"Our margin RMSE:       {r['our_margin_rmse']:.2f}  (line: {r['line_margin_rmse']:.2f})")
    print(f"ATS (>=1.5pt edge):    {w}-{l}-{p}  ({r['ats_pct']:.1%})")
    print(f"Our total RMSE:        {r['our_total_rmse']:.2f}  (line: {r['line_total_rmse']:.2f})")
    print(f"O/U (>=3pt edge):      {ow}-{ol}-{op}  ({r['ou_pct']:.1%})")
