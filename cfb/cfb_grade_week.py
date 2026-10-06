"""Weekly CFB pipeline: refresh data, grade last week's picks, generate next.

    python3 cfb/cfb_grade_week.py     # needs custom.collegefootballdata connected

1. Re-pulls the current season's games/lines/PPA from CFBD.
2. Grades every pick in site/data/cfb_picks.json against final scores.
3. Appends the graded week to site/data/cfb_season_2026.json.
4. Generates next week's cfb_picks.json when the week is fully final.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_cfb import merge_season, fetch_season, get_client
from cfb_ratings import DATA as CFB_DATA, REPO

SITE_DATA = REPO / "site" / "data"
SEASON = 2026


def grade_pick(p: dict, home_score: int, away_score: int) -> dict:
    actual_margin = home_score - away_score
    actual_total = home_score + away_score
    r: dict = {"home_score": home_score, "away_score": away_score}
    if p["pick_spread"]:
        cover = actual_margin - p["line_spread"]
        r["ats"] = ("push" if abs(cover) < 0.01
                    else ("win" if (cover > 0) == (p["pick_spread"] == "home") else "loss"))
    if p["pick_total"]:
        diff = actual_total - p["line_total"]
        r["ou"] = ("push" if abs(diff) < 0.01
                   else ("win" if (diff > 0) == (p["pick_total"] == "over") else "loss"))
    return r


def grade_parlay(parlay: dict | None, picks: list[dict]) -> dict | None:
    # Preserves the generator's parlay metadata (combined_prob, fair_odds,
    # book_pays) — dropping them blanks the parlay card on /cfb (2026-10-06).
    if not parlay:
        return None
    graded = dict(parlay)  # keep combined_prob / fair_odds / book_pays
    by_game = {(p["home"], p["away"]): p for p in picks}
    results = []
    for leg in parlay["legs"]:
        away, home = leg["game"].split(" @ ")  # leg games are "away @ home"
        p = by_game.get((home, away))
        r = (p or {}).get("result")
        if not r:
            graded["result"] = None
            return graded
        key = "ats" if leg["market"] == "spread" else "ou"
        if key not in r:
            graded["result"] = None
            return graded
        results.append(r[key])
    if any(x == "loss" for x in results):
        res = "loss"
    elif all(x == "win" for x in results):
        res = "win"
    else:
        res = "push"
    graded["result"] = res
    return graded


def main() -> None:
    # 1. fresh data for the current season
    client = get_client()
    fetch_season(client, SEASON)
    df = merge_season(SEASON)
    dest = CFB_DATA / "cfb_games.parquet"
    old = pd.read_parquet(dest)
    new = pd.concat([old[old["season"] != SEASON], df], ignore_index=True)
    new.to_parquet(dest, index=False)
    print(f"refreshed {len(df)} {SEASON} games")

    # 2. grade last week's picks
    picks_path = SITE_DATA / "cfb_picks.json"
    week_data = json.loads(picks_path.read_text())
    week = week_data["week"]
    picks = week_data["picks"]
    final = df[df["home_score"].notna()].set_index(["home_team", "away_team"])

    graded, pending = 0, 0
    for p in picks:
        key = (p["home"], p["away"])
        if key not in final.index:
            p["result"] = None
            pending += 1
            continue
        g = final.loc[key]
        p["result"] = grade_pick(p, int(g["home_score"]), int(g["away_score"]))
        graded += 1

    # 3. append to season log
    log_path = SITE_DATA / f"cfb_season_{SEASON}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() \
        else {"sport": "cfb", "season": SEASON, "weeks": {}}
    log["weeks"][str(week)] = {
        "generated": week_data["generated"],
        "complete": pending == 0,
        "picks": picks,
        "parlay": grade_parlay(week_data.get("parlay"), picks),
    }
    log_path.write_text(json.dumps(log, indent=2))
    print(f"Week {week}: graded {graded}, pending {pending} -> {log_path}")

    # 4. next week's picks when fully final
    if pending == 0:
        from cfb_weekly_picks import main as gen
        gen()
    else:
        print("Week not fully final; keeping current cfb_picks.json.")


if __name__ == "__main__":
    main()
