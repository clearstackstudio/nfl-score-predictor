#!/usr/bin/env python3
"""Build site/data/calibration.json — calibration evidence for the Honest Line
calibration dashboard.

READ-ONLY wrt the repo: the bin tables below are transcribed LITERALS, the
fitted curves are imported from src/recalibration.py, and the only file this
writes is site/data/calibration.json. Re-running produces byte-identical
output (idempotent).

Source 1 — bin tables (2026-10-09):
    ~/workspace/goals/nfl-score-prediction-website/files/calibration-check.md
    Percentages transcribed as 0–1 decimals to 3 places; n values exact.
Source 2 — NCAAB bins (not in the report; built 2026-10-09):
    `TZ=America/Los_Angeles .venv-cfb/bin/python src/ncaab/fit_recalibration.py \
        --results data/ncaab/backtest_results.json`
    Same 50–55/55–60/60–65/65–70/70%+ edges on the RAW published ATS prob.
    Totals used the same edges (note: the report's other totals tables stop
    at 65–70% because they had no 70%+ bin; NCAAB does, so it is included).
Source 3 — fitted recalibration curves: imported from src/recalibration.py
    _CURVES (points (raw_prob, empirical_rate), anchored at (0.50, 0.50)).
    MLB has no curve (moneyline probs are already calibrated) -> null.

Run from anywhere: python3 bin/build_calibration.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
from recalibration import _CURVES  # noqa: E402


def bins(labels, rows):
    """labels: list of bin labels; rows: list of (n, predicted, actual)."""
    return [
        {"label": lab, "n": n, "predicted": p, "actual": a}
        for lab, (n, p, a) in zip(labels, rows)
    ]


FIVE = ["50–55%", "55–60%", "60–65%", "65–70%", "70%+"]
FOUR = ["50–55%", "55–60%", "60–65%", "65–70%"]

# --- Source 1: transcribed from calibration-check.md (2026-10-09) -----------
TABLES = {
    # NFL — live model is EPA, walk-forward 2021–2024
    ("nfl", "ats"): {
        "backtest": "Walk-forward 2021–2024, EPA model",
        "bins": bins(FIVE, [
            (196, 0.532, 0.434),
            (214, 0.575, 0.491),
            (210, 0.623, 0.495),
            (137, 0.674, 0.504),
            (234, 0.775, 0.449),
        ]),
        "verdict": "Severely overconfident — a published 77% hit 45%.",
    },
    ("nfl", "totals"): {
        "backtest": "Walk-forward 2021–2024, EPA model",
        "bins": bins(FOUR, [
            (96, 0.538, 0.510),
            (192, 0.574, 0.510),
            (180, 0.623, 0.533),
            (106, 0.663, 0.481),
        ]),
        "verdict": "Overconfident — 65–70% publishes at 66%, hits 48%.",
    },
    # CFB — walk-forward PPA 2014–2026 (8,945 games through 2025 in the
    # published backtest + 278 more from the 2026 season to date in this re-run)
    ("cfb", "ats"): {
        "backtest": "Walk-forward 2014–2026, PPA model",
        "bins": bins(FIVE, [
            (1552, 0.531, 0.499),
            (1871, 0.574, 0.506),
            (1643, 0.624, 0.514),
            (1256, 0.675, 0.469),
            (2284, 0.780, 0.497),
        ]),
        "verdict": "Severely overconfident — the 70%+ bin (n=2,284) hits 49.7%.",
    },
    ("cfb", "totals"): {
        "backtest": "Walk-forward 2014–2026, PPA model",
        "bins": bins(FOUR, [
            (1065, 0.536, 0.493),
            (1790, 0.574, 0.508),
            (1560, 0.624, 0.519),
            (718, 0.662, 0.527),
        ]),
        "verdict": "Overconfident — recalibration slope 0.30, still far below 1.",
    },
    # NBA — walk-forward 2008–2023, 18,552 games, rest-adjusted final model
    ("nba", "ats"): {
        "backtest": "Walk-forward 2008–2023, rest-adjusted model",
        "bins": bins(FIVE, [
            (5161, 0.533, 0.510),
            (5478, 0.573, 0.499),
            (3011, 0.622, 0.500),
            (1270, 0.672, 0.524),
            (758, 0.743, 0.513),
        ]),
        "verdict": "Severely overconfident — slope ≈ 0; 70%+ is a coin flip.",
    },
    ("nba", "totals"): {
        "backtest": "Walk-forward 2008–2023, rest-adjusted model",
        "bins": bins(FOUR, [
            (4382, 0.535, 0.502),
            (5698, 0.573, 0.491),
            (2852, 0.622, 0.475),
            (785, 0.663, 0.502),
        ]),
        "verdict": "Severely overconfident — slope negative.",
    },
    # --- Source 2: NCAAB, from fit_recalibration.py output (2026-10-09) ---
    # Walk-forward 2013–2021 + 2025–2026, 47,794 games in the replay.
    ("ncaab", "ats"): {
        "backtest": "Walk-forward 2013–2021 + 2025–2026, efficiency model",
        "bins": bins(FIVE, [
            (436, 0.549, 0.484),
            (11736, 0.574, 0.494),
            (8830, 0.623, 0.495),
            (5444, 0.673, 0.493),
            (8003, 0.790, 0.498),
        ]),
        "verdict": "Severely overconfident — a raw 79% recalibrates to ~50%.",
    },
    ("ncaab", "totals"): {
        "backtest": "Walk-forward 2013–2021 + 2025–2026, efficiency model",
        # No games fell in the 50–55% bin (totals need |edge| >= threshold),
        # so it is omitted, unlike the ATS table.
        "bins": bins(
            ["55–60%", "60–65%", "65–70%", "70%+"],
            [
                (8005, 0.582, 0.509),
                (8787, 0.623, 0.505),
                (6012, 0.673, 0.503),
                (7579, 0.774, 0.518),
            ],
        ),
        "verdict": "Overconfident — empirical hit rates sit at ~50–52% in every bin.",
    },
    # MLB — walk-forward 2012–2021, 22,765 games; proper two-sided win prob
    # from a generative runs model (tuned alpha=0.025, carryover=0.25,
    # home_edge=0.130, sigma=4.135). Roughly well-calibrated: no curve fitted.
    ("mlb", "moneyline"): {
        "backtest": "Walk-forward 2012–2021, runs model",
        "bins": bins(
            ["<35%", "35–40%", "40–45%", "45–50%",
             "50–55%", "55–60%", "60–65%", "65%+"],
            [
                (976, 0.304, 0.350),
                (1446, 0.378, 0.446),
                (2908, 0.427, 0.491),
                (4724, 0.477, 0.511),
                (5123, 0.524, 0.544),
                (3929, 0.573, 0.573),
                (2204, 0.622, 0.616),
                (1455, 0.691, 0.661),
            ],
        ),
        "verdict": "Roughly calibrated — the exception; slight tilt favoring underdogs.",
    },
}

MARKETS = [
    ("ats", "Against the spread"),
    ("totals", "Totals"),
]
MLB_MARKET = ("moneyline", "Moneyline")

SPORTS = [
    ("nfl", "NFL"),
    ("cfb", "College Football"),
    ("nba", "NBA"),
    ("ncaab", "College Basketball"),
    ("mlb", "MLB"),
]


def main() -> None:
    sports = []
    for sport_id, label in SPORTS:
        markets = []
        for market_id, market_label in ([MLB_MARKET] if sport_id == "mlb" else MARKETS):
            t = TABLES[(sport_id, market_id)]
            curve_pts = _CURVES.get((sport_id, market_id))
            markets.append({
                "id": market_id,
                "label": market_label,
                "backtest": {
                    "label": t["backtest"],
                    "games": sum(b["n"] for b in t["bins"]),
                    "bins": t["bins"],
                },
                "curve": [[x, y] for x, y in curve_pts] if curve_pts else None,
                "verdict": t["verdict"],
            })
        sports.append({"id": sport_id, "label": label, "markets": markets})

    payload = {
        "generated": "2026-10-09",
        "note": (
            "Backtest calibration evidence for the Honest Line calibration "
            "dashboard. Spread/total bins transcribed from "
            "goals/nfl-score-prediction-website/files/calibration-check.md "
            "(2026-10-09); NCAAB bins computed 2026-10-09 via "
            "src/ncaab/fit_recalibration.py (--results "
            "data/ncaab/backtest_results.json); fitted recalibration curves "
            "imported from src/recalibration.py _CURVES (MLB moneyline is "
            "already calibrated, so its curve is null). "
            "predicted = mean published probability in the bin; actual = "
            "empirical cover/hit rate. All values are 0–1 decimals."
        ),
        "sports": sports,
    }

    out = REPO / "site" / "data" / "calibration.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
