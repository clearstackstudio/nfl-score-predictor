"""Daily NCAAB picks: current ratings -> today's (or tomorrow's) games.

Mirrors src/nba/daily_picks.py. Trains the adjusted-efficiency model on
data/ncaab/games.csv plus every data/ncaab/merged/YYYY-MM-DD.json finals
day through yesterday, chronologically (prediction precedes update, same
leakage-safe discipline as backtest.py), then predicts the target day's
games against the latest logged consensus line and writes
site/data/ncaab_picks.json. The day's picks are appended to
site/data/ncaab_season_2027.json, which grade_day.py later grades.

Honesty rules (same as the rest of this repo):
  - The betting line is NEVER a model input, anywhere. It is only the
    benchmark the picks are compared against.
  - Prediction precedes update; games train in chronological order.
  - Exhibition/preseason games are excluded from training and flagged
    experimental in the output (the model was validated on
    regular/postseason games only).

November note: the model's November updates are down-weighted
(efficiency.NOV_ALPHA_FACTOR) for transfer-portal roster noise.

Usage:
    TZ=America/Los_Angeles .venv-cfb/bin/python src/ncaab/daily_picks.py \
        [--date YYYY-MM-DD] [--force]
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import re
import statistics
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parent.parent))
from efficiency import NCAABEfficiency, HOME_EDGE_PTS, sanitize_poss
from features import apply_rest_adjustment, apply_rest_adjustment_total
from teams import normalize_team
from recalibration import recalibrate

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "ncaab"
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")

SEASON = 2027  # 2026-27 season, ending-year convention like games.csv

# Residual noise of OUR model on the 2013-2026 walk-forward backtest
# (data/ncaab/backtest_results.md, final model). Same role as the NBA
# pipeline's MARGIN_SD/TOTAL_SD: P(picked side covers) = Phi(|edge| / sd) --
# display probability only. The raw Phi value goes through empirical
# recalibration (src/recalibration.py) before display.
MARGIN_SD = 12.3
TOTAL_SD = 18.2

# Rest adjustment: DROPPED (0.0). The backtest tuning split showed a
# -0.16 pts/day margin slope improving RMSE by 0.006 -- inside noise with
# an implausible sign (see src/ncaab/backtest.py USE_REST). Kept at 0.0.
REST_MARGIN_PTS_PER_DAY = 0.0
REST_TOTAL_PTS_PER_DAY = 0.0
REST_MEAN_DAYS = 3.0

SPREAD_PICK_MIN = 0.5  # |spread edge| needed to publish a spread pick
TOTAL_PICK_MIN = 1.0   # |total edge| needed to publish a total pick

# Total circuit breaker (mirrors the NBA pipeline): if our total is more
# than this many points from the market total, publish no total pick.
TOTAL_CIRCUIT = 8.5

BOOK_PARLAY_PAYS = {2: "+260", 3: "+600"}

# Regular-season openers by ending-year season. A game tipping before its
# season's opener is preseason/exhibition: excluded from training, flagged
# experimental in the picks output.
SEASON_OPENERS = {2027: datetime.date(2026, 11, 3)}


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_american(p: float) -> str:
    if p > 0.5:
        return f"-{round(100 * p / (1 - p))}"
    if p < 0.5:
        return f"+{round(100 * (1 - p) / p)}"
    return "+100"


def pick_spread_label(pick_side: str | None, line_margin: float,
                      home: str, away: str) -> str | None:
    if not pick_side:
        return None
    team = home if pick_side == "home" else away
    margin = line_margin if pick_side == "home" else -line_margin
    if abs(margin) < 0.05:
        return "Pick'em"
    return f"{team} -{margin:g}" if margin > 0 else f"{team} +{-margin:g}"


def pick_total_label(pick_total: str | None, line_total: float) -> str | None:
    if not pick_total:
        return None
    return f"{'Over' if pick_total == 'over' else 'Under'} {line_total:g}"


def season_of(d: datetime.date) -> int:
    """NCAAB season ending year for a calendar date (Nov-Dec -> next year)."""
    return d.year + 1 if d.month >= 11 else d.year


def is_preseason(commence: datetime.date) -> bool:
    opener = SEASON_OPENERS.get(season_of(commence))
    if opener is None:
        opener = datetime.date(season_of(commence) - 1, 11, 1)
        print(f"WARNING: no opener on record for season {season_of(commence)}; "
              f"assuming {opener} for preseason detection")
    return commence < opener


def consensus_line(game: dict) -> tuple[float, float] | None:
    """Median spread/total across bookmakers in an odds-snapshot game.

    Spread returned in home-margin convention (positive = home favored):
    The Odds API quotes each team's spread point from that team's
    perspective (negative = favored), so home margin = -(home team's point).
    Returns None when no book has both a spread and a total.
    """
    spreads, totals = [], []
    for bm in game.get("bookmakers", []):
        for m in bm.get("markets", []):
            outcomes = {o["name"]: o.get("point") for o in m.get("outcomes", [])}
            if m.get("key") == "spreads" and game["home_team"] in outcomes:
                pt = outcomes[game["home_team"]]
                if pt is not None:
                    spreads.append(-float(pt))
            elif m.get("key") == "totals" and "Over" in outcomes:
                pt = outcomes["Over"]
                if pt is not None:
                    totals.append(float(pt))
    if not spreads or not totals:
        return None
    return statistics.median(spreads), statistics.median(totals)


def canonical_teams(season: int) -> set[str]:
    """CBBD team names for a season (the D1 membership list). Falls back to
    the most recent season on disk."""
    for s in (season, season - 1, 2026):
        p = DATA / "raw" / f"d1_{s}.json"
        if p.exists():
            return set(json.loads(p.read_text()))
    raise FileNotFoundError("no d1_<season>.json found under data/ncaab/raw/")


def load_training_rows(yesterday: datetime.date) -> pd.DataFrame:
    """games.csv + every merged finals day through yesterday, chronological.

    Preseason/exhibition finals are excluded. Team names are already
    canonical CBBD names in games.csv; merged finals are normalized
    (fail loud on unknown names).
    """
    rows = []
    hist = pd.read_csv(DATA / "games.csv", parse_dates=["date"])
    for r in hist.itertuples():
        rows.append({
            "date": r.date.date() if hasattr(r.date, "date") else r.date,
            "season": int(r.season),
            "home_team": r.home_team, "away_team": r.away_team,
            "home_score": float(r.home_score), "away_score": float(r.away_score),
            "neutral": bool(int(r.neutral)),
            "poss": float(r.poss) if pd.notna(r.poss) else None,
        })
    season = SEASON
    canon = canonical_teams(season)
    merged_dir = DATA / "merged"
    if merged_dir.is_dir():
        for p in sorted(merged_dir.glob("*.json")):
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name):
                continue
            day = json.loads(p.read_text())
            if day.get("date", "") > yesterday.isoformat():
                continue
            for g in day.get("games", []):
                final = g.get("final")
                if not final:
                    continue
                commence = datetime.datetime.fromisoformat(
                    g["commence_time"]).date()
                if is_preseason(commence):
                    continue
                rows.append({
                    "date": commence,
                    "season": season_of(commence),
                    "home_team": normalize_team(g["home_team"], canon),
                    "away_team": normalize_team(g["away_team"], canon),
                    "home_score": float(final["home_score"]),
                    "away_score": float(final["away_score"]),
                    "neutral": bool(g.get("neutral_site", False)),
                    "poss": None,
                })
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


def train(df: pd.DataFrame, roll_to_season: int | None = None
          ) -> tuple[NCAABEfficiency, dict]:
    """Chronological training; returns (model, last game date per team).

    Season boundaries call new_season() once per season step.
    """
    model = NCAABEfficiency()
    last_season = None
    last_date: dict[tuple[str, int], datetime.date] = {}
    for r in df.itertuples():
        season = int(r.season)
        if last_season is not None and season != last_season:
            for _ in range(season - last_season):
                model.new_season()
        last_season = season
        _ = model.predict(r.home_team, r.away_team, neutral=r.neutral)
        # Merged finals don't carry pace: use the model's own tempo
        # estimate so the PPP update stays consistent. Box pace is
        # sanitized (see efficiency.sanitize_poss).
        poss = sanitize_poss(r.poss, int(r.season))
        if poss is None:
            poss = model.predict_poss(r.home_team, r.away_team)
        d = r.date
        month = d.month if hasattr(d, "month") else int(str(d)[5:7])
        model.update(r.home_team, r.away_team, r.home_score, r.away_score,
                     poss, month)
        for team in (r.home_team, r.away_team):
            key = (team, season)
            if key not in last_date or d > last_date[key]:
                last_date[key] = d
    if roll_to_season is not None and last_season is not None:
        for _ in range(last_season + 1, roll_to_season + 1):
            model.new_season()
    return model, last_date


def rest_days(team: str, season: int, game_date: datetime.date,
              last_date: dict) -> float:
    prev = last_date.get((team, season))
    if prev is None:
        return float("nan")
    return float(min(max((game_date - prev).days - 1, -1), 10))


def latest_snapshot() -> tuple[str, dict] | None:
    cands: dict[str, Path] = {}
    for dname in ("merged", "odds_log"):
        d = DATA / dname
        if not d.is_dir():
            continue
        for p in d.glob("*.json"):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name):
                if dname == "merged" or p.stem not in cands:
                    cands[p.stem] = p
    if not cands:
        return None
    latest = max(cands)
    return latest, json.loads(cands[latest].read_text())


def pt_date(iso: str) -> datetime.date:
    return datetime.datetime.fromisoformat(iso).astimezone(PT).date()


def build_parlay(picks: list[dict]) -> dict | None:
    legs = []
    for p in picks:
        game = f"{p['away']} @ {p['home']}"
        if p["pick_spread"]:
            legs.append({"game": game, "market": "spread",
                         "label": p["pick_spread_label"],
                         "prob": p["cover_prob"]})
        if p["pick_total"]:
            legs.append({"game": game, "market": "total",
                         "label": p["pick_total_label"],
                         "prob": p["ou_prob"]})
    legs.sort(key=lambda l: -l["prob"])
    legs = legs[:3]
    if len(legs) < 2:
        return None
    combined = round(math.prod(l["prob"] for l in legs), 3)
    return {"legs": legs, "combined_prob": combined,
            "fair_odds": fair_american(combined),
            "book_pays": BOOK_PARLAY_PAYS[len(legs)]}


def validate_picks(picks: list[dict]) -> None:
    for p in picks:
        se = abs(p["spread_edge"])
        if p["pick_spread"]:
            assert 0.5 <= p["cover_prob"] <= 1.0, p
            assert se >= SPREAD_PICK_MIN - 0.05, p
        else:
            assert p["cover_prob"] is None and se < SPREAD_PICK_MIN + 0.05, p
        if p["pick_total"]:
            assert 0.5 <= p["ou_prob"] <= 1.0, p
        else:
            assert p["ou_prob"] is None, p


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate today's NCAAB picks")
    ap.add_argument("--date", default=None,
                    help="game day YYYY-MM-DD (default: today, PT)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a day entry that was already graded")
    args = ap.parse_args()

    today = datetime.datetime.now(PT).date()
    target = (datetime.date.fromisoformat(args.date) if args.date else today)
    yesterday = today - datetime.timedelta(days=1)

    snap = latest_snapshot()
    if snap is None:
        print("no odds snapshots found; cannot generate picks")
        sys.exit(1)
    snap_date, odds = snap

    game_date = None
    day_games: list[dict] = []
    for cand in (target, target + datetime.timedelta(days=1)):
        gs = [g for g in odds.get("games", [])
              if g.get("commence_time") and pt_date(g["commence_time"]) == cand]
        if gs:
            game_date, day_games = cand, gs
            break
    if game_date is None:
        out = {
            "sport": "ncaab", "season": SEASON, "date": target.isoformat(),
            "preseason": False, "experimental_note": None,
            "generated": datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z"),
            "disclaimer": ("Model probabilities for entertainment. Our backtest "
                           "shows no proven edge vs the closing line — track "
                           "record published openly."),
            "parlay": None, "picks": [],
            "pending_reason": (
                f"No NCAAB games with logged lines on {target} or "
                f"{target + datetime.timedelta(days=1)}. "
                f"(Regular season starts ~Nov 3, 2026.)"),
            "odds_snapshot": snap_date,
        }
        dest = SITE_DATA / "ncaab_picks.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2))
        print(f"no games {target} or +1d -> {dest} (pending)")
        return

    print(f"game day {game_date} ({len(day_games)} games in snapshot {snap_date})")

    df = load_training_rows(yesterday)
    print(f"training: {len(df):,} games through {df['date'].max()}")
    season = season_of(game_date)
    model, last_date = train(df, roll_to_season=season)

    preseason_day = is_preseason(game_date)
    experimental_note = None
    if preseason_day:
        experimental_note = (
            "Preseason/exhibition games -- rotations and effort differ from "
            "the regular season, and this model was validated on "
            "regular/postseason games only. Treat these picks as experimental.")

    canon = canonical_teams(season)
    seen = set()
    picks = []
    for g in sorted(day_games, key=lambda x: x["commence_time"]):
        home = normalize_team(g["home_team"], canon)
        away = normalize_team(g["away_team"], canon)
        if (home, away) in seen:
            continue
        seen.add((home, away))
        line = consensus_line(g)
        if line is None:
            print(f"  skip {away} @ {home}: no book with spread+total")
            continue
        line_margin, line_total = line
        neutral = bool(g.get("neutral_site", False))

        saved_edge = model.home_edge
        if neutral:
            model.home_edge = 0.0
        our_margin, our_total = model.predict(home, away, neutral=neutral)
        model.home_edge = saved_edge

        hr = rest_days(home, season, game_date, last_date)
        ar = rest_days(away, season, game_date, last_date)
        our_margin = apply_rest_adjustment(our_margin, hr, ar,
                                           pts_per_day=REST_MARGIN_PTS_PER_DAY)
        our_total = apply_rest_adjustment_total(our_total, hr, ar,
                                                pts_per_day=REST_TOTAL_PTS_PER_DAY,
                                                mean_days=REST_MEAN_DAYS)

        spread_edge = our_margin - line_margin
        total_edge = our_total - line_total

        pick_side = ("home" if spread_edge > 0 else "away") \
            if abs(spread_edge) >= SPREAD_PICK_MIN else None
        pick_total = ("over" if total_edge > 0 else "under") \
            if abs(total_edge) >= TOTAL_PICK_MIN else None
        total_note = None
        if pick_total and abs(total_edge) > TOTAL_CIRCUIT:
            pick_total = None
            total_note = ("No play -- our total is too far from the market "
                          "to trust.")
        cover_prob = recalibrate(normal_cdf(abs(spread_edge) / MARGIN_SD),
                                 "ncaab", "ats")
        ou_prob = recalibrate(normal_cdf(abs(total_edge) / TOTAL_SD),
                              "ncaab", "totals")

        ct = datetime.datetime.fromisoformat(g["commence_time"]).astimezone(PT)
        picks.append({
            "away": away, "home": home,
            "away_abbr": away, "home_abbr": home,
            "gameday": ct.strftime("%Y-%m-%d"),
            "weekday": ct.strftime("%A"),
            "neutral": neutral,
            "preseason": preseason_day,
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

    parlay = build_parlay(picks)
    validate_picks(picks)

    out = {
        "sport": "ncaab", "season": season, "date": game_date.isoformat(),
        "preseason": preseason_day,
        "experimental_note": experimental_note,
        "generated": datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z"),
        "disclaimer": ("Model probabilities for entertainment. Our backtest "
                       "shows no proven edge vs the closing line — track "
                       "record published openly."),
        "parlay": parlay,
        "picks": picks,
        "odds_snapshot": snap_date,
    }
    dest = SITE_DATA / "ncaab_picks.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"{len(picks)} games -> {dest}")

    log_path = SITE_DATA / f"ncaab_season_{season}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() \
        else {"sport": "ncaab", "season": season, "days": {}}
    day_key = game_date.isoformat()
    existing = log["days"].get(day_key)
    if existing and existing.get("graded") and not args.force:
        print(f"day {day_key} already graded; season log left untouched "
              f"(use --force to overwrite)")
    else:
        log["days"][day_key] = {
            "date": day_key, "generated": out["generated"],
            "preseason": preseason_day,
            "experimental_note": experimental_note,
            "graded": False, "complete": False,
            "picks": picks, "parlay": parlay,
        }
        log_path.write_text(json.dumps(log, indent=2))
        print(f"day {day_key} logged -> {log_path}")

    if parlay:
        print("Parlay of the day:")
        for l in parlay["legs"]:
            print(f"  {l['label']} ({l['game']}) {l['prob']:.0%}")
        print(f"  combined {parlay['combined_prob']:.1%} · "
              f"fair {parlay['fair_odds']} · book pays {parlay['book_pays']}")
    for p in picks:
        s = (f"{p['away']} @ {p['home']}: line {p['line_spread']:+} / "
             f"{p['line_total']}, ours {p['our_spread']:+} / {p['our_total']:.0f}")
        if p["pick_spread"]:
            s += f"  PICK {p['pick_spread']} {p['cover_prob']:.0%}"
        if p["pick_total"]:
            s += f"  {p['pick_total'].upper()} {p['ou_prob']:.0%}"
        if p.get("preseason"):
            s += "  [PRESEASON - experimental]"
        print(s)


if __name__ == "__main__":
    main()
