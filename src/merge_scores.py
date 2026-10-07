"""Merge final scores into the current week's picks.json as games finish.

Unlike grade_week.py (Tuesday full-week grading + roll-forward), this only
fills in `result` for games that are final, so the This Week page can show
per-game right/wrong badges on the model's picks during the week. It also
syncs the graded week into season_2026.json so /track-record shows results.

Safe to run any time: it never touches picks or lines, and only commits when
a new final score appeared or the season log changed.
"""
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grade_week import grade_pick, grade_parlay, SEASON  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
SITE_DATA = os.path.join(ROOT, "site", "data")
PARQUET = os.path.join(DATA, "schedules_games.parquet")
PARQUET_URL = "https://github.com/nflverse/nflverse-data/releases/download/schedules/games.parquet"
GIT_ID = ["-c", "user.name=clearstackstudio",
          "-c", "user.email=334314751+clearstackstudio@users.noreply.github.com"]


def main() -> None:
    import pandas as pd

    picks_path = os.path.join(SITE_DATA, "picks.json")
    week_data = json.loads(open(picks_path).read())
    week = week_data["week"]
    picks = week_data["picks"]

    os.makedirs(DATA, exist_ok=True)
    urllib.request.urlretrieve(PARQUET_URL, PARQUET)
    sched = pd.read_parquet(PARQUET)
    s26 = sched[(sched["season"] == 2026) & (sched["week"] == week)]
    final = s26[s26["home_score"].notna()].set_index(["home_team", "away_team"])

    changed = 0
    for p in picks:
        key = (p["home_abbr"], p["away_abbr"])
        if key not in final.index:
            continue
        g = final.loc[key]
        new_result = grade_pick(p, int(g["home_score"]), int(g["away_score"]))
        if p.get("result") != new_result:
            p["result"] = new_result
            changed += 1

    # Keep the parlay badge in sync with graded legs.
    new_parlay = grade_parlay(week_data.get("parlay"), picks)
    if new_parlay != week_data.get("parlay"):
        week_data["parlay"] = new_parlay
        changed += 1

    with open(picks_path, "w") as f:
        json.dump(week_data, f, indent=2)

    # Sync the season log so /track-record shows the graded results.
    # (grade_week.py only appends once; the nightly merge is what fills
    # in results as games go final.) Always sync — the log may be stale even
    # when no new scores appeared this run.
    log_path = os.path.join(SITE_DATA, f"season_{SEASON}.json")
    log = json.loads(open(log_path).read()) if os.path.exists(log_path) \
        else {"season": SEASON, "weeks": {}}
    pending = sum(1 for p in picks if not p.get("result"))
    log["weeks"][str(week)] = {
        "generated": week_data["generated"],
        "complete": pending == 0,
        "picks": picks,
        "parlay": week_data.get("parlay"),
    }
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    subprocess.run(["git", *GIT_ID, "add", "site/data/picks.json",
                    f"site/data/season_{SEASON}.json"],
                   cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("merge_scores: no changes to commit")
        return
    subprocess.run(["git", *GIT_ID, "commit", "-m",
                    f"Merge final scores into week {week} picks ({changed} games)"],
                   cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print(f"merge_scores: synced week {week}, pushed")


if __name__ == "__main__":
    main()
