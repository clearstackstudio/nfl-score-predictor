"""Measure rest/travel effects on NFL margin residuals.

Walk-forward 2021-2024 (same leakage-safe setup as the validated backtest),
saving per-game our_margin, then:
  1. bucket by rest differential (home_rest - away_rest)
  2. Thursday games: does the short week hurt?
  3. bucket by away-team travel distance (haversine between stadiums)

If a bucket shows a systematic residual, that's a real adjustment.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from epa_ratings import (HOME_EDGE_PTS, PLAYS_PER_GAME, adjusted_ratings,
                         load_team_games)
from stadiums import STADIUMS


def haversine_miles(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, [a[0], a[1], b[0], b[1]])
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * 3959 * math.asin(math.sqrt(h))


sched = pd.read_parquet("data/schedules_games.parquet")
tg = load_team_games([2021, 2022, 2023, 2024, 2025, 2026])

games = sched[(sched.season >= 2021) & (sched.season <= 2024)
              & (sched.game_type == "REG") & sched.home_score.notna()].copy()
games = games.sort_values(["season", "week", "gameday"]).reset_index(drop=True)

gid_first = {}
for i, r in tg.iterrows():
    gid_first.setdefault(r["game_id"], i)

prior, last_season, season_final = {}, None, {}
rows = []
for _, row in games.iterrows():
    season = int(row["season"])
    if last_season is not None and season != last_season:
        prior = {t: (0.5 * v[0], 0.5 * v[1]) for t, v in season_final.items()}
    last_season = season
    cutoff = gid_first.get(row["game_id"])
    if cutoff is None:
        continue
    off, deff, pace = adjusted_ratings(tg, cutoff, season, prior)
    home, away = row["home_team"], row["away_team"]
    if home not in off or away not in off:
        continue
    exp_home_off = off[home] + deff[away]
    exp_away_off = off[away] + deff[home]
    exp_plays = (pace.get(home, PLAYS_PER_GAME)
                 + pace.get(away, PLAYS_PER_GAME)) / 2
    our_margin = (exp_home_off - exp_away_off) * exp_plays + HOME_EDGE_PTS
    # travel: away stadium -> game site (home stadium; neutral sites skipped)
    travel = None
    if row.get("location") == "Home" and away in STADIUMS and home in STADIUMS:
        travel = haversine_miles(STADIUMS[away][:2], STADIUMS[home][:2])
    rows.append({
        "rest_diff": int(row["home_rest"]) - int(row["away_rest"]),
        "home_rest": int(row["home_rest"]),
        "away_rest": int(row["away_rest"]),
        "weekday": row["weekday"],
        "travel_mi": travel,
        "our_margin": our_margin,
        "actual_margin": float(row["home_score"]) - float(row["away_score"]),
    })
    off2, def2, _ = adjusted_ratings(tg, cutoff + 2, season, prior)
    season_final = {t: (off2[t], def2[t]) for t in off2}

d = pd.DataFrame(rows)
d["resid"] = d["actual_margin"] - d["our_margin"]  # >0: home outperformed us
print(f"games: {len(d)}")
print()
print("== rest differential (home - away) ==")
print(d.groupby("rest_diff")["resid"].agg(["count", "mean"]).round(2).to_string())
print()
print("== Thursday games ==")
thu = d[d["weekday"] == "Thursday"]
print(f"n={len(thu)}, mean resid (home margin err): {thu['resid'].mean():.2f}")
print()
print("== away travel distance ==")
d["travel_bucket"] = pd.cut(d["travel_mi"], [0, 500, 1000, 1500, 3000],
                            labels=["<500", "500-1000", "1000-1500", "1500+"])
print(d.groupby("travel_bucket", observed=True)["resid"]
      .agg(["count", "mean"]).round(2).to_string())
