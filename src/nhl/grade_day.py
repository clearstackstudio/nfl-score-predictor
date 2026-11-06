"""Daily NHL grading: grade published picks against finals.

Published counterpart of shadow_grade.py. Finals come straight from
the official NHL API (the same fetch the shadow grader uses — there is
no separate merged-finals file in the NHL pipeline, so merging is
inherent: the finals are pulled at grade time). Per-pick grading math
is shadow_grade.grade_pick itself, imported — the published record and
the shadow record can never drift apart in how a game is scored.

Reads the day's published picks from site/data/nhl_season_<season>.json,
writes per-pick results back into that file, and recomputes
site/data/nhl_track_record.json from the stored results on every run
(the NBA grade_day.py pattern — idempotent, a re-run can never
double-count).

Market-comparison honesty rule: the Nov 1, 2026 Ottawa @ Anaheim game
(game_id 2026020231) froze in the shadow log with an invalid market
moneyline (-1.0 across 8 books). Seeded picks from that game carry
market_excluded=true and are left out of every market-Brier mean; the
model's own numbers still count it. The exclusion and its reason are
disclosed on the track-record page.

Totals are context only: results carry the totals error for the
model-total RMSE context stat, but no totals win/loss record is kept.

Usage:
    python3 src/nhl/grade_day.py [--date YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shadow_grade import fetch_finals, grade_pick  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")

MODEL_DESC = (
    "Expected-goals ratings model (v1.1): team offense/defense ratings "
    "fitted walk-forward on MoneyPuck expected goals, a 0.20-goal "
    "home-ice term, a rest-day term, Poisson win probabilities, and a "
    "calibration map fitted on the discovery period (a=-0.0279, "
    "b=1.2755). The betting line is never an input — only the "
    "benchmark. Moneyline picks publish when model and market disagree "
    "by 2.0 points or more; totals are context only.")


def grade_site_pick(p: dict, home_goals: int, away_goals: int) -> dict:
    """Grade one published pick; returns its stored result dict."""
    shadow_shape = {
        "game_id": p["game_id"], "date": p["gameday"],
        "home": p["home_abbr"], "away": p["away_abbr"],
        "p_home_raw": p["p_home_raw"], "p_home_cal": p["p_home_cal"],
        "market_p_home": p.get("market_p_home"),
        "model_total": p["model_total"], "total_line": p.get("total_line"),
        "totals_flag": False,
    }
    g = grade_pick(shadow_shape, home_goals, away_goals)
    home_win = home_goals > away_goals
    su = None
    if p.get("pick_side"):
        picked_home = p["pick_side"] == "home"
        su = "win" if picked_home == home_win else "loss"
    return {
        "home_score": home_goals, "away_score": away_goals,
        "su": su,
        "model_correct": bool(g["su_correct"]),
        "brier_raw": g["brier_raw"],
        "brier_cal": g["brier_cal"],
        # Excluded games never enter a market comparison.
        "market_brier": (None if p.get("market_excluded")
                         else g["market_brier"]),
        "total_error": g["model_total_error"],
    }


def season_aggregate(season: int, days: dict[str, dict]) -> dict:
    """Recompute a season's track-record entry from stored per-day
    results (NBA grade_day.py pattern). Brier means are PAIRED: only
    games with a market line that is not excluded count — for the
    model or the market — so the comparison is always same-games."""
    games = 0
    su_correct = 0
    paired = 0
    brier_raw = brier_cal = market_brier = 0.0
    pick_w = pick_l = 0
    total_se = 0.0
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
            su_correct += bool(r["model_correct"])
            total_se += float(r["total_error"]) ** 2
            if r.get("market_brier") is not None:
                paired += 1
                brier_raw += float(r["brier_raw"])
                brier_cal += float(r["brier_cal"])
                market_brier += float(r["market_brier"])
            if r.get("su") == "win":
                pick_w += 1
            elif r.get("su") == "loss":
                pick_l += 1
    pick_dec = pick_w + pick_l
    return {
        "season": season,
        "days": graded_days,
        "games": games,
        "straight_up_pct": round(su_correct / games, 4) if games else None,
        "paired_games": paired,
        "brier_raw": round(brier_raw / paired, 4) if paired else None,
        "brier_cal": round(brier_cal / paired, 4) if paired else None,
        "market_brier": round(market_brier / paired, 4) if paired else None,
        "pick_w": pick_w, "pick_l": pick_l,
        "pick_pct": round(pick_w / pick_dec, 4) if pick_dec else None,
        "totals_rmse": round(math.sqrt(total_se / games), 3) if games else None,
    }


def rebuild_track_record(season: int, log: dict) -> dict:
    """Fold one season's aggregate into nhl_track_record.json,
    preserving the seeded disclosure/backtest blocks."""
    track_path = SITE_DATA / "nhl_track_record.json"
    track = (json.loads(track_path.read_text()) if track_path.exists()
             else {"model": MODEL_DESC, "seasons": []})
    track.setdefault("model", MODEL_DESC)
    seasons = {s["season"]: s for s in track.get("seasons", [])}
    seasons[season] = season_aggregate(season, log["days"])
    track["seasons"] = [seasons[s] for s in sorted(seasons)]
    track_path.write_text(json.dumps(track, indent=2))
    return seasons[season]


def main() -> None:
    ap = argparse.ArgumentParser(description="Grade one day of NHL picks")
    ap.add_argument("--date", default=None,
                    help="YYYY-MM-DD (default: yesterday, PT)")
    args = ap.parse_args()

    today = datetime.datetime.now(PT).date()
    target = (datetime.date.fromisoformat(args.date) if args.date
              else today - datetime.timedelta(days=1))
    day_key = target.isoformat()

    # Season file: try the ending-year conventions around the date.
    log_path = None
    log = None
    for season_guess in (target.year + 1, target.year):
        cand = SITE_DATA / f"nhl_season_{season_guess}.json"
        if cand.exists():
            data = json.loads(cand.read_text())
            if day_key in data.get("days", {}):
                log_path, log = cand, data
                break
    if log is None:
        print(f"no published picks for {day_key} in any NHL season log; "
              f"nothing to grade")
        sys.exit(1)
    season = int(log["season"])
    day = log["days"][day_key]
    picks = day["picks"]

    finals = fetch_finals(day_key, {})
    graded, pending = 0, 0
    for p in picks:
        fin = finals.get(p["game_id"])
        if fin is None:
            p["result"] = None
            pending += 1
            continue
        p["result"] = grade_site_pick(p, fin[0], fin[1])
        graded += 1

    day["graded"] = True
    day["complete"] = pending == 0
    day["graded_at"] = datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z")
    log_path.write_text(json.dumps(log, indent=2))
    print(f"{day_key}: graded {graded}, pending {pending} -> {log_path}")

    if pending:
        print("day not fully final; track record untouched. Re-run once "
              "the remaining finals are posted by the NHL API.")
        return

    agg = rebuild_track_record(season, log)

    def pct(x):
        return f"{x:.1%}" if x is not None else "n/a"

    def brier(x):
        return f"{x:.4f}" if x is not None else "n/a"

    print(f"season {season}: {agg['games']} games, "
          f"SU {pct(agg['straight_up_pct'])}, "
          f"picks {agg['pick_w']}-{agg['pick_l']} "
          f"({pct(agg['pick_pct'])}), "
          f"Brier cal {brier(agg['brier_cal'])} vs market "
          f"{brier(agg['market_brier'])} (paired n={agg['paired_games']}) "
          f"-> {SITE_DATA / 'nhl_track_record.json'}")


if __name__ == "__main__":
    main()
