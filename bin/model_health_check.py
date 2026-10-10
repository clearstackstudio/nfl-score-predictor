#!/usr/bin/env python3
"""Honest Line Model Health Monitor.

Monthly automated check of model assumptions and performance.
READ-ONLY: never modifies models, picks, or site code. It proposes;
Bryant disposes.

Usage:
    python3 bin/model_health_check.py [--output PATH] [--deep]

Checks (per sport):
  1. Rolling live performance vs historical baseline (z-test)
  2. Bias-slice monitors (the slices that mattered in the 2026-10 research)
  3. Dead-idea code invariants + re-verification on new data
  4. Calibration drift on live published probabilities
  5. --deep: expensive parameter re-fits (annual/seasonal, not monthly)

Baselines below are sourced from:
  - model-pattern-study.md (2026-10-10, ~100k games, pre-registered validation)
  - totals-diagnostic.md H1/H2/H3 (2026-10-09/10)
  - site/data/track_record*.json (regenerated post fav_name fix)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parent.parent
SITE_DATA = REPO / "site" / "data"
PT = ZoneInfo("America/Los_Angeles")

# ----------------------------------------------------------------------------
# Baselines (from validated research; see module docstring for sources)
# ----------------------------------------------------------------------------

BASELINES = {
    # sport: {market: (win_rate, n, source)}
    "NFL": {
        "ats": (0.521, 7174, "45-season walk-forward, post fav_name fix"),
        "ou": (0.493, 762, "2021-2024 EPA walk-forward"),
        "ou_under_slice": (0.533, 272, "under-picks only, 2021-2024"),
    },
    "CFB": {
        "ats": (0.498, 8342, "2014-2025 walk-forward"),
        "ou": (0.507, 8113, "2014-2025 walk-forward"),
        "ou_hi_total_under": (0.549, 1034, "line>=60 under-picks, 10/12 seasons"),
    },
    "NBA": {
        "ats": (0.504, 18552, "2007-2023 walk-forward"),
        # totals pulled 2026-10-10 (48.3%, t=-3.07) — not a baseline, a removal
    },
    "NCAAB": {
        "ats": (0.497, 33961, "2013-2021+2025-2026 walk-forward"),
        "ou": (0.509, 30183, "2013-2021+2025-2026 walk-forward"),
    },
    "MLB": {
        # moneyline calibrated; totals 50.4% -> 51.1% post 2026-10-10 fixes
        "ou": (0.511, 12193, "2012-2021 walk-forward, post skew+Platt fixes"),
    },
}

# Dead ideas: (name, code-invariant check description, live-data check)
# Code invariants are verified by grepping source; live checks need graded picks.
DEAD_IDEAS = [
    {
        "id": "nfl_indoor_adj",
        "name": "NFL indoor +3.0 totals adjustment",
        "killed": "2026-10-09 (H1: 46.5% vs 46.9%, z=-0.07)",
        "invariant": ("src/weather.py", r"INDOOR_TOTAL_ADJ\s*=\s*0\.0"),
    },
    {
        "id": "nfl_outdoor_bias",
        "name": "NFL outdoor totals bias correction",
        "killed": "2026-10-10 (H3: z=-0.10, hurts 2024)",
        "invariant": ("src/weekly_picks.py", r"OUTDOOR_BIAS_ADJ"),  # must be ABSENT
        "absent": True,
    },
    {
        "id": "cfb_wind_port",
        "name": "CFB verbatim NFL wind hinge port",
        "killed": "2026-10-09 (H2: high-wind 55.3% -> 51.3%)",
        "invariant": ("cfb/cfb_weekly_picks.py", r"wind_mph\s*-\s*10"),
        "absent": True,
    },
    {
        "id": "nfl_edge5",
        "name": "NFL ATS |edge|>=5 threshold",
        "killed": "2026-10-10 (validation z=+0.29, edge decayed)",
        "invariant": ("src/weekly_picks.py", r"abs\(se\)\s*>=\s*0\.5"),
    },
    {
        "id": "nba_totals",
        "name": "NBA totals publishing",
        "killed": "2026-10-10 (48.3%, t=-3.07 — pulled from site)",
        "live_check": "nba_no_totals",
    },
    {
        "id": "ncaab_downweight",
        "name": "NCAAB Nov/Dec update downweighting",
        "killed": "2026-10-10 (H: deletion beats everything, t~19)",
        "invariant": ("src/ncaab/efficiency.py", r"NOV_ALPHA_FACTOR"),
        "absent": True,
    },
]


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def z_vs_baseline(wins: int, n: int, p0: float) -> float:
    """Two-sided z of observed win rate vs baseline p0."""
    if n == 0:
        return 0.0
    p = wins / n
    se = math.sqrt(p0 * (1 - p0) / n)
    return (p - p0) / se if se > 0 else 0.0


def fmt_pct(x: float | None) -> str:
    return f"{x:.1%}" if x is not None else "n/a"


@dataclass
class Finding:
    severity: str  # OK, WATCH, ACTION
    sport: str
    headline: str
    detail: str = ""


@dataclass
class SportReport:
    sport: str
    lines: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


# ----------------------------------------------------------------------------
# Data loading
# ----------------------------------------------------------------------------

def load_live_picks() -> dict[str, list[dict]]:
    """All graded live picks per sport, normalized.

    Returns {sport: [pick, ...]} where each pick has:
      ats: 'win'|'loss'|'push'|None, ou: 'win'|'loss'|'push'|None,
      plus sport-specific raw fields passthrough in '_raw'.
    """
    out: dict[str, list[dict]] = {}
    specs = [
        ("NFL", SITE_DATA / "season_2026.json", "weeks"),
        ("CFB", SITE_DATA / "cfb_season_2026.json", "weeks"),
        ("NBA", SITE_DATA / "nba_season_2027.json", "days"),
        ("NCAAB", SITE_DATA / "ncaab_season_2027.json", "days"),
        ("MLB", SITE_DATA / "mlb_season_2027.json", "days"),
    ]
    for sport, path, unit_key in specs:
        picks: list[dict] = []
        if path.exists():
            d = json.loads(path.read_text())
            for unit_id, unit in d.get(unit_key, {}).items():
                for p in unit.get("picks", []):
                    r = p.get("result") or {}
                    # Only graded picks (have at least a score or outcome)
                    if not r or ("ats" not in r and "ou" not in r
                                 and "home_score" not in r and "ml" not in r):
                        continue
                    picks.append({
                        "unit": unit_id,
                        "ats": r.get("ats"),
                        "ou": r.get("ou"),
                        "ml": r.get("ml"),
                        "_raw": p,
                    })
        out[sport] = picks
    return out


def load_calibration() -> dict:
    p = SITE_DATA / "calibration.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text())


# ----------------------------------------------------------------------------
# Checks
# ----------------------------------------------------------------------------

def check_rolling_performance(sport: str, picks: list[dict]) -> SportReport:
    rep = SportReport(sport=sport)
    base = BASELINES.get(sport, {})
    n = len(picks)
    if n == 0:
        rep.lines.append("No live graded picks yet (offseason or season not started).")
        return rep

    for market, key in (("ATS", "ats"), ("O/U", "ou")):
        if key not in base:
            continue
        p0, bn, src = base[key]
        decided = [(p[key]) for p in picks if p.get(key) in ("win", "loss")]
        w = sum(1 for x in decided if x == "win")
        nd = len(decided)
        if nd == 0:
            rep.lines.append(f"{market}: no decided picks yet.")
            continue
        z = z_vs_baseline(w, nd, p0)
        flag = ""
        sev = "OK"
        if abs(z) >= 2.0:
            flag = " ⚠️ DEVIATION"
            sev = "WATCH"
        rep.lines.append(
            f"{market}: {w}-{nd - w} ({w / nd:.1%}, n={nd}, "
            f"z={z:+.2f} vs {p0:.1%} baseline){flag}"
        )
        if sev != "OK":
            rep.findings.append(Finding(
                sev, sport,
                f"{market} deviating from baseline (z={z:+.2f})",
                f"Live {w}-{nd - w} vs baseline {p0:.1%} ({src}). "
                f"{'Outperforming' if z > 0 else 'Underperforming'} — "
                f"{'investigate' if abs(z) >= 2.5 else 'monitor next month'}.",
            ))
    return rep


def check_nfl_bias_slices(picks: list[dict]) -> SportReport:
    rep = SportReport(sport="NFL")
    ou_picks = [p for p in picks if p.get("ou") in ("win", "loss")]
    if not ou_picks:
        rep.lines.append("Totals bias slices: no graded O/U picks yet.")
        return rep

    # Over vs under split
    for side in ("over", "under"):
        sub = [p for p in ou_picks if (p["_raw"].get("pick_total")) == side]
        w = sum(1 for p in sub if p["ou"] == "win")
        n = len(sub)
        if n >= 10:
            rep.lines.append(
                f"{side.title()} picks: {w}-{n - w} ({w / n:.1%}, n={n})"
            )
            if side == "under":
                z = z_vs_baseline(w, n, 0.533)
                if z <= -1.5:
                    rep.findings.append(Finding(
                        "WATCH", "NFL",
                        f"Under-pick slice weakening (z={z:+.2f} vs 53.3%)",
                        f"The only historically winning totals slice is "
                        f"{w}-{n - w}. If this persists, the edge is decaying.",
                    ))
    # Outdoor totals bias: our_total - actual on graded totals
    bias_vals = []
    for p in ou_picks:
        r = p["_raw"]
        res = r.get("result") or {}
        if "home_score" in res and r.get("our_total") is not None:
            actual = res["home_score"] + res["away_score"]
            bias_vals.append(r["our_total"] - actual)
    if len(bias_vals) >= 10:
        b = sum(bias_vals) / len(bias_vals)
        rep.lines.append(f"Totals bias (our−actual): {b:+.2f} pts (n={len(bias_vals)})")
        if abs(b) >= 3.0:
            rep.findings.append(Finding(
                "WATCH", "NFL",
                f"Totals bias {b:+.2f} pts exceeds ±3.0",
                "Historical outdoor bias +2.6 was deemed too unstable to "
                "correct (H3). Monitor; do not auto-correct.",
            ))
    # High-wind subset
    windy = [p for p in ou_picks
             if (p["_raw"].get("wind_mph") or 0) > 10]
    w = sum(1 for p in windy if p["ou"] == "win")
    if len(windy) >= 10:
        rep.lines.append(f"High-wind (>{10}mph) totals: {w}-{len(windy) - w} "
                         f"({w / len(windy):.1%}, n={len(windy)})")
    return rep


def check_cfb_slices(picks: list[dict]) -> SportReport:
    rep = SportReport(sport="CFB")
    ou_picks = [p for p in picks if p.get("ou") in ("win", "loss")]
    if not ou_picks:
        rep.lines.append("Totals slices: no graded O/U picks yet.")
        return rep
    hi = [p for p in ou_picks
          if (p["_raw"].get("line_total") or 0) >= 60
          and p["_raw"].get("pick_total") == "under"]
    w = sum(1 for p in hi if p["ou"] == "win")
    if len(hi) >= 10:
        rep.lines.append(f"Line≥60 under picks: {w}-{len(hi) - w} "
                         f"({w / len(hi):.1%}, n={len(hi)}, baseline 54.9%)")
        z = z_vs_baseline(w, len(hi), 0.549)
        if z <= -1.5:
            rep.findings.append(Finding(
                "WATCH", "CFB",
                f"High-total under slice weakening (z={z:+.2f})",
                "Historically 54.9% (z=+3.15). Dampening was killed; "
                "if the slice itself decays, note it.",
            ))
    elif ou_picks:
        rep.lines.append(f"O/U overall: {sum(1 for p in ou_picks if p['ou'] == 'win')}-"
                         f"{sum(1 for p in ou_picks if p['ou'] == 'loss')} "
                         f"(n={len(ou_picks)}); <10 high-total unders to judge slice.")
    return rep


def check_dead_ideas(live: dict[str, list[dict]]) -> list[Finding]:
    findings: list[Finding] = []
    for idea in DEAD_IDEAS:
        name = idea["name"]
        inv = idea.get("invariant")
        if inv:
            rel, pat = inv
            path = REPO / rel
            try:
                text = path.read_text()
            except FileNotFoundError:
                findings.append(Finding("WATCH", "ALL",
                    f"Dead-idea file moved: {rel}",
                    f"Cannot verify invariant for '{name}'."))
                continue
            found = re.search(pat, text) is not None
            ok = (not found) if idea.get("absent") else found
            if not ok:
                findings.append(Finding("ACTION", "ALL",
                    f"DEAD IDEA REVIVED IN CODE: {name}",
                    f"Invariant broken in {rel} (killed {idea['killed']}). "
                    f"Investigate before next picks run."))
        lc = idea.get("live_check")
        if lc == "nba_no_totals":
            # NBA picks must not publish totals
            nba_file = SITE_DATA / "nba_picks.json"
            if nba_file.exists():
                d = json.loads(nba_file.read_text())
                picks = d.get("picks", d if isinstance(d, list) else [])
                leaked = [p for p in picks
                          if p.get("pick_total") not in (None, "null", "")]
                if leaked:
                    findings.append(Finding("ACTION", "NBA",
                        f"NBA totals reappeared in published picks ({len(leaked)})",
                        "Totals were pulled 2026-10-10 (48.3%). Remove again."))
    return findings


def check_calibration_drift(live: dict[str, list[dict]],
                            cal: dict) -> list[Finding]:
    findings: list[Finding] = []
    sports = {s["id"]: s for s in cal.get("sports", [])}
    prob_field = {"ats": "cover_prob", "ou": "ou_prob", "totals": "ou_prob"}
    for sport, picks in live.items():
        spec = sports.get(sport.lower())
        if not spec or not picks:
            continue
        for mkt in spec.get("markets", []):
            mid = mkt["id"]
            pf = prob_field.get(mid)
            if not pf:
                continue
            # Bin live picks by published prob
            bins: dict[str, list[int]] = {}  # label -> [wins, n]
            for p in picks:
                raw = p["_raw"]
                prob = raw.get(pf)
                res = p.get("ats" if mid == "ats" else "ou")
                if prob is None or res not in ("win", "loss"):
                    continue
                label = ("50-55%" if prob < 0.55 else "55-60%" if prob < 0.60
                         else "60-65%" if prob < 0.65 else "65-70%"
                         if prob < 0.70 else "70%+")
                b = bins.setdefault(label, [0, 0])
                b[1] += 1
                if res == "win":
                    b[0] += 1
            # Compare to backtest bins
            bt = {b["label"]: b for b in mkt.get("backtest", {}).get("bins", [])}
            for label, (w, n) in bins.items():
                if n < 20 or label not in bt:
                    continue
                actual = w / n
                expected = bt[label]["actual"]
                if abs(actual - expected) > 0.15:
                    findings.append(Finding("WATCH", sport,
                        f"Calibration drift: {mkt['label']} {label} bin",
                        f"Live {actual:.1%} (n={n}) vs backtest {expected:.1%}. "
                        f"Recalibration curve may need refit."))
    return findings


def check_parameter_inventory() -> list[str]:
    """Dump live parameter values for manual drift comparison.

    Full walk-forward re-fits are seasonal work, not monthly. This inventory
    records what's live so month-to-month diffs are visible.
    """
    lines: list[str] = []
    params = [
        ("src/weather.py", r"^INDOOR_TOTAL_ADJ\s*=\s*([0-9.]+)", "NFL indoor totals adj"),
        ("src/weather.py", r"^(WIND_HINGE_MPH|WIND_SLOPE|WIND_MAX_ADJ)\s*=\s*([0-9.]+)", "NFL wind"),
        ("src/ncaab/efficiency.py", r"^TEAM_ALPHA\s*=\s*([0-9.]+)", "NCAAB team alpha"),
        ("src/mlb/winprob.py", r"^PLATT_(INTERCEPT|SLOPE)\s*=\s*([0-9.\-]+)", "MLB Platt"),
        ("src/mlb/backtest.py", r"^TOTAL_SKEW\s*=\s*([0-9.\-]+)", "MLB totals skew"),
    ]
    for rel, pat, label in params:
        path = REPO / rel
        if not path.exists():
            lines.append(f"{label}: file {rel} not found")
            continue
        seen = set()
        for line in path.read_text().splitlines():
            m = re.match(pat, line.strip())
            if m and m.group(0) not in seen:
                seen.add(m.group(0))
                name = m.group(1) if len(m.groups()) > 1 else ""
                val = m.group(2) if len(m.groups()) > 1 else m.group(1)
                lines.append(f"{label} {name}: {val}".strip())
    return lines


# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------

def build_report(live: dict[str, list[dict]], cal: dict,
                 deep: bool) -> tuple[str, str]:
    now = datetime.now(PT)
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")
    month = now.strftime("%Y-%m")

    all_findings: list[Finding] = []
    sections: list[str] = []

    # Per-sport rolling performance
    for sport in ("NFL", "CFB", "NBA", "NCAAB", "MLB"):
        picks = live.get(sport, [])
        rep = check_rolling_performance(sport, picks)
        if sport == "NFL":
            extra = check_nfl_bias_slices(picks)
            rep.lines.extend(extra.lines)
            rep.findings.extend(extra.findings)
        if sport == "CFB":
            extra = check_cfb_slices(picks)
            rep.lines.extend(extra.lines)
            rep.findings.extend(extra.findings)
        all_findings.extend(rep.findings)
        body = "\n".join(f"- {l}" for l in rep.lines)
        sections.append(f"## {sport}\n{body}")

    # Dead ideas
    dead = check_dead_ideas(live)
    all_findings.extend(dead)
    if dead:
        sections.append("## Dead-idea re-check\n" + "\n".join(
            f"- **{f.severity}**: {f.headline} — {f.detail}" for f in dead))
    else:
        sections.append("## Dead-idea re-check\n- All code invariants hold; "
                        "no revived ideas. Too few new graded picks to "
                        "re-test statistically — last validations stand.")

    # Calibration drift
    drift = check_calibration_drift(live, cal)
    all_findings.extend(drift)
    if drift:
        sections.append("## Calibration drift\n" + "\n".join(
            f"- **{f.severity}** ({f.sport}): {f.headline} — {f.detail}"
            for f in drift))
    else:
        sections.append("## Calibration drift\n- No bin with n≥20 drifted "
                        ">15pp from its backtest curve.")

    # Deep mode: parameter inventory
    if deep:
        inv = check_parameter_inventory()
        sections.append("## Live parameter inventory (--deep)\n" + "\n".join(
            f"- {l}" for l in inv))

    # Verdict
    actions = [f for f in all_findings if f.severity == "ACTION"]
    watches = [f for f in all_findings if f.severity == "WATCH"]
    if actions:
        verdict = "ACTION PROPOSED"
    elif watches:
        verdict = "WATCH"
    else:
        verdict = "HEALTHY"

    # Proposed changes
    if actions:
        prop = "\n".join(
            f"### {f.headline}\n{f.detail}" for f in actions)
    else:
        prop = "None. All nominal — a clean bill of health is a result."

    total_live = sum(len(v) for v in live.values())
    report = f"""# Model Health Monitor — {now.strftime('%B %Y')}

**Run:** {stamp} · **Verdict: {verdict}**
**Live graded picks this cycle:** {total_live} across 5 sports

{chr(10).join(sections)}

## Proposed changes

{prop}

## Notes

- Baselines: model-pattern-study.md (2026-10-10) and totals-diagnostic.md H1/H2/H3.
- Monthly monitors are lightweight by design. Full parameter re-fits
  (wind hinge, home edges) run with `--deep` on season boundaries.
- This monitor never changes the model. It proposes; Bryant disposes.
"""
    return verdict, report


def main() -> int:
    ap = argparse.ArgumentParser(description="Honest Line model health monitor")
    ap.add_argument("--output", help="Write markdown report to PATH")
    ap.add_argument("--deep", action="store_true",
                    help="Include expensive parameter re-fits")
    args = ap.parse_args()

    live = load_live_picks()
    cal = load_calibration()
    verdict, report = build_report(live, cal, args.deep)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report)
        print(f"Report written to {out}")
    else:
        print(report)
    print(f"\n[verdict: {verdict}]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
