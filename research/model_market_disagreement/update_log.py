#!/usr/bin/env python3
"""Append newly graded games to the model-vs-market disagreement log.

Part of the standing watch defined in WATCH.md (same directory).
Measurement only — this script never touches the model or any site data.

Sources (read-only):
  - site/data/season_2026.json  (archived graded weeks)
  - site/data/picks.json        (current week, may overlap the archive)

Writes only research/model_market_disagreement/log.csv.
Idempotent: a game is logged once, keyed by
season|week|gameday|AWAY@HOME. Ungraded games (no merged result yet)
are skipped and picked up on a later run once graded.

Run with the repo venv:
  ~/workspace/nfl-score-predictor/.venv-cfb/bin/python \
    research/model_market_disagreement/update_log.py
"""

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
LOG = HERE / "log.csv"

FIELDS = [
    "season", "week", "gameday", "away_abbr", "home_abbr", "game_id",
    "our_spread", "line_spread", "actual_margin", "disagreement",
    "abs_disagreement", "bucket", "model_err", "line_err", "excess",
]

BUCKETS = ["<3", "3-6.9", "7-9.9", ">=10"]


def bucket_of(abs_disagreement: float) -> str:
    if abs_disagreement < 3:
        return "<3"
    if abs_disagreement < 7:
        return "3-6.9"
    if abs_disagreement < 10:
        return "7-9.9"
    return ">=10"


def game_rows(season: int, week: int, picks: list) -> list:
    """Build log rows for the graded games in one week's pick list."""
    rows = []
    for g in picks:
        result = g.get("result") or {}
        home_score = result.get("home_score")
        away_score = result.get("away_score")
        our = g.get("our_spread")
        line = g.get("line_spread")
        if home_score is None or away_score is None or our is None or line is None:
            continue  # not graded yet, or missing a spread — skip, never guess
        actual_margin = home_score - away_score
        disagreement = our - line
        model_err = abs(our - actual_margin)
        line_err = abs(line - actual_margin)
        game_id = f"{season}|{week}|{g.get('gameday')}|{g.get('away_abbr')}@{g.get('home_abbr')}"
        rows.append({
            "season": season,
            "week": week,
            "gameday": g.get("gameday") or "",
            "away_abbr": g.get("away_abbr") or "",
            "home_abbr": g.get("home_abbr") or "",
            "game_id": game_id,
            "our_spread": round(our, 2),
            "line_spread": round(line, 2),
            "actual_margin": actual_margin,
            "disagreement": round(disagreement, 2),
            "abs_disagreement": round(abs(disagreement), 2),
            "bucket": bucket_of(abs(disagreement)),
            "model_err": round(model_err, 2),
            "line_err": round(line_err, 2),
            "excess": round(model_err - line_err, 2),
        })
    return rows


def collect_candidate_rows() -> list:
    rows = []
    season_path = REPO / "site" / "data" / "season_2026.json"
    if season_path.exists():
        data = json.loads(season_path.read_text())
        season = data.get("season", 2026)
        for week_str, week_data in sorted(data.get("weeks", {}).items(),
                                          key=lambda kv: int(kv[0])):
            rows.extend(game_rows(season, int(week_str),
                                  week_data.get("picks", [])))
    picks_path = REPO / "site" / "data" / "picks.json"
    if picks_path.exists():
        data = json.loads(picks_path.read_text())
        rows.extend(game_rows(data.get("season", 2026), int(data.get("week")),
                              data.get("picks", [])))
    return rows


def load_log() -> list:
    if not LOG.exists():
        return []
    with LOG.open(newline="") as f:
        return list(csv.DictReader(f))


def write_log(rows: list) -> None:
    with LOG.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list) -> None:
    print(f"\nRunning bucket summary — {len(rows)} graded games logged")
    print(f"{'bucket':<8} {'n':>4} {'mean excess':>12} {'mean model_err':>15} "
          f"{'mean line_err':>14}")
    combined_ge7 = []
    for b in BUCKETS:
        sel = [r for r in rows if r["bucket"] == b]
        if b in ("7-9.9", ">=10"):
            combined_ge7.extend(sel)
        if not sel:
            print(f"{b:<8} {0:>4} {'—':>12} {'—':>15} {'—':>14}")
            continue
        n = len(sel)
        mean = lambda key: sum(float(r[key]) for r in sel) / n
        print(f"{b:<8} {n:>4} {mean('excess'):>12.2f} "
              f"{mean('model_err'):>15.2f} {mean('line_err'):>14.2f}")
    if combined_ge7:
        n = len(combined_ge7)
        mean_excess = sum(float(r["excess"]) for r in combined_ge7) / n
        print(f"\nDecision bucket >=7: n={n}, mean excess = {mean_excess:+.2f} "
              f"(graduation bar: mean excess > 0 at n >= 25, checkpoint only)")
    else:
        print("\nDecision bucket >=7: n=0 so far")
    weeks = sorted({int(r["week"]) for r in rows})
    if weeks:
        print(f"Weeks covered: {weeks[0]}–{weeks[-1]} "
              f"({', '.join(str(w) for w in weeks)})")


def main() -> int:
    existing = load_log()
    seen = {r["game_id"] for r in existing}
    new_rows = []
    for row in collect_candidate_rows():
        if row["game_id"] in seen:
            continue
        seen.add(row["game_id"])
        new_rows.append(row)
    if new_rows:
        all_rows = existing + new_rows
        all_rows.sort(key=lambda r: (int(r["season"]), int(r["week"]),
                                     r["gameday"], r["game_id"]))
        write_log(all_rows)
        print(f"Appended {len(new_rows)} newly graded game(s):")
        for r in new_rows:
            print(f"  W{r['week']} {r['away_abbr']}@{r['home_abbr']} "
                  f"disagreement {float(r['disagreement']):+.1f} "
                  f"excess {float(r['excess']):+.1f}")
    else:
        print("No new graded games to append.")
        all_rows = existing
    print_summary(all_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
