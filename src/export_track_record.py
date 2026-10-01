"""Export the Elo walk-forward backtest as per-season track record JSON.

This is the transparency backbone of the site: every season's real
backtested numbers, no cherry-picking. Regenerate with:
    python3 export_track_record.py
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from backtest import load_games, closing_home_spread, PICK_THRESHOLD
from ratings import EloRatings

REPO = Path(__file__).resolve().parent.parent


def main() -> None:
    games = load_games()
    elo = EloRatings()
    seasons: dict[int, dict] = {}

    for _, row in games.iterrows():
        season = int(row["schedule_season"])
        s = seasons.setdefault(season, {
            "games": 0, "su": 0, "our_se": 0.0, "line_se": 0.0,
            "w": 0, "l": 0, "p": 0,
        })
        home, away = row["team_home"], row["team_away"]
        neutral = bool(row["stadium_neutral"])
        our = elo.game_prediction(home, away, neutral)
        actual = float(row["score_home"]) - float(row["score_away"])
        line = closing_home_spread(row)

        s["games"] += 1
        s["su"] += (our > 0) == (actual > 0)
        s["our_se"] += (our - actual) ** 2
        s["line_se"] += (line - actual) ** 2
        e = our - line
        if abs(e) >= PICK_THRESHOLD:
            r = actual - line
            if abs(r) < 0.01:
                s["p"] += 1
            elif (r > 0) == (e > 0):
                s["w"] += 1
            else:
                s["l"] += 1
        elo.record_game(home, away, actual, season, neutral)

    out = []
    for season in sorted(seasons):
        s = seasons[season]
        n = s["games"]
        decided = s["w"] + s["l"]
        out.append({
            "season": season,
            "games": n,
            "straight_up_pct": round(s["su"] / n, 4),
            "our_rmse": round(math.sqrt(s["our_se"] / n), 2),
            "line_rmse": round(math.sqrt(s["line_se"] / n), 2),
            "ats_w": s["w"], "ats_l": s["l"], "ats_p": s["p"],
            "ats_pct": round(s["w"] / decided, 4) if decided else None,
        })
    dest = REPO / "site" / "data" / "track_record.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({
        "model": "Margin-adjusted Elo, fundamentals only (final scores; the line is never an input). Walk-forward: every prediction made before learning the result.",
        "seasons": out,
    }, indent=2))
    print(f"{len(out)} seasons -> {dest}")


if __name__ == "__main__":
    main()
