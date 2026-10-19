"""Daily NBA picks: current ratings -> today's (or tomorrow's) games.

Reads data/nba/games.csv (2007-2023) plus every data/nba/merged/YYYY-MM-DD.json
finals day through yesterday, trains margin-adjusted Elo + efficiency totals
chronologically (prediction precedes update, same leakage-safe discipline as
backtest.py), then predicts the target day's games against the latest logged
consensus line and writes site/data/nba_picks.json. The day's picks are also
appended to site/data/nba_season_2027.json, which grade_day.py later grades.

Honesty rules (same as the rest of this repo):
  - The betting line is NEVER a model input, anywhere. It is only the
    benchmark the picks are compared against.
  - Prediction precedes update; games train in chronological order.
  - Preseason games are excluded from training and flagged experimental in
    the output (the model was validated on regular-season games only).
  - Early regular-season boards are also flagged experimental while the
    model is warming up: until every team has WARMUP_GAMES_PER_TEAM
    current-season regular-season games in training, the ratings have seen
    too little of the new season to present the board as settled. The flag
    is computed from the training state each run and clears itself.

Usage:
    python3 src/nba/daily_picks.py [--date YYYY-MM-DD] [--force]

--date selects the game day (default: today, America/Los_Angeles). When the
target day has no games with logged lines, tomorrow is tried instead --
at 9pm the useful slate is tomorrow's, not today's already-finished games.
When neither day has games, picks: [] is emitted with a pending_reason.

Season timing: the 2026-27 regular season starts ~Oct 20, 2026. Games
commencing before the season opener are preseason (flagged, experimental).
Boards after the opener stay flagged (as early-season experimental) until
the warm-up threshold above is met.
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
from elo import ELO_PER_POINT, ELO_START, NBAElo
from totals import NBATotals
from features import (REST_CAP_DAYS, apply_rest_adjustment,
                      apply_rest_adjustment_total)
from stars import apply_star_adjustment, load_stars_out
from teams import CANONICAL_TEAMS, normalize_team
from recalibration import recalibrate

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "nba"
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")

SEASON = 2027  # 2026-27 season, ending-year convention like games.csv

# Residual noise of OUR model on the 2008-2023 walk-forward backtest
# (data/nba/backtest_results.md, final model with rest adjustment).
# Same role as the NFL pipeline's MARGIN_SD/TOTAL_SD:
# P(picked side covers) = Phi(|edge| / sd) -- display probability only.
# Since 2026-10-09 the raw Phi value goes through empirical recalibration
# (src/recalibration.py) before display; see the calibration check.
MARGIN_SD = 12.50
TOTAL_SD = 18.26

SPREAD_PICK_MIN = 0.5  # |spread edge| needed to publish a spread pick (mirrors NFL/CFB)
TOTAL_PICK_MIN = 1.0   # |total edge| needed to publish a total pick

# NBA totals picks are NOT published (H6, approved by Bryant 2026-10-12).
# The pre-registered walk-forward test (2008-2023; modern era 2018-2023)
# found totals picks lose at EVERY threshold, including the live
# |edge|>=1.0 (48.0%, n=5,271, z=-2.85); higher thresholds are worse
# (45.3% at >=8.0). No threshold cleared the pre-registered adoption bar
# (>=52% on >=500 decided picks in the modern era). The model still
# predicts totals internally (our_total/line_total are emitted for
# context) but no over/under pick is published. Revisit only if a future
# model version clears that bar in a new pre-registered test.
PUBLISH_TOTALS = False

# Total circuit breaker (same idea as the NFL/CFB pipelines): if our total
# is more than this many points from the market total, publish no total pick.
# An extreme disagreement is more likely our model being wrong than the
# market being wrong. Scaled from the NFL's 7.0 by the backtest total
# residual SD ratio (18.26 vs 15.4 -> ~8.3), rounded to the CFB value.
TOTAL_CIRCUIT = 8.5

BOOK_PARLAY_PAYS = {2: "+260", 3: "+600"}

# Regular-season openers by ending-year season. A game commencing before its
# season's opener is preseason: excluded from training, flagged experimental
# in the picks output.
SEASON_OPENERS = {2027: datetime.date(2026, 10, 20)}

# Early-season warm-up: a regular-season board is flagged experimental
# until EVERY team has at least this many current-season regular-season
# games in the training data. Five games per team is the point where each
# club has a real (if small) sample of the new season in its rating; at
# ~3 games per team per week the flag clears itself roughly 10-12 days
# after the opener with no manual step. (Bryant, 2026-10-19: the 2026-27
# opener board is generated from ratings carried across a multi-season
# data gap at near-prior strength, so early boards must not publish as
# normal until the model has warmed up on real 2026-27 games.)
WARMUP_GAMES_PER_TEAM = 5

WARMUP_NOTE = (
    "Early season -- the model's ratings are still warming up on this "
    "season's games: it has not yet seen five regular-season games per "
    "team, so the ratings lean on prior seasons more than usual. Treat "
    "these picks as experimental and provisional.")


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_american(p: float) -> str:
    """American odds for a true probability p."""
    if p > 0.5:
        return f"-{round(100 * p / (1 - p))}"
    if p < 0.5:
        return f"+{round(100 * (1 - p) / p)}"
    return "+100"


def pick_spread_label(pick_side: str | None, line_margin: float,
                      home: str, away: str) -> str | None:
    """Display label from the PICKED team's perspective (home-margin
    convention: positive = home favored)."""
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
    """NBA season ending year for a calendar date (Oct-Dec -> next year)."""
    return d.year + 1 if d.month >= 10 else d.year


def is_preseason(commence: datetime.date) -> bool:
    """True when a game tips before its season's regular-season opener."""
    opener = SEASON_OPENERS.get(season_of(commence))
    if opener is None:
        # Unknown future season: assume mid-October opener, loudly.
        opener = datetime.date(season_of(commence) - 1, 10, 15)
        print(f"WARNING: no opener on record for season {season_of(commence)}; "
              f"assuming {opener} for preseason detection")
    return commence < opener


def season_games_per_team(df: pd.DataFrame, season: int) -> dict[str, int]:
    """Regular-season games per team in the training frame for one season.

    load_training_rows already excludes preseason finals, so every counted
    game is a regular-season game the model actually trained on.
    """
    counts = {t: 0 for t in CANONICAL_TEAMS}
    cur = df[df["season"] == season]
    for r in cur.itertuples():
        if r.home_team in counts:
            counts[r.home_team] += 1
        if r.away_team in counts:
            counts[r.away_team] += 1
    return counts


def warming_up(df: pd.DataFrame, season: int) -> bool:
    """True while some team has fewer than WARMUP_GAMES_PER_TEAM games of
    the given season in training -- i.e. the model's ratings have not yet
    warmed up on the new season and its boards stay flagged experimental.
    Evaluated from the same training frame the ratings are built from, so
    the flag clears on its own as finals merge in."""
    counts = season_games_per_team(df, season)
    return min(counts[t] for t in CANONICAL_TEAMS) < WARMUP_GAMES_PER_TEAM


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


def load_training_rows(yesterday: datetime.date) -> pd.DataFrame:
    """games.csv + every merged finals day through yesterday, chronological.

    Preseason finals are excluded (preseason rotations would corrupt
    regular-season ratings). Team names are normalized (fail loud).
    """
    rows = []
    hist = pd.read_csv(DATA / "games.csv", parse_dates=["date"])
    for r in hist.itertuples():
        rows.append({
            "date": r.date.date() if hasattr(r.date, "date") else r.date,
            "season": int(r.season),
            "home_team": normalize_team(r.home_team),
            "away_team": normalize_team(r.away_team),
            "home_score": float(r.home_score),
            "away_score": float(r.away_score),
        })
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
                    continue  # preseason finals never train the model
                rows.append({
                    "date": commence,
                    "season": season_of(commence),
                    "home_team": normalize_team(g["home_team"]),
                    "away_team": normalize_team(g["away_team"]),
                    "home_score": float(final["home_score"]),
                    "away_score": float(final["away_score"]),
                })
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    return df


def train(df: pd.DataFrame, roll_to_season: int | None = None
          ) -> tuple[NBAElo, NBATotals, dict]:
    """Chronological training; returns (elo, totals, last game date per team).

    Season boundaries call new_season() once per season step. When
    roll_to_season is given, seasons are rolled forward to it even with no
    games (e.g. the 2024-2027 data gap), so stale ratings regress toward
    the mean instead of being treated as fresh.
    """
    elo, totals = NBAElo(), NBATotals()
    last_season = None
    last_date: dict[tuple[str, int], datetime.date] = {}
    for r in df.itertuples():
        season = int(r.season)
        if last_season is not None and season != last_season:
            for _ in range(season - last_season):
                elo.new_season()
                totals.new_season()
        last_season = season
        # Predict-then-update keeps the backtest discipline visible even
        # though only the final trained state is used here.
        _ = elo.predict_margin(r.home_team, r.away_team)
        _ = totals.predict_total(r.home_team, r.away_team)
        elo.update(r.home_team, r.away_team, r.home_score, r.away_score)
        totals.update(r.home_team, r.away_team, r.home_score, r.away_score)
        d = r.date
        for team in (r.home_team, r.away_team):
            key = (team, season)
            if key not in last_date or d > last_date[key]:
                last_date[key] = d
    if roll_to_season is not None and last_season is not None:
        for _ in range(last_season + 1, roll_to_season + 1):
            elo.new_season()
            totals.new_season()
    return elo, totals, last_date


def rest_days(team: str, season: int, game_date: datetime.date,
              last_date: dict) -> float:
    """Full days off since the team's previous game this season (NaN when
    none -- e.g. season openers, mirroring add_rest_days)."""
    prev = last_date.get((team, season))
    if prev is None:
        return float("nan")
    return float(min(max((game_date - prev).days - 1, -1), REST_CAP_DAYS))


def latest_snapshot() -> tuple[str, dict] | None:
    """Freshest odds data: merged/<date>.json preferred (superset of the raw
    odds log), else the raw odds_log/<date>.json. Returns (date, data)."""
    cands: dict[str, Path] = {}
    for dname in ("merged", "odds_log"):
        d = DATA / dname
        if not d.is_dir():
            continue
        for p in d.glob("*.json"):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", p.name):
                # merged/ wins ties: same games plus any merged finals.
                if dname == "merged" or p.stem not in cands:
                    cands[p.stem] = p
    if not cands:
        return None
    latest = max(cands)
    return latest, json.loads(cands[latest].read_text())


def pt_date(iso: str) -> datetime.date:
    return datetime.datetime.fromisoformat(iso).astimezone(PT).date()


def build_parlay(picks: list[dict]) -> dict | None:
    """Parlay of the day: the 3 highest-probability legs (spread or total).

    Entertainment only -- legs are roughly independent (different games), so
    the combined probability is the product. Our model's probabilities are
    unproven (see track record), so 'fair odds' are the model's view, not a
    promise.
    """
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


def export_power_rankings(elo: NBAElo, season: int,
                          note: str | None = None) -> None:
    """Write site/data/nba_power_rankings.json from the trained Elo ratings.

    Read-only use of the ratings. The published number converts Elo with
    the model's own fitted rate (ELO_PER_POINT = 30 Elo points per point
    of margin -- the same conversion NBAElo.predict_margin uses):
    rating = (team Elo - mean Elo of the 30 teams) / ELO_PER_POINT, i.e.
    expected margin vs the average team on a neutral court, before the
    nightly rest/star adjustments. Movement arrows come from the previous
    export when its date differs; same-day re-runs keep the morning's
    baseline (the daily analog of the NFL export's week rule).
    """
    dest = SITE_DATA / "nba_power_rankings.json"
    today = datetime.datetime.now(PT).strftime("%Y-%m-%d")
    prev_ranks: dict[str, int] = {}
    try:
        old = json.loads(dest.read_text())
        if old.get("asof") is not None and old.get("asof") != today:
            for t in old.get("teams", []):
                if t.get("abbr") and t.get("rank"):
                    prev_ranks[t["abbr"]] = int(t["rank"])
        elif old.get("asof") is not None:
            for t in old.get("teams", []):
                if t.get("abbr") and t.get("prev_rank"):
                    prev_ranks[t["abbr"]] = int(t["prev_rank"])
    except Exception:
        pass
    elos = {t: elo.ratings.get(t, ELO_START) for t in CANONICAL_TEAMS}
    mean_elo = sum(elos.values()) / len(elos)
    rows = sorted(
        ((round((e - mean_elo) / ELO_PER_POINT, 1), t) for t, e in elos.items()),
        key=lambda r: (-r[0], r[1]))
    teams = [
        {"rank": i + 1, "team": t, "abbr": t, "rating": pts,
         "prev_rank": prev_ranks.get(t)}
        for i, (pts, t) in enumerate(rows)
    ]
    out = {
        "sport": "nba",
        "season": int(season),
        "asof": today,
        "updated": datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z"),
        "note": note or ("Model-internal predictive ratings: the model's Elo "
                 "ratings converted to expected margin vs an average team "
                 "on a neutral court at the model's fitted rate (30 Elo "
                 "points per point of margin), before nightly rest/star "
                 "adjustments. Not a resume ranking; moves only on game "
                 "results."),
        "teams": teams,
    }
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"NBA power rankings: {len(teams)} teams -> {dest}")


def validate_picks(picks: list[dict]) -> None:
    """Fail loudly BEFORE publishing, never after.

    Edges are stored rounded to 0.1 while the pick/no-pick decision uses the
    raw edge, so the boundary checks allow a 0.05 rounding tolerance.
    """
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
    ap = argparse.ArgumentParser(description="Generate today's NBA picks")
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

    # Game day: the target date if it has games with lines, else tomorrow.
    # (At 9pm the useful slate is tomorrow's, not today's finished games.)
    game_date = None
    day_games: list[dict] = []
    for cand in (target, target + datetime.timedelta(days=1)):
        gs = [g for g in odds.get("games", [])
              if g.get("commence_time") and pt_date(g["commence_time"]) == cand]
        if gs:
            game_date, day_games = cand, gs
            break
    if game_date is None:
        # Rankings still refresh on no-game days: they are the model's
        # current state (e.g. preseason ratings carried across the
        # offseason rollover), independent of any slate.
        df = load_training_rows(yesterday)
        elo, _totals, _last_date = train(df, roll_to_season=SEASON)
        export_power_rankings(elo, SEASON)
        warmup = warming_up(df, SEASON)
        out = {
            "sport": "nba", "season": SEASON, "date": target.isoformat(),
            "preseason": False, "warming_up": warmup,
            "experimental_note": WARMUP_NOTE if warmup else None,
            "generated": datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z"),
            "disclaimer": ("Model probabilities for entertainment. Our backtest "
                           "shows no proven edge vs the closing line — track "
                           "record published openly."),
            "parlay": None, "picks": [],
            "pending_reason": (
                f"No NBA games with logged lines on {target} or {target + datetime.timedelta(days=1)}. "
                f"(Regular season starts ~Oct 20, 2026.)"),
            "odds_snapshot": snap_date,
        }
        dest = SITE_DATA / "nba_picks.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2))
        print(f"no games {target} or +1d -> {dest} (pending)")
        return

    print(f"game day {game_date} ({len(day_games)} games in snapshot {snap_date})")

    df = load_training_rows(yesterday)
    print(f"training: {len(df):,} games through {df['date'].max()}")
    season = season_of(game_date)
    elo, totals, last_date = train(df, roll_to_season=season)
    export_power_rankings(elo, season)
    if df["season"].max() < season:
        print(f"note: no training data for seasons "
              f"{int(df['season'].max()) + 1}..{season}; ratings regressed "
              f"to near-prior across the gap")

    preseason_day = is_preseason(game_date)
    warmup = not preseason_day and warming_up(df, season)
    experimental_note = None
    if preseason_day:
        experimental_note = (
            "Preseason games -- rotations and effort differ from the regular "
            "season, and this model was validated on regular-season games only. "
            "Treat these picks as experimental.")
    elif warmup:
        experimental_note = WARMUP_NOTE
        print("note: early-season warm-up (some team has fewer than "
              f"{WARMUP_GAMES_PER_TEAM} season-{season} games in training); "
              "board flagged experimental")

    seen = set()
    picks = []
    # Star absences: nightly designations from data/nba/star_out.json
    # (populated by the news watch). Missing/stale file -> no adjustment.
    stars_out = load_stars_out(season, game_date)
    for g in sorted(day_games, key=lambda x: x["commence_time"]):
        home = normalize_team(g["home_team"])
        away = normalize_team(g["away_team"])
        if (home, away) in seen:
            continue
        seen.add((home, away))
        line = consensus_line(g)
        if line is None:
            print(f"  skip {away} @ {home}: no book with spread+total")
            continue
        line_margin, line_total = line

        hr = rest_days(home, season, game_date, last_date)
        ar = rest_days(away, season, game_date, last_date)
        our_margin = apply_rest_adjustment(
            elo.predict_margin(home, away), hr, ar)
        our_margin = apply_star_adjustment(
            our_margin,
            len(stars_out.get(home, ())),
            len(stars_out.get(away, ())))
        our_total = apply_rest_adjustment_total(
            totals.predict_total(home, away), hr, ar)

        spread_edge = our_margin - line_margin  # >0: we like home more than line
        total_edge = our_total - line_total     # >0: we like over more than line

        pick_side = ("home" if spread_edge > 0 else "away") \
            if abs(spread_edge) >= SPREAD_PICK_MIN else None
        pick_total = ("over" if total_edge > 0 else "under") \
            if PUBLISH_TOTALS and abs(total_edge) >= TOTAL_PICK_MIN else None
        total_note = None
        if pick_total and abs(total_edge) > TOTAL_CIRCUIT:
            # Extreme disagreement with an efficient market is more likely
            # our error than our edge -- skip instead of publishing
            # false confidence.
            pick_total = None
            total_note = ("No play -- our total is too far from the market "
                          "to trust.")
        # Raw Phi(|edge|/sd) is systematically overconfident (2026-10-09
        # calibration check), so the empirical curve is applied to the final
        # edge-derived probability -- after rest and star adjustments, which
        # feed the edge. Picks (threshold-based) are unchanged.
        cover_prob = recalibrate(normal_cdf(abs(spread_edge) / MARGIN_SD),
                                 "nba", "ats")
        ou_prob = recalibrate(normal_cdf(abs(total_edge) / TOTAL_SD),
                              "nba", "totals")

        ct = datetime.datetime.fromisoformat(g["commence_time"]).astimezone(PT)
        picks.append({
            "away": away, "home": home,
            "away_abbr": away, "home_abbr": home,
            "gameday": ct.strftime("%Y-%m-%d"),
            "weekday": ct.strftime("%A"),
            "neutral": False,
            "preseason": preseason_day,
            # home-margin convention: positive = home favored
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
            # Both sides' spread text, generator-owned, for the pick'em UI.
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
        "sport": "nba", "season": season, "date": game_date.isoformat(),
        "preseason": preseason_day,
        "warming_up": warmup,
        "experimental_note": experimental_note,
        "generated": datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z"),
        "disclaimer": ("Model probabilities for entertainment. Our backtest "
                       "shows no proven edge vs the closing line — track "
                       "record published openly."),
        "parlay": parlay,
        "picks": picks,
        "odds_snapshot": snap_date,
    }
    dest = SITE_DATA / "nba_picks.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"{len(picks)} games -> {dest}")

    # Append to the season log for later grading (never silently overwrite
    # a day that was already graded).
    log_path = SITE_DATA / f"nba_season_{season}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() \
        else {"sport": "nba", "season": season, "days": {}}
    day_key = game_date.isoformat()
    existing = log["days"].get(day_key)
    if existing and existing.get("graded") and not args.force:
        print(f"day {day_key} already graded; season log left untouched "
              f"(use --force to overwrite)")
    else:
        log["days"][day_key] = {
            "date": day_key, "generated": out["generated"],
            "preseason": preseason_day,
            "warming_up": warmup,
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
