"""Export the CFB walk-forward backtest as track-record JSON + calibration.

The transparency backbone: every season's real backtested numbers,
no cherry-picking. Also writes data/cfb/cfb_backtest.json with the
margin/total SDs that calibrate weekly pick probabilities.

    python3 cfb/cfb_export_track_record.py [2014-2025]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cfb_ratings import REPO, run_backtest

DATA = REPO / "data" / "cfb"


def main() -> None:
    seasons = None
    if len(sys.argv) > 1:
        a, b = sys.argv[1].split("-")
        seasons = list(range(int(a), int(b) + 1))
    r = run_backtest(seasons)

    w, l, p = r["ats"]
    ow, ol, op = r["ou"]
    (DATA / "cfb_backtest.json").write_text(json.dumps({
        "games": r["games"],
        "seasons": [s["season"] for s in r["seasons"]],
        "margin_sd": r["margin_sd"],
        "total_sd": r["total_sd"],
        "overall": {
            "straight_up_pct": round(r["straight_up_pct"], 4),
            "our_margin_rmse": round(r["our_margin_rmse"], 2),
            "line_margin_rmse": round(r["line_margin_rmse"], 2),
            "ats": [w, l, p], "ats_pct": round(r["ats_pct"], 4),
            "our_total_rmse": round(r["our_total_rmse"], 2),
            "line_total_rmse": round(r["line_total_rmse"], 2),
            "ou": [ow, ol, op], "ou_pct": round(r["ou_pct"], 4),
        },
    }, indent=2))

    dest = REPO / "site" / "data" / "cfb_track_record.json"
    dest.write_text(json.dumps({
        "model": ("Opponent-adjusted PPA/play ratings (garbage time excluded), "
                  "FBS-vs-FBS only. The betting line is never an input. "
                  "Walk-forward: every prediction made before learning the result."),
        "overall": {
            "games": r["games"],
            "straight_up_pct": round(r["straight_up_pct"], 4),
            "our_margin_rmse": round(r["our_margin_rmse"], 2),
            "line_margin_rmse": round(r["line_margin_rmse"], 2),
            "ats": [w, l, p], "ats_pct": round(r["ats_pct"], 4),
            "our_total_rmse": round(r["our_total_rmse"], 2),
            "line_total_rmse": round(r["line_total_rmse"], 2),
            "ou": [ow, ol, op], "ou_pct": round(r["ou_pct"], 4),
        },
        "seasons": r["seasons"],
    }, indent=2))
    print(f"{len(r['seasons'])} seasons, {r['games']:,} games -> {dest}")
    print(f"ATS {w}-{l}-{p} ({r['ats_pct']:.1%}) | "
          f"margin RMSE ours {r['our_margin_rmse']:.2f} vs line {r['line_margin_rmse']:.2f}")


if __name__ == "__main__":
    main()
