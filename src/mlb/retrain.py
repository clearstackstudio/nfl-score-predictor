#!/usr/bin/env python3
"""Retrain the MLB team ratings through end of the 2026 season.

Combines the 2012-2021 game records (src/mlb/data.py, from the Kaggle odds
file) with the 2022-2026 backfill (data/mlb/scores_2022_2026.csv, from the
free MLB Stats API -- see backfill_scores.py), then runs the same
leakage-safe walk-forward fitter with the TUNED hyperparameters
(alpha=1/40, carryover=0.25; tuned once on 2012-2015, never re-tuned).

The home edge is REFIT on the full 2012-2026 span -- it is a descriptive
statistic, not a tuned parameter, and more data makes it better. Sigma
(4.135, fitted on the 2012-2015 tuning residuals) is kept as-is; see
winprob.py.

Output: src/mlb/ratings_2026.json -- the fitted ratings state the 2027
live-picks script will load via load_ratings() below. This does NOT touch
backtest_results.json (the published 2012-2021 walk-forward verdict stands).

Usage:
    python3 src/mlb/retrain.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import load_games
from ratings import MLBRatings, fit_home_edge, walk_forward
from winprob import SIGMA

REPO = Path(__file__).resolve().parent.parent.parent
BACKFILL_CSV = REPO / "data" / "mlb" / "scores_2022_2026.csv"
ARTIFACT = Path(__file__).resolve().parent / "ratings_2026.json"

# Tuned once on the 2012-2015 walk-forward split (see backtest_results.json).
ALPHA = 1 / 40
CARRYOVER = 0.25


def load_backfill() -> pd.DataFrame:
    df = pd.read_csv(BACKFILL_CSV, parse_dates=["date"])
    df["neutral"] = df["neutral"].astype(str) == "True"
    return df[["date", "season", "home", "away", "home_runs",
               "away_runs", "park", "neutral"]]


def load_all_games() -> pd.DataFrame:
    old = load_games()[["date", "season", "home", "away", "home_runs",
                        "away_runs", "park", "neutral"]]
    new = load_backfill()
    games = pd.concat([old, new], ignore_index=True)
    games = games.sort_values("date", kind="stable").reset_index(drop=True)
    return games


def save_ratings(r: MLBRatings, path: Path = ARTIFACT) -> dict:
    state = {
        "trained_through": None,  # filled by main()
        "seasons": None,          # filled by main()
        "games": None,            # filled by main()
        "alpha": r.alpha,
        "carryover": r.carryover,
        "home_edge": r.home_edge,
        "sigma": SIGMA,
        "off": r.off,
        "deff": r.deff,
        "park_runs": r.park_runs,
        "park_games": r.park_games,
        "lg_runs": r.lg_runs,
        "lg_games": r.lg_games,
    }
    path.write_text(json.dumps(state, indent=1))
    return state


def load_ratings(path: Path = ARTIFACT) -> MLBRatings:
    """Rehydrate a fitted MLBRatings for the 2027 live-picks script."""
    state = json.loads(path.read_text())
    r = MLBRatings(alpha=state["alpha"], carryover=state["carryover"],
                   home_edge=state["home_edge"])
    r.off = state["off"]
    r.deff = state["deff"]
    r.park_runs = state["park_runs"]
    r.park_games = state["park_games"]
    r.lg_runs = state["lg_runs"]
    r.lg_games = state["lg_games"]
    return r


def main() -> None:
    games = load_all_games()
    print(f"Loaded {len(games):,} games, {games['date'].min().date()} .. "
          f"{games['date'].max().date()}")
    print(games.groupby("season").size().to_string())

    home_edge = fit_home_edge(games)
    print(f"\nrefit home edge on 2012-2026: {home_edge:.3f} runs "
          f"(2012-2021 value was 0.130)")

    r = walk_forward(games, ALPHA, CARRYOVER, home_edge)
    print(f"\nwalk-forward complete: {len(r.off)} teams rated, "
          f"{r.lg_games:,} team-games in league average")

    state = save_ratings(r)
    state["trained_through"] = games["date"].max().strftime("%Y-%m-%d")
    state["seasons"] = sorted(int(s) for s in games["season"].unique())
    state["games"] = len(games)
    ARTIFACT.write_text(json.dumps(state, indent=1))
    print(f"wrote {ARTIFACT}")

    # Sanity: top-5 by net rating (off - deff).
    net = {t: r.off.get(t, 0) - r.deff.get(t, 0) for t in r.off}
    top = sorted(net.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("\ntop-5 by net rating (off - deff):")
    for t, v in top:
        print(f"  {t}: {v:+.2f} runs/game")


if __name__ == "__main__":
    main()
