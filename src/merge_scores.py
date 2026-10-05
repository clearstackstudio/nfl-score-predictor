"""Merge final scores into the current week's picks.json as games finish.

Unlike grade_week.py (Tuesday full-week grading + roll-forward), this only
fills in `result` for games that are final, so the This Week page can show
per-game right/wrong badges on the model's picks during the week.

Safe to run any time: it never touches picks, lines, or the season log, and
only commits when a new final score appeared.
"""
import json
import os
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from grade_week import grade_pick  # noqa: E402

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

    if changed == 0:
        print("merge_scores: no new final scores")
        return

    with open(picks_path, "w") as f:
        json.dump(week_data, f, indent=2)

    subprocess.run(["git", *GIT_ID, "add", "site/data/picks.json"],
                   cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("merge_scores: no changes to commit")
        return
    subprocess.run(["git", *GIT_ID, "commit", "-m",
                    f"Merge final scores into week {week} picks ({changed} games)"],
                   cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print(f"merge_scores: graded {changed} games, pushed")


if __name__ == "__main__":
    main()
