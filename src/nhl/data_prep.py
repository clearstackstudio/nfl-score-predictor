"""MoneyPuck team game-by-game CSV -> tidy team-game table for the NHL model.

Source: data/nhl/moneypuck_all_teams_gamebygame.csv (MoneyPuck.com,
free for non-commercial use with credit). Regular season only
(NHL gameId type '02'), situation 'all'. One row per team-game.
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"
SRC = DATA / "moneypuck_all_teams_gamebygame.csv"
OUT = DATA / "team_games.parquet"

# MoneyPuck used dotted codes in early seasons (L.A, N.J, S.J, T.B);
# normalize to the modern NHL codes so team identity is continuous
# (and joins to standard odds feeds work).
CODE_FIX = {"L.A": "LAK", "N.J": "NJD", "S.J": "SJS", "T.B": "TBL"}


def build() -> pd.DataFrame:
    df = pd.read_csv(
        SRC,
        usecols=["season", "gameId", "gameDate", "playerTeam", "opposingTeam",
                 "home_or_away", "situation", "goalsFor", "goalsAgainst",
                 "xGoalsFor", "xGoalsAgainst", "iceTime"],
        low_memory=False,
    )
    df = df[(df["situation"] == "all")
            & (df["gameId"].astype(str).str[4:6] == "02")]
    tg = pd.DataFrame({
        "season": df["season"].astype(int),          # start year: 2019 = 2019-20
        "game_id": df["gameId"].astype(int),
        "date": pd.to_datetime(df["gameDate"].astype(str), format="%Y%m%d"),
        "team": df["playerTeam"].replace(CODE_FIX),
        "opp": df["opposingTeam"].replace(CODE_FIX),
        "home": (df["home_or_away"] == "HOME").astype(int),
        "gf": df["goalsFor"].astype(float),
        "ga": df["goalsAgainst"].astype(float),
        "xgf": df["xGoalsFor"].astype(float),
        "xga": df["xGoalsAgainst"].astype(float),
        "ice_s": df["iceTime"].astype(float),
    })
    tg = tg.sort_values(["date", "game_id", "home"]).reset_index(drop=True)
    # A few 2011-2013 games are mislabeled in the source (both teams
    # marked AWAY). Drop any game that doesn't pair cleanly, then assert.
    chk = tg.groupby("game_id")["home"].agg(["count", "sum"])
    bad_ids = chk[(chk["count"] != 2) | (chk["sum"] != 1)].index
    if len(bad_ids):
        print(f"data_prep: dropping {len(bad_ids)} unpaired games "
              f"(seasons {sorted(tg[tg.game_id.isin(bad_ids)]['season'].unique())})")
        tg = tg[~tg["game_id"].isin(bad_ids)].reset_index(drop=True)
    chk = tg.groupby("game_id")["home"].agg(["count", "sum"])
    assert (chk["count"] == 2).all() and (chk["sum"] == 1).all(), "game pairing broken"
    # Ground-truth scores: MoneyPuck's goalsFor omits the shootout-
    # deciding goal (~7% of games show an impossible tied final).
    # Official NHL API scores (scores_api.py) replace gf/ga for the
    # modeling window, where coverage is 100% (verified 2026-10-20).
    scores_path = DATA / "official_scores.parquet"
    if scores_path.exists():
        sc = pd.read_parquet(scores_path)[["game_id", "home_goals", "away_goals"]]
        tg = tg.merge(sc, on="game_id", how="left")
        have = tg["home_goals"].notna()
        tg.loc[have & (tg["home"] == 1), "gf"] = tg.loc[have & (tg["home"] == 1), "home_goals"]
        tg.loc[have & (tg["home"] == 1), "ga"] = tg.loc[have & (tg["home"] == 1), "away_goals"]
        tg.loc[have & (tg["home"] == 0), "gf"] = tg.loc[have & (tg["home"] == 0), "away_goals"]
        tg.loc[have & (tg["home"] == 0), "ga"] = tg.loc[have & (tg["home"] == 0), "home_goals"]
        tg = tg.drop(columns=["home_goals", "away_goals"])
        window = tg[tg["season"].between(2018, 2025)]
        assert (window["gf"] != window["ga"]).all(), "tied finals remain in window"
        print(f"data_prep: official scores applied to {have.sum()} team-games")
    tg.to_parquet(OUT, index=False)
    return tg


if __name__ == "__main__":
    tg = build()
    n_games = tg["game_id"].nunique()
    print(f"team-games: {len(tg)}  games: {n_games}")
    print("seasons:", sorted(tg["season"].unique()))
    ot = tg.groupby("game_id")["ice_s"].max()
    reached_ot = ot[ot > 3600]
    so = reached_ot[(reached_ot >= 3899) & (reached_ot <= 3901)]
    print(f"games past regulation: {len(reached_ot)}  shootout-length (3900s): {len(so)}"
          f"  OT-decided share: {1 - len(so) / len(reached_ot):.3f}")
