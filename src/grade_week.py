"""Weekly pipeline: grade last week's picks, then generate next week's.

Run after a week's games are final (nflverse updates within ~a day):
    python3 grade_week.py

1. Re-downloads 2026 play-by-play + schedules.
2. Grades every pick in site/data/picks.json against final scores.
3. Appends the graded week to site/data/season_2026.json (the live record).
4. Generates next week's picks.json.

ATS grading uses the home-margin convention (+ = home favored):
    cover_margin = actual_margin - line_margin
    home covers if > 0, push if == 0, away covers if < 0.
O/U: actual_total vs line_total, push if equal.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent


def grade_pick(p: dict, home_score: int, away_score: int) -> dict:
    """Grade one pick against a final score. Home-margin convention (+ = home favored)."""
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
    """Grade the weekly parlay: win = every leg wins, loss = any leg loses,
    push = no losses but at least one push (standard voided-leg reduction).
    None result while any leg's game is still pending."""
    if not parlay:
        return None
    by_game = {(p["home_abbr"], p["away_abbr"]): p for p in picks}
    results = []
    for leg in parlay["legs"]:
        p = by_game.get((leg["home_abbr"], leg["away_abbr"]))
        r = (p or {}).get("result")
        if not r:
            return {"legs": parlay["legs"], "result": None}
        key = "ats" if leg["market"] == "spread" else "ou"
        if key not in r:
            return {"legs": parlay["legs"], "result": None}
        results.append(r[key])
    if any(x == "loss" for x in results):
        res = "loss"
    elif all(x == "win" for x in results):
        res = "win"
    else:
        res = "push"
    return {"legs": parlay["legs"], "result": res}


DATA = REPO / "data"
SITE_DATA = REPO / "site" / "data"
SEASON = 2026


def download(url: str, dest: Path) -> None:
    import urllib.request
    urllib.request.urlretrieve(url, dest)


def main() -> None:
    # 1. fresh data
    download("https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_2026.parquet",
             DATA / "play_by_play_2026.parquet")
    download("https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet",
             DATA / "schedules_games.parquet")

    picks_path = SITE_DATA / "picks.json"
    week_data = json.loads(picks_path.read_text())
    week = week_data["week"]
    picks = week_data["picks"]

    # 2. grade against final scores
    sched = pd.read_parquet(DATA / "schedules_games.parquet")
    s26 = sched[(sched["season"] == SEASON) & (sched["week"] == week)]
    final = s26[s26["home_score"].notna()].set_index(["home_team", "away_team"])

    graded, pending = 0, 0
    for p in picks:
        key = (p["home_abbr"], p["away_abbr"])
        if key not in final.index:
            p["result"] = None
            pending += 1
            continue
        g = final.loc[key]
        p["result"] = grade_pick(p, int(g["home_score"]), int(g["away_score"]))
        graded += 1

    # 3. append to season log
    log_path = SITE_DATA / f"season_{SEASON}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() else {"season": SEASON, "weeks": {}}
    log["weeks"][str(week)] = {
        "generated": week_data["generated"],
        "complete": pending == 0,
        "picks": picks,
        "parlay": grade_parlay(week_data.get("parlay"), picks),
    }
    log_path.write_text(json.dumps(log, indent=2))
    print(f"Week {week}: graded {graded}, pending {pending} -> {log_path}")

    # 4. next week's picks (only when the week is fully final)
    if pending == 0:
        from weekly_picks import main as gen
        gen()
    else:
        print("Week not fully final yet; keeping current picks.json ungraded games as-is.")


if __name__ == "__main__":
    main()
