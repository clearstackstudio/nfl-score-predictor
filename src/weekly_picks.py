"""Weekly picks generator: current team ratings -> this week's games.

Reads nflverse play-by-play (all completed games), builds opponent-adjusted
EPA ratings exactly like the backtest, then predicts the upcoming week's
games: our spread, our total, edge vs the market line, and cover
probabilities. Output: site/data/picks.json for the website.

The market line comes from the nflverse schedule (spread_line/total_line).
Our numbers never use the line as an input.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd

from epa_ratings import (
    ABBR_TO_FULL, HOME_EDGE_PTS, PLAYS_PER_GAME, REPO, adjusted_ratings,
    load_team_games,
)

DATA = REPO / "data"
SEASON = 2026


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


MARGIN_SD = 13.5  # typical NFL std of (actual margin - predicted margin)


def current_ratings(team_games: pd.DataFrame, season: int):
    """Ratings using every completed game, with prior-season carryover."""
    end_prev = len(team_games[team_games["season"] < season])
    if end_prev:
        off_p, def_p = adjusted_ratings(team_games, end_prev, season - 1, {})
        prior = {t: (0.5 * off_p[t], 0.5 * def_p[t]) for t in off_p}
    else:
        prior = {}
    return adjusted_ratings(team_games, len(team_games), season, prior)


def main() -> None:
    team_games = load_team_games([2021, 2022, 2023, 2024, 2025, 2026])
    off, deff = current_ratings(team_games, SEASON)

    sched = pd.read_parquet(DATA / "schedules_games.parquet")
    played_weeks = sorted(
        team_games[team_games["season"] == SEASON]["week"].unique())
    next_week = max(played_weeks) + 1
    upcoming = sched[(sched["season"] == SEASON)
                     & (sched["week"] == next_week)].copy()
    upcoming = upcoming[upcoming["spread_line"].notna()]

    # EPA->points constant: combined offensive EPA/game ≈ 0, so the constant
    # is just the trailing average total. Calibrate on completed games.
    done = team_games[team_games["season"] == SEASON]
    per_game_epa = done.groupby("game_id")["off_epa"].sum()
    sched_done = sched[(sched["season"] == SEASON) & sched["home_score"].notna()]
    avg_total = (sched_done["home_score"] + sched_done["away_score"]).mean()
    epa_const = float(avg_total - per_game_epa.mean())

    picks = []
    for _, g in upcoming.sort_values("gameday").iterrows():
        home, away = g["home_team"], g["away_team"]
        if home not in off or away not in off:
            continue
        exp_home_off = off[home] + deff[away]
        exp_away_off = off[away] + deff[home]
        # All spreads expressed as HOME MARGIN: positive = home favored.
        # (nflverse spread_line already uses this convention.)
        our_margin = (exp_home_off - exp_away_off) * PLAYS_PER_GAME + HOME_EDGE_PTS
        line_margin = float(g["spread_line"])
        our_total = (exp_home_off + exp_away_off) * PLAYS_PER_GAME + epa_const
        line_total = float(g["total_line"])

        spread_edge = our_margin - line_margin   # >0: we like home more than line
        total_edge = our_total - line_total      # >0: we like over more than line

        pick_side = ("home" if spread_edge > 0 else "away") if abs(spread_edge) >= 0.5 else None
        pick_total = ("over" if total_edge > 0 else "under") if abs(total_edge) >= 1.0 else None
        # P(our picked side covers) = Phi(|edge| / sd): how far our number sits
        # from the line, in units of typical game noise.
        cover_prob = normal_cdf(abs(spread_edge) / MARGIN_SD)
        ou_prob = normal_cdf(abs(total_edge) / MARGIN_SD)

        picks.append({
            "away": ABBR_TO_FULL.get(away, away),
            "home": ABBR_TO_FULL.get(home, home),
            "away_abbr": away, "home_abbr": home,
            "gameday": str(g["gameday"]),
            "weekday": g["weekday"],
            # home-margin convention: positive = home favored
            "line_spread": round(line_margin, 1),
            "line_total": line_total,
            "our_spread": round(our_margin, 1),
            "our_total": round(our_total, 1),
            "spread_edge": round(spread_edge, 1),
            "total_edge": round(total_edge, 1),
            "pick_spread": pick_side,
            "pick_total": pick_total,
            "cover_prob": round(cover_prob, 3) if pick_side else None,
            "ou_prob": round(ou_prob, 3) if pick_total else None,
            "home_qb": g.get("home_qb_name"), "away_qb": g.get("away_qb_name"),
        })

    out = {
        "season": SEASON, "week": int(next_week),
        "generated": pd.Timestamp.now("America/Los_Angeles").strftime("%Y-%m-%d %H:%M %Z"),
        "disclaimer": ("Model probabilities for entertainment. Our backtest shows "
                       "no edge vs the closing line — track record published openly."),
        "picks": picks,
    }
    dest = REPO / "site" / "data" / "picks.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"Week {next_week}: {len(picks)} games -> {dest}")
    for p in picks:
        s = (f"{p['away_abbr']} @ {p['home_abbr']}: line {p['line_spread']:+} / {p['line_total']}, "
             f"ours {p['our_spread']:+} / {p['our_total']:.0f}")
        if p["pick_spread"]:
            s += f"  PICK {p['pick_spread']} {p['cover_prob']:.0%}"
        print(s)


if __name__ == "__main__":
    main()
