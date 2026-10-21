"""NHL shadow grading: grade frozen shadow picks against finals.

Reads data/nhl/shadow/picks.jsonl (frozen by shadow_picks.py — never
mutated here), appends one grade row per finished game to
data/nhl/shadow/grades.jsonl, and rebuilds the running summary at
data/nhl/shadow/summary.json. Finals come from the official NHL API
(shootout goal included — that is how totals settle). Grades cover:
moneyline correctness + Brier (model raw, model calibrated, and the
logged market's de-vigged Brier), and totals over/under/push vs the
logged market total for every game with a line, flagged or not.
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scores_api import fetch  # noqa: E402

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"
SHADOW = DATA / "shadow"
PICKS = SHADOW / "picks.jsonl"
GRADES = SHADOW / "grades.jsonl"
SUMMARY = SHADOW / "summary.json"
PT = ZoneInfo("America/Los_Angeles")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def fetch_finals(date_str: str, cache: dict) -> dict[int, tuple[int, int]]:
    """game_id -> (home_goals, away_goals) for finished games that day."""
    if date_str in cache:
        return cache[date_str]
    data = fetch(f"https://api-web.nhle.com/v1/score/{date_str}")
    out = {}
    for g in data.get("games", []):
        if g.get("gameState") in ("OFF", "FINAL"):
            ht, at = g["homeTeam"], g["awayTeam"]
            if "score" in ht and "score" in at:
                out[int(g["id"])] = (int(ht["score"]), int(at["score"]))
    cache[date_str] = out
    return out


def grade_pick(pick: dict, home_goals: int, away_goals: int) -> dict:
    """Pure grading of one frozen pick against a final score."""
    y = 1 if home_goals > away_goals else 0
    g = {
        "game_id": pick["game_id"], "date": pick["date"],
        "home": pick["home"], "away": pick["away"],
        "home_goals": home_goals, "away_goals": away_goals,
        "home_win": y,
        "brier_raw": round((pick["p_home_raw"] - y) ** 2, 6),
        "brier_cal": round((pick["p_home_cal"] - y) ** 2, 6),
        "market_brier": (round((pick["market_p_home"] - y) ** 2, 6)
                         if pick.get("market_p_home") is not None else None),
        "su_correct": bool((pick["p_home_cal"] > 0.5) == (y == 1)),
        "actual_total": home_goals + away_goals,
        "model_total_error": round(
            pick["model_total"] - (home_goals + away_goals), 4),
        "totals_flag": bool(pick.get("totals_flag")),
        "totals_result": None,
    }
    line = pick.get("total_line")
    if line is not None:
        actual = home_goals + away_goals
        edge = pick["model_total"] - line
        if actual == line:
            g["totals_result"] = "push"
        elif edge == 0:
            g["totals_result"] = None
        elif (actual > line) == (edge > 0):
            g["totals_result"] = "win"
        else:
            g["totals_result"] = "loss"
    return g


def _record(rows: list[dict]) -> dict:
    w = sum(1 for r in rows if r["totals_result"] == "win")
    l = sum(1 for r in rows if r["totals_result"] == "loss")
    p = sum(1 for r in rows if r["totals_result"] == "push")
    return {"w": w, "l": l, "p": p,
            "win_pct": round(w / (w + l), 4) if (w + l) else None}


def build_summary(picks: list[dict], grades: list[dict]) -> dict:
    graded = [g for g in grades if g is not None]
    n = len(graded)
    mkt = [g for g in graded if g["market_brier"] is not None]
    with_line = [g for g in graded if g["totals_result"] is not None]
    flagged = [g for g in with_line if g["totals_flag"]]
    return {
        "generated_at": datetime.now(PT).isoformat(),
        "games_logged": len(picks),
        "games_graded": n,
        "dates_graded": sorted({g["date"] for g in graded}),
        "moneyline": {
            "brier_raw": round(sum(g["brier_raw"] for g in graded) / n, 4)
            if n else None,
            "brier_cal": round(sum(g["brier_cal"] for g in graded) / n, 4)
            if n else None,
            "market_brier": round(
                sum(g["market_brier"] for g in mkt) / len(mkt), 4)
            if mkt else None,
            "su_acc_cal": round(
                sum(g["su_correct"] for g in graded) / n, 4) if n else None,
        },
        "totals_flagged": _record(flagged),
        "totals_all": _record(with_line),
        "totals_rmse": round(
            (sum(g["model_total_error"] ** 2 for g in graded) / n) ** 0.5, 3)
        if n else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Grade NHL shadow picks")
    ap.add_argument("--date", default=None,
                    help="grade only this slate date YYYY-MM-DD "
                         "(default: every ungraded date before today PT)")
    args = ap.parse_args()

    picks = load_jsonl(PICKS)
    grades = load_jsonl(GRADES)
    done = {g["game_id"] for g in grades}
    today = datetime.now(PT).date()
    cache: dict = {}
    new_grades = []
    for pick in picks:
        if pick["game_id"] in done:
            continue
        if args.date and pick["date"] != args.date:
            continue
        if not args.date and pick["date"] >= today.isoformat():
            continue
        finals = fetch_finals(pick["date"], cache)
        fin = finals.get(pick["game_id"])
        if fin is None:
            continue
        new_grades.append(grade_pick(pick, fin[0], fin[1]))

    if new_grades:
        SHADOW.mkdir(parents=True, exist_ok=True)
        with GRADES.open("a") as f:
            for g in new_grades:
                f.write(json.dumps(g) + "\n")
        grades.extend(new_grades)
    summary = build_summary(picks, grades)
    SHADOW.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2))
    print(f"graded {len(new_grades)} new games; "
          f"{summary['games_graded']} total graded of "
          f"{summary['games_logged']} logged")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
