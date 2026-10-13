"""Step 3: re-run the published walk-forward backtest, saving per-game residuals.

Reuses src/backtest.load_games, closing_home_spread and src ratings.EloRatings
verbatim — the pipeline is reused, not rebuilt.

Fidelity gate (pre-registered): the re-run must reproduce the published
figures (52.1% ATS, model RMSE 13.67 vs line 13.32) within rounding before any
coach join is trusted.

Output: residuals.csv — one row per game with model/actual/line margins
(home-team perspective) plus season/week/date/teams for the coach join.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "src"))

from backtest import PICK_THRESHOLD, closing_home_spread, load_games  # noqa: E402
from ratings import EloRatings  # noqa: E402

OUT = Path(__file__).resolve().parent
CSV = OUT / "residuals.csv"


def main() -> None:
    games = load_games()
    print("columns:", list(games.columns))
    print("seasons:", int(games["schedule_season"].min()), "-", int(games["schedule_season"].max()))

    elo = EloRatings()
    rows = []
    n = ats_w = ats_l = ats_p = 0
    su_w = 0
    our_se = line_se = 0.0
    for _, row in games.iterrows():
        home, away = row["team_home"], row["team_away"]
        neutral = bool(row["stadium_neutral"])
        season = int(row["schedule_season"])

        our_margin = elo.game_prediction(home, away, neutral)  # home perspective
        actual_margin = float(row["score_home"]) - float(row["score_away"])
        line_margin = closing_home_spread(row)

        su_w += (our_margin > 0) == (actual_margin > 0)
        our_se += (our_margin - actual_margin) ** 2
        line_se += (line_margin - actual_margin) ** 2
        edge = our_margin - line_margin
        ats_pick = ""
        if abs(edge) >= PICK_THRESHOLD:
            picked_home = edge > 0
            result = actual_margin - line_margin
            if abs(result) < 0.01:
                ats_p += 1
                ats_pick = "push"
            elif (result > 0) == picked_home:
                ats_w += 1
                ats_pick = "win"
            else:
                ats_l += 1
                ats_pick = "loss"
        n += 1
        rows.append(
            {
                "season": season,
                "week": row.get("schedule_week"),
                "date": str(row["schedule_date"])[:10],
                "team_home": home,
                "team_away": away,
                "neutral": int(neutral),
                "our_margin": our_margin,      # home perspective
                "actual_margin": actual_margin,
                "line_margin": line_margin,
                "ats_pick": ats_pick,          # win/loss/push/"" ("" = no pick)
                "picked_home": int(edge > 0) if abs(edge) >= PICK_THRESHOLD else -1,
            }
        )
        elo.record_game(home, away, actual_margin, season, neutral)

    decided = ats_w + ats_l
    our_rmse = math.sqrt(our_se / n)
    line_rmse = math.sqrt(line_se / n)
    ats_pct = ats_w / decided
    print(f"Games: {n:,}")
    print(f"Our RMSE: {our_rmse:.2f} (published 13.67)")
    print(f"Line RMSE: {line_rmse:.2f} (published 13.32)")
    print(f"ATS: {ats_w}-{ats_l}-{ats_p} = {ats_pct:.1%} (published 52.1%)")

    ok = (
        abs(our_rmse - 13.67) < 0.005
        and abs(line_rmse - 13.32) < 0.005
        and abs(ats_pct - 0.521) < 0.0005
    )
    print("FIDELITY GATE:", "PASS" if ok else "FAIL")
    if not ok:
        raise SystemExit("fidelity gate failed — do not proceed to coach join")

    pd.DataFrame(rows).to_csv(CSV, index=False)
    print(f"wrote {CSV}")


if __name__ == "__main__":
    main()
