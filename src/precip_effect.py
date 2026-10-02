"""Measure precipitation + indoor/outdoor effects on NFL total residuals.

Walk-forward 2021-2024 (same leakage-safe setup as src/weather_effect.py).
Wind adjustment (src/weather.py hinge) applied first, like production.

Rain: Open-Meteo archive hourly precipitation summed over the game window
(kickoff hour through +3h, ET) for outdoor games at the home team's primary
stadium. Buckets E[actual_total - adj_total | precip].
Indoor/outdoor: dome + retractable (not is_outdoor) vs outdoor, overall and
per season, to check stability.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from epa_ratings import (PLAYS_PER_GAME, adjusted_ratings, load_team_games)
from stadiums import is_outdoor
from weather import wind_total_adjustment

REPO = Path(__file__).resolve().parent.parent

sched = pd.read_parquet(REPO / "data" / "schedules_games.parquet")
tg = load_team_games([2021, 2022, 2023, 2024, 2025, 2026])

games = sched[(sched.season >= 2021) & (sched.season <= 2024)
              & (sched.game_type == "REG") & sched.home_score.notna()].copy()
games = games.sort_values(["season", "week", "gameday"]).reset_index(drop=True)

# primary stadium per home team; drop neutral-site/international games
prim = games.groupby("home_team")["stadium_id"].agg(
    lambda x: x.mode().iloc[0])
games = games[games.apply(
    lambda r: r["stadium_id"] == prim[r["home_team"]], axis=1)].copy()

gid_first = {}
for i, r in tg.iterrows():
    gid_first.setdefault(r["game_id"], i)

# precipitation at game window
try:
    pr = pd.read_parquet(REPO / "data" / "nfl_stadium_precip.parquet")
    pr["time"] = pd.to_datetime(pr["time"])
    have_precip = True
except FileNotFoundError:
    have_precip = False
    pr = None


def game_precip(home, gameday, gametime):
    """Sum of hourly precip (in) over kickoff hour .. +3h, ET."""
    if not have_precip:
        return float("nan")
    hhmm = (gametime or "13:00")[:5]
    kick = pd.Timestamp(f"{gameday}T{hhmm}")
    sub = pr[(pr["team"] == home)
             & (pr["time"] >= kick) & (pr["time"] <= kick + pd.Timedelta(hours=3))]
    if len(sub) == 0:
        return float("nan")
    return float(sub["precip_in"].sum())


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
    wind_adj = wind_total_adjustment(
        None if pd.isna(row["wind"]) else float(row["wind"]), home)
    rows.append({
        "season": season,
        "indoor": not is_outdoor(home),
        "roof": row["roof"],
        "eff_indoor": row["roof"] in ("dome", "closed"),
        "precip_in": (game_precip(home, row["gameday"], row["gametime"])
                      if is_outdoor(home) else 0.0),
        "our_total": our_total + wind_adj,
        "wind_adj": wind_adj,
        "actual_total": float(row["home_score"]) + float(row["away_score"]),
    })
    off2, def2, _ = adjusted_ratings(tg, cutoff + 2, season, prior)
    season_final = {t: (off2[t], def2[t]) for t in off2}

d = pd.DataFrame(rows)
d["resid"] = d["actual_total"] - d["our_total"]
print(f"games: {len(d)}")

# ---- Task 3: indoor vs outdoor ----
print()
print("== indoor (dome+retractable) vs outdoor ==")
t = d.groupby("indoor")["resid"].agg(["count", "mean", "std"]).round(2)
print(t.to_string())
print()
print("by season:")
t = d.groupby(["season", "indoor"])["resid"].agg(["count", "mean"]).round(2)
print(t.to_string())
print()
print("== effective indoor (actual roof dome/closed) vs outdoor ==")
t = d.groupby("eff_indoor")["resid"].agg(["count", "mean", "std"]).round(2)
print(t.to_string())
print()
print("by season (effective):")
t = d.groupby(["season", "eff_indoor"])["resid"].agg(["count", "mean"]).round(2)
print(t.to_string())

# ---- Task 2: rain ----
if have_precip:
    out = d[~d["indoor"]].copy()
    out = out[out["precip_in"].notna()].copy()
    out["bucket"] = pd.cut(
        out["precip_in"], [-0.01, 0.001, 0.1, 0.25, 0.5, 99],
        labels=["dry", "trace-0.1", "0.1-0.25", "0.25-0.5", "0.5+"])
    print()
    print("== rain buckets (outdoor, game-window precip inches) ==")
    print(f"outdoor games with precip: {len(out)}")
    print(out.groupby("bucket", observed=True)["resid"]
          .agg(["count", "mean", "std"]).round(2).to_string())
    print()
    print("heavy rain (>=0.25in) by season:")
    hr = out[out["precip_in"] >= 0.25]
    print(hr.groupby("season")["resid"].agg(["count", "mean"]).round(2)
          .to_string() if len(hr) else "none")
    # candidate hinge fits
    def rain_adj(p, k, hinge, cap):
        return -min(cap, max(0.0, p - hinge) * k)
    before = float(np.sqrt((out["resid"] ** 2).mean()))
    print(f"\nbaseline outdoor RMSE: {before:.2f}")
    for k, hinge, cap in [(8.0, 0.25, 6.0), (12.0, 0.25, 6.0), (8.0, 0.1, 6.0)]:
        a = np.array([rain_adj(p, k, hinge, cap) for p in out["precip_in"]])
        after = float(np.sqrt(((out["resid"] + a) ** 2).mean()))
        n = int((a != 0).sum())
        print(f"k={k} hinge={hinge} cap={cap}: RMSE {before:.2f} -> "
              f"{after:.2f} ({n} games adjusted)")
else:
    print("\nprecip data not available; run fetch first")
