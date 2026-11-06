"""Seed the published NHL season log + track record from the shadow log.

ONE-OFF launch step (2026-11-06). The public track record seeds from
the pre-launch shadow record: 110 games frozen nightly Oct 21 – Nov 5,
2026 and graded against official NHL API finals, exactly as logged in
data/nhl/shadow/picks.jsonl + grades.jsonl. Those files are append-only
history — this script only READS them.

Conversion rules (disclosed on the track-record page):
  - Every shadow game becomes a season-log pick. In shadow, the pick
    was the model's favored side in every game (the shadow graded
    straight-up accuracy); from Nov 6 the published board applies the
    2.0pp disagreement gate, so not every game carries a pick.
  - The Nov 1 Ottawa @ Anaheim game (game_id 2026020231) froze with an
    invalid market moneyline (-1.0 across 8 books). Its pick carries
    market_excluded=true: the model's own numbers count the game, no
    market comparison does.
  - Aggregates are recomputed by grade_day.season_aggregate from the
    converted rows and asserted against the canonical checkpoint
    numbers (stage3-shadow-update-2026-11-06.md) before anything is
    written: paired n=104, Brier raw 0.2320 / calibrated 0.2312 vs
    market 0.2304.

Usage:
    python3 src/nhl/seed_season_log.py
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from daily_picks import ABBR_TO_NAME, fmt_ml  # noqa: E402
from grade_day import MODEL_DESC, season_aggregate  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "nhl"
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")
SEASON = 2027
EXCLUDED_GAME_ID = 2026020231

CANONICAL = {"paired": 104, "brier_raw": 0.2320, "brier_cal": 0.2312,
             "market_brier": 0.2304, "games": 110}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def seed_pick(pick: dict, grade: dict) -> dict:
    home_abbr, away_abbr = pick["home"], pick["away"]
    home, away = ABBR_TO_NAME[home_abbr], ABBR_TO_NAME[away_abbr]
    p_home = float(pick["p_home_cal"])
    pick_side = "home" if p_home > 0.5 else "away"
    excluded = pick["game_id"] == EXCLUDED_GAME_ID
    start = datetime.datetime.fromisoformat(
        pick["start_time_utc"].replace("Z", "+00:00")).astimezone(PT)
    return {
        "away": away, "home": home,
        "away_abbr": away_abbr, "home_abbr": home_abbr,
        "game_id": pick["game_id"],
        "gameday": pick["date"],
        "weekday": start.strftime("%A"),
        "start_time_pt": start.strftime("%H:%M"),
        "home_ml": pick.get("home_ml"), "away_ml": pick.get("away_ml"),
        "market_p_home": pick.get("market_p_home"),
        "market_p_away": (round(1 - pick["market_p_home"], 4)
                          if pick.get("market_p_home") is not None else None),
        "p_home_raw": pick["p_home_raw"], "p_home_cal": pick["p_home_cal"],
        "p_away_cal": round(1 - p_home, 4),
        "model_total": pick["model_total"],
        "total_line": pick.get("total_line"),
        "over_price": pick.get("over_price"),
        "under_price": pick.get("under_price"),
        "pick_side": pick_side,
        "pick_label": (f"{home} {fmt_ml(pick.get('home_ml'))}"
                       if pick_side == "home"
                       else f"{away} {fmt_ml(pick.get('away_ml'))}"),
        "pick_prob": round(p_home if pick_side == "home" else 1 - p_home, 4),
        "edge_pp": (round((p_home - pick["market_p_home"]) * 100, 1)
                    if pick.get("market_p_home") is not None else None),
        "market_excluded": excluded,
        "source": "shadow",
        "result": {
            "home_score": grade["home_goals"],
            "away_score": grade["away_goals"],
            "su": "win" if grade["su_correct"] else "loss",
            "model_correct": bool(grade["su_correct"]),
            "brier_raw": grade["brier_raw"],
            "brier_cal": grade["brier_cal"],
            "market_brier": (None if excluded else grade["market_brier"]),
            "total_error": grade["model_total_error"],
        },
    }


def main() -> None:
    picks = load_jsonl(DATA / "shadow" / "picks.jsonl")
    grades = {g["game_id"]: g for g in load_jsonl(DATA / "shadow" / "grades.jsonl")}
    graded_picks = [p for p in picks if p["game_id"] in grades]
    assert len(graded_picks) == CANONICAL["games"], len(graded_picks)

    days: dict[str, dict] = {}
    for p in sorted(graded_picks, key=lambda x: (x["date"], x["start_time_utc"] or "")):
        g = grades[p["game_id"]]
        sp = seed_pick(p, g)
        day = days.setdefault(p["date"], {
            "date": p["date"],
            "generated": datetime.datetime.fromisoformat(
                p["frozen_at"]).astimezone(PT).strftime("%Y-%m-%d %H:%M %Z"),
            "preseason": False, "warming_up": False,
            "experimental_note": None,
            "graded": True, "complete": True,
            "picks": [], "parlay": None,
            "source": "shadow",
            "graded_at": "2026-11-06 06:40 PST",
        })
        day["picks"].append(sp)

    agg = season_aggregate(SEASON, days)
    print("seed aggregate:", json.dumps(agg, indent=2))
    for key in ("paired_games", "games"):
        want = CANONICAL["paired" if key == "paired_games" else "games"]
        assert agg[key] == want, (key, agg[key], want)
    for key in ("brier_raw", "brier_cal", "market_brier"):
        assert abs(agg[key] - CANONICAL[key]) <= 0.0002, (key, agg[key])
    print("canonical checkpoint numbers reproduced ✓")

    log_path = SITE_DATA / f"nhl_season_{SEASON}.json"
    log = {"sport": "nhl", "season": SEASON, "days": {}}
    if log_path.exists():
        existing = json.loads(log_path.read_text())
        for dk, dv in existing.get("days", {}).items():
            if dv.get("source") != "shadow":
                log["days"][dk] = dv  # never clobber live days
    log["days"].update(days)
    log["days"] = dict(sorted(log["days"].items()))
    log_path.write_text(json.dumps(log, indent=2))
    print(f"season log -> {log_path} ({len(days)} shadow days)")

    bs = json.loads((DATA / "backtest_summary.json").read_text())
    me = json.loads((DATA / "market_eval.json").read_text())
    track = {
        "model": MODEL_DESC,
        "backtest": {
            "discovery": {
                "games": bs["discovery"]["games"],
                "brier_cal": bs["discovery"]["brier_cal"],
                "su_pct": bs["discovery"]["su_acc"],
            },
            "validation": {
                "games": bs["validation"]["games"],
                "brier_cal": bs["validation"]["brier_cal"],
                "su_pct": bs["validation"]["su_acc"],
            },
            "market_eval_2025_26": {
                "games": me["games"],
                "model_brier": me["model_brier"],
                "market_brier": me["market_brier"],
                "model_su_pct": me["model_su_acc"],
                "market_su_pct": me["market_su_acc"],
            },
        },
        "shadow_seed": {
            "label": "Pre-launch shadow record",
            "dates": "2026-10-21 – 2026-11-05",
            "games_logged": len(picks),
            "games_graded": len(graded_picks),
            "paired_games": CANONICAL["paired"],
            "brier_raw": CANONICAL["brier_raw"],
            "brier_cal": CANONICAL["brier_cal"],
            "market_brier": CANONICAL["market_brier"],
            "su_pct_ex_invalid": 0.578,
            "su_record_ex_invalid": "63-46",
            "su_pct_all_games": 0.573,
            "note": (
                "Before this section launched, the model ran in shadow "
                "for 16 nights: picks frozen before puck drop, graded "
                "against official finals, nothing published. That frozen "
                "record is the seed of this track record — shown in "
                "full, including the one excluded game below. On the "
                "104 games that froze with a valid market line, model "
                "and market are an effective tie (calibrated Brier "
                "0.2312 vs 0.2304). The model has not beaten the market "
                "and no edge is claimed."),
            "excluded_game": {
                "date": "2026-11-01",
                "game_id": EXCLUDED_GAME_ID,
                "matchup": "Ottawa Senators @ Anaheim Ducks",
                "frozen_home_ml": -1.0,
                "books": 8,
                "market_p_home": 0.018,
                "market_brier": 0.9643,
                "final_score": "Anaheim won 6-3",
                "reason": (
                    "The game froze with an invalid market moneyline: "
                    "-1.0 across all 8 books, a 1.8% implied home win "
                    "chance for a home favorite. That single bad feed "
                    "value would flatter the model in every market "
                    "comparison, so the game is excluded from all of "
                    "them. The frozen shadow record itself is unchanged."),
                "model_line": (
                    "Model-only, counted in full: the model had Anaheim "
                    "at 46.8% raw / 45.2% calibrated — it picked Ottawa, "
                    "and Ottawa lost 6-3. The miss counts in the model's "
                    "own numbers; only the market comparison excludes "
                    "the game."),
            },
        },
        "seasons": [agg],
    }
    track_path = SITE_DATA / "nhl_track_record.json"
    track_path.write_text(json.dumps(track, indent=2))
    print(f"track record -> {track_path}")


if __name__ == "__main__":
    main()
