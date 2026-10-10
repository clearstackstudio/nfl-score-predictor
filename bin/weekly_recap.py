#!/usr/bin/env python3
"""Weekly Honest Recap generator.

Reads the graded picks from the most recently completed week(s) across all
sports with live picks (NFL, CFB, NBA, NCAAB), and generates a markdown-style
recap JSON: overall record, per-sport records, best call, worst miss, and one
honest observation. Factual, no hype, no excuses.

Usage:
    python3 bin/weekly_recap.py [--date YYYY-MM-DD] [--force]

Writes:
    site/data/recaps/<id>.json        the recap
    site/data/recaps/index.json       updated index (newest first)

Prints the recap as plain text for chat delivery. Exits 0 with "NO_NEW_WEEK"
on stdout when there is nothing new to recap.
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "site" / "data"
RECAPS = DATA / "recaps"

SPORTS = [
    # (sport_id, label, season_file, period_key, period_label)
    ("nfl", "NFL", "season_2026.json", "weeks", "Week"),
    ("cfb", "CFB", "cfb_season_2026.json", "weeks", "Week"),
    ("nba", "NBA", "nba_season_2027.json", "days", None),
    ("ncaab", "NCAAB", "ncaab_season_2027.json", "days", None),
]


def load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def covered_periods() -> set[tuple[str, str]]:
    """(sport, period) pairs already covered by existing recaps."""
    covered: set[tuple[str, str]] = set()
    idx = load_json(RECAPS / "index.json")
    if not idx:
        return covered
    for entry in idx.get("recaps", []):
        r = load_json(RECAPS / f"{entry['id']}.json")
        if r:
            for c in r.get("covers", []):
                covered.add((c["sport"], str(c["period"])))
    return covered


def latest_completed(sport: str, season_file: str, period_key: str) -> str | None:
    d = load_json(DATA / season_file)
    if not d:
        return None
    periods = d.get(period_key, {})
    done = [k for k, v in periods.items() if v.get("complete")]
    if not done:
        return None
    # weeks: numeric sort; days: date-string sort (both ascending, take last)
    try:
        return sorted(done, key=lambda k: int(k))[-1]
    except ValueError:
        return sorted(done)[-1]


def summarize_picks(picks: list[dict]) -> dict:
    ats = [0, 0, 0]  # w, l, p
    ou = [0, 0, 0]
    for p in picks:
        r = p.get("result") or {}
        if p.get("pick_spread"):
            v = r.get("ats")
            ats[0 if v == "win" else 1 if v == "loss" else 2] += 1
        if p.get("pick_total"):
            v = r.get("ou")
            ou[0 if v == "win" else 1 if v == "loss" else 2] += 1
    return {"ats": ats, "ou": ou}


def pick_label(p: dict, kind: str) -> str:
    if kind == "spread":
        return p.get("pick_spread_label") or f"{p['away_abbr']}@{p['home_abbr']} {p.get('pick_spread')}"
    return p.get("pick_total_label") or f"{p['away_abbr']}@{p['home_abbr']} {p.get('pick_total')}"


def find_best_worst(picks: list[dict]) -> tuple[dict | None, dict | None]:
    """Best call = winning pick with the largest |edge| (boldest correct call).
    Worst miss = losing pick with the highest published probability
    (most confident wrong call)."""
    best = None
    worst = None
    for p in picks:
        r = p.get("result") or {}
        for kind, res_key, edge_key, prob_key in (
            ("spread", "ats", "spread_edge", "cover_prob"),
            ("total", "ou", "total_edge", "ou_prob"),
        ):
            if not p.get(f"pick_{kind}"):
                continue
            res = r.get(res_key)
            edge = abs(p.get(edge_key) or 0)
            prob = p.get(prob_key) or 0.5
            if res == "win" and (best is None or edge > best["_edge"]):
                best = {
                    "_edge": edge,
                    "label": pick_label(p, kind),
                    "kind": kind,
                    "edge": round(p.get(edge_key) or 0, 1),
                    "prob": round(prob, 3),
                    "game": f"{p['away_abbr']} at {p['home_abbr']}",
                    "score": f"{r.get('away_score')}–{r.get('home_score')}",
                }
            if res == "loss" and (worst is None or prob > worst["_prob"]):
                worst = {
                    "_prob": prob,
                    "label": pick_label(p, kind),
                    "kind": kind,
                    "edge": round(p.get(edge_key) or 0, 1),
                    "prob": round(prob, 3),
                    "game": f"{p['away_abbr']} at {p['home_abbr']}",
                    "score": f"{r.get('away_score')}–{r.get('home_score')}",
                }
    if best:
        del best["_edge"]
    if worst:
        del worst["_prob"]
    return best, worst


def pct(w: int, l: int) -> float | None:
    return round(w / (w + l), 3) if w + l else None


def build_observation(overall: dict, sports: list[dict]) -> str:
    aw, al, _ = overall["ats"]
    ow, ol, _ = overall["ou"]
    total_w, total_l = aw + ow, al + ol
    total_decided = total_w + total_l
    wr = (total_w / total_decided) if total_decided else 0.5

    # Directional splits for totals
    parts: list[str] = []
    if wr < 0.45 and total_decided >= 10:
        parts.append(
            f"Rough week — {total_w}-{total_l} across {total_decided} decided picks. "
            "No spin: the model was wrong more than it was right."
        )
    elif wr > 0.55 and total_decided >= 10:
        parts.append(
            f"Good week at {total_w}-{total_l}. One week doesn't prove anything, "
            "but we'll take it."
        )
    else:
        parts.append(
            f"About what you'd expect from a coin-flip operation: {total_w}-{total_l}."
        )

    # Totals direction detail
    ou_parts = []
    for s in sports:
        ow_, ol_, _ = s["ou"]
        if ow_ + ol_ >= 5:
            ou_parts.append((s["label"], ow_, ol_))
    if ou_parts:
        under_note = []
        for label, ow_, ol_ in ou_parts:
            under_note.append(f"{label} totals {ow_}-{ol_}")
        parts.append("Totals detail: " + "; ".join(under_note) + ".")

    # Sport standouts
    for s in sports:
        sw, sl, _ = s["ats"]
        if sw + sl >= 8:
            if sw / (sw + sl) >= 0.65:
                parts.append(f"{s['label']} spreads carried the week at {sw}-{sl}.")
            elif sw / (sw + sl) <= 0.35:
                parts.append(f"{s['label']} spreads were the damage at {sw}-{sl}.")

    return " ".join(parts)


def season_to_date() -> dict:
    out: dict[str, dict] = {}
    for sport, label, season_file, period_key, _ in SPORTS:
        d = load_json(DATA / season_file)
        if not d:
            continue
        ats = [0, 0, 0]
        ou = [0, 0, 0]
        for _, w in d.get(period_key, {}).items():
            s = summarize_picks(w.get("picks", []))
            for i in range(3):
                ats[i] += s["ats"][i]
                ou[i] += s["ou"][i]
        out[sport] = {"label": label, "ats": ats, "ou": ou}
    return out


def fmt_record(rec: list[int]) -> str:
    return f"{rec[0]}-{rec[1]}" + (f"-{rec[2]}" if rec[2] else "")


def recap_text(r: dict) -> str:
    lines = [
        f"Honest Line weekly recap — {r['period_label']}",
        "",
        f"Overall: {fmt_record(r['overall']['ats'])} ATS, {fmt_record(r['overall']['ou'])} totals.",
    ]
    for s in r["sports"]:
        lines.append(
            f"{s['label']} {s['period']}: {fmt_record(s['ats'])} ATS, {fmt_record(s['ou'])} totals."
        )
    lines.append("")
    if r.get("best_call"):
        b = r["best_call"]
        lines.append(f"Best call: {b['label']} ({b['game']}, {b['score']}).")
    if r.get("worst_miss"):
        w = r["worst_miss"]
        lines.append(
            f"Worst miss: {w['label']} ({w['game']}, {w['score']}) — "
            f"published at {w['prob']:.0%} and lost."
        )
    lines.append("")
    lines.append(r["observation"])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="Recap date YYYY-MM-DD (default: today PT)")
    ap.add_argument("--force", action="store_true", help="Regenerate even if already covered")
    args = ap.parse_args()

    if args.date:
        today = datetime.date.fromisoformat(args.date)
    else:
        # PT date
        import time
        pt = time.gmtime(time.time() - 7 * 3600)
        today = datetime.date(pt.tm_year, pt.tm_mon, pt.tm_mday)

    covered = covered_periods() if not args.force else set()
    sports_data = []
    for sport, label, season_file, period_key, period_word in SPORTS:
        period = latest_completed(sport, season_file, period_key)
        if not period or (sport, period) in covered:
            continue
        d = load_json(DATA / season_file)
        w = d[period_key][period]
        picks = [p for p in w["picks"] if p.get("result")]
        if not picks:
            continue
        summary = summarize_picks(picks)
        best, worst = find_best_worst(picks)
        period_disp = f"{period_word} {period}" if period_word else period
        sports_data.append(
            {
                "sport": sport,
                "label": label,
                "period": period_disp,
                "period_key": period,
                "ats": summary["ats"],
                "ou": summary["ou"],
                "best_call": best,
                "worst_miss": worst,
                "n_picks": len(picks),
            }
        )

    if not sports_data:
        print("NO_NEW_WEEK")
        return 0

    overall_ats = [0, 0, 0]
    overall_ou = [0, 0, 0]
    for s in sports_data:
        for i in range(3):
            overall_ats[i] += s["ats"][i]
            overall_ou[i] += s["ou"][i]
    overall = {"ats": overall_ats, "ou": overall_ou}

    # Cross-sport best/worst: boldest correct call and most confident miss
    all_best, all_worst = None, None
    for s in sports_data:
        b, wr = s["best_call"], s["worst_miss"]
        if b and (all_best is None or abs(b["edge"]) > abs(all_best["edge"])):
            all_best = {**b, "sport": s["label"], "period": s["period"]}
        if wr and (all_worst is None or wr["prob"] > all_worst["prob"]):
            all_worst = {**wr, "sport": s["label"], "period": s["period"]}

    period_label = " · ".join(f"{s['label']} {s['period']}" for s in sports_data)
    recap_id = today.isoformat()

    recap = {
        "id": recap_id,
        "title": f"Weekly recap — {today.strftime('%b %-d, %Y')}",
        "period_label": period_label,
        "published": recap_id,
        "covers": [{"sport": s["sport"], "period": s["period_key"]} for s in sports_data],
        "overall": overall,
        "sports": [
            {
                "sport": s["sport"],
                "label": s["label"],
                "period": s["period"],
                "ats": s["ats"],
                "ou": s["ou"],
                "n_picks": s["n_picks"],
            }
            for s in sports_data
        ],
        "best_call": all_best,
        "worst_miss": all_worst,
        "observation": build_observation(overall, sports_data),
        "season_to_date": season_to_date(),
    }

    RECAPS.mkdir(parents=True, exist_ok=True)
    (RECAPS / f"{recap_id}.json").write_text(json.dumps(recap, indent=2) + "\n")

    # Update index (newest first)
    idx_path = RECAPS / "index.json"
    idx = load_json(idx_path) or {"recaps": []}
    idx["recaps"] = [e for e in idx["recaps"] if e["id"] != recap_id]
    idx["recaps"].insert(
        0,
        {"id": recap_id, "title": recap["title"], "period_label": period_label,
         "published": recap_id},
    )
    idx_path.write_text(json.dumps(idx, indent=2) + "\n")

    print(recap_text(recap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
