"""Daily NHL picks: publish the v1.1 model's moneyline board.

PUBLISHED counterpart of shadow_picks.py (which stays untouched as the
append-only shadow log). The model itself is unchanged: rows come from
shadow_picks.build_picks — the frozen v1.1 spec (expected-goals ratings
on MoneyPuck xG, home-ice 0.20 goals, rest-day term, calibration map
fitted on the discovery period) — so a published board and the shadow
log can never disagree about what the model said.

What gets published, per game (mirrors the NBA section's rules):
  - Only games with a consensus market moneyline (median across US
    books, The Odds API, fetched by the shadow generator). A game with
    no line cannot carry a pick and is skipped, loudly.
  - The pick is the model's favored side (by calibrated probability),
    published only when the model and the de-vigged market disagree by
    at least PICK_MIN_PP percentage points — the NHL analog of the
    NBA's spread-disagreement threshold. Closer than that, the honest
    call is "no play — we agree with Vegas here."
  - Totals are CONTEXT ONLY (Bryant, 2026-10-28 tightening, kept at
    launch): the model's expected total and the market total are shown
    side by side, but no totals pick is published and no totals record
    is kept.
  - No NHL parlay.

Guards mirrored from src/nba/daily_picks.py:
  - Board-date guard: the selected game day is the first day, starting
    at the target, whose games are all still un-tipped; if that day is
    more than 2 days out, refuse and write nothing (a far-future board
    means the odds feed has not posted the real next slate).
  - Shrink guard: never overwrite a date's published board with fewer
    games than are already recorded for it.

Outputs:
  site/data/nhl_picks.json        — the live board
  site/data/nhl_season_<season>.json — the season log grade_day.py grades

Usage:
    python3 src/nhl/daily_picks.py [--date YYYY-MM-DD] [--force]
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_eval import NAME_TO_ABBR  # noqa: E402
from shadow_picks import build_picks  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")

# Publication threshold: |model - market| win-probability gap, in
# percentage points, needed to publish a moneyline pick. Chosen from
# the shadow record's disagreement distribution (113 frozen games:
# median gap 4.6pp; a 2.0pp gate publishes ~79% of games and keeps
# near-coin-flip agreements as honest no-plays).
PICK_MIN_PP = 2.0

ABBR_TO_NAME: dict[str, str] = {}
for _name, _abbr in NAME_TO_ABBR.items():
    ABBR_TO_NAME.setdefault(_abbr, _name)  # first spelling wins (canonical)

DISCLAIMER = (
    "Model probabilities for entertainment. Our backtest and pre-launch "
    "shadow record show a model at market level, not ahead of it — no "
    "edge is claimed. Track record published openly.")


def season_of(game_id: int) -> int:
    """Ending-year season for an NHL game id (2026xxxxxx -> 2027)."""
    return int(str(game_id)[:4]) + 1


def fmt_ml(ml: float | None) -> str:
    """American odds display: -170 / +146 / -183.5 (median across books)."""
    if ml is None:
        return "—"
    v = float(ml)
    s = str(int(v)) if v == int(v) else str(round(v, 2)).rstrip("0").rstrip(".")
    return f"+{s}" if v > 0 else s


def recorded_pick_count(day: datetime.date, season: int) -> int:
    """Games already published for a date (live board and/or season
    log) — the shrink guard's baseline, mirroring the NBA pipeline."""
    count = 0
    try:
        board = json.loads((SITE_DATA / "nhl_picks.json").read_text())
        if board.get("date") == day.isoformat():
            count = max(count, len(board.get("picks", [])))
    except Exception:
        pass
    try:
        log = json.loads((SITE_DATA / f"nhl_season_{season}.json").read_text())
        entry = log.get("days", {}).get(day.isoformat())
        if entry:
            count = max(count, len(entry.get("picks", [])))
    except Exception:
        pass
    return count


def to_site_pick(row: dict) -> dict | None:
    """Convert one frozen shadow-model row to the published pick shape.

    Returns None when the game has no consensus moneyline — it cannot
    carry a pick, so it is not published (NBA precedent)."""
    if row.get("home_ml") is None or row.get("away_ml") is None \
            or row.get("market_p_home") is None:
        return None
    home_abbr, away_abbr = row["home"], row["away"]
    home, away = ABBR_TO_NAME[home_abbr], ABBR_TO_NAME[away_abbr]
    p_home = float(row["p_home_cal"])
    market_home = float(row["market_p_home"])
    edge_pp = round((p_home - market_home) * 100, 1)
    pick_side = None
    if abs(edge_pp) >= PICK_MIN_PP:
        pick_side = "home" if p_home > 0.5 else "away"
    pick_prob = None
    pick_label = None
    if pick_side == "home":
        pick_prob = round(p_home, 4)
        pick_label = f"{home} {fmt_ml(row['home_ml'])}"
    elif pick_side == "away":
        pick_prob = round(1 - p_home, 4)
        pick_label = f"{away} {fmt_ml(row['away_ml'])}"
    start = datetime.datetime.fromisoformat(
        row["start_time_utc"].replace("Z", "+00:00")).astimezone(PT)
    return {
        "away": away, "home": home,
        "away_abbr": away_abbr, "home_abbr": home_abbr,
        "game_id": row["game_id"],
        "gameday": start.strftime("%Y-%m-%d"),
        "weekday": start.strftime("%A"),
        "start_time_pt": start.strftime("%H:%M"),
        "home_ml": row["home_ml"], "away_ml": row["away_ml"],
        "market_p_home": market_home,
        "market_p_away": round(1 - market_home, 4),
        "p_home_raw": row["p_home_raw"], "p_home_cal": row["p_home_cal"],
        "p_away_cal": round(1 - p_home, 4),
        "model_total": row["model_total"],
        "total_line": row.get("total_line"),
        "over_price": row.get("over_price"),
        "under_price": row.get("under_price"),
        "pick_side": pick_side,
        "pick_label": pick_label,
        "pick_prob": pick_prob,
        "edge_pp": edge_pp,
        "result": None,
    }


def validate_picks(picks: list[dict]) -> None:
    """Fail loudly BEFORE publishing, never after (NBA pattern)."""
    for p in picks:
        if p["pick_side"]:
            assert abs(p["edge_pp"]) >= PICK_MIN_PP - 0.05, p
            assert p["pick_prob"] is not None and 0.5 <= p["pick_prob"] <= 1.0, p
            favored = "home" if p["p_home_cal"] > 0.5 else "away"
            assert p["pick_side"] == favored, p
        else:
            assert abs(p["edge_pp"]) < PICK_MIN_PP + 0.05, p
            assert p["pick_prob"] is None and p["pick_label"] is None, p


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate today's NHL picks")
    ap.add_argument("--date", default=None,
                    help="target day YYYY-MM-DD (default: today, PT)")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a day entry that was already graded")
    args = ap.parse_args()

    today = datetime.datetime.now(PT).date()
    target = (datetime.date.fromisoformat(args.date) if args.date else today)
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    # Game day: the first day, starting at the target, that still has
    # UN-TIPPED games. A game whose start time has passed is never
    # selected — its frozen line would no longer be a pre-game line.
    game_date = None
    day_rows: list[dict] = []
    for offset in range(0, 4):
        cand = target + datetime.timedelta(days=offset)
        rows, _info = build_picks(cand)
        untipped = []
        for r in rows:
            st = r.get("start_time_utc")
            if st and datetime.datetime.fromisoformat(
                    st.replace("Z", "+00:00")) > now_utc:
                untipped.append(r)
        if untipped:
            game_date, day_rows = cand, untipped
            break

    if game_date is None:
        out = {
            "sport": "nhl", "season": None, "date": target.isoformat(),
            "preseason": False, "warming_up": False,
            "experimental_note": None,
            "generated": datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z"),
            "disclaimer": DISCLAIMER,
            "parlay": None, "picks": [],
            "pending_reason": (
                f"No NHL games on or after {target} in the schedule feed."),
        }
        # Shrink guard: an empty board must never replace a published one.
        for season_guess in (target.year + 1, target.year):
            if recorded_pick_count(target, season_guess) > 0:
                print(f"ERROR: shrink guard: {target} already has "
                      f"published games, but no un-tipped games remain; "
                      f"refusing to replace the board with an empty one. "
                      f"Picks files unchanged.")
                sys.exit(1)
        dest = SITE_DATA / "nhl_picks.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2))
        print(f"no un-tipped NHL games on/after {target} -> {dest} (pending)")
        return

    # Board-date guard (NBA, 2026-11-05): a first un-tipped day more
    # than 2 days out is never the real next slate — refuse before
    # anything is written.
    if (game_date - today).days > 2:
        print(f"ERROR: board-date guard: selected game day {game_date} "
              f"is {(game_date - today).days} days after today ({today}); "
              f"the schedule/odds feed likely has not posted the next "
              f"real slate. Refusing to publish; no files written.")
        sys.exit(1)

    season = season_of(day_rows[0]["game_id"])
    picks = []
    skipped = []
    for r in sorted(day_rows, key=lambda x: x["start_time_utc"] or ""):
        p = to_site_pick(r)
        if p is None:
            skipped.append(f"{r['away']}@{r['home']}")
        else:
            picks.append(p)
    if skipped:
        print(f"WARNING skipped (no consensus moneyline): {skipped}")
    validate_picks(picks)

    # Shrink guard: never overwrite a date's published board with fewer
    # games than it already has.
    recorded = recorded_pick_count(game_date, season)
    if len(picks) < recorded:
        print(f"ERROR: shrink guard: {game_date} already has {recorded} "
              f"published games, but this run produced only {len(picks)}; "
              f"refusing to overwrite the fuller board. Picks files "
              f"unchanged.")
        sys.exit(1)

    generated = datetime.datetime.now(PT).strftime("%Y-%m-%d %H:%M %Z")
    out = {
        "sport": "nhl", "season": season, "date": game_date.isoformat(),
        "preseason": False, "warming_up": False,
        "experimental_note": None,
        "generated": generated,
        "disclaimer": DISCLAIMER,
        "parlay": None,
        "picks": picks,
    }
    dest = SITE_DATA / "nhl_picks.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"{len(picks)} games -> {dest}")

    # Append to the season log for later grading (never silently
    # overwrite a day that was already graded).
    log_path = SITE_DATA / f"nhl_season_{season}.json"
    log = json.loads(log_path.read_text()) if log_path.exists() \
        else {"sport": "nhl", "season": season, "days": {}}
    day_key = game_date.isoformat()
    existing = log["days"].get(day_key)
    if existing and existing.get("graded") and not args.force:
        print(f"day {day_key} already graded; season log left untouched "
              f"(use --force to overwrite)")
    else:
        log["days"][day_key] = {
            "date": day_key, "generated": generated,
            "preseason": False, "warming_up": False,
            "experimental_note": None,
            "graded": False, "complete": False,
            "picks": picks, "parlay": None,
        }
        log_path.write_text(json.dumps(log, indent=2))
        print(f"day {day_key} logged -> {log_path}")

    for p in picks:
        s = (f"{p['away']} @ {p['home']}: model {p['p_away_cal']:.1%} / "
             f"{p['p_home_cal']:.1%}, market {p['market_p_away']:.1%} / "
             f"{p['market_p_home']:.1%}, ML {fmt_ml(p['away_ml'])} / "
             f"{fmt_ml(p['home_ml'])}, total {p['model_total']:.2f} vs "
             f"{p['total_line']}")
        if p["pick_side"]:
            s += f"  PICK {p['pick_label']} ({p['pick_prob']:.0%})"
        else:
            s += "  no play"
        print(s)


if __name__ == "__main__":
    main()
