#!/usr/bin/env python3
"""Fetch + cache all MLB Stats API data for the pitcher-layer test.

Everything lands under research/mlb_pitcher/cache/ and is resumable:
a response already on disk is never re-requested. Serial requests with
small sleeps (the API is free; be polite).

Three pulls:
  1. schedule/{date}.json  -- one call per date that has a verdict-sample
     game (scores_2022_2026.csv, seasons 2023-2026), hydrate=probablePitcher.
  2. people/{pitcher_id}.json -- season pitching stats (components, for
     prior-season FIP) for every unique probable pitcher on those dates,
     seasons 2022-2025 in one call each.
  3. league/{season}_{team_id}.json -- team pitching totals for the 30
     clubs, prior seasons 2022-2025 (league FIP constant + league-average
     FIP from exact aggregation).

Usage:
    .venv-cfb/bin/python research/mlb_pitcher/fetch_data.py [--only schedule|people|league]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CACHE = HERE / "cache"
API = "https://statsapi.mlb.com/api/v1"
SCORES_CSV = REPO / "data" / "mlb" / "scores_2022_2026.csv"

VERDICT_SEASONS = (2023, 2024, 2025, 2026)
PRIOR_SEASONS = (2022, 2023, 2024, 2025)

# MLB Stats API team id -> repo abbreviation (data.py conventions: the
# Athletics are "OAK" in every season).
TEAM_ABBR = {
    108: "LAA", 109: "ARI", 110: "BAL", 111: "BOS", 112: "CHC",
    113: "CIN", 114: "CLE", 115: "COL", 116: "DET", 117: "HOU",
    118: "KC", 119: "LAD", 120: "WSH", 121: "NYM", 133: "OAK",
    134: "PIT", 135: "SD", 136: "SEA", 137: "SF", 138: "STL",
    139: "TB", 140: "TEX", 141: "TOR", 142: "MIN", 143: "PHI",
    144: "ATL", 145: "CWS", 146: "MIA", 147: "NYY", 158: "MIL",
}

SLEEP = 0.22

_session = requests.Session()
_session.headers["User-Agent"] = "honest-line-research/1.0 (preregistered backtest)"
_calls_made = 0


def get_cached(url: str, path: Path) -> dict:
    """Return parsed JSON for url, from disk if present, else fetch+save."""
    global _calls_made
    if path.exists():
        return json.loads(path.read_text())
    last_err = None
    for attempt in range(3):
        try:
            r = _session.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            path.write_text(json.dumps(data))
            _calls_made += 1
            time.sleep(SLEEP)
            return data
        except Exception as e:  # retry with backoff; surface after 3 tries
            last_err = e
            time.sleep(1.0 + attempt)
    raise RuntimeError(f"failed after 3 tries: {url}: {last_err}")


def schedule_dates() -> list[str]:
    g = pd.read_csv(SCORES_CSV, parse_dates=["date"])
    dates = sorted(g[g["season"].isin(VERDICT_SEASONS)]["date"]
                   .dt.strftime("%Y-%m-%d").unique())
    return dates


def fetch_schedule(dates: list[str]) -> None:
    out = CACHE / "schedule"
    out.mkdir(parents=True, exist_ok=True)
    for i, d in enumerate(dates):
        get_cached(f"{API}/schedule?sportId=1&date={d}&hydrate=probablePitcher",
                   out / f"{d}.json")
        if (i + 1) % 100 == 0:
            print(f"  schedule {i + 1}/{len(dates)} (api calls so far: {_calls_made})",
                  flush=True)
    print(f"schedule done: {len(dates)} dates, {_calls_made} api calls this run")


def probable_pitcher_ids(dates: list[str]) -> list[int]:
    ids: set[int] = set()
    for d in dates:
        data = json.loads((CACHE / "schedule" / f"{d}.json").read_text())
        for day in data.get("dates", []):
            for g in day.get("games", []):
                for side in ("home", "away"):
                    pp = g["teams"][side].get("probablePitcher")
                    if pp:
                        ids.add(int(pp["id"]))
    return sorted(ids)


def fetch_people(ids: list[int]) -> None:
    out = CACHE / "people"
    out.mkdir(parents=True, exist_ok=True)
    seasons = ",".join(str(s) for s in PRIOR_SEASONS)
    for i, pid in enumerate(ids):
        get_cached(f"{API}/people/{pid}/stats?stats=season&group=pitching"
                   f"&seasons={seasons}", out / f"{pid}.json")
        if (i + 1) % 100 == 0:
            print(f"  people {i + 1}/{len(ids)} (api calls so far: {_calls_made})",
                  flush=True)
    print(f"people done: {len(ids)} pitchers, {_calls_made} api calls this run")


def fetch_league() -> None:
    out = CACHE / "league"
    out.mkdir(parents=True, exist_ok=True)
    for season in PRIOR_SEASONS:
        for tid in sorted(TEAM_ABBR):
            get_cached(f"{API}/teams/{tid}/stats?stats=season&group=pitching"
                       f"&season={season}", out / f"{season}_{tid}.json")
    print(f"league done: {len(PRIOR_SEASONS) * len(TEAM_ABBR)} team-seasons, "
          f"{_calls_made} api calls this run")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["schedule", "people", "league"], default=None)
    args = ap.parse_args()

    dates = schedule_dates()
    print(f"verdict-sample dates to cover: {len(dates)}")
    if args.only in (None, "schedule"):
        fetch_schedule(dates)
    if args.only in (None, "people"):
        ids = probable_pitcher_ids(dates)
        print(f"unique probable pitchers on those dates: {len(ids)}")
        fetch_people(ids)
    if args.only in (None, "league"):
        fetch_league()
    print(f"TOTAL api calls this run: {_calls_made}")


if __name__ == "__main__":
    sys.exit(main())
