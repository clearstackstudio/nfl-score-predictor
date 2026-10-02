"""Calibrate the CFB wind effect on total residuals.

Walk-forward 2022-2024 (leakage-safe, same as the validated backtest),
saving per-game our_total, joined to historical Open-Meteo wind at kickoff.
Measures E[actual_total - our_total | wind] for outdoor games.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfb_ratings import (CARRYOVER, adjusted_ratings, load_team_games,
                         predict)

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data" / "cfb"
STADIUMS = json.loads((REPO / "cfb" / "cfb_stadiums.json").read_text())


def main():
    wind = pd.read_parquet(DATA / "cfb_stadium_wind.parquet")
    wind = wind.set_index(["school", "time"])["wind_mph"]

    team_games = load_team_games()
    games = pd.read_parquet(DATA / "cfb_games.parquet")
    games = games[(games["season"] >= 2022) & (games["season"] <= 2024)].copy()
    games = games.dropna(subset=["line_spread", "line_total"]).copy()
    games = games.sort_values(["season", "week", "date"]).reset_index(drop=True)
    # FBS-vs-FBS only, non-neutral (neutral-site stadiums aren't in our map)
    games = games[~games["neutral"]].copy()

    gid_first: dict[int, int] = {}
    for i, r in team_games.iterrows():
        gid_first.setdefault(int(r["game_id"]), i)

    prior: dict = {}
    last_season = None
    season_final: dict = {}
    epa_const_hist: list[float] = []
    rows = []
    for _, row in games.iterrows():
        season = int(row["season"])
        if last_season is not None and season != last_season:
            prior = {t: (CARRYOVER * v[0], CARRYOVER * v[1])
                     for t, v in season_final.items()}
        last_season = season
        cutoff = gid_first.get(int(row["game_id"]))
        if cutoff is None:
            continue
        home = row["home_team"]
        stad = STADIUMS.get(home)
        if not stad or stad["dome"]:
            continue
        off, deff, pace = adjusted_ratings(team_games, cutoff, season, prior)
        epa_const = (sum(epa_const_hist) / len(epa_const_hist)
                     if epa_const_hist else 58.0)
        pr = predict(off, deff, pace, home, row["away_team"],
                     False, epa_const)
        if pr is None:
            continue
        our_margin, our_total = pr
        actual_total = float(row["home_score"]) + float(row["away_score"])
        # wind at kickoff: nearest archived hour to game UTC time
        kickoff = pd.Timestamp(row["date"], tz="UTC").floor("h")
        try:
            w = float(wind.loc[(home, kickoff)])
        except KeyError:
            w = float("nan")
        rows.append({"wind": w, "our_total": our_total,
                     "actual_total": actual_total})
        epa_const_hist.append(actual_total)
        off2, def2, _ = adjusted_ratings(team_games, cutoff + 2, season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    d = pd.DataFrame(rows)
    d["resid"] = d["actual_total"] - d["our_total"]
    d = d[d["wind"].notna()].copy()
    d["bucket"] = pd.cut(d["wind"], [0, 5, 10, 15, 20, 100],
                         labels=["0-5", "5-10", "10-15", "15-20", "20+"])
    print(f"games with wind: {len(d)}")
    print()
    print(d.groupby("bucket", observed=True)["resid"]
          .agg(["count", "mean"]).round(2).to_string())

    # hinge fit: adj = -k * max(0, wind - 10), report RMSE before/after
    def adj(w, k, cap):
        return -min(cap, max(0.0, w - 10.0) * k)
    for k, cap in [(1.0, 8.0), (1.0, 10.0), (1.2, 10.0)]:
        d["a"] = [adj(w, k, cap) for w in d["wind"]]
        before = float(np.sqrt((d["resid"] ** 2).mean()))
        after = float(np.sqrt(((d["resid"] + d["a"]) ** 2).mean()))
        n = int((d["a"] != 0).sum())
        print(f"k={k} cap={cap}: RMSE {before:.2f} -> {after:.2f} ({n} games)")


if __name__ == "__main__":
    main()
