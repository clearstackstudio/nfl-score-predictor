"""Shadow QB-ablation watch — bookkeeping ONLY. Never writes outside
data/shadow/qb_ablation/ (gitignored). Reads site/data/picks.json and
site/data/season_2026.json read-only; imports the live pipeline's pure
functions read-only so the shadow arm uses the exact live rules.

Purpose: settle prong (c) of the 2026-11-02 QB-term ablation study
(verdict INCONCLUSIVE). Each week, grade the picks the model WOULD have
made with the QB term zeroed, alongside the live picks, from the same
published board.

Method (the study's ablation definition, applied to published fields):
the QB term enters our_margin only via expected offensive EPA, so on the
published board
    margin_noqb = our_spread - (qb_adj_home - qb_adj_away)   [points]
    total_noqb  = our_total  - (qb_adj_home + qb_adj_away)
with edges rounded to 0.1 BEFORE thresholding, exactly as the live
generator rounds (verified: stored spread_edge == round(our_spread -
line_spread, 1) on every published game, 2026 weeks 5-8, 0 mismatches).
Spread pick at |edge| >= 0.5; total pick at |edge| >= 1.0 with the live
7.0 circuit breaker. Probabilities, labels and the parlay are recomputed
with weekly_picks' own functions; grading uses grade_week.grade_pick /
grade_parlay verbatim against the same finals the live record used.

Modes:
    generate  shadow board for the current picks.json week
    grade     rebuild the ledger from season_2026.json
    all       both (default; what the nightly cron runs)
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from grade_week import grade_parlay, grade_pick  # noqa: E402
from recalibration import recalibrate  # noqa: E402
from weekly_picks import (  # noqa: E402
    MARGIN_SD, TOTAL_CIRCUIT, TOTAL_SD, build_parlay, normal_cdf,
    pick_spread_label, pick_total_label,
)

REPO = Path(__file__).resolve().parent.parent
SITE_DATA = REPO / "site" / "data"
SHADOW_DIR = REPO / "data" / "shadow" / "qb_ablation"
SEASON = 2026
TOLERANCE_PER_WEEK = -0.10  # pre-registered prong-(c) tolerance, winners/week

SETTLE_CRITERION = (
    "The watch resolves when, over completed live-era weeks (2026 season "
    "weeks whose published board carries QB-adjustment fields; week 4 "
    "predates the fields and is not derivable), the 95% interval on "
    "cumulative delta winners/week (ablated minus live) excludes the "
    "-0.10/week tolerance -- entirely above -0.10 means the recent-era "
    "pick-value drag does not reproduce live (removal case re-openable); "
    "entirely below -0.10 confirms the drag (KEEP side strengthened) -- "
    "or at the end of the 2026 regular season, whichever comes first. "
    "Bryant decides adoption either way; this watch changes nothing."
)


def ablate_pick(p: dict) -> dict:
    """One published pick -> its QB-term-zeroed shadow twin.

    Mirrors the live pick schema so build_parlay/grade_pick apply
    verbatim. Asserts the study's sanity identity: on a game where both
    QB adjustments are 0.0, the shadow pick must equal the live pick.
    """
    qh, qa = float(p["qb_adj_home"]), float(p["qb_adj_away"])
    margin_noqb = round(p["our_spread"] - (qh - qa), 1)
    total_noqb = round(p["our_total"] - (qh + qa), 1)
    se = round(margin_noqb - p["line_spread"], 1)
    te = round(total_noqb - p["line_total"], 1)

    side = ("home" if se > 0 else "away") if abs(se) >= 0.5 else None
    tot = ("over" if te > 0 else "under") if abs(te) >= 1.0 else None
    note = None
    if tot and abs(te) > TOTAL_CIRCUIT:
        tot = None
        note = ("No play — our number is too far from the "
                "market to trust.")
    cover = recalibrate(normal_cdf(abs(se) / MARGIN_SD), "nfl", "ats")
    ou = recalibrate(normal_cdf(abs(te) / TOTAL_SD), "nfl", "totals")

    s = dict(p)  # carry identity, lines, weather, QBs verbatim
    s.update({
        "our_spread": margin_noqb,
        "our_total": total_noqb,
        "spread_edge": se,
        "total_edge": te,
        "qb_adj_home": 0.0,
        "qb_adj_away": 0.0,
        "pick_spread": side,
        "pick_total": tot,
        "pick_total_note": note,
        "pick_spread_label": pick_spread_label(side, p["line_spread"],
                                               p["home_abbr"], p["away_abbr"]),
        "pick_total_label": pick_total_label(tot, p["line_total"]),
        "spread_labels": {
            "home": pick_spread_label("home", p["line_spread"],
                                      p["home_abbr"], p["away_abbr"]),
            "away": pick_spread_label("away", p["line_spread"],
                                      p["home_abbr"], p["away_abbr"]),
        },
        "cover_prob": round(cover, 3) if side else None,
        "ou_prob": round(ou, 3) if tot else None,
        "result": None,
        # Reconstruction tolerance: published fields are 0.1-rounded, so
        # the ablated edge can sit up to ~0.15 from the full-precision
        # value; flag picks whose threshold call is inside that band.
        "rounding_borderline": bool(
            (side is None and 0.3 <= abs(se) < 0.5)
            or (side is not None and 0.5 <= abs(se) < 0.7)
            or (tot is None and note is None and 0.8 <= abs(te) < 1.0)
            or (tot is not None and 1.0 <= abs(te) < 1.2)),
    })
    if qh == 0.0 and qa == 0.0:
        assert s["pick_spread"] == p["pick_spread"], \
            f"identity fail (spread): {p['away_abbr']} @ {p['home_abbr']}"
        assert s["pick_total"] == p["pick_total"], \
            f"identity fail (total): {p['away_abbr']} @ {p['home_abbr']}"
        assert s["spread_edge"] == p["spread_edge"]
        assert s["total_edge"] == p["total_edge"]
    return s


def wlp(results: list[str]) -> tuple[int, int, int]:
    return (results.count("win"), results.count("loss"),
            results.count("push"))


def generate() -> dict:
    """Shadow board for the week currently in picks.json (pre-game record).

    Re-derived whenever the source board changes (line moves / refresh),
    mirroring how the live board itself is refreshed; first_seen keeps
    the timestamp of the first derivation for that board version chain.
    """
    src = SITE_DATA / "picks.json"
    doc = json.loads(src.read_text())
    src_hash = hashlib.sha256(src.read_bytes()).hexdigest()
    picks = []
    for p in doc["picks"]:
        if "qb_adj_home" not in p:
            print(f"generate: {p['away_abbr']} @ {p['home_abbr']} lacks QB "
                  "fields; week not derivable, skipping generate")
            return {"generated": False}
        s = ablate_pick(p)
        if p.get("result"):
            s["result"] = grade_pick(s, p["result"]["home_score"],
                                     p["result"]["away_score"])
        picks.append(s)
    live_open = [dict(p, result=None) for p in doc["picks"]]
    # Reproduction check: rebuilding the live parlay from the live picks
    # (results stripped) must match the stored parlay leg-for-leg. The
    # stored copy may carry a grading "result" key (grade_parlay adds
    # one), so compare the generator-owned fields only. A mismatch on a
    # partially graded week is expected when the parlay froze at first
    # publish under the consistency rule; on a fresh board it must match.
    rebuilt_live_parlay = build_parlay(live_open)
    stored_parlay = doc.get("parlay") or {}
    parlay_check = (
        rebuilt_live_parlay is not None
        and rebuilt_live_parlay["legs"] == stored_parlay.get("legs")
        and rebuilt_live_parlay["combined_prob"]
        == stored_parlay.get("combined_prob"))
    shadow = {
        "watch": "qb_ablation_shadow",
        "season": doc["season"],
        "week": doc["week"],
        "source_picks_generated": doc["generated"],
        "source_picks_sha256": src_hash,
        "method": ("margin_noqb = our_spread - (qb_adj_home - qb_adj_away); "
                   "live thresholds/probs/labels/parlay rules via "
                   "weekly_picks imports; see src/shadow_qb_ablation.py"),
        "parlay": build_parlay(picks),
        "live_parlay_check": parlay_check,
        "picks": picks,
    }
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    dest = SHADOW_DIR / f"season{doc['season']}_week{doc['week']:02d}.json"
    prev = {}
    if dest.exists():
        prev = json.loads(dest.read_text())
    shadow["first_seen"] = prev.get("first_seen") \
        if prev.get("source_picks_sha256") == src_hash else doc["generated"]
    if prev.get("source_picks_sha256") != src_hash:
        dest.write_text(json.dumps(shadow, indent=2))
        print(f"generate: shadow board -> {dest} "
              f"(week {doc['week']}, {len(picks)} games, "
              f"live-parlay reproduction check: "
              f"{shadow['live_parlay_check']})")
    else:
        print(f"generate: week {doc['week']} shadow board already current")
    return {"generated": True, "week": doc["week"]}


def grade_week_shadow(week_doc: dict) -> dict | None:
    """Grade one season-log week: live from stored results, shadow derived
    from the same stored board and graded on the same finals."""
    picks = week_doc["picks"]
    if not picks or any("qb_adj_home" not in p for p in picks):
        return None
    live_ats, live_ou, sh_ats, sh_ou = [], [], [], []
    shadow_picks = []
    for p in picks:
        s = ablate_pick(p)
        r = p.get("result")
        if r:
            live_ats.append(r["ats"]) if "ats" in r else None
            live_ou.append(r["ou"]) if "ou" in r else None
            s["result"] = grade_pick(s, r["home_score"], r["away_score"])
            sh_ats.append(s["result"]["ats"]) if "ats" in s["result"] \
                else None
            sh_ou.append(s["result"]["ou"]) if "ou" in s["result"] \
                else None
        shadow_picks.append(s)
    open_shadow = [dict(s, result=None) for s in shadow_picks]
    parlay = grade_parlay(build_parlay(open_shadow), shadow_picks)
    lw, ll, lp = wlp(live_ats)
    sw, sl, sp = wlp(sh_ats)
    return {
        "complete": bool(week_doc.get("complete")),
        "games_graded": len(live_ats) + sum(
            1 for p in picks if p.get("result") and "ats" not in p["result"]),
        "live_ats": {"w": lw, "l": ll, "p": lp, "winners": lw},
        "shadow_ats": {"w": sw, "l": sl, "p": sp, "winners": sw},
        "delta_winners": sw - lw,
        "live_ou": dict(zip("wlp", wlp(live_ou))),
        "shadow_ou": dict(zip("wlp", wlp(sh_ou))),
        "shadow_parlay_result": (parlay or {}).get("result"),
        "live_parlay_result": (week_doc.get("parlay") or {}).get("result"),
        "borderline_picks": sum(1 for s in shadow_picks
                                if s["rounding_borderline"]),
    }


def grade() -> dict:
    log = json.loads((SITE_DATA / f"season_{SEASON}.json").read_text())
    weeks, skipped = {}, {}
    tot_live = tot_shadow = 0
    deltas: list[float] = []
    for wk in sorted(log["weeks"], key=int):
        res = grade_week_shadow(log["weeks"][wk])
        if res is None:
            skipped[wk] = "not derivable: published board predates " \
                          "QB-adjustment fields"
            continue
        weeks[wk] = res
        if res["complete"]:
            tot_live += res["live_ats"]["winners"]
            tot_shadow += res["shadow_ats"]["winners"]
            deltas.append(float(res["delta_winners"]))
    n = len(deltas)
    cum_delta = tot_shadow - tot_live
    per_week = (cum_delta / n) if n else None
    ci = None
    if n >= 2:
        mean = sum(deltas) / n
        var = sum((d - mean) ** 2 for d in deltas) / (n - 1)
        half = 1.96 * math.sqrt(var / n)
        ci = [round(mean - half, 3), round(mean + half, 3)]
    elif n == 1:
        ci = None  # one week: no interval yet, say so plainly
    status = "collecting"
    if ci and ci[0] > TOLERANCE_PER_WEEK:
        status = ("RESOLVED (interval above -0.10/wk): live-era drag does "
                  "not reproduce; removal case re-openable — Bryant decides")
    elif ci and ci[1] < TOLERANCE_PER_WEEK:
        status = ("RESOLVED (interval below -0.10/wk): live-era drag "
                  "confirmed; KEEP strengthened — Bryant decides")
    ledger = {
        "watch": "qb_ablation_shadow",
        "purpose": ("Settle prong (c) of the 2026-11-02 QB-term ablation "
                    "study (INCONCLUSIVE): does zeroing the QB term cost "
                    "winners/week on live-era boards? Bookkeeping only; "
                    "nothing here feeds the model, the site, or any pick."),
        "settle_criterion": SETTLE_CRITERION,
        "tolerance_winners_per_week": TOLERANCE_PER_WEEK,
        "season": SEASON,
        "updated": __import__("pandas").Timestamp.now(
            "America/Los_Angeles").strftime("%Y-%m-%d %H:%M %Z"),
        "weeks": weeks,
        "weeks_skipped": skipped,
        "cumulative_completed_weeks": {
            "weeks_counted": n,
            "live_winners": tot_live,
            "shadow_winners": tot_shadow,
            "delta_winners": cum_delta,
            "delta_winners_per_week": None if per_week is None
            else round(per_week, 3),
            "delta_per_week_95ci": ci,
            "uncertainty_note": (
                "Normal-approx 95% interval on the per-week delta-winners "
                "series (weeks are the unit). With few weeks it is wide "
                "by design; it is a bookkeeping gauge, not the study's "
                "paired test." if ci else
                "Fewer than 2 completed weeks: no interval yet."),
        },
        "status": status,
        "totals_note": ("O/U lines in the ledger are informational only. "
                        "The study's verdict covers the margin/ATS role; "
                        "the QB term also feeds our_total, unmeasured by "
                        "the study and not verdict-bearing here."),
    }
    SHADOW_DIR.mkdir(parents=True, exist_ok=True)
    (SHADOW_DIR / "ledger.json").write_text(json.dumps(ledger, indent=2))
    lines = [
        "# QB-ablation shadow watch — ledger",
        "",
        ledger["purpose"],
        "",
        f"**Settle criterion:** {SETTLE_CRITERION}",
        "",
        f"**Status:** {status}",
        "",
        "| Week | Complete | Live ATS | Shadow ATS | Δ winners |",
        "|---|---|---|---|---|",
    ]
    for wk in sorted(weeks, key=int):
        r = weeks[wk]
        la, sa = r["live_ats"], r["shadow_ats"]
        lines.append(
            f"| {wk} | {'yes' if r['complete'] else 'provisional'} "
            f"| {la['w']}-{la['l']}-{la['p']} "
            f"| {sa['w']}-{sa['l']}-{sa['p']} "
            f"| {r['delta_winners']:+d} |")
    for wk, why in skipped.items():
        lines.append(f"| {wk} | — | skipped: {why} | | |")
    c = ledger["cumulative_completed_weeks"]
    lines += [
        "",
        f"Cumulative (completed weeks): {c['weeks_counted']} weeks, "
        f"live {c['live_winners']} winners vs shadow "
        f"{c['shadow_winners']} (Δ {c['delta_winners']:+d}, "
        f"{c['delta_winners_per_week']} per week, "
        f"95% CI {c['delta_per_week_95ci']}).",
        "",
        f"Updated: {ledger['updated']}",
    ]
    (SHADOW_DIR / "LEDGER.md").write_text("\n".join(lines) + "\n")
    print(f"grade: ledger rebuilt — {n} completed weeks, cumulative "
          f"delta {cum_delta:+d} winners "
          f"({per_week if per_week is None else round(per_week, 3)}/week), "
          f"status: {status}")
    return ledger


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("generate", "all"):
        generate()
    if mode in ("grade", "all"):
        grade()
    if mode not in ("generate", "grade", "all"):
        raise SystemExit(f"unknown mode {mode!r}")


if __name__ == "__main__":
    main()
