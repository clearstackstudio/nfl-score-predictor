"""Measure the weather effect on NFL total residuals.

Walk-forward 2021-2024 (same leakage-safe setup as the validated backtest),
saving per-game our_total, then bucketing outdoor games by wind speed to
measure E[actual_total - our_total | wind]. If high wind systematically
suppresses scoring relative to our model, that's a real adjustment.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from epa_ratings import (HOME_EDGE_PTS, PLAYS_PER_GAME, adjusted_ratings,
                         load_team_games)

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
    our_total = (exp_home_off + exp_away_off) * exp_plays + 44.5
    rows.append({
        "wind": row["wind"], "temp": row["temp"], "roof": row["roof"],
        "our_total": our_total,
        "actual_total": float(row["home_score"]) + float(row["away_score"]),
    })
    off2, def2, _ = adjusted_ratings(tg, cutoff + 2, season, prior)
    season_final = {t: (off2[t], def2[t]) for t in off2}

d = pd.DataFrame(rows)
d["resid"] = d["actual_total"] - d["our_total"]


def wind_adj(wind, roof):
    """Hinge adjustment: -1.0 pts per mph above 10, outdoor only, cap -8."""
    if roof != "outdoors" or pd.isna(wind):
        return 0.0
    return -min(8.0, max(0.0, float(wind) - 10.0) * 1.0)


d["adj"] = [wind_adj(w, r) for w, r in zip(d["wind"], d["roof"])]
d["resid_adj"] = d["actual_total"] - (d["our_total"] + d["adj"])
n = len(d)
print(f"total RMSE before: {np.sqrt((d['resid']**2).mean()):.2f}")
print(f"total RMSE after:  {np.sqrt((d['resid_adj']**2).mean()):.2f}")
print(f"games adjusted: {(d['adj'] != 0).sum()} of {n}")
print()
out = d[d["roof"] == "outdoors"].copy()
out["wind_bucket"] = pd.cut(out["wind"], [0, 5, 10, 15, 20, 100],
                            labels=["0-5", "5-10", "10-15", "15-20", "20+"])
print(f"outdoor games with wind data: {out['wind'].notna().sum()} of {len(out)}")
print()
print(out.groupby("wind_bucket", observed=True)["resid"]
      .agg(["count", "mean"]).round(2).to_string())
print()
calm = out[out["wind"] <= 10].copy()
calm["temp_bucket"] = pd.cut(calm["temp"], [0, 32, 45, 60, 120],
                             labels=["<=32", "33-45", "46-60", "60+"])
print(calm.groupby("temp_bucket", observed=True)["resid"]
      .agg(["count", "mean"]).round(2).to_string())
