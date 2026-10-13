"""Backfill final scores into the current week's cfb_picks.json from ESPN.

Fallback for when the CollegeFootballData quota is exhausted (the normal
path is cfb_merge_scores.py). ESPN's public scoreboard API needs no key.
Matching is by normalized (home, away) school-name pair (ESPN
team.location vs the CFBD names stored in the picks), and every fill goes
through cfb_grade_week.grade_pick — identical grading to the CFBD path.

Safety rules:
  - Only games ESPN marks STATUS_FINAL are filled.
  - A pick that already has a result is never changed; if ESPN's score
    disagrees with a stored result, the script aborts before writing.
  - The season log sync, commit, and push mirror cfb_merge_scores.py.

Proven 2026-10-12: all 55 week-6 picks matched, and ESPN reproduced the
4 CFBD-graded Oct 8 results exactly before the backfill ran.

Run with the repo venv (imports cfb_grade_week, which imports cfbd):
    .venv-cfb/bin/python cfb/cfb_backfill_espn.py
"""
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfb_grade_week import grade_pick, grade_parlay, SEASON  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE_DATA = os.path.join(ROOT, "site", "data")
GIT_ID = ["-c", "user.name=clearstackstudio",
          "-c", "user.email=334314751+clearstackstudio@users.noreply.github.com"]


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def espn_finals(gameday: str) -> dict:
    """{(norm_home, norm_away): (home_score, away_score)} for final games."""
    url = ("https://site.api.espn.com/apis/site/v2/sports/football/"
           "college-football/scoreboard?dates="
           f"{gameday.replace('-', '')}&groups=80&limit=200")
    with urllib.request.urlopen(url, timeout=30) as r:
        events = json.load(r).get("events", [])
    out = {}
    for e in events:
        if e["status"]["type"]["name"] != "STATUS_FINAL":
            continue
        by = {c["homeAway"]: c for c in e["competitions"][0]["competitors"]}
        h, a = by["home"], by["away"]
        out[(norm(h["team"]["location"]), norm(a["team"]["location"]))] = (
            int(h["score"]), int(a["score"]))
    return out


def main() -> None:
    picks_path = os.path.join(SITE_DATA, "cfb_picks.json")
    week_data = json.loads(open(picks_path).read())
    week = week_data["week"]
    picks = week_data["picks"]

    finals: dict = {}
    for day in sorted({p["gameday"] for p in picks}):
        finals.update(espn_finals(day))
    print(f"espn finals loaded: {len(finals)}")

    changed = 0
    for p in picks:
        key = (norm(p["home"]), norm(p["away"]))
        if key not in finals:
            continue
        home_pts, away_pts = finals[key]
        existing = p.get("result")
        if existing:
            if (existing["home_score"], existing["away_score"]) != (home_pts, away_pts):
                print(f"ABORT: stored result disagrees with ESPN for "
                      f"{p['away']} @ {p['home']}: stored "
                      f"{existing['away_score']}-{existing['home_score']} vs "
                      f"espn {away_pts}-{home_pts}")
                sys.exit(1)
            continue
        p["result"] = grade_pick(p, home_pts, away_pts)
        changed += 1

    new_parlay = grade_parlay(week_data.get("parlay"), picks)
    if new_parlay != week_data.get("parlay"):
        week_data["parlay"] = new_parlay
        changed += 1

    with open(picks_path, "w") as f:
        json.dump(week_data, f, indent=2)

    log_path = os.path.join(SITE_DATA, f"cfb_season_{SEASON}.json")
    log = json.loads(open(log_path).read()) if os.path.exists(log_path) \
        else {"sport": "cfb", "season": SEASON, "weeks": {}}
    pending = sum(1 for p in picks if not p.get("result"))
    log["weeks"][str(week)] = {
        "generated": week_data["generated"],
        "complete": pending == 0,
        "picks": picks,
        "parlay": week_data.get("parlay"),
    }
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    subprocess.run(["git", *GIT_ID, "add", "site/data/cfb_picks.json",
                    f"site/data/cfb_season_{SEASON}.json"],
                   cwd=ROOT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        print("cfb_backfill_espn: no changes to commit")
        return
    subprocess.run(["git", *GIT_ID, "commit", "-m",
                    f"Backfill CFB week {week} finals from ESPN ({changed} updates; CFBD quota exhausted)"],
                   cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "main"], cwd=ROOT, check=True)
    print(f"cfb_backfill_espn: week {week} backfilled ({changed} updates), "
          f"pending={pending}, pushed")


if __name__ == "__main__":
    main()
