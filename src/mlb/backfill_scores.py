#!/usr/bin/env python3
"""One-time backfill: 2022-2026 MLB regular-season final scores.

Source: the FREE MLB Stats API (https://statsapi.mlb.com, no key needed).
Output: data/mlb/scores_2022_2026.csv -- ONE ROW PER GAME:

    date, season, home, away, home_runs, away_runs, park, neutral

Conventions (chosen to match the 2012-2021 training file):
  * Team codes match the original file: the Athletics are "OAK" in every
    season (the API calls them "ATH" from 2025 on) -- one franchise, one code.
  * ``park`` is the CANONICAL park key from src/mlb/data.py's PARK_HOME
    wherever the physical park is unchanged (sponsor renames are mapped to
    the old key so park-factor history is preserved). Genuinely new parks
    (Sutter Health Park, Steinbrenner Field, Las Vegas Ballpark) keep their
    API names -- the 100-game shrinkage prior in ratings.py handles them.
  * ``neutral`` follows data.py's philosophy: international series, classics
    and special-event games where neither club is at home.
  * "Completed Early" games (official rain-shortened finals) are included;
    Postponed/Cancelled entries are not (their makeup games appear separately).

Home/away comes straight from the API -- no park-tenant inference needed
(unlike the 2012-2021 file, which lacked a home/away column).

Usage:
    python3 src/mlb/backfill_scores.py            # writes data/mlb/scores_2022_2026.csv
    python3 src/mlb/backfill_scores.py --check    # re-read the CSV and validate it
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
OUT = REPO / "data" / "mlb" / "scores_2022_2026.csv"

SEASONS = (2022, 2023, 2024, 2025, 2026)
COMPLETED = {"Final", "Completed Early"}

# API venue name -> canonical park key (see module docstring).
PARK_MAP = {
    "American Family Field": "Miller Park",
    "Angel Stadium": "Angel Stadium",
    "Busch Stadium": "Busch Stadium",
    "Chase Field": "Chase Field",
    "Citi Field": "Citi Field",
    "Citizens Bank Park": "Citizens Bank Park",
    "Comerica Park": "Comerica Park",
    "Coors Field": "Coors Field",
    "Daikin Park": "Minute Maid Park",
    "Dodger Stadium": "Dodger Stadium",
    "UNIQLO Field at Dodger Stadium": "Dodger Stadium",
    "Fenway Park": "Fenway Park",
    "Globe Life Field": "Globe Life Field",
    "Great American Ball Park": "Great American Ballpark",
    "Guaranteed Rate Field": "Guaranteed Rate Field",
    "Rate Field": "Guaranteed Rate Field",
    "Kauffman Stadium": "Kauffman Stadium",
    "Minute Maid Park": "Minute Maid Park",
    "Nationals Park": "Nationals Park",
    "Oakland Coliseum": "Oakland Coliseum",
    "Oracle Park": "AT&T Park",
    "Oriole Park at Camden Yards": "Camden Yards",
    "Petco Park": "PETCO Park",
    "PNC Park": "PNC Park",
    "Progressive Field": "Progressive Field",
    "Rogers Centre": "Rogers Centre",
    "T-Mobile Park": "T-Mobile Park",
    "Target Field": "Target Field",
    "Tropicana Field": "Tropicana Field",
    "Truist Park": "Suntrust Park",
    "Wrigley Field": "Wrigley Field",
    "Yankee Stadium": "Yankee Stadium",
    "loanDepot park": "Marlins Park",
    # Genuinely new parks (own park-factor history starts here).
    "Sutter Health Park": "Sutter Health Park",          # Athletics, Sacramento 2025+
    "George M. Steinbrenner Field": "George M. Steinbrenner Field",  # Rays, Tampa 2025
    "Las Vegas Ballpark": "Las Vegas Ballpark",          # 6 Athletics "home" games, Jun 2026
}

# Neutral-site venues, 2022-2026 (extends data.py's NEUTRAL_PARKS).
NEUTRAL_VENUES = {
    "Tokyo Dome",                 # 2025 Tokyo Series
    "London Stadium",             # 2023/2024 London Series
    "Gocheok Sky Dome",           # 2024 Seoul Series
    "Estadio Alfredo Harp Helu",  # 2023/2026 Mexico City Series
    "Field of Dreams",            # Iowa games
    "Rickwood Field",             # 2024 Rickwood Classic
    "Bristol Motor Speedway",     # 2025 Speedway Classic
    "Muncy Bank Ballpark",        # LL Classic 2022/2023 (was BB&T Ballpark at Bowman Field)
    "Journey Bank Ballpark",      # LL Classic 2025/2026 (same venue, renamed)
}

TEAM_FIX = {"ATH": "OAK", "AZ": "ARI"}  # one franchise, one code


def get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def team_codes(season: int) -> dict[int, str]:
    d = get(f"https://statsapi.mlb.com/api/v1/teams?sportId=1&season={season}")
    out = {}
    for t in d["teams"]:
        code = TEAM_FIX.get(t["abbreviation"], t["abbreviation"])
        out[t["id"]] = code
    return out


def fetch_season(season: int) -> list[dict]:
    codes = team_codes(season)
    d = get(
        f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={season}"
        f"&gameType=R&startDate={season}-01-01&endDate={season}-12-31"
    )
    by_pk: dict[int, dict] = {}
    for day in d["dates"]:
        for g in day["games"]:
            st = g["status"]["detailedState"]
            if st not in COMPLETED:
                continue
            pk = g["gamePk"]
            # Suspended-then-completed games share a gamePk; keep the entry
            # with scores present, preferring "Final".
            cur = by_pk.get(pk)
            if cur is not None and not (
                st == "Final" and cur["status"] != "Final"
            ):
                continue
            by_pk[pk] = {"game": g, "status": st}

    games = []
    seen_dates_teams = Counter()
    for pk, entry in by_pk.items():
        g = entry["game"]
        hs = g["teams"]["home"].get("score")
        aws = g["teams"]["away"].get("score")
        assert hs is not None and aws is not None, f"missing score in {pk}"
        hid = g["teams"]["home"]["team"]["id"]
        aid = g["teams"]["away"]["team"]["id"]
        home, away = codes[hid], codes[aid]
        venue = g["venue"]["name"]
        assert venue in PARK_MAP or venue in NEUTRAL_VENUES, f"unknown venue: {venue}"
        park = PARK_MAP.get(venue, venue)  # neutral venues keep their own name
        games.append(
            {
                "date": g["officialDate"],
                "season": season,
                "home": home,
                "away": away,
                "home_runs": int(hs),
                "away_runs": int(aws),
                "park": park,
                "neutral": venue in NEUTRAL_VENUES,
            }
        )
        seen_dates_teams[(g["officialDate"], home, away)] += 1

    # No team pair should meet twice on the same date except doubleheaders
    # (which the API lists as separate gamePks -- both are real games).
    dupes = {k: c for k, c in seen_dates_teams.items() if c > 2}
    assert not dupes, f"triple-booked date/team pairs: {dupes}"

    games.sort(key=lambda r: (r["date"], r["home"], r["away"]))
    return games


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="validate the written CSV instead of fetching")
    args = ap.parse_args()

    if args.check:
        check()
        return

    all_games: list[dict] = []
    for season in SEASONS:
        games = fetch_season(season)
        print(f"{season}: {len(games)} completed games", flush=True)
        all_games.extend(games)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "date", "season", "home", "away",
            "home_runs", "away_runs", "park", "neutral",
        ])
        w.writeheader()
        w.writerows(all_games)
    print(f"wrote {OUT} ({len(all_games)} games)")

    # Per-team game counts as a sanity check (162-game seasons).
    per_team = Counter()
    for r in all_games:
        per_team[(r["season"], r["home"])] += 1
        per_team[(r["season"], r["away"])] += 1
    for season in SEASONS:
        counts = sorted(per_team[(season, t)] for t in {r["home"] for r in all_games if r["season"] == season} | {r["away"] for r in all_games if r["season"] == season})
        print(f"{season}: per-team games min={min(counts)} max={max(counts)}")


def check() -> None:
    rows = list(csv.DictReader(open(OUT)))
    print(f"{len(rows)} game rows")
    by_season = Counter(r["season"] for r in rows)
    for s in sorted(by_season):
        print(f"  season {s}: {by_season[s]} games")
    teams = set()
    for r in rows:
        teams.add(r["home"])
        teams.add(r["away"])
        assert r["home"] != r["away"]
        assert int(r["home_runs"]) >= 0 and int(r["away_runs"]) >= 0
        assert r["neutral"] in ("True", "False")
    print(f"  {len(teams)} distinct team codes: {sorted(teams)}")
    neut = sum(1 for r in rows if r["neutral"] == "True")
    print(f"  neutral-site games: {neut}")
    parks = Counter(r["park"] for r in rows)
    print(f"  {len(parks)} distinct parks")
    # chronological order
    dates = [r["date"] for r in rows]
    assert dates == sorted(dates), "rows not chronological"
    print("  chronological order OK")


if __name__ == "__main__":
    main()
