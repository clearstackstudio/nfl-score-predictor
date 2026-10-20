"""Official final scores from the free NHL API (api-web.nhle.com).

MoneyPuck's goalsFor excludes the shootout-deciding goal, so ~7% of
games show an impossible tied final score and no winner. The NHL API
club-schedule endpoint is the authoritative fix: one call per team per
season returns every game with official scores (shootout goal included,
which is also how totals settle). Output: data/nhl/official_scores.parquet
keyed by NHL game id.
"""
import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"
SEASONS = [20182019, 20192020, 20202021, 20212022, 20222023,
           20232024, 20242025, 20252026]
# NHL API abbrev variants -> MoneyPuck/modern codes
ABBR_FIX = {"LA": "LAK", "NJ": "NJD", "SJ": "SJS", "TB": "TBL"}


def fetch(url: str) -> dict:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (HonestLine data pull)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> None:
    tg = pd.read_parquet(DATA / "team_games.parquet")
    teams = sorted(tg[tg["season"] >= 2018]["team"].unique())
    games: dict[int, dict] = {}
    for season_id in SEASONS:
        for team in teams:
            url = (f"https://api-web.nhle.com/v1/club-schedule-season/"
                   f"{team}/{season_id}")
            try:
                data = fetch(url)
            except Exception as e:  # team may not exist that season (SEA/UTA)
                print(f"skip {team} {season_id}: {e}")
                continue
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
    sc = pd.DataFrame(games.values())
    sc.to_parquet(DATA / "official_scores.parquet", index=False)
    print(f"official scores: {len(sc)} games")

    # coverage + home-team agreement against MoneyPuck
    mp = tg[tg["season"] >= 2018]
    mp_games = mp[mp["home"] == 1][["game_id", "team"]].rename(
        columns={"team": "mp_home"})
    m = mp_games.merge(sc, on="game_id", how="left")
    have = m["home_goals"].notna()
    print(f"MoneyPuck games 2018+: {len(m)}  with official score: {have.sum()}"
          f" ({have.mean():.3%})")
    agree = (m.loc[have, "mp_home"] == m.loc[have, "api_home"]).mean()
    print(f"home-team agreement: {agree:.3%}")


if __name__ == "__main__":
    main()
