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
    load_qb_plays, load_team_games, qb_adjustments,
)
from weather import (fetch_kickoff_winds, indoor_total_adjustment,
                     wind_total_adjustment)

DATA = REPO / "data"
SEASON = 2026


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


MARGIN_SD = 14.5  # backtest RMSE of (actual margin - our margin), 2021-2024
TOTAL_SD = 15.4   # backtest RMSE of (actual total - our total), 2021-2024
TOTAL_CIRCUIT = 7.0  # |total_edge| beyond this is more likely model error than
                     # edge (Thursday's 11.1pt miss); skip the pick instead of
                     # publishing false confidence.


def pick_spread_label(pick_side: str | None, line_margin: float,
                      home_abbr: str, away_abbr: str) -> str | None:
    """Display label from the PICKED team's perspective.

    The bug this prevents: pairing the favorite-centric number with the
    underdog's abbreviation ("NE -6.5" when the line is Bills -6.5).
    Correct output names the picked team with their own number ("NE +6.5").
    """
    if not pick_side:
        return None
    team = home_abbr if pick_side == "home" else away_abbr
    margin = line_margin if pick_side == "home" else -line_margin
    if abs(margin) < 0.05:
        return "Pick'em"
    return f"{team} -{margin:g}" if margin > 0 else f"{team} +{-margin:g}"


def pick_total_label(pick_total: str | None, line_total: float) -> str | None:
    if not pick_total:
        return None
    return f"{'Over' if pick_total == 'over' else 'Under'} {line_total:g}"


def fair_american(p: float) -> str:
    """American odds for a true probability p."""
    if p > 0.5:
        return f"-{round(100 * p / (1 - p))}"
    if p < 0.5:
        return f"+{round(100 * (1 - p) / p)}"
    return "+100"


# What US books typically pay on a standard parlay (varies by book).
BOOK_PARLAY_PAYS = {2: "+260", 3: "+600"}


def _norm_qb_name(nm: str) -> str:
    nm = nm.lower().replace(".", "")
    for suf in (" jr", " sr", " ii", " iii", " iv", " v"):
        if nm.endswith(suf):
            nm = nm[: -len(suf)]
    return nm.strip()


def load_qb_overrides(season: int, week: int) -> dict:
    """Manual starter overrides for mid-week QB news.

    data/qb_overrides.json: {"season": 2026, "week": 5,
                             "starters": {"PIT": "Aaron Rodgers"}}.
    Returns {team_abbr: qb_gsis_id}. Empty when the file is absent or stale.
    """
    p = DATA / "qb_overrides.json"
    if not p.exists():
        return {}
    cfg = json.loads(p.read_text())
    if cfg.get("season") != season or cfg.get("week") != week:
        print(f"qb_overrides: stale (for {cfg.get('season')} W{cfg.get('week')}), ignoring")
        return {}
    sched = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["home_qb_name", "home_qb_id", "away_qb_name", "away_qb_id"])
    name_to_id: dict[str, str] = {}
    for r in sched.itertuples():
        for nm, i in ((r.home_qb_name, r.home_qb_id),
                      (r.away_qb_name, r.away_qb_id)):
            if nm and i == i:
                name_to_id[_norm_qb_name(nm)] = str(i)
    out = {}
    for team, name in cfg.get("starters", {}).items():
        qid = name_to_id.get(_norm_qb_name(name))
        if qid:
            out[team] = qid
        else:
            print(f"qb_overrides: no GSIS id for {name!r}, skipping")
    return out


def current_ratings(team_games: pd.DataFrame, season: int):
    """Ratings using every completed game, with prior-season carryover."""
    end_prev = len(team_games[team_games["season"] < season])
    if end_prev:
        off_p, def_p, _ = adjusted_ratings(team_games, end_prev, season - 1, {})
        prior = {t: (0.5 * off_p[t], 0.5 * def_p[t]) for t in off_p}
    else:
        prior = {}
    return adjusted_ratings(team_games, len(team_games), season, prior)


def build_parlay(picks: list[dict]) -> dict | None:
    """Parlay of the week: the 3 highest-probability picks (spread or total).

    Entertainment only — legs are roughly independent (different games), so
    the combined probability is the product. Our model's probabilities are
    unproven (see track record), so the 'fair odds' below are the model's
    view, not a promise.
    """
    legs = []
    for p in picks:
        game = f"{p['away_abbr']} @ {p['home_abbr']}"
        if p["pick_spread"]:
            legs.append({
                "game": game,
                "away_abbr": p["away_abbr"], "home_abbr": p["home_abbr"],
                "market": "spread",
                "label": p["pick_spread_label"],
                "prob": p["cover_prob"],
            })
        if p["pick_total"]:
            legs.append({
                "game": game,
                "away_abbr": p["away_abbr"], "home_abbr": p["home_abbr"],
                "market": "total",
                "label": p["pick_total_label"],
                "prob": p["ou_prob"],
            })
    legs.sort(key=lambda l: -l["prob"])
    legs = legs[:3]
    if len(legs) < 2:
        return None
    combined = 1.0
    for l in legs:
        combined *= l["prob"]
    combined = round(combined, 3)  # round once; fair odds derive from this exact value
    return {
        "legs": legs,
        "combined_prob": combined,
        "fair_odds": fair_american(combined),
        "book_pays": BOOK_PARLAY_PAYS[len(legs)],
    }


def validate_picks(picks: list[dict], parlay: dict | None) -> None:
    """Recompute every display label and consistency rule from raw fields.

    Raises AssertionError on any mismatch. Called BEFORE picks.json is
    written, so a labeling bug can never reach the website — the previous
    week's file stays live instead.
    """
    for p in picks:
        # Labels must match a fresh recomputation (catches team/number mixups).
        assert p["pick_spread_label"] == pick_spread_label(
            p["pick_spread"], p["line_spread"], p["home_abbr"], p["away_abbr"]
        ), f"label mismatch: {p['away_abbr']} @ {p['home_abbr']}"
        assert p["pick_total_label"] == pick_total_label(
            p["pick_total"], p["line_total"]
        ), f"total label mismatch: {p['away_abbr']} @ {p['home_abbr']}"

        # The label must name the picked team, never the opponent.
        if p["pick_spread"]:
            team = p["home_abbr"] if p["pick_spread"] == "home" else p["away_abbr"]
            assert p["pick_spread_label"].startswith(team + " ") or \
                p["pick_spread_label"] == "Pick'em", \
                f"label names wrong team: {p['pick_spread_label']}"

        # Both sides' spread labels (used by the pick'em UI) must also check out.
        assert p["spread_labels"]["home"] == pick_spread_label(
            "home", p["line_spread"], p["home_abbr"], p["away_abbr"])
        assert p["spread_labels"]["away"] == pick_spread_label(
            "away", p["line_spread"], p["home_abbr"], p["away_abbr"])
        assert p["spread_labels"]["home"].startswith(p["home_abbr"] + " ") or \
            p["spread_labels"]["home"] == "Pick'em"
        assert p["spread_labels"]["away"].startswith(p["away_abbr"] + " ") or \
            p["spread_labels"]["away"] == "Pick'em"

        # Pick side must agree with the direction of the edge, and picks
        # only exist past the minimum edge thresholds.
        se, te = p["spread_edge"], p["total_edge"]
        if p["pick_spread"]:
            assert abs(se) >= 0.5, "spread pick below 0.5pt threshold"
            assert (se > 0) == (p["pick_spread"] == "home"), "spread pick wrong side"
            assert p["cover_prob"] is not None and 0.5 < p["cover_prob"] <= 1.0
        else:
            assert abs(se) < 0.5 and p["cover_prob"] is None
        if p["pick_total"]:
            assert abs(te) >= 1.0, "total pick below 1pt threshold"
            assert (te > 0) == (p["pick_total"] == "over"), "total pick wrong side"
            assert p["ou_prob"] is not None and 0.5 < p["ou_prob"] <= 1.0
            assert not p.get("pick_total_note"), "picked total should not carry a skip note"
        else:
            assert p["ou_prob"] is None
            if p.get("pick_total_note"):
                # circuit breaker: extreme disagreement, skipped deliberately
                assert abs(te) > TOTAL_CIRCUIT, "skip note without extreme edge"
            else:
                assert abs(te) < 1.0, "missing total pick without reason"

    if parlay:
        assert 2 <= len(parlay["legs"]) <= 3, "parlay must have 2-3 legs"
        by_game = {(p["home_abbr"], p["away_abbr"]): p for p in picks}
        prod = 1.0
        for leg in parlay["legs"]:
            p = by_game[(leg["home_abbr"], leg["away_abbr"])]
            key = "pick_spread_label" if leg["market"] == "spread" else "pick_total_label"
            assert leg["label"] == p[key], f"parlay leg label wrong: {leg}"
            probkey = "cover_prob" if leg["market"] == "spread" else "ou_prob"
            assert leg["prob"] == p[probkey] and leg["prob"] is not None
            prod *= leg["prob"]
        assert abs(prod - parlay["combined_prob"]) < 0.002, "parlay combined prob wrong"
        assert parlay["fair_odds"] == fair_american(parlay["combined_prob"])
        assert parlay["book_pays"] == BOOK_PARLAY_PAYS[len(parlay["legs"])]


def main() -> None:
    team_games = load_team_games([2021, 2022, 2023, 2024, 2025, 2026])
    off, deff, pace = current_ratings(team_games, SEASON)
    qb_plays = load_qb_plays([2021, 2022, 2023, 2024, 2025, 2026])

    sched = pd.read_parquet(DATA / "schedules_games.parquet")
    played_weeks = sorted(
        team_games[team_games["season"] == SEASON]["week"].unique())
    next_week = max(played_weeks) + 1
    upcoming = sched[(sched["season"] == SEASON)
                     & (sched["week"] == next_week)].copy()
    upcoming = upcoming[upcoming["spread_line"].notna()]

    # QB adjustments: schedule QBs, with manual overrides for mid-week news.
    qb_over = load_qb_overrides(SEASON, next_week)
    matchups = []
    for _, g in upcoming.sort_values("gameday").iterrows():
        hq = qb_over.get(g["home_team"])
        if not hq and pd.notna(g["home_qb_id"]):
            hq = str(g["home_qb_id"])
        aq = qb_over.get(g["away_team"])
        if not aq and pd.notna(g["away_qb_id"]):
            aq = str(g["away_qb_id"])
        matchups.append((g["home_team"], g["away_team"], hq, aq))
    qadj = qb_adjustments(qb_plays, team_games, len(team_games), SEASON, matchups)

    # EPA->points constant: combined offensive EPA/game ≈ 0, so the constant
    # is just the trailing average total. Calibrate on completed games.
    done = team_games[team_games["season"] == SEASON]
    per_game_epa = done.groupby("game_id")["off_epa"].sum()
    sched_done = sched[(sched["season"] == SEASON) & sched["home_score"].notna()]
    avg_total = (sched_done["home_score"] + sched_done["away_score"]).mean()
    epa_const = float(avg_total - per_game_epa.mean())

    picks = []
    # Wind: forecast at kickoff per outdoor stadium (one API call per
    # stadium-date; failures -> None -> no adjustment, never a crash).
    wx_games = [{"home_team": g["home_team"], "gameday": str(g["gameday"]),
                 "gametime": str(g.get("gametime") or "13:00")}
                for _, g in upcoming.iterrows()]
    kickoff_winds = fetch_kickoff_winds(wx_games)
    for _, g in upcoming.sort_values("gameday").iterrows():
        home, away = g["home_team"], g["away_team"]
        if home not in off or away not in off:
            continue
        exp_home_off = off[home] + deff[away] + qadj.get(home, 0.0)
        exp_away_off = off[away] + deff[home] + qadj.get(away, 0.0)
        # Expected pace: average of the two teams' trailing plays/game.
        # Totals = efficiency x pace, not efficiency x a league constant.
        exp_plays = (pace.get(home, PLAYS_PER_GAME)
                     + pace.get(away, PLAYS_PER_GAME)) / 2
        # All spreads expressed as HOME MARGIN: positive = home favored.
        # (nflverse spread_line already uses this convention.)
        our_margin = (exp_home_off - exp_away_off) * exp_plays + HOME_EDGE_PTS
        line_margin = float(g["spread_line"])
        our_total = (exp_home_off + exp_away_off) * exp_plays + epa_const
        # Wind adjustment (outdoor stadiums only): high wind suppresses
        # scoring ~1 pt per mph above 10, capped at -8. Calibrated on
        # 2021-2024 walk-forward totals; uses forecast wind at kickoff.
        wind_mph = kickoff_winds.get((home, str(g["gameday"])))
        wind_adj = wind_total_adjustment(wind_mph, home)
        our_total += wind_adj
        # Indoor adjustment: domes / retractable roofs play ~3 pts higher
        # than the model expects (perfect conditions, fast track).
        # Calibrated 2026-10-02 on 2021-2024 walk-forward totals.
        indoor_adj = indoor_total_adjustment(home)
        our_total += indoor_adj
        line_total = float(g["total_line"])

        spread_edge = our_margin - line_margin   # >0: we like home more than line
        total_edge = our_total - line_total      # >0: we like over more than line

        pick_side = ("home" if spread_edge > 0 else "away") if abs(spread_edge) >= 0.5 else None
        pick_total = ("over" if total_edge > 0 else "under") if abs(total_edge) >= 1.0 else None
        pick_total_note = None
        if pick_total and abs(total_edge) > TOTAL_CIRCUIT:
            # Extreme disagreement with an efficient market is more likely
            # our error than our edge — skip instead of publishing
            # false confidence.
            pick_total = None
            pick_total_note = ("No play — our number is too far from the "
                               "market to trust.")
        # P(our picked side covers) = Phi(|edge| / sd): how far our number sits
        # from the line, in units of typical game noise. Totals use their own
        # calibrated noise (TOTAL_SD), not the margin's.
        cover_prob = normal_cdf(abs(spread_edge) / MARGIN_SD)
        ou_prob = normal_cdf(abs(total_edge) / TOTAL_SD)

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
            "qb_adj_home": round(qadj.get(home, 0.0) * exp_plays, 1),
            "qb_adj_away": round(qadj.get(away, 0.0) * exp_plays, 1),
            "wind_mph": round(wind_mph) if wind_mph is not None else None,
            "wind_adj_pts": round(wind_adj, 1),
            "indoor_adj_pts": round(indoor_adj, 1),
            "pick_spread": pick_side,
            "pick_total": pick_total,
            "pick_total_note": pick_total_note,
            "pick_spread_label": pick_spread_label(pick_side, line_margin, home, away),
            "pick_total_label": pick_total_label(pick_total, line_total),
            # Both sides' spread text, generator-owned, for the pick'em UI.
            "spread_labels": {
                "home": pick_spread_label("home", line_margin, home, away),
                "away": pick_spread_label("away", line_margin, home, away),
            },
            "cover_prob": round(cover_prob, 3) if pick_side else None,
            "ou_prob": round(ou_prob, 3) if pick_total else None,
            "home_qb": g.get("home_qb_name"), "away_qb": g.get("away_qb_name"),
        })

    parlay = build_parlay(picks)
    validate_picks(picks, parlay)  # fail loudly BEFORE publishing, never after
    out = {
        "season": SEASON, "week": int(next_week),
        "generated": pd.Timestamp.now("America/Los_Angeles").strftime("%Y-%m-%d %H:%M %Z"),
        "disclaimer": ("Model probabilities for entertainment. Our backtest shows "
                       "no edge vs the closing line — track record published openly."),
        "parlay": parlay,
        "picks": picks,
    }
    dest = REPO / "site" / "data" / "picks.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"Week {next_week}: {len(picks)} games -> {dest}")
    if out["parlay"]:
        print("Parlay of the week:")
        for l in out["parlay"]["legs"]:
            print(f"  {l['label']} ({l['game']}) {l['prob']:.0%}")
        pl = out["parlay"]
        print(f"  combined {pl['combined_prob']:.1%} · fair {pl['fair_odds']} · book pays {pl['book_pays']}")
    for p in picks:
        s = (f"{p['away_abbr']} @ {p['home_abbr']}: line {p['line_spread']:+} / {p['line_total']}, "
             f"ours {p['our_spread']:+} / {p['our_total']:.0f}")
        if p["pick_spread"]:
            s += f"  PICK {p['pick_spread']} {p['cover_prob']:.0%}"
        print(s)


if __name__ == "__main__":
    main()
