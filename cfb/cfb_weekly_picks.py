"""Weekly CFB picks: current PPA ratings -> this week's games.

Builds opponent-adjusted PPA ratings from all completed games (exactly
like the backtest), pulls the upcoming week's schedule + closing lines
live from the CFBD API, and writes site/data/cfb_picks.json.

The market line is never an input — only the benchmark.
"""
from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
from cfb_ratings import (CARRYOVER, HOME_EDGE_PTS, PLAYS_PER_GAME, REPO,
                         adjusted_ratings, load_team_games, predict)
from recalibration import recalibrate, CALIBRATION_VERSION

DATA = REPO / "data" / "cfb"
SEASON = 2026


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_american(p: float) -> str:
    if p > 0.5:
        return f"-{round(100 * p / (1 - p))}"
    if p < 0.5:
        return f"+{round(100 * (1 - p) / p)}"
    return "+100"


BOOK_PARLAY_PAYS = {2: "+260", 3: "+600"}

# Total circuit breaker (same idea as the NFL model): if our total is more
# than this many points from the market total, publish no total pick. An
# extreme disagreement is more likely our model being wrong than the market
# being wrong. Scaled from the NFL's 7.0 by the backtest total residual SD
# (18.71 vs 15.4).
TOTAL_CIRCUIT = 8.5


def _gameday_et(start: str) -> dict:
    """Map CFBD's UTC startDate to the US-Eastern calendar date + weekday.

    Without this, Thursday 8pm CT kickoffs (Friday 01:00 UTC) display as
    Friday. Eastern covers the continental-US viewing audience; Hawai'i
    home games are the known edge case.
    """
    try:
        dt = pd.Timestamp(start)
        if dt.tzinfo is None:
            dt = dt.tz_localize("UTC")
        et = dt.tz_convert("America/New_York")
        return {"gameday": et.strftime("%Y-%m-%d"),
                "weekday": et.strftime("%A")}
    except Exception:
        return {"gameday": str(start)[:10], "weekday": ""}


def pick_spread_label(pick_side, line_margin, home, away):
    if not pick_side:
        return None
    team = home if pick_side == "home" else away
    margin = line_margin if pick_side == "home" else -line_margin
    if abs(margin) < 0.05:
        return "Pick'em"
    return f"{team} -{margin:g}" if margin > 0 else f"{team} +{-margin:g}"


def pick_total_label(pick_total, line_total):
    if not pick_total:
        return None
    return f"{'Over' if pick_total == 'over' else 'Under'} {line_total:g}"


def current_ratings(team_games: pd.DataFrame, season: int):
    end_prev = len(team_games[team_games["season"] < season])
    if end_prev:
        off_p, def_p, _ = adjusted_ratings(team_games, end_prev, season - 1, {})
        prior = {t: (CARRYOVER * off_p[t], CARRYOVER * def_p[t]) for t in off_p}
    else:
        prior = {}
    return adjusted_ratings(team_games, len(team_games), season, prior)


# Verified 2026-10-01 against completed CFBD games: the raw /lines spread
# is an AWAY margin (spread > 0 means the away team is favored). Negate to
# get a home margin (positive = home favored), matching the convention used
# in fetch_cfb.py ingestion, the backtest, grading, and the site.
RAW_SPREAD_SIGN = -1.0


def verify_spread_convention() -> None:
    """Loud sanity check: stored line_spread must correlate positively with
    actual home margin. Raises if CFBD ever changes its convention, so we
    fail visibly instead of silently flipping every pick."""
    import numpy as np
    g = pd.read_parquet(DATA / "cfb_games.parquet")
    g = g.dropna(subset=["line_spread", "home_score", "away_score"]).head(2000)
    if len(g) < 50:
        print("spread check skipped: not enough graded games yet")
        return
    m = (g["home_score"] - g["away_score"]).to_numpy()
    s = g["line_spread"].to_numpy()
    corr = float(np.corrcoef(s, m)[0, 1])
    print(f"spread convention check: corr(line_spread, home margin)={corr:+.2f}")
    if corr < 0.5:
        raise RuntimeError(
            f"spread convention broken (corr={corr:+.2f}); CFBD may have "
            "changed its spread sign. Refusing to generate picks.")


def fetch_upcoming_week(season: int):
    """Week with the next unplayed games: schedule + lines, live from the API.

    The latest week with completed games is usually still in progress
    (midweek games go final days before Saturday), so only advance past it
    when every game in it is final. Advancing blindly on max(played)+1
    skipped an entire Saturday slate on 2026-10-08 after 3 Wednesday
    games went final.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_cfb import get_client
    import cfbd
    from cfbd.api import games_api, betting_api
    client = get_client()
    ga, ba = games_api.GamesApi(client), betting_api.BettingApi(client)

    def week_games(week):
        out = []
        for st in ("regular", "postseason"):
            try:
                for x in ga.get_games(year=season, week=week, season_type=st,
                                      classification="fbs"):
                    out.append(x.to_dict())
            except Exception as e:
                print(f"  games w{week} {st}: {e}")
        return out

    team_games = load_team_games()
    played = team_games[team_games["season"] == season]["week"].unique()
    latest = int(max(played)) if len(played) else 1
    probe = week_games(latest)
    if any(not g.get("completed") for g in probe):
        next_week = latest
    else:
        next_week = latest + 1
    print(f"next week: {next_week} (latest week with finals: {latest})")

    sched = probe if next_week == latest else week_games(next_week)
    lines = {}
    for st in ("regular", "postseason"):
        try:
            for l in ba.get_lines(year=season, week=next_week, season_type=st):
                d = l.to_dict()
                lines[d["id"]] = d
        except Exception as e:
            print(f"  lines w{next_week} {st}: {e}")
    return next_week, sched, lines


def main() -> None:
    team_games = load_team_games()
    off, deff, pace = current_ratings(team_games, SEASON)
    verify_spread_convention()
    sign = RAW_SPREAD_SIGN

    try:
        cfg = json.loads((DATA / "cfb_backtest.json").read_text())
        margin_sd = cfg["margin_sd"]
        total_sd = cfg.get("total_sd", 12.0)
    except FileNotFoundError:
        margin_sd, total_sd = 16.5, 12.0
        print("no backtest calibration found; using default SDs")

    next_week, sched, lines = fetch_upcoming_week(SEASON)

    done = pd.read_parquet(DATA / "cfb_games.parquet")
    done = done[(done["season"] == SEASON) & done["home_score"].notna()]
    epa_const = float((done["home_score"] + done["away_score"]).mean()) \
        if len(done) else 58.0

    import statistics
    picks = []
    for g in sched:
        if g.get("completed"):
            continue
        if g.get("homeClassification") != "fbs" or g.get("awayClassification") != "fbs":
            continue
        home, away = g["homeTeam"], g["awayTeam"]
        ln = lines.get(g["id"], {}).get("lines", []) or []
        spreads = [float(x["spread"]) for x in ln if x.get("spread") is not None]
        totals = [float(x["overUnder"]) for x in ln if x.get("overUnder") is not None]
        if not spreads or not totals:
            continue
        line_margin = sign * statistics.median(spreads)
        line_total = statistics.median(totals)
        pr = predict(off, deff, pace, home, away, bool(g.get("neutralSite")), epa_const)
        if pr is None:
            continue
        our_margin, our_total = pr
        spread_edge = our_margin - line_margin
        total_edge = our_total - line_total
        pick_side = ("home" if spread_edge > 0 else "away") \
            if abs(spread_edge) >= 0.5 else None
        pick_total = ("over" if total_edge > 0 else "under") \
            if abs(total_edge) >= 1.0 else None
        # Raw Phi(|edge|/sd) probabilities are systematically overconfident
        # (2026-10-09 calibration check) -- the empirical curve makes the
        # published number mean what it says. Picks (threshold-based) are
        # unchanged; only the displayed probability is recalibrated.
        cover_prob = recalibrate(normal_cdf(abs(spread_edge) / margin_sd),
                                 "cfb", "ats")
        ou_prob = recalibrate(normal_cdf(abs(total_edge) / total_sd),
                              "cfb", "totals")

        # Total circuit breaker: extreme disagreement with the market is a
        # model-error signal, not an edge. Suppress the pick but still show
        # both numbers so the disagreement is visible.
        total_note = None
        if pick_total and abs(total_edge) > TOTAL_CIRCUIT:
            pick_total = None
            ou_prob = None
            total_note = ("No play — our total is too far from the market "
                          "to trust.")
        picks.append({
            "away": away, "home": home,
            "away_abbr": away, "home_abbr": home,
            # CFBD startDate is UTC; Thursday-night games would otherwise
            # display as Friday. Convert to US Eastern for the date shown.
            **_gameday_et(g.get("startDate", "")),
            "neutral": bool(g.get("neutralSite")),
            "line_spread": round(line_margin, 1),
            "line_total": line_total,
            "our_spread": round(our_margin, 1),
            "our_total": round(our_total, 1),
            "spread_edge": round(spread_edge, 1),
            "total_edge": round(total_edge, 1),
            "pick_spread": pick_side,
            "pick_total": pick_total,
            "pick_spread_label": pick_spread_label(pick_side, line_margin, home, away),
            "pick_total_label": pick_total_label(pick_total, line_total),
            "pick_total_note": total_note,
            "spread_labels": {
                "home": pick_spread_label("home", line_margin, home, away),
                "away": pick_spread_label("away", line_margin, home, away),
            },
            "cover_prob": round(cover_prob, 3) if pick_side else None,
            "ou_prob": round(ou_prob, 3) if pick_total else None,
        })

    # Graded carry-over + parlay lock: the nightly merge writes finals into
    # cfb_picks.json, but this script regenerates only upcoming games. A
    # mid-week re-run must not wipe the week's graded badges — and the
    # published parlay is a public record, so re-runs keep it exactly as
    # published instead of silently swapping legs as lines move.
    old_doc = {}
    try:
        old_doc = json.loads((REPO / "site" / "data" / "cfb_picks.json").read_text())
    except Exception:
        pass
    same_week = (old_doc.get("sport") == "cfb"
                 and old_doc.get("season") == SEASON
                 and old_doc.get("week") == next_week)
    if same_week:
        have = {(p["away"], p["home"]) for p in picks}
        for op in old_doc.get("picks", []):
            if op.get("result") and (op["away"], op["home"]) not in have:
                picks.append(op)  # already final: keep published pick + grade

    # Methodology-aware parlay lock: a calibration change rebuilds the parlay
    # once so the site never displays probabilities from a superseded formula.
    if (same_week and old_doc.get("parlay")
            and old_doc["parlay"].get("calibration") == CALIBRATION_VERSION):
        parlay = old_doc["parlay"]
        print("Parlay locked at first publish — carrying over.")
    else:
        # Parlay of the week: 3 highest-probability legs.
        legs = []
        for p in picks:
            if p.get("result"):
                continue  # already final: never a live parlay leg
            game = f"{p['away']} @ {p['home']}"
            if p["pick_spread"]:
                legs.append({"game": game, "market": "spread",
                             "label": p["pick_spread_label"], "prob": p["cover_prob"]})
            if p["pick_total"]:
                legs.append({"game": game, "market": "total",
                             "label": p["pick_total_label"], "prob": p["ou_prob"]})
        legs.sort(key=lambda l: -l["prob"])
        legs = legs[:3]
        parlay = None
        if len(legs) >= 2:
            combined = round(math.prod(l["prob"] for l in legs), 3)
            parlay = {"legs": legs, "combined_prob": combined,
                      "fair_odds": fair_american(combined),
                      "book_pays": BOOK_PARLAY_PAYS[len(legs)],
                      "calibration": CALIBRATION_VERSION}

    out = {
        "sport": "cfb", "season": SEASON, "week": next_week,
        "generated": pd.Timestamp.now("America/Los_Angeles").strftime("%Y-%m-%d %H:%M %Z"),
        "disclaimer": ("Model probabilities for entertainment. Our backtest shows "
                       "no proven edge vs the closing line — track record published openly."),
        "parlay": parlay,
        "picks": picks,
    }
    dest = REPO / "site" / "data" / "cfb_picks.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"Week {next_week}: {len(picks)} games -> {dest}")


if __name__ == "__main__":
    main()
