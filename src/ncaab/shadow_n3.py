"""Shadow N3 watch -- bookkeeping ONLY. Never writes outside
data/shadow/ncaab_n3/ (gitignored via data/.gitignore). Reads
site/data/ncaab_season_2027.json, data/ncaab/games.csv and
data/ncaab/merged/<date>.json read-only. Nothing here feeds the
model, the picks, or the site.

Purpose: Model Improvement Program Study #2 (2026-11-08; goal files:
ncaab-improvement-study-2-2026-11-08.md, pre-registration frozen in
hidden_files/ncaab-study2/prereg.md) found the NCAAB totals are
over-dispersed in every phase (calibration slope 0.748 vs the line's
0.972 -- the CFB totals disease in a second sport). Candidate N3 --
totals shrinkage toward the expanding league anchor -- cleared its
pre-registered bar in full: walk-forward chose s* = 0.75 in 9 of 11
seasons, pooled total RMSE gain +0.200 (twice the bar), improved in
11 of 11 seasons, O/U winners/week +1.22. Verdict PROMISING. Bryant
approved this live shadow on 2026-11-08 ("Shadow N3 now").
Adoption remains his separate call; this watch changes nothing.

Arm (the pre-registered N3 transform at the fixed modal s = 0.75,
per Study #2 Part E -- the shadow does not re-select per season):
    total' = lg_total_prior + 0.75 * (our_total - lg_total_prior)
where lg_total_prior is the expanding mean of actual totals over
all prior games. Construction route: the live model applies NO
shrinkage today -- the season log's our_total IS the raw model
total -- so the arm is a direct deterministic transform of the
published board's totals (the CFB C1/C2 shadow precedent: arms as
functions of the published predictions guarantee live and shadow
are graded on identical games with identical lines). The only
recovered quantity is the anchor, computed live exactly as the
pre-registration specifies ("computable live from training finals
through yesterday"):

    lg_total_prior(day entry) = mean actual total over the
    training corpus daily_picks.py itself assembled for that
    entry -- games.csv rows with a recorded spread AND total (the
    study frame's lined corpus; build_frame.py's filter) dated on
    or before the cutoff, plus finals from data/ncaab/merged/
    day files dated on or before the cutoff (preseason/exhibition
    finals excluded, mirroring load_training_rows), where the
    cutoff = (PT date of the entry's `generated` stamp) - 1 day
    -- daily_picks' own "through yesterday" boundary. The anchor
    is frozen into the day's snapshot file at snapshot time.

Published our_total is rounded to 0.1 by daily_picks.py, so the arm
inherits at most 0.05 of rounding -- the same published-fields
basis the CFB arms used.

Pick rules (live rules, pre-registration protocol): totals pick
when 1.0 <= |total' - line_total| <= 8.5 (the 8.5 circuit
breaker), over above the line, under below. The live arm uses the
board's own published pick_total. Errors are computed on every
graded game, picks or not. Grading uses grade_day.grade_pick
verbatim for both arms; finals come from data/ncaab/merged/
<date>.json matched with shadow_bigline.py's logic, with the same
labeled season-log fallback (never overrides a merged match).

Population: every game in each day entry the nightly picks run
appends to the season log from 2026-11-08 on (games with a model
total and a market total), whether or not it carried a published
totals pick. The shadow record starts with the first day entry
snapshotted after setup (2026-11-08); the 2026-11-07 dry run used
to validate this script was validation-only and is NOT part of
the record.

Settle design: an INTERIM read rides the 2026-11-22 NCAAB decision
day (this arm's rows reported alongside the big-line shadow read;
the watch continues after). FINAL settle on 2026-12-27: the full
live-vs-N3 read (total RMSE and O/U winners/week on identical
games) with the adoption question for Bryant; the cron job then
removes itself. No new pass/fail bar is set for the shadow -- the
pre-registered backtest bar is already cleared; the settle read
informs Bryant's adoption call.

Modes:
    snapshot  copy window slates from the season log, computing
              the N3 arm per game
    grade     grade snapshotted games from merged finals; rebuild
              the ledger
    all       both (default; what the nightly cron runs)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from grade_day import grade_pick  # noqa: E402
from teams import normalize_team  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data" / "ncaab"
SITE_DATA = REPO / "site" / "data"
SHADOW_DIR = REPO / "data" / "shadow" / "ncaab_n3"
PT = ZoneInfo("America/Los_Angeles")

S_N3 = 0.75
TOTAL_PICK_MIN = 1.0
TOTAL_CIRCUIT = 8.5

RECORD_START = date(2026, 11, 8)   # first day entries in the record
WINDOW_END = date(2026, 12, 27)     # final settle date
INTERIM_DATE = date(2026, 11, 22)   # NCAAB decision day

# Mirrors daily_picks.SEASON_OPENERS (preseason detection for the
# anchor's merged-finals inclusion).
SEASON_OPENERS = {2027: date(2026, 11, 1)}

ARM_DEFINITION = (
    "total' = lg_total_prior + 0.75 * (our_total - lg_total_prior); "
    "s = 0.75 fixed (Study #2 walk-forward modal choice, Part E). "
    "lg_total_prior = expanding mean of actual totals over the "
    "training corpus daily_picks.py assembled for the day entry "
    "(games.csv lined rows + merged finals, both through the "
    "generation date minus one day; preseason finals excluded)."
)

SETTLE_FRAMING = (
    "Settle read, live vs N3 on identical games: total RMSE and "
    "O/U winners/week. Backtest reference (Study #2, pre-registered "
    "bar cleared): total RMSE gain +0.200, 11/11 seasons, O/U "
    "+1.22 winners/week. Interim read rides the 2026-11-22 NCAAB "
    "decision day; final settle 2026-12-27 with the adoption "
    "question. Adoption is Bryant's separate call."
)


def now_pt() -> datetime:
    return datetime.now(PT)


def season_of(d: date) -> int:
    """NCAAB season ending year (mirrors daily_picks.season_of)."""
    return d.year + 1 if d.month >= 11 else d.year


def is_preseason(commence: date) -> bool:
    """Mirrors daily_picks.is_preseason."""
    opener = SEASON_OPENERS.get(season_of(commence))
    if opener is None:
        opener = date(season_of(commence) - 1, 11, 1)
    return commence < opener


def window_dates(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def canonical_teams(season: int) -> set[str] | None:
    """Mirrors grade_day.py's fallback chain for the D1 list."""
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


_anchor_cache: dict[date, tuple[float, int, int, int]] = {}


def compute_lg_total_prior(cutoff: date) -> tuple[float, int, int, int]:
    """(anchor, n_hist, n_merged, n_total) -- the expanding mean of
    actual totals over daily_picks' training corpus through the
    cutoff (see module docstring for the exact corpus)."""
    if cutoff in _anchor_cache:
        return _anchor_cache[cutoff]
    tot_sum, n_hist = 0.0, 0
    with open(DATA / "games.csv", newline="") as f:
        for r in csv.DictReader(f):
            if not r["spread"] or not r["total"]:
                continue  # the frame's lined-games filter
            if r["date"] > cutoff.isoformat():
                continue
            tot_sum += float(r["home_score"]) + float(r["away_score"])
            n_hist += 1
    n_merged = 0
    merged_dir = DATA / "merged"
    if merged_dir.is_dir():
        for p in sorted(merged_dir.glob("*.json")):
            stem = p.stem
            if len(stem) != 10 or stem > cutoff.isoformat():
                continue
            day = json.loads(p.read_text())
            for g in day.get("games", []):
                fin = g.get("final")
                if not fin:
                    continue
                commence = datetime.fromisoformat(
                    g["commence_time"]).date()
                if is_preseason(commence):
                    continue
                tot_sum += (float(fin["home_score"])
                            + float(fin["away_score"]))
                n_merged += 1
    n = n_hist + n_merged
    out = (round(tot_sum / n, 4) if n else float("nan"),
           n_hist, n_merged, n)
    _anchor_cache[cutoff] = out
    return out


def generation_cutoff(day: dict) -> date:
    """daily_picks trains through (run date - 1); the entry's
    `generated` stamp carries the run date (PT)."""
    gen = str(day.get("generated", ""))
    gen_date = date.fromisoformat(gen[:10])
    return gen_date - timedelta(days=1)


def n3_arm(our_total: float, line_total: float,
           lg_prior: float) -> tuple[float, str | None]:
    """(total', pick) for the N3 arm from a published pick row."""
    total = round(lg_prior + S_N3 * (our_total - lg_prior), 1)
    edge = round(total - line_total, 1)
    pick = None
    if TOTAL_PICK_MIN <= edge <= TOTAL_CIRCUIT:
        pick = "over"
    elif -TOTAL_CIRCUIT <= edge <= -TOTAL_PICK_MIN:
        pick = "under"
    return total, pick


def extract_rows(day: dict, lg_prior: float) -> list[dict]:
    """Pre-result fields + N3 arm for every priced game that day."""
    rows = []
    for p in day.get("picks", []):
        if p.get("our_total") is None or p.get("line_total") is None:
            continue
        n3_total, n3_pick = n3_arm(p["our_total"], p["line_total"],
                                   lg_prior)
        rows.append({
            "date": p.get("gameday") or day.get("date"),
            "home": p["home"],
            "away": p["away"],
            "neutral": bool(p.get("neutral", False)),
            "line_total": p["line_total"],
            "live_total": p["our_total"],
            "live_pick": p.get("pick_total"),
            "lg_total_prior": lg_prior,
            "n3_total": n3_total,
            "n3_pick": n3_pick,
            "final": None,
            "final_source": None,
            "actual_total": None,
            "live_total_err": None,
            "n3_total_err": None,
            "live_ou": None,
            "n3_ou": None,
        })
    return rows


def rows_hash(rows: list[dict]) -> str:
    keys = ("date", "home", "away", "neutral", "line_total",
            "live_total", "live_pick", "lg_total_prior", "n3_total",
            "n3_pick")
    canon = [{k: r[k] for k in keys} for r in rows]
    return hashlib.sha256(
        json.dumps(canon, sort_keys=True).encode()).hexdigest()


def snapshot(start: date, end: date, shadow_dir: Path) -> dict:
    days_dir = shadow_dir / "days"
    days_dir.mkdir(parents=True, exist_ok=True)
    logs: dict[int, dict | None] = {}
    result = {}
    # Slates exist only once the nightly picks run appends them (game
    # day = run day or run day + 1), so future dates are skipped
    # silently; they enter the window as their entries land.
    last_sought = min(end, now_pt().date() + timedelta(days=1))
    for d in window_dates(start, last_sought):
        season = season_of(d)
        if season not in logs:
            logs[season] = load_season_log(season)
        log = logs[season]
        day = (log or {}).get("days", {}).get(d.isoformat())
        dest = days_dir / f"{d.isoformat()}.json"
        if day is None:
            result[d.isoformat()] = "no slate in season log (yet)"
            continue
        cutoff = generation_cutoff(day)
        lg_prior, n_hist, n_merged, n_tot = compute_lg_total_prior(
            cutoff)
        rows = extract_rows(day, lg_prior)
        h = rows_hash(rows)
        prev = json.loads(dest.read_text()) if dest.exists() else None
        graded = bool(prev) and any(
            g.get("final") is not None for g in prev.get("games", []))
        if prev and prev.get("source_hash") == h:
            result[d.isoformat()] = f"current ({len(rows)} games)"
            continue
        if graded:
            # Never rewrite history after finals land.
            prev["source_changed_after_grading"] = True
            dest.write_text(json.dumps(prev, indent=2))
            result[d.isoformat()] = (
                "source changed after grading; frozen snapshot kept")
            continue
        doc = {
            "watch": "ncaab_n3_shadow",
            "date": d.isoformat(),
            "source": (f"site/data/ncaab_season_{season}.json "
                       f"days[{d.isoformat()}]"),
            "source_generated": day.get("generated"),
            "source_hash": h,
            "first_seen": (prev or {}).get("first_seen")
            or now_pt().strftime("%Y-%m-%d %H:%M %Z"),
            "snapshotted_at": now_pt().strftime("%Y-%m-%d %H:%M %Z"),
            "preseason": bool(day.get("preseason", False)),
            "s_n3": S_N3,
            "lg_total_prior": lg_prior,
            "lg_total_prior_cutoff": cutoff.isoformat(),
            "lg_total_prior_games": n_tot,
            "lg_total_prior_hist_games": n_hist,
            "lg_total_prior_merged_games": n_merged,
            "lg_total_prior_method": (
                "mean actual total over games.csv rows with a "
                "recorded spread and total, plus merged finals, "
                "both dated on or before the cutoff (generation "
                "date - 1), preseason finals excluded -- "
                "daily_picks.py's training corpus"),
            "games": rows,
        }
        dest.write_text(json.dumps(doc, indent=2))
        result[d.isoformat()] = (
            f"snapshotted ({len(rows)} games, anchor {lg_prior} "
            f"on {n_tot} games through {cutoff.isoformat()})")
    for k, v in result.items():
        print(f"snapshot {k}: {v}")
    return result


def load_finals(d: date) -> dict[tuple[str, str], tuple[float, float]]:
    """Finals from the same merged file grade_day.py uses, matched
    the same way (mirrors shadow_bigline.py)."""
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


def season_log_results(d: date) -> dict[tuple[str, str], tuple[float, float]]:
    """Stored per-pick results in the season log -- grade_day.py's
    own output, from the same merged finals. Labeled fallback only;
    never overrides a merged-file match."""
    log = load_season_log(season_of(d))
    day = (log or {}).get("days", {}).get(d.isoformat())
    out = {}
    for p in (day or {}).get("picks", []):
        r = p.get("result")
        if r and "home_score" in r and "away_score" in r:
            out[(p["home"], p["away"])] = (float(r["home_score"]),
                                           float(r["away_score"]))
    return out


def apply_final(g: dict, hs: float, aws: float, source: str) -> None:
    at = hs + aws
    g["final"] = {"home_score": hs, "away_score": aws}
    g["final_source"] = source
    g["actual_total"] = at
    live = grade_pick({"pick_spread": None,
                       "pick_total": g["live_pick"],
                       "line_total": g["line_total"]}, hs, aws)
    g["live_ou"] = live.get("ou")
    n3 = grade_pick({"pick_spread": None,
                     "pick_total": g["n3_pick"],
                     "line_total": g["line_total"]}, hs, aws)
    g["n3_ou"] = n3.get("ou")
    g["live_total_err"] = round(g["live_total"] - at, 2)
    g["n3_total_err"] = round(g["n3_total"] - at, 2)


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


def wlp(rows: list[dict], key: str) -> tuple[int, int, int, int]:
    """(wins, losses, pushes, picks) for a graded-result field."""
    vals = [r[key] for r in rows if r.get(key) is not None]
    return (vals.count("win"), vals.count("loss"),
            vals.count("push"), len(vals))


def rmse(rows: list[dict], key: str) -> float | None:
    vals = [r[key] for r in rows if r.get(key) is not None]
    if not vals:
        return None
    return round(math.sqrt(statistics.mean(v * v for v in vals)), 2)


def day_stats(rows: list[dict]) -> dict:
    graded = [r for r in rows if r.get("final") is not None]
    lo = wlp(graded, "live_ou")
    no = wlp(graded, "n3_ou")
    return {
        "games": len(rows), "graded": len(graded),
        "total_rmse_live": rmse(graded, "live_total_err"),
        "total_rmse_n3": rmse(graded, "n3_total_err"),
        "ou_live": {"w": lo[0], "l": lo[1], "p": lo[2], "picks": lo[3]},
        "ou_n3": {"w": no[0], "l": no[1], "p": no[2], "picks": no[3]},
    }


def rebuild_ledger(start: date, end: date, shadow_dir: Path) -> dict:
    days_dir = shadow_dir / "days"
    day_docs: dict[str, dict] = {}
    if days_dir.is_dir():
        for dest in sorted(days_dir.glob("*.json")):
            doc = json.loads(dest.read_text())
            if start <= date.fromisoformat(doc["date"]) <= end:
                day_docs[doc["date"]] = doc
    per_day = {}
    all_rows: list[dict] = []
    iso_weeks: set[tuple[int, int]] = set()
    for key in sorted(day_docs):
        rows = day_docs[key].get("games", [])
        all_rows.extend(rows)
        st = day_stats(rows)
        per_day[key] = {
            **st,
            "lg_total_prior": day_docs[key].get("lg_total_prior"),
            "source_generated": day_docs[key].get("source_generated"),
            "note": day_docs[key].get("source_generated") or "",
        }
        if st["graded"]:
            iso = date.fromisoformat(key).isocalendar()
            iso_weeks.add((iso.year, iso.week))
    cum = day_stats(all_rows)
    nw = len(iso_weeks)

    def per_wk(wins: int) -> float | None:
        return round(wins / nw, 2) if nw else None

    winners = {
        "iso_weeks_with_graded_games": nw,
        "ou_winners_per_week_live": per_wk(cum["ou_live"]["w"]),
        "ou_winners_per_week_n3": per_wk(cum["ou_n3"]["w"]),
    }
    if nw:
        winners["ou_delta_n3_minus_live"] = round(
            winners["ou_winners_per_week_n3"]
            - winners["ou_winners_per_week_live"], 2)
    today = now_pt().date()
    if today >= WINDOW_END:
        status = (
            "FINAL SETTLE -- live vs N3 on identical games: total "
            f"RMSE live {cum['total_rmse_live']} vs N3 "
            f"{cum['total_rmse_n3']}; O/U winners/week live "
            f"{winners['ou_winners_per_week_live']} vs N3 "
            f"{winners['ou_winners_per_week_n3']} (delta "
            f"{winners.get('ou_delta_n3_minus_live')}) over {nw} "
            "ISO week(s). Adoption is Bryant's separate call.")
    elif today >= INTERIM_DATE:
        status = (
            "INTERIM (Nov 22 NCAAB decision day) -- live vs N3 so "
            f"far: total RMSE live {cum['total_rmse_live']} vs N3 "
            f"{cum['total_rmse_n3']}; O/U winners/week live "
            f"{winners['ou_winners_per_week_live']} vs N3 "
            f"{winners['ou_winners_per_week_n3']}. Watch continues "
            "to the Dec 27 final settle.")
    else:
        status = "collecting"
    ledger = {
        "watch": "ncaab_n3_shadow",
        "purpose": ("Pre-registered live shadow of Model Improvement "
                    "Program Study #2's PROMISING candidate N3 "
                    "(totals shrinkage to s = 0.75 toward the "
                    "expanding league anchor; 2026-11-08; Bryant "
                    "approved the shadow the same day). Bookkeeping "
                    "only; nothing here feeds the model, the site, "
                    "or any pick."),
        "arm_definition": ARM_DEFINITION,
        "settle_framing": SETTLE_FRAMING,
        "window": {"start": start.isoformat(), "end": end.isoformat(),
                   "interim": INTERIM_DATE.isoformat(),
                   "final_settle": WINDOW_END.isoformat()},
        "s_n3": S_N3,
        "updated": now_pt().strftime("%Y-%m-%d %H:%M %Z"),
        "days": per_day,
        "cumulative": cum,
        "winners_per_week": winners,
        "games_snapshotted": len(all_rows),
        "games_graded": cum["graded"],
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
        "# NCAAB N3 shadow watch -- ledger",
        "",
        ledger["purpose"],
        "",
        f"**Arm:** {ARM_DEFINITION}",
        "",
        f"**Settle framing:** {SETTLE_FRAMING}",
        "",
        f"**Window:** {start.isoformat()} to {end.isoformat()} "
        f"(interim {INTERIM_DATE.isoformat()}, final settle "
        f"{WINDOW_END.isoformat()})",
        "",
        f"**Status:** {status}",
        "",
        "## Cumulative (identical games, live vs N3)",
        "",
        f"- Total RMSE: live {cum['total_rmse_live']} vs N3 "
        f"{cum['total_rmse_n3']}",
        f"- O/U: live {cum['ou_live']['w']}-{cum['ou_live']['l']}-"
        f"{cum['ou_live']['p']} ({cum['ou_live']['picks']} picks) vs "
        f"N3 {cum['ou_n3']['w']}-{cum['ou_n3']['l']}-{cum['ou_n3']['p']} "
        f"({cum['ou_n3']['picks']} picks)",
        f"- O/U winners/week over {nw} ISO week(s) with graded "
        f"games: live {winners['ou_winners_per_week_live']} vs N3 "
        f"{winners['ou_winners_per_week_n3']}",
        "",
        "## Days",
        "",
    ]
    for k in sorted(per_day):
        s = per_day[k]
        lines.append(
            f"- {k}: {s['graded']}/{s['games']} graded (anchor "
            f"{s['lg_total_prior']}) -- total RMSE live "
            f"{s['total_rmse_live']} / N3 {s['total_rmse_n3']}; O/U "
            f"live {s['ou_live']['w']}-{s['ou_live']['l']}-"
            f"{s['ou_live']['p']} vs N3 {s['ou_n3']['w']}-"
            f"{s['ou_n3']['l']}-{s['ou_n3']['p']}")
    lines += ["", f"Updated: {ledger['updated']}"]
    (shadow_dir / "LEDGER.md").write_text("\n".join(lines) + "\n")
    print(f"grade: ledger rebuilt -- {cum['graded']} graded of "
          f"{len(all_rows)} snapshotted across {len(day_docs)} "
          f"day(s); status: {status}")
    return ledger


def main() -> None:
    ap = argparse.ArgumentParser(
        description="NCAAB N3 shadow watch (bookkeeping only)")
    ap.add_argument("mode", nargs="?", default="all",
                    choices=("snapshot", "grade", "all"))
    ap.add_argument("--start", default=None,
                    help="window start YYYY-MM-DD (default 2026-11-08)")
    ap.add_argument("--end", default=None,
                    help="window end YYYY-MM-DD (default 2026-12-27)")
    ap.add_argument("--dir", default=None,
                    help="shadow dir override (validation runs only; "
                         "default data/shadow/ncaab_n3)")
    args = ap.parse_args()
    start = (date.fromisoformat(args.start) if args.start
             else RECORD_START)
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
