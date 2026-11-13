"""Shadow C1/C2 watch -- bookkeeping ONLY. Never writes outside
data/shadow/cfb_c1c2/ (gitignored via data/.gitignore). Reads
site/data/cfb_picks.json, site/data/cfb_season_2026.json,
data/cfb/raw/games_2026.json and data/cfb/cfb_games.parquet read-only.
Nothing here feeds the model, the picks, or the site.

Purpose: CFB Improvement Study #1 (2026-11-07, Model Improvement
Program; goal files: cfb-improvement-study-1-2026-11-07.md) found the
CFB model's disease is variance, not bias (calibration slope 0.73 vs
the market's 1.01), and two pre-registered candidates cleared their
walk-forward bars (Part D): C1 totals shrinkage extension and C2
margin shrinkage. Bryant approved shadowing BOTH on 2026-11-07.
Adoption remains his separate call; this watch changes nothing.

Arms (Part C definitions, applied to the published board):
  C1  total' = epa_const + s1*(raw_total - epa_const), where raw_total
      is the model's unshrunk total. The live total is
      epa_const + 0.7*dev + wind_adj (predict() at TOTAL_SHRINKAGE=0.7,
      then the adopted wind hinge), so dev is recovered from the
      published fields as (our_total - wind_adj_pts - epa_const)/0.7
      and total' = epa_const + s1*dev + wind_adj_pts -- the wind hinge
      is applied identically to both arms, so the ONLY difference
      between the C1 arm and the live board is the shrinkage factor.
  C2  margin' = s2*our_spread, from the published margin directly.
Transforming the published predictions (rather than re-running the
ratings) mirrors the NFL QB-ablation shadow's method: the arms are
deterministic functions of the live board, so live and shadow are
graded on identical games with identical lines. epa_const is
recomputed with cfb_weekly_picks.py's own formula (mean total of
completed current-season games in cfb_games.parquet); the weekly
snapshot runs Friday midday, after the Friday-morning board
generation and before any Friday kickoff or parquet refresh, so the
recomputed anchor is the anchor the board itself used.

Scale selection (the pre-registered rule, Part C: per evaluation
season, s chosen on prior seasons only, min prior pooled RMSE over
the grid; 2026 is the evaluation season, so the prior pool is all of
frame B, seasons 2014-2025 -- 2026 rows never enter the selection):
  s1 = 0.40 (grid 0.40-0.70; pooled prior totals RMSE 17.394 vs
       17.401 at 0.45 -- the argmin sits ON the grid boundary, the
       same boundary touch the study reported for its 2025
       walk-forward pick and did not chase; the grid is not extended
       here). The identical computation reproduces the study's
       per-season walk-forward picks (0.45 modal, 0.50 twice, 0.40
       for 2025).
  s2 = 0.75 (grid 0.70-1.00; pooled prior margin RMSE 17.351 vs
       17.370 at 0.70 and 17.369 at 0.80 -- matches the study's modal
       walk-forward pick).
Scales are FIXED for the whole window (the pre-registration selects
per season, not per week).

Pick rules (live rules, Part C protocol): spread pick when
|edge| >= 0.5 (edge rounded to 0.1 first, as the live generator
rounds); totals pick when 1.0 <= |edge| <= 8.5 (the 8.5 circuit
breaker). The live arm uses the board's own published picks. Errors
are computed on every graded game, picks or not. Grading uses
cfb_grade_week.grade_pick verbatim for all three arms.

Finals: data/cfb/raw/games_2026.json (the stored finals the nightly
merge grades from), matched by (week, home, away); a game the raw
file cannot match falls back -- labeled final_source=
"season_log_result" per game and counted in the ledger -- to the
result the nightly merge stored in the season log. The fallback
never overrides a raw-file match.

Window: every board the Friday refresh generates from Week 10
through championship weekend (boards generated on or before
2026-12-06; postseason/bowl boards are out of scope -- postseason
was Candidate C4's segment, killed in Study #1, and the settle was
set for early December). Snapshot excludes games already final on
the board at snapshot time (counted and listed in the week file).

Settle read (after all window games are graded, expected at the
Friday 2026-12-11 run): per arm vs live on identical games -- C1:
totals RMSE and O/U winners/week; C2: margin RMSE and ATS
winners/week. Study #1's bars frame the read (C1: error gain with
O/U winners/week not > 1.0 below live; C2: error gain with ATS
winners/week not > 1.0 below live). The arms were tested
independently; there is deliberately NO combined C1+C2 arm.

Modes:
    snapshot  snapshot the current board's week into the shadow
    grade     grade snapshotted games from stored finals; rebuild ledger
    all       both (default; what the weekly cron runs)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cfb_grade_week import grade_pick  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SITE_DATA = REPO / "site" / "data"
CFB_DATA = REPO / "data" / "cfb"
SHADOW_DIR = REPO / "data" / "shadow" / "cfb_c1c2"
PT = ZoneInfo("America/Los_Angeles")

SEASON = 2026
S_C1 = 0.40
S_C2 = 0.75
LIVE_TOTAL_S = 0.7
SPREAD_PICK_MIN = 0.5
TOTAL_PICK_MIN = 1.0
TOTAL_CIRCUIT = 8.5
WINDOW_LAST_BOARD_DATE = date(2026, 12, 6)  # championship weekend

SELECTION_PROVENANCE = (
    "Scales selected 2026-11-07 by the pre-registered rule (Study #1 "
    "Part C: per evaluation season, argmin over the grid of pooled "
    "RMSE on prior seasons only), applied to evaluation season 2026 "
    "with the prior pool = frame B seasons 2014-2025 (8,947 games; "
    "2026 rows excluded). C1 totals: s*=0.40 (pooled RMSE 17.394 vs "
    "17.401 @0.45, 17.680 @0.70 eval-pool) -- argmin on the grid "
    "boundary, reported not chased, grid not extended. C2 margins: "
    "s*=0.75 (17.351 vs 17.370 @0.70, 17.369 @0.80). Fixed for the "
    "whole window."
)

SETTLE_FRAMING = (
    "Settle read, live vs shadow on identical games. C1 (totals "
    "shrinkage 0.70 -> 0.40): totals RMSE and O/U winners/week. C2 "
    "(margin shrinkage 1.00 -> 0.75): margin RMSE and ATS "
    "winners/week. Study #1 guardrails frame the read: an arm "
    "supports adoption only if its error improves while its "
    "winners/week stays within 1.0 of live. Adoption is Bryant's "
    "separate call either way; the arms were tested independently "
    "and there is no combined arm."
)


def now_pt() -> datetime:
    return datetime.now(PT)


def compute_epa_const() -> tuple[float, int]:
    """The live generator's anchor: mean total of completed
    current-season games in cfb_games.parquet (cfb_weekly_picks.py,
    verbatim formula). Returns (epa_const, n_games)."""
    import pandas as pd
    done = pd.read_parquet(CFB_DATA / "cfb_games.parquet")
    done = done[(done["season"] == SEASON) & done["home_score"].notna()]
    if not len(done):
        return 58.0, 0
    return float((done["home_score"] + done["away_score"]).mean()), len(done)


def c1_arm(p: dict, epa_const: float) -> tuple[float, str | None]:
    """(total', pick) for the C1 arm from a published pick row."""
    wind = p.get("wind_adj_pts") or 0.0
    dev = (p["our_total"] - wind - epa_const) / LIVE_TOTAL_S
    total = round(epa_const + S_C1 * dev + wind, 1)
    edge = round(total - p["line_total"], 1)
    pick = None
    if TOTAL_PICK_MIN <= edge <= TOTAL_CIRCUIT:
        pick = "over"
    elif -TOTAL_CIRCUIT <= edge <= -TOTAL_PICK_MIN:
        pick = "under"
    return total, pick


def c2_arm(p: dict) -> tuple[float, str | None]:
    """(margin', pick) for the C2 arm from a published pick row."""
    margin = round(S_C2 * p["our_spread"], 1)
    edge = round(margin - p["line_spread"], 1)
    pick = None
    if edge >= SPREAD_PICK_MIN:
        pick = "home"
    elif edge <= -SPREAD_PICK_MIN:
        pick = "away"
    return margin, pick


def rows_hash(rows: list[dict]) -> str:
    keys = ("away", "home", "gameday", "neutral", "line_spread",
            "line_total", "live_spread", "live_total", "wind_adj_pts",
            "live_pick_spread", "live_pick_total", "c1_total",
            "c1_pick", "c2_margin", "c2_pick")
    canon = [{k: r[k] for k in keys} for r in rows]
    return hashlib.sha256(
        json.dumps(canon, sort_keys=True).encode()).hexdigest()


def extract_rows(board: dict, epa_const: float) -> tuple[list[dict], list[str]]:
    rows, excluded = [], []
    for p in board.get("picks", []):
        label = f"{p['away']} @ {p['home']}"
        if p.get("result"):
            excluded.append(label)
            continue
        if p.get("our_spread") is None or p.get("our_total") is None:
            excluded.append(f"{label} (no model prediction)")
            continue
        c1_total, c1_pick = c1_arm(p, epa_const)
        c2_margin, c2_pick = c2_arm(p)
        rows.append({
            "away": p["away"], "home": p["home"],
            "gameday": p.get("gameday"),
            "weekday": p.get("weekday"),
            "neutral": bool(p.get("neutral", False)),
            "line_spread": p["line_spread"],
            "line_total": p["line_total"],
            "live_spread": p["our_spread"],
            "live_total": p["our_total"],
            "wind_mph": p.get("wind_mph"),
            "wind_adj_pts": p.get("wind_adj_pts") or 0.0,
            "live_pick_spread": p.get("pick_spread"),
            "live_pick_total": p.get("pick_total"),
            "c1_total": c1_total, "c1_pick": c1_pick,
            "c2_margin": c2_margin, "c2_pick": c2_pick,
            "final": None, "final_source": None,
            "actual_margin": None, "actual_total": None,
            "live_ats": None, "live_ou": None,
            "c1_ou": None, "c2_ats": None,
            "live_margin_err": None, "c2_margin_err": None,
            "live_total_err": None, "c1_total_err": None,
        })
    return rows, excluded


def snapshot(shadow_dir: Path) -> dict:
    board_path = SITE_DATA / "cfb_picks.json"
    board = json.loads(board_path.read_text())
    week = int(board["week"])
    generated = str(board.get("generated", ""))
    try:
        board_date = date.fromisoformat(generated[:10])
    except ValueError:
        board_date = None
    weeks_dir = shadow_dir / "weeks"
    weeks_dir.mkdir(parents=True, exist_ok=True)
    dest = weeks_dir / f"week-{week:02d}.json"
    if board_date is not None and board_date > WINDOW_LAST_BOARD_DATE:
        msg = (f"board week {week} generated {generated} is past the "
               f"window (boards through {WINDOW_LAST_BOARD_DATE}); "
               "not snapshotted")
        print(f"snapshot: {msg}")
        return {"week": week, "status": msg}
    epa_const, epa_n = compute_epa_const()
    epa_const = round(epa_const, 4)
    rows, excluded = extract_rows(board, epa_const)
    h = rows_hash(rows)
    prev = json.loads(dest.read_text()) if dest.exists() else None
    if prev and prev.get("source_hash") == h:
        msg = f"week {week} current ({len(rows)} games)"
        print(f"snapshot: {msg}")
        return {"week": week, "status": msg}
    graded = bool(prev) and any(
        g.get("final") is not None for g in prev.get("games", []))
    if prev and graded:
        prev["source_changed_after_grading"] = True
        dest.write_text(json.dumps(prev, indent=2))
        msg = (f"week {week} source changed after grading; "
               "frozen snapshot kept")
        print(f"snapshot: {msg}")
        return {"week": week, "status": msg}
    doc = {
        "watch": "cfb_c1c2_shadow",
        "season": SEASON,
        "week": week,
        "source": "site/data/cfb_picks.json",
        "source_generated": generated,
        "source_hash": h,
        "first_seen": (prev or {}).get("first_seen")
        or now_pt().strftime("%Y-%m-%d %H:%M %Z"),
        "snapshotted_at": now_pt().strftime("%Y-%m-%d %H:%M %Z"),
        "epa_const": epa_const,
        "epa_const_games": epa_n,
        "epa_const_method": ("mean total of completed 2026 games in "
                             "data/cfb/cfb_games.parquet, "
                             "cfb_weekly_picks.py's own formula"),
        "s_c1": S_C1, "s_c2": S_C2,
        "excluded_final_at_snapshot": excluded,
        "games": rows,
    }
    dest.write_text(json.dumps(doc, indent=2))
    msg = (f"week {week} snapshotted ({len(rows)} games, "
           f"{len(excluded)} already final excluded, "
           f"epa_const {epa_const} on {epa_n} games)")
    print(f"snapshot: {msg}")
    return {"week": week, "status": msg}


def load_raw_finals() -> tuple[dict, dict]:
    """Stored finals from data/cfb/raw/games_2026.json -- the file the
    nightly merge grades from. Returns (by_week_key, by_team_key);
    by_team_key only holds matchups unique across the season."""
    p = CFB_DATA / "raw" / f"games_{SEASON}.json"
    by_week: dict[tuple, tuple[float, float]] = {}
    by_team: dict[tuple, tuple[float, float]] = {}
    counts: dict[tuple, int] = {}
    if not p.exists():
        return by_week, by_team
    for g in json.loads(p.read_text()):
        if not g.get("completed"):
            continue
        hp, ap = g.get("homePoints"), g.get("awayPoints")
        if hp is None or ap is None:
            continue
        key = (g["homeTeam"], g["awayTeam"])
        by_week[(g.get("week"), g["homeTeam"], g["awayTeam"])] = (
            float(hp), float(ap))
        counts[key] = counts.get(key, 0) + 1
        by_team[key] = (float(hp), float(ap))
    by_team = {k: v for k, v in by_team.items() if counts[k] == 1}
    return by_week, by_team


def season_log_results(week: int) -> dict[tuple[str, str], dict]:
    """Stored per-pick results in the season log -- the nightly
    merge's own output, from the same finals. Labeled fallback only."""
    p = SITE_DATA / f"cfb_season_{SEASON}.json"
    if not p.exists():
        return {}
    log = json.loads(p.read_text())
    wk = (log.get("weeks") or {}).get(str(week)) or {}
    out = {}
    for pk in wk.get("picks", []):
        r = pk.get("result")
        if r and "home_score" in r and "away_score" in r:
            out[(pk["home"], pk["away"])] = r
    return out


def apply_final(g: dict, hs: float, aws: float, source: str) -> None:
    am = hs - aws
    at = hs + aws
    g["final"] = {"home_score": hs, "away_score": aws}
    g["final_source"] = source
    g["actual_margin"] = am
    g["actual_total"] = at
    live = grade_pick({"pick_spread": g["live_pick_spread"],
                       "pick_total": g["live_pick_total"],
                       "line_spread": g["line_spread"],
                       "line_total": g["line_total"]}, hs, aws)
    g["live_ats"] = live.get("ats")
    g["live_ou"] = live.get("ou")
    c1 = grade_pick({"pick_spread": None, "pick_total": g["c1_pick"],
                     "line_spread": g["line_spread"],
                     "line_total": g["line_total"]}, hs, aws)
    g["c1_ou"] = c1.get("ou")
    c2 = grade_pick({"pick_spread": g["c2_pick"], "pick_total": None,
                     "line_spread": g["line_spread"],
                     "line_total": g["line_total"]}, hs, aws)
    g["c2_ats"] = c2.get("ats")
    g["live_margin_err"] = round(g["live_spread"] - am, 2)
    g["c2_margin_err"] = round(g["c2_margin"] - am, 2)
    g["live_total_err"] = round(g["live_total"] - at, 2)
    g["c1_total_err"] = round(g["c1_total"] - at, 2)


def grade(shadow_dir: Path) -> dict:
    weeks_dir = shadow_dir / "weeks"
    by_week, by_team = load_raw_finals()
    if weeks_dir.is_dir():
        for dest in sorted(weeks_dir.glob("week-*.json")):
            doc = json.loads(dest.read_text())
            week = int(doc["week"])
            stored = None
            changed = False
            for g in doc.get("games", []):
                if g.get("final") is not None:
                    continue
                key_w = (week, g["home"], g["away"])
                key_t = (g["home"], g["away"])
                if key_w in by_week:
                    hs, aws = by_week[key_w]
                    apply_final(g, hs, aws, "raw_finals")
                    changed = True
                elif key_t in by_team:
                    hs, aws = by_team[key_t]
                    apply_final(g, hs, aws, "raw_finals")
                    changed = True
                else:
                    if stored is None:
                        stored = season_log_results(week)
                    r = stored.get(key_t)
                    if r:
                        apply_final(g, float(r["home_score"]),
                                    float(r["away_score"]),
                                    "season_log_result")
                        changed = True
            if changed:
                doc["graded_at"] = now_pt().strftime("%Y-%m-%d %H:%M %Z")
                dest.write_text(json.dumps(doc, indent=2))
                n = sum(1 for g in doc["games"]
                        if g.get("final") is not None)
                fb = sum(1 for g in doc["games"]
                         if g.get("final_source") == "season_log_result")
                print(f"grade week {week}: {n}/{len(doc['games'])} "
                      f"games graded ({fb} via season-log fallback)")
    return rebuild_ledger(shadow_dir)


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


def week_stats(rows: list[dict]) -> dict:
    graded = [r for r in rows if r.get("final") is not None]
    la = wlp(graded, "live_ats")
    ca = wlp(graded, "c2_ats")
    lo = wlp(graded, "live_ou")
    co = wlp(graded, "c1_ou")
    return {
        "games": len(rows), "graded": len(graded),
        "margin_rmse_live": rmse(graded, "live_margin_err"),
        "margin_rmse_c2": rmse(graded, "c2_margin_err"),
        "total_rmse_live": rmse(graded, "live_total_err"),
        "total_rmse_c1": rmse(graded, "c1_total_err"),
        "ats_live": {"w": la[0], "l": la[1], "p": la[2], "picks": la[3]},
        "ats_c2": {"w": ca[0], "l": ca[1], "p": ca[2], "picks": ca[3]},
        "ou_live": {"w": lo[0], "l": lo[1], "p": lo[2], "picks": lo[3]},
        "ou_c1": {"w": co[0], "l": co[1], "p": co[2], "picks": co[3]},
    }


def rebuild_ledger(shadow_dir: Path) -> dict:
    weeks_dir = shadow_dir / "weeks"
    week_docs: dict[int, dict] = {}
    if weeks_dir.is_dir():
        for dest in sorted(weeks_dir.glob("week-*.json")):
            doc = json.loads(dest.read_text())
            week_docs[int(doc["week"])] = doc
    per_week = {}
    all_rows: list[dict] = []
    for wk in sorted(week_docs):
        rows = week_docs[wk].get("games", [])
        all_rows.extend(rows)
        per_week[str(wk)] = {
            **week_stats(rows),
            "excluded_final_at_snapshot": len(
                week_docs[wk].get("excluded_final_at_snapshot", [])),
            "epa_const": week_docs[wk].get("epa_const"),
            "source_generated": week_docs[wk].get("source_generated"),
        }
    cum = week_stats(all_rows)
    full_weeks = [wk for wk in sorted(week_docs)
                  if per_week[str(wk)]["games"] > 0
                  and per_week[str(wk)]["graded"] == per_week[str(wk)]["games"]]
    nfw = len(full_weeks)

    def per_wk(wins: int) -> float | None:
        return round(wins / nfw, 2) if nfw else None

    winners = {
        "weeks_fully_graded": nfw,
        "ats_winners_per_week_live": per_wk(cum["ats_live"]["w"]),
        "ats_winners_per_week_c2": per_wk(cum["ats_c2"]["w"]),
        "ou_winners_per_week_live": per_wk(cum["ou_live"]["w"]),
        "ou_winners_per_week_c1": per_wk(cum["ou_c1"]["w"]),
    }
    if nfw:
        winners["ats_delta_c2_minus_live"] = round(
            winners["ats_winners_per_week_c2"]
            - winners["ats_winners_per_week_live"], 2)
        winners["ou_delta_c1_minus_live"] = round(
            winners["ou_winners_per_week_c1"]
            - winners["ou_winners_per_week_live"], 2)
    window_complete = bool(week_docs) and all(
        s["graded"] == s["games"] for s in per_week.values())
    final = now_pt().date() > WINDOW_LAST_BOARD_DATE
    if final and window_complete:
        status = (
            "FINAL -- window complete. "
            f"Totals: live RMSE {cum['total_rmse_live']} vs C1 "
            f"{cum['total_rmse_c1']}; O/U winners/week live "
            f"{winners['ou_winners_per_week_live']} vs C1 "
            f"{winners['ou_winners_per_week_c1']} "
            f"(delta {winners.get('ou_delta_c1_minus_live')}). "
            f"Margins: live RMSE {cum['margin_rmse_live']} vs C2 "
            f"{cum['margin_rmse_c2']}; ATS winners/week live "
            f"{winners['ats_winners_per_week_live']} vs C2 "
            f"{winners['ats_winners_per_week_c2']} "
            f"(delta {winners.get('ats_delta_c2_minus_live')}). "
            "Adoption is Bryant's separate call.")
    elif final:
        status = ("FINAL (window ended with ungraded games -- "
                  "figures cover graded games only).")
    else:
        status = "collecting"
    ledger = {
        "watch": "cfb_c1c2_shadow",
        "purpose": ("Pre-registered live shadow of CFB Improvement "
                    "Study #1's two PROMISING candidates (2026-11-07; "
                    "Bryant approved shadowing both the same day). "
                    "C1: totals shrinkage 0.70 -> 0.40. C2: margin "
                    "shrinkage 1.00 -> 0.75. Bookkeeping only; "
                    "nothing here feeds the model, the site, or any "
                    "pick. Arms run independently; no combined arm."),
        "selection_provenance": SELECTION_PROVENANCE,
        "settle_framing": SETTLE_FRAMING,
        "window": ("boards generated 2026-11-06 through "
                   f"{WINDOW_LAST_BOARD_DATE.isoformat()} (Weeks 10 "
                   "through championship weekend); postseason "
                   "excluded"),
        "s_c1": S_C1, "s_c2": S_C2,
        "updated": now_pt().strftime("%Y-%m-%d %H:%M %Z"),
        "weeks": per_week,
        "cumulative": cum,
        "winners_per_week": winners,
        "games_snapshotted": len(all_rows),
        "games_graded": cum["graded"],
        "finals_from_raw": sum(
            1 for r in all_rows if r.get("final_source") == "raw_finals"),
        "finals_from_season_log_fallback": sum(
            1 for r in all_rows
            if r.get("final_source") == "season_log_result"),
        "status": status,
    }
    shadow_dir.mkdir(parents=True, exist_ok=True)
    (shadow_dir / "ledger.json").write_text(json.dumps(ledger, indent=2))
    lines = [
        "# CFB C1/C2 shadow watch -- ledger",
        "",
        ledger["purpose"],
        "",
        f"**Selection:** {SELECTION_PROVENANCE}",
        "",
        f"**Settle framing:** {SETTLE_FRAMING}",
        "",
        f"**Window:** {ledger['window']}",
        "",
        f"**Status:** {status}",
        "",
        "## Cumulative (identical games, live vs shadow)",
        "",
        f"- Totals RMSE: live {cum['total_rmse_live']} vs C1 "
        f"{cum['total_rmse_c1']}",
        f"- O/U: live {cum['ou_live']['w']}-{cum['ou_live']['l']}-"
        f"{cum['ou_live']['p']} ({cum['ou_live']['picks']} picks) vs "
        f"C1 {cum['ou_c1']['w']}-{cum['ou_c1']['l']}-{cum['ou_c1']['p']} "
        f"({cum['ou_c1']['picks']} picks)",
        f"- Margin RMSE: live {cum['margin_rmse_live']} vs C2 "
        f"{cum['margin_rmse_c2']}",
        f"- ATS: live {cum['ats_live']['w']}-{cum['ats_live']['l']}-"
        f"{cum['ats_live']['p']} ({cum['ats_live']['picks']} picks) vs "
        f"C2 {cum['ats_c2']['w']}-{cum['ats_c2']['l']}-"
        f"{cum['ats_c2']['p']} ({cum['ats_c2']['picks']} picks)",
        f"- Winners/week over {nfw} fully graded week(s): ATS live "
        f"{winners['ats_winners_per_week_live']} vs C2 "
        f"{winners['ats_winners_per_week_c2']}; O/U live "
        f"{winners['ou_winners_per_week_live']} vs C1 "
        f"{winners['ou_winners_per_week_c1']}",
        "",
        "## Weeks",
        "",
    ]
    for wk in sorted(per_week, key=int):
        s = per_week[wk]
        lines.append(
            f"- Week {wk}: {s['graded']}/{s['games']} graded "
            f"(epa_const {s['epa_const']}; "
            f"{s['excluded_final_at_snapshot']} final at snapshot "
            f"excluded) -- totals RMSE live {s['total_rmse_live']} / "
            f"C1 {s['total_rmse_c1']}; O/U live "
            f"{s['ou_live']['w']}-{s['ou_live']['l']}-{s['ou_live']['p']} "
            f"vs C1 {s['ou_c1']['w']}-{s['ou_c1']['l']}-{s['ou_c1']['p']}; "
            f"margin RMSE live {s['margin_rmse_live']} / C2 "
            f"{s['margin_rmse_c2']}; ATS live "
            f"{s['ats_live']['w']}-{s['ats_live']['l']}-{s['ats_live']['p']} "
            f"vs C2 {s['ats_c2']['w']}-{s['ats_c2']['l']}-"
            f"{s['ats_c2']['p']}")
    lines += ["", f"Updated: {ledger['updated']}"]
    (shadow_dir / "LEDGER.md").write_text("\n".join(lines) + "\n")
    print(f"grade: ledger rebuilt -- {cum['graded']} graded of "
          f"{len(all_rows)} snapshotted across {len(week_docs)} "
          f"week(s); status: {status}")
    return ledger


def main() -> None:
    ap = argparse.ArgumentParser(
        description="CFB C1/C2 shadow watch (bookkeeping only)")
    ap.add_argument("mode", nargs="?", default="all",
                    choices=("snapshot", "grade", "all"))
    ap.add_argument("--dir", default=None,
                    help="shadow dir override (validation runs only; "
                         "default data/shadow/cfb_c1c2)")
    args = ap.parse_args()
    shadow_dir = Path(args.dir) if args.dir else SHADOW_DIR
    if not shadow_dir.is_absolute():
        shadow_dir = REPO / shadow_dir
    if args.mode in ("snapshot", "all"):
        snapshot(shadow_dir)
    if args.mode in ("grade", "all"):
        grade(shadow_dir)


if __name__ == "__main__":
    main()
