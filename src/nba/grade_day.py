"""Grade one day of NBA picks against finals.

    python3 src/nba/grade_day.py --date YYYY-MM-DD   # default: yesterday (PT)

Reads the day's published picks from site/data/nba_season_<season>.json,
finals from data/nba/merged/<date>.json, writes per-pick results back into
the day entry, and -- when every pick has a final -- folds the day into
site/data/nba_track_record.json ({model, seasons}, mirroring the NFL
track_record.json shape).

Idempotent: the track record is recomputed from the stored per-day results
every run, and graded dates are kept in a set, so re-running a date never
double-counts. A day with any pick still missing its final is left
incomplete (graded: False/complete: False in the season log, untouched in
the track record); re-run it once the finals land.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "nba"
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")
TRACK_PATH = SITE_DATA / "nba_track_record.json"

MODEL_DESC = ("Margin-adjusted Elo + efficiency totals with rest adjustment "
              "(final scores; the line is never an input). Walk-forward: "
              "every prediction made before learning the result.")


def grade_pick(p: dict, home_score: float, away_score: float) -> dict:
    """Grade one published pick. Mirrors cfb/cfb_grade_week.grade_pick."""
    actual_margin = home_score - away_score
    actual_total = home_score + away_score
    r: dict = {"home_score": home_score, "away_score": away_score}
    if p["pick_spread"]:
        cover = actual_margin - p["line_spread"]  # >0: home covers
        r["ats"] = ("push" if abs(cover) < 0.01
                    else ("win" if (cover > 0) == (p["pick_spread"] == "home")
                          else "loss"))
    if p["pick_total"]:
        diff = actual_total - p["line_total"]  # >0: over hits
        r["ou"] = ("push" if abs(diff) < 0.01
                   else ("win" if (diff > 0) == (p["pick_total"] == "over")
                         else "loss"))
    return r


def grade_parlay(parlay: dict | None, picks: list[dict]) -> dict | None:
    """Mirror cfb/cfb_grade_week.grade_parlay. None result while any leg's
    game is still pending."""
    if not parlay:
        return None
    by_game = {(p["home"], p["away"]): p for p in picks}
    results = []
    for leg in parlay["legs"]:
        away, home = leg["game"].split(" @ ")  # leg games are "away @ home"
        p = by_game.get((home, away))
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


def season_aggregate(season: int, days: dict[str, dict]) -> dict:
    """Recompute a season's track-record entry from stored per-day results."""
    games = su = 0
    our_se = line_se = 0.0
    ats_w = ats_l = ats_p = 0
    ou_w = ou_l = ou_p = 0
    graded_days = []
    for day_key in sorted(days):
        day = days[day_key]
        if not day.get("complete"):
            continue
        graded_days.append(day_key)
        for p in day["picks"]:
            r = p.get("result")
            if not r:
                continue
            games += 1
            actual_margin = r["home_score"] - r["away_score"]
            su += (p["our_spread"] > 0) == (actual_margin > 0)
            our_se += (p["our_spread"] - actual_margin) ** 2
            line_se += (p["line_spread"] - actual_margin) ** 2
            if p["pick_spread"]:
                if r["ats"] == "win":
                    ats_w += 1
                elif r["ats"] == "loss":
                    ats_l += 1
                else:
                    ats_p += 1
            if p["pick_total"]:
                if r["ou"] == "win":
                    ou_w += 1
                elif r["ou"] == "loss":
                    ou_l += 1
                else:
                    ou_p += 1
    ats_dec = ats_w + ats_l
    ou_dec = ou_w + ou_l
    return {
        "season": season,
        "days": graded_days,
        "games": games,
        "straight_up_pct": round(su / games, 4) if games else None,
        "our_rmse": round(math.sqrt(our_se / games), 2) if games else None,
        "line_rmse": round(math.sqrt(line_se / games), 2) if games else None,
        "ats_w": ats_w, "ats_l": ats_l, "ats_p": ats_p,
        "ats_pct": round(ats_w / ats_dec, 4) if ats_dec else None,
        "ou_w": ou_w, "ou_l": ou_l, "ou_p": ou_p,
        "ou_pct": round(ou_w / ou_dec, 4) if ou_dec else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Grade one day of NBA picks")
    ap.add_argument("--date", default=None,
                    help="YYYY-MM-DD (default: yesterday, PT)")
    args = ap.parse_args()

    today = datetime.datetime.now(PT).date()
    target = (datetime.date.fromisoformat(args.date) if args.date
              else today - datetime.timedelta(days=1))
    day_key = target.isoformat()

    merged_path = DATA / "merged" / f"{day_key}.json"
    if not merged_path.exists():
        print(f"no merged finals for {day_key} ({merged_path} missing); "
              f"cannot grade")
        sys.exit(1)
    merged = json.loads(merged_path.read_text())
    finals = {}
    for g in merged.get("games", []):
        f = g.get("final")
        if f:
            finals[(g["home_team"], g["away_team"])] = (
                float(f["home_score"]), float(f["away_score"]))

    # Find the day's published picks in the season log.
    season = target.year + 1 if target.month >= 10 else target.year
    log_path = SITE_DATA / f"nba_season_{season}.json"
    if not log_path.exists():
        print(f"no season log {log_path}; no picks published for {day_key}")
        sys.exit(1)
    log = json.loads(log_path.read_text())
    day = log["days"].get(day_key)
    if day is None:
        print(f"no picks published for {day_key} in {log_path}")
        sys.exit(1)
    picks = day["picks"]

    graded, pending = 0, 0
    for p in picks:
        key = (p["home"], p["away"])
        if key not in finals:
            p["result"] = None
            pending += 1
            continue
        hs, aws = finals[key]
        p["result"] = grade_pick(p, hs, aws)
        graded += 1

    day["graded"] = True
    day["complete"] = pending == 0
    day["graded_at"] = datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z")
    day["parlay"] = grade_parlay(day.get("parlay"), picks)
    log_path.write_text(json.dumps(log, indent=2))
    print(f"{day_key}: graded {graded}, pending {pending} -> {log_path}")

    if pending:
        print("day not fully final; track record untouched. Re-run once "
              "the remaining finals land in merged/.")
        return

    # Fold into the track record, recomputed from stored results so a
    # re-run can never double-count.
    track = (json.loads(TRACK_PATH.read_text()) if TRACK_PATH.exists()
             else {"model": MODEL_DESC, "seasons": []})
    seasons = {s["season"]: s for s in track["seasons"]}
    seasons[season] = season_aggregate(season, log["days"])
    track["seasons"] = [seasons[s] for s in sorted(seasons)]
    TRACK_PATH.write_text(json.dumps(track, indent=2))
    agg = seasons[season]
    def pct(x):
        return f"{x:.1%}" if x is not None else "n/a"
    print(f"season {season}: {agg['games']} games, "
          f"SU {pct(agg['straight_up_pct'])}, "
          f"ATS {agg['ats_w']}-{agg['ats_l']}-{agg['ats_p']} "
          f"({pct(agg['ats_pct'])} on {agg['ats_w'] + agg['ats_l']}), "
          f"O/U {agg['ou_w']}-{agg['ou_l']}-{agg['ou_p']} "
          f"({pct(agg['ou_pct'])} on {agg['ou_w'] + agg['ou_l']}) "
          f"-> {TRACK_PATH}")


if __name__ == "__main__":
    main()
