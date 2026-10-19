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


ABBR_TO_FULL = {
    "ARI": "Arizona Diamondbacks", "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles", "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs", "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians", "COL": "Colorado Rockies",
    "CWS": "Chicago White Sox", "DET": "Detroit Tigers",
    "HOU": "Houston Astros", "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels", "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins", "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins", "NYM": "New York Mets",
    "NYY": "New York Yankees", "OAK": "Athletics",
    "PHI": "Philadelphia Phillies", "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres", "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants", "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays", "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays", "WSH": "Washington Nationals",
}


def export_power_rankings(state: dict, note: str | None = None) -> None:
    """Write site/data/mlb_power_rankings.json from a fitted ratings state.

    Read-only use of the ratings: rating = off - deff = expected run
    differential per game vs an average team in a neutral park (off/deff
    are park-adjusted expected runs scored/allowed per game vs
    league-average opposition) -- the same net number main() sanity-
    prints. Movement arrows come from the previous export when its
    season differs; same-season re-retrains keep the existing baseline
    (the seasonal analog of the NFL export's week rule).
    """
    import datetime
    from zoneinfo import ZoneInfo
    dest = REPO / "site" / "data" / "mlb_power_rankings.json"
    season = int(state["seasons"][-1]) if state.get("seasons") else None
    prev_ranks: dict[str, int] = {}
    try:
        old = json.loads(dest.read_text())
        if old.get("season") is not None and int(old["season"]) != season:
            for t in old.get("teams", []):
                if t.get("abbr") and t.get("rank"):
                    prev_ranks[t["abbr"]] = int(t["rank"])
        elif old.get("season") is not None:
            for t in old.get("teams", []):
                if t.get("abbr") and t.get("prev_rank"):
                    prev_ranks[t["abbr"]] = int(t["prev_rank"])
    except Exception:
        pass
    rows = sorted(
        ((round(state["off"][t] - state["deff"][t], 2), t)
         for t in state["off"] if t in state["deff"]),
        key=lambda r: (-r[0], r[1]))
    teams = [
        {"rank": i + 1, "team": ABBR_TO_FULL.get(t, t), "abbr": t,
         "rating": pts, "prev_rank": prev_ranks.get(t)}
        for i, (pts, t) in enumerate(rows)
    ]
    out = {
        "sport": "mlb",
        "season": season,
        "asof": state.get("trained_through"),
        "updated": datetime.datetime.now(
            ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M %Z"),
        "note": note or ("Model-internal predictive ratings: expected run "
                 "differential per game vs an average team in a neutral "
                 "park, from park-adjusted runs scored/allowed ratings. "
                 "Not a resume ranking; moves only on game results."),
        "teams": teams,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"MLB power rankings: {len(teams)} teams -> {dest}")


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
    export_power_rankings(state)

    # Sanity: top-5 by net rating (off - deff).
    net = {t: r.off.get(t, 0) - r.deff.get(t, 0) for t in r.off}
    top = sorted(net.items(), key=lambda kv: kv[1], reverse=True)[:5]
    print("\ntop-5 by net rating (off - deff):")
    for t, v in top:
        print(f"  {t}: {v:+.2f} runs/game")


if __name__ == "__main__":
    main()
