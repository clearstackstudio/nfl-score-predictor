"""Shadow big-line diagnostic -- bookkeeping ONLY. Never writes outside
data/shadow/ncaab_bigline/ (gitignored via data/.gitignore). Reads
site/data/ncaab_season_<season>.json and data/ncaab/merged/<date>.json
read-only. Nothing here feeds the model, the picks, or the site.

Purpose: the 2026-11-07 diagnostic (goal files:
ncaab-big-line-shrink-diagnostic-2026-11-07.md) found that NCAAB's 9-21
ATS start concentrates in one shape: early-season ratings shrink
top-vs-bottom gaps, so in games lined |spread| >= 20 the model priced
the favorite 15-30 points closer than the market and manufactured fake
underdog edges (published picks, Nov 1-6: model margin MAE 23.7 /
bias +23.7 in the >=20 bucket vs market 3.6 / +0.8 on the same games).
Bryant approved this pre-registered shadow on 2026-11-07 to test the
hypothesis on the FULL slate, not just published picks.

Population: EVERY game in the window for which the live pipeline
produced a model margin and a market spread -- i.e. every game entry
the daily-picks job computed into the season log (games with a
consensus spread+total), whether or not it carried a published ATS
pick. The published pick side is stored per row for context only.

Conventions (verified 2026-11-07: this exact convention reproduces the
diagnostic's published-pick numbers from the stored season file --
>=20 bucket model MAE 23.67 / bias +23.67, market 3.59 / +0.77; all 30
picks model MAE 14.80, market 3.80):
  - All margins are HOME-signed: market_spread = line_spread
    (positive = home favored), model_margin = our_spread (positive =
    model favors home), final_margin = home_score - away_score.
  - Errors are signed actual-minus-prediction:
    model_error = final_margin - model_margin,
    market_error = final_margin - market_spread.
    Bias = mean signed error (positive = favorites beat the number by
    more than predicted); MAE = mean absolute error.
  - Buckets by |market_spread|: 0-6, 6-12, 12-20, 20+.

Grading: finals come from data/ncaab/merged/<date>.json, matched with
grade_day.py's own logic. A game the merged file cannot match falls
back -- labeled final_source="season_log_result" per game and counted
in the ledger -- to the result grade_day.py itself stored in the
season log (written from those same finals). The fallback exists
because the pre-fix Nov 1-3 merged files carry swapped team labels on
some rows; it never overrides a merged-file match.

Window: games played Nov 8-21, 2026 (America/Los_Angeles dates -- the
season log's day keys are PT dates by construction).

Pre-registered confirmation read (do not alter): the hypothesis is
CONFIRMED if, over the window, the 20+ bucket's mean model bias stays
> +8 while the market's stays < +3. Any other outcome = not confirmed.
The shrinkage candidate is NOT part of this watch; it comes only after
a confirmed read, as a separate backtest-only step Bryant approves.

Modes:
    snapshot  copy window slates from the season log (pre-result fields)
    grade     grade snapshotted games from merged finals; rebuild ledger
    all       both (default; what the nightly cron runs)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from teams import normalize_team  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "ncaab"
SITE_DATA = REPO / "site" / "data"
SHADOW_DIR = REPO / "data" / "shadow" / "ncaab_bigline"
PT = ZoneInfo("America/Los_Angeles")

WINDOW_START = date(2026, 11, 8)
WINDOW_END = date(2026, 11, 21)
BUCKETS = ("0-6", "6-12", "12-20", "20+")
MODEL_BIAS_CONFIRM = 8.0    # 20+ bucket model bias must stay ABOVE this
MARKET_BIAS_CONFIRM = 3.0   # 20+ bucket market bias must stay BELOW this

CONFIRMATION_CRITERION = (
    "The hypothesis is CONFIRMED if, over the window, the 20+ bucket's "
    "mean model bias stays > +8 while the market's stays < +3. Any "
    "other outcome = not confirmed. (Pre-registered 2026-11-07 in "
    "ncaab-big-line-shrink-diagnostic-2026-11-07.md; Bryant approved "
    "the shadow the same day. Measurement only -- this watch changes "
    "nothing, and the shrinkage candidate requires a confirmed read "
    "plus a separate approval.)"
)


def now_pt() -> datetime:
    return datetime.now(PT)


def season_of(d: date) -> int:
    """NCAAB season ending year (mirrors daily_picks.season_of)."""
    return d.year + 1 if d.month >= 11 else d.year


def window_dates(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def bucket_of(market_spread: float) -> str:
    a = abs(market_spread)
    if a < 6:
        return "0-6"
    if a < 12:
        return "6-12"
    if a < 20:
        return "12-20"
    return "20+"


def canonical_teams(season: int) -> set[str] | None:
    """Mirrors grade_day.py's fallback chain for the D1 membership list."""
    for s in (season, season - 1, 2026):
        p = DATA / "raw" / f"d1_{s}.json"
        if p.exists():
            return set(json.loads(p.read_text()))
    return None


def load_season_log(season: int) -> dict | None:
    p = SITE_DATA / f"ncaab_season_{season}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def extract_rows(day: dict) -> list[dict]:
    """Pre-result fields for every game the pipeline priced that day."""
    rows = []
    for p in day.get("picks", []):
        if p.get("our_spread") is None or p.get("line_spread") is None:
            continue
        rows.append({
            "date": p.get("gameday") or day.get("date"),
            "home": p["home"],
            "away": p["away"],
            "neutral": bool(p.get("neutral", False)),
            "market_spread": p["line_spread"],
            "model_margin": p["our_spread"],
            "bucket": bucket_of(p["line_spread"]),
            "published_pick": p.get("pick_spread"),
            "final_margin": None,
            "model_error": None,
            "market_error": None,
            "final": None,
            "final_source": None,
        })
    return rows


def rows_hash(rows: list[dict]) -> str:
    keys = ("date", "home", "away", "neutral", "market_spread",
            "model_margin", "published_pick")
    canon = [{k: r[k] for k in keys} for r in rows]
    return hashlib.sha256(
        json.dumps(canon, sort_keys=True).encode()).hexdigest()


def snapshot(start: date, end: date, shadow_dir: Path) -> dict:
    days_dir = shadow_dir / "days"
    days_dir.mkdir(parents=True, exist_ok=True)
    logs: dict[int, dict | None] = {}
    result = {}
    for d in window_dates(start, end):
        season = season_of(d)
        if season not in logs:
            logs[season] = load_season_log(season)
        log = logs[season]
        day = (log or {}).get("days", {}).get(d.isoformat())
        dest = days_dir / f"{d.isoformat()}.json"
        if day is None:
            result[d.isoformat()] = "no slate in season log (yet)"
            continue
        rows = extract_rows(day)
        h = rows_hash(rows)
        prev = json.loads(dest.read_text()) if dest.exists() else None
        graded = bool(prev) and any(
            g.get("final") is not None for g in prev.get("games", []))
        if prev and prev.get("source_hash") == h:
            result[d.isoformat()] = f"current ({len(rows)} games)"
            continue
        if graded:
            # Never rewrite history after finals land; a pre-grade line
            # refresh is the only legitimate source change.
            prev["source_changed_after_grading"] = True
            dest.write_text(json.dumps(prev, indent=2))
            result[d.isoformat()] = (
                "source changed after grading; frozen snapshot kept")
            continue
        doc = {
            "watch": "ncaab_bigline_shadow",
            "date": d.isoformat(),
            "source": (f"site/data/ncaab_season_{season}.json "
                       f"days[{d.isoformat()}]"),
            "source_generated": day.get("generated"),
            "source_hash": h,
            "first_seen": (prev or {}).get("first_seen")
            or now_pt().strftime("%Y-%m-%d %H:%M %Z"),
            "snapshotted_at": now_pt().strftime("%Y-%m-%d %H:%M %Z"),
            "preseason": bool(day.get("preseason", False)),
            "games": rows,
        }
        dest.write_text(json.dumps(doc, indent=2))
        result[d.isoformat()] = f"snapshotted ({len(rows)} games)"
    for k, v in result.items():
        print(f"snapshot {k}: {v}")
    return result


def load_finals(d: date) -> dict[tuple[str, str], tuple[float, float]]:
    """Finals from the same merged file grade_day.py uses, matched the
    same way (Odds API names normalized to canonical CBBD names)."""
    p = DATA / "merged" / f"{d.isoformat()}.json"
    if not p.exists():
        return {}
    merged = json.loads(p.read_text())
    canon = canonical_teams(season_of(d))
    finals = {}
    for g in merged.get("games", []):
        f = g.get("final")
        if not f:
            continue
        ht, at = g["home_team"], g["away_team"]
        if canon is not None:
            try:
                ht = normalize_team(ht, canon)
                at = normalize_team(at, canon)
            except ValueError:
                pass  # keep raw names; the game simply won't match
        finals[(ht, at)] = (float(f["home_score"]),
                            float(f["away_score"]))
    return finals


def bucket_stats(rows: list[dict]) -> dict:
    graded = [r for r in rows if r.get("final") is not None]
    if not graded:
        return {"n": 0, "model_bias": None, "model_mae": None,
                "market_bias": None, "market_mae": None}
    me = [r["model_error"] for r in graded]
    ke = [r["market_error"] for r in graded]
    return {
        "n": len(graded),
        "model_bias": round(statistics.mean(me), 2),
        "model_mae": round(statistics.mean(abs(x) for x in me), 2),
        "market_bias": round(statistics.mean(ke), 2),
        "market_mae": round(statistics.mean(abs(x) for x in ke), 2),
    }


def rebuild_ledger(start: date, end: date, shadow_dir: Path) -> dict:
    days_dir = shadow_dir / "days"
    all_rows: list[dict] = []
    day_status = {}
    for d in window_dates(start, end):
        key = d.isoformat()
        dest = days_dir / f"{key}.json"
        if not dest.exists():
            day_status[key] = {
                "snapshotted": False, "games": 0, "graded": 0,
                "unmatched": [],
                "note": ("no season-log slate for this date"
                         if d < now_pt().date() else "pending"),
            }
            continue
        doc = json.loads(dest.read_text())
        games = doc.get("games", [])
        graded = [g for g in games if g.get("final") is not None]
        unmatched = [f"{g['away']} @ {g['home']}" for g in games
                     if g.get("final") is None
                     and (DATA / "merged" / f"{key}.json").exists()]
        all_rows.extend(games)
        day_status[key] = {
            "snapshotted": True, "games": len(games),
            "graded": len(graded), "unmatched": unmatched,
            "note": doc.get("source_generated") or "",
        }
    buckets = {b: bucket_stats([r for r in all_rows
                                 if r["bucket"] == b]) for b in BUCKETS}
    overall = bucket_stats(all_rows)
    b20 = buckets["20+"]
    confirmed = bool(
        b20["n"] and b20["model_bias"] is not None
        and b20["model_bias"] > MODEL_BIAS_CONFIRM
        and b20["market_bias"] is not None
        and b20["market_bias"] < MARKET_BIAS_CONFIRM)
    window_complete = all(
        (s["snapshotted"] and s["graded"] == s["games"])
        or (not s["snapshotted"] and s["note"].startswith("no season-log"))
        for s in day_status.values())
    final = now_pt().date() > end
    if final and window_complete:
        status = ("FINAL -- CONFIRMED: the 20+ bucket's model bias "
                  f"({b20['model_bias']:+.2f}) stayed > +8 while the "
                  f"market's ({b20['market_bias']:+.2f}) stayed < +3. "
                  "The shrink hypothesis is confirmed on a full slate. "
                  "Next step is Bryant's call (backtest-only shrinkage "
                  "candidate)." if confirmed else
                  "FINAL -- NOT CONFIRMED: the pre-registered read did "
                  f"not hold (20+ bucket model bias {b20['model_bias']}, "
                  f"market bias {b20['market_bias']}, n={b20['n']}). "
                  "No candidate follows from this watch.")
    elif final:
        status = ("FINAL (window ended with ungraded games -- figures "
                  "below cover graded games only): "
                  + ("CONFIRMED on graded games" if confirmed
                     else "NOT CONFIRMED on graded games")
                  + " per the pre-registered read.")
    else:
        status = "collecting"
    ledger = {
        "watch": "ncaab_bigline_shadow",
        "purpose": ("Pre-registered test of the 2026-11-07 diagnostic's "
                    "shrink hypothesis on the FULL slate (every game "
                    "the pipeline priced, not just published picks): "
                    "do early-season ratings shrink big favorites? "
                    "Bookkeeping only; nothing here feeds the model, "
                    "the site, or any pick."),
        "confirmation_criterion": CONFIRMATION_CRITERION,
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "conventions": ("Home-signed margins; error = final_margin - "
                        "predicted; bias = mean signed error; buckets "
                        "by |market_spread|: 0-6, 6-12, 12-20, 20+."),
        "updated": now_pt().strftime("%Y-%m-%d %H:%M %Z"),
        "days": day_status,
        "buckets": buckets,
        "overall": overall,
        "games_snapshotted": len(all_rows),
        "games_graded": overall["n"],
        "finals_from_merged": sum(
            1 for r in all_rows if r.get("final_source") == "merged"),
        "finals_from_season_log_fallback": sum(
            1 for r in all_rows
            if r.get("final_source") == "season_log_result"),
        "status": status,
    }
    shadow_dir.mkdir(parents=True, exist_ok=True)
    (shadow_dir / "ledger.json").write_text(json.dumps(ledger, indent=2))
    lines = [
        "# NCAAB big-line shadow diagnostic -- ledger",
        "",
        ledger["purpose"],
        "",
        f"**Confirmation criterion:** {CONFIRMATION_CRITERION}",
        "",
        f"**Window:** {start.isoformat()} to {end.isoformat()} "
        f"(games played, PT dates)",
        "",
        f"**Status:** {status}",
        "",
        "| Bucket | n | Model bias | Model MAE | Market bias | "
        "Market MAE |",
        "|---|---|---|---|---|---|",
    ]
    def fmt(x):
        return "n/a" if x is None else f"{x:+.2f}"
    for b in BUCKETS:
        s = buckets[b]
        lines.append(
            f"| {b} | {s['n']} | {fmt(s['model_bias'])} "
            f"| {s['model_mae'] if s['model_mae'] is not None else 'n/a'} "
            f"| {fmt(s['market_bias'])} "
            f"| {s['market_mae'] if s['market_mae'] is not None else 'n/a'} |")
    lines.append(
        f"| ALL | {overall['n']} | {fmt(overall['model_bias'])} "
        f"| {overall['model_mae'] if overall['model_mae'] is not None else 'n/a'} "
        f"| {fmt(overall['market_bias'])} "
        f"| {overall['market_mae'] if overall['market_mae'] is not None else 'n/a'} |")
    lines += ["", "Days:"]
    for k in sorted(day_status):
        s = day_status[k]
        if s["snapshotted"]:
            extra = (f"; unmatched: {'; '.join(s['unmatched'])}"
                     if s["unmatched"] else "")
            lines.append(f"- {k}: {s['graded']}/{s['games']} graded"
                         f"{extra}")
        else:
            lines.append(f"- {k}: {s['note']}")
    lines += ["", f"Updated: {ledger['updated']}"]
    (shadow_dir / "LEDGER.md").write_text("\n".join(lines) + "\n")
    print(f"grade: ledger rebuilt -- {overall['n']} graded of "
          f"{len(all_rows)} snapshotted; 20+ bucket n={b20['n']}, "
          f"model bias {b20['model_bias']}, market bias "
          f"{b20['market_bias']}; status: {status}")
    return ledger


def apply_final(g: dict, hs: float, aws: float, source: str) -> None:
    g["final"] = {"home_score": hs, "away_score": aws}
    g["final_margin"] = hs - aws
    g["model_error"] = round(g["final_margin"] - g["model_margin"], 2)
    g["market_error"] = round(g["final_margin"] - g["market_spread"], 2)
    g["final_source"] = source


def season_log_results(d: date) -> dict[tuple[str, str], tuple[float, float]]:
    """Stored per-pick results in the season log -- grade_day.py's own
    output, written from the same merged finals. Used ONLY as a labeled
    fallback for games the merged file cannot match (the pre-fix Nov
    1-3 merged files carry swapped team labels on some rows: the final
    sits on the wrong game's row, so name matching misses games
    grade_day itself graded fine)."""
    log = load_season_log(season_of(d))
    day = (log or {}).get("days", {}).get(d.isoformat())
    out = {}
    for p in (day or {}).get("picks", []):
        r = p.get("result")
        if r and "home_score" in r and "away_score" in r:
            out[(p["home"], p["away"])] = (float(r["home_score"]),
                                           float(r["away_score"]))
    return out


def grade(start: date, end: date, shadow_dir: Path) -> dict:
    days_dir = shadow_dir / "days"
    if days_dir.is_dir():
        for dest in sorted(days_dir.glob("*.json")):
            doc = json.loads(dest.read_text())
            d = date.fromisoformat(doc["date"])
            if not (start <= d <= end):
                continue
            finals = load_finals(d)
            changed = False
            for g in doc.get("games", []):
                if g.get("final") is not None:
                    continue
                key = (g["home"], g["away"])
                if key in finals:
                    hs, aws = finals[key]
                    apply_final(g, hs, aws, "merged")
                    changed = True
            if any(g.get("final") is None for g in doc.get("games", [])):
                stored = season_log_results(d)
                for g in doc.get("games", []):
                    if g.get("final") is not None:
                        continue
                    key = (g["home"], g["away"])
                    if key in stored:
                        hs, aws = stored[key]
                        apply_final(g, hs, aws, "season_log_result")
                        changed = True
            if changed:
                doc["graded_at"] = now_pt().strftime("%Y-%m-%d %H:%M %Z")
                dest.write_text(json.dumps(doc, indent=2))
                n = sum(1 for g in doc["games"]
                        if g.get("final") is not None)
                fb = sum(1 for g in doc["games"]
                         if g.get("final_source") == "season_log_result")
                print(f"grade {doc['date']}: {n}/{len(doc['games'])} "
                      f"games graded ({fb} via season-log fallback)")
    return rebuild_ledger(start, end, shadow_dir)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="NCAAB big-line shadow diagnostic (bookkeeping only)")
    ap.add_argument("mode", nargs="?", default="all",
                    choices=("snapshot", "grade", "all"))
    ap.add_argument("--start", default=None,
                    help="window start YYYY-MM-DD (default 2026-11-08)")
    ap.add_argument("--end", default=None,
                    help="window end YYYY-MM-DD (default 2026-11-21)")
    ap.add_argument("--dir", default=None,
                    help="shadow dir override (validation runs only; "
                         "default data/shadow/ncaab_bigline)")
    args = ap.parse_args()
    start = (date.fromisoformat(args.start) if args.start
             else WINDOW_START)
    end = date.fromisoformat(args.end) if args.end else WINDOW_END
    shadow_dir = Path(args.dir) if args.dir else SHADOW_DIR
    if not shadow_dir.is_absolute():
        shadow_dir = REPO / shadow_dir
    if args.mode in ("snapshot", "all"):
        snapshot(start, end, shadow_dir)
    if args.mode in ("grade", "all"):
        grade(start, end, shadow_dir)


if __name__ == "__main__":
    main()
