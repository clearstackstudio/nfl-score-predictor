"""Merge final scores into the current week's cfb_picks.json as games finish.

Unlike cfb_grade_week.py (full-week grading + season log + roll-forward),
this only fills in `result` for games that are final, so the CFB This Week
page can show per-game right/wrong badges on the model's picks during the week.

Safe to run any time: it never touches picks, lines, or the season log, and
only commits when a new final score appeared.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_cfb import get_client  # noqa: E402
from cfb_grade_week import grade_pick, grade_parlay, SEASON  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = os.path.join(ROOT, "site", "data")
GIT_ID = ["-c", "user.name=clearstackstudio",
          "-c", "user.email=334314751+clearstackstudio@users.noreply.github.com"]


def main() -> None:
    import cfbd
    from cfbd.api import games_api

    picks_path = os.path.join(SITE_DATA, "cfb_picks.json")
    week_data = json.loads(open(picks_path).read())
    week = week_data["week"]
    picks = week_data["picks"]

    client = get_client()
    games = games_api.GamesApi(client)
    # Single lightweight call: this week's FBS games with scores as they finalize.
    g = games.get_games(year=SEASON, week=week, classification="fbs")
    final = {(x.home_team, x.away_team): x for x in g
             if x.home_points is not None}

    changed = 0
    for p in picks:
        key = (p["home"], p["away"])
        if key not in final:
            continue
        x = final[key]
        new_result = grade_pick(p, int(x.home_points), int(x.away_points))
        if p.get("result") != new_result:
            p["result"] = new_result
            changed += 1

    # Keep the parlay badge in sync with graded legs.
    new_parlay = grade_parlay(week_data.get("parlay"), picks)
    if new_parlay != week_data.get("parlay"):
        week_data["parlay"] = new_parlay
        changed += 1

    if changed == 0:
        print("cfb_merge_scores: no new final scores")
        return

    with open(picks_path, "w") as f:
        json.dump(week_data, f, indent=2)

    subprocess.run(["git", *GIT_ID, "add", "site/data/cfb_picks.json"],
                   cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("cfb_merge_scores: no changes to commit")
        return
    subprocess.run(["git", *GIT_ID, "commit", "-m",
                    f"Merge final scores into CFB week {week} picks ({changed} updates)"],
                   cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print(f"cfb_merge_scores: graded {changed} updates, pushed")


if __name__ == "__main__":
    main()
