"""Current-season ingest for the NHL shadow pipeline.

Refreshes the two model inputs to the current season to date:
1. MoneyPuck's all-teams game-by-game CSV (the xG source data_prep.py
   reads) — re-downloaded whole; MoneyPuck updates it nightly.
2. Official NHL API scores for the current season — upserted into
   data/nhl/official_scores.parquet by game_id (older seasons are
   already complete and are never refetched). Official scores are
   the only honest labels: MoneyPuck's goalsFor excludes the
   shootout-deciding goal (~7% of games tie impossibly).

Then team_games.parquet is rebuilt via data_prep.build() and the
current season is verified: every game has an official score and no
tied finals remain. Data plumbing only — the model (v1.1) is frozen.
"""
import json
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_prep  # noqa: E402
from scores_api import ABBR_FIX, fetch  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"
MP_URL = ("https://moneypuck.com/moneypuck/playerData/careers/"
          "gameByGame/all_teams.csv")
MP_CSV = DATA / "moneypuck_all_teams_gamebygame.csv"
SCORES = DATA / "official_scores.parquet"
TEAMS = ["ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL", "DAL",
         "DET", "EDM", "FLA", "LAK", "MIN", "MTL", "NJD", "NSH", "NYI",
         "NYR", "OTT", "PHI", "PIT", "SEA", "SJS", "STL", "TBL", "TOR",
         "UTA", "VAN", "VGK", "WPG", "WSH"]


def current_season(today: date | None = None) -> int:
    """MoneyPuck/NHL season start year for 'now' (2026 = 2026-27)."""
    t = today or date.today()
    return t.year if t.month >= 8 else t.year - 1


def refresh_moneypuck(season: int) -> None:
    tmp = MP_CSV.with_suffix(".csv.tmp")
    subprocess.run(
        ["curl", "-sS", "-L", "--fail", "--max-time", "1200",
         "-o", str(tmp), MP_URL],
        check=True)
    ok = False
    try:
        if tmp.stat().st_size < 50_000_000:
            raise RuntimeError(f"MoneyPuck CSV suspiciously small: "
                               f"{tmp.stat().st_size} bytes")
        max_season = 0
        for chunk in pd.read_csv(tmp, usecols=["season"], chunksize=500000,
                                 low_memory=False):
            max_season = max(max_season, int(chunk["season"].max()))
        if max_season < season:
            raise RuntimeError("MoneyPuck CSV does not reach the current "
                               f"season ({season})")
        ok = True
    finally:
        if ok:
            tmp.replace(MP_CSV)
        else:
            tmp.unlink(missing_ok=True)
    print(f"ingest: MoneyPuck CSV refreshed ({MP_CSV.stat().st_size:,} bytes)")


def refresh_official_scores(season: int) -> int:
    """Upsert current-season official finals into official_scores.parquet."""
    season_id = season * 10000 + season + 1
    games: dict[int, dict] = {}
    for team in TEAMS:
        url = (f"https://api-web.nhle.com/v1/club-schedule-season/"
               f"{team}/{season_id}")
        data = fetch(url)
        for g in data.get("games", []):
            if g.get("gameType") != 2:
                continue
            ht, at = g["homeTeam"], g["awayTeam"]
            if "score" not in ht or "score" not in at:
                continue
            games[int(g["id"])] = {
                "game_id": int(g["id"]),
                "api_home": ABBR_FIX.get(ht["abbrev"], ht["abbrev"]),
                "api_away": ABBR_FIX.get(at["abbrev"], at["abbrev"]),
                "home_goals": int(ht["score"]),
                "away_goals": int(at["score"]),
            }
        time.sleep(0.05)
    new = pd.DataFrame(games.values())
    old = pd.read_parquet(SCORES) if SCORES.exists() else pd.DataFrame(
        columns=new.columns)
    old = old[~old["game_id"].isin(new["game_id"])]
    out = pd.concat([old, new], ignore_index=True).sort_values(
        "game_id").reset_index(drop=True)
    out.to_parquet(SCORES, index=False)
    print(f"ingest: official scores — {len(new)} current-season finals "
          f"upserted; {len(out)} total")
    return len(new)


def verify(tg: pd.DataFrame, season: int) -> dict:
    cur = tg[tg["season"] == season]
    games = cur["game_id"].nunique()
    sc = pd.read_parquet(SCORES)
    covered = cur["game_id"].isin(set(sc["game_id"])).all()
    h = cur[cur["home"] == 1][["game_id", "gf"]].merge(
        cur[cur["home"] == 0][["game_id", "gf"]], on="game_id",
        suffixes=("_h", "_a"))
    ties = int((h["gf_h"] == h["gf_a"]).sum())
    info = {
        "season": season,
        "games": int(games),
        "first_date": str(cur["date"].min().date()),
        "last_date": str(cur["date"].max().date()),
        "official_score_coverage": bool(covered),
        "tied_finals": ties,
    }
    assert covered, "current-season games missing official scores"
    assert ties == 0, f"{ties} tied finals remain in current season"
    return info


def main() -> None:
    season = current_season()
    if "--skip-download" not in sys.argv:
        refresh_moneypuck(season)
    refresh_official_scores(season)
    tg = data_prep.build()
    info = verify(tg, season)
    print("ingest OK:", json.dumps(info))


if __name__ == "__main__":
    main()
