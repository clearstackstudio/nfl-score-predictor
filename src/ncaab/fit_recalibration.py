"""Fit empirical probability-recalibration curves for NCAAB.

Replays the walk-forward backtest with the final fitted params (from
backtest --out results.json), recording per game:
  raw ATS prob = Phi(|spread_edge| / margin_resid_sd) and whether the
  picked side covered; raw totals prob = Phi(|total_edge| / total_resid_sd)
  and whether the picked total hit.

Bins by raw prob and prints (raw_prob, empirical_rate) curve points in the
src/recalibration.py format, plus a calibration table. Mirrors the
2026-10-09 calibration check that produced the NFL/NBA/CFB curves.

Usage:
    TZ=America/Los_Angeles .venv-cfb/bin/python src/ncaab/fit_recalibration.py \
        --results data/ncaab/backtest_results.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from efficiency import NCAABEfficiency
from features import (add_rest_days, apply_rest_adjustment,
                      apply_rest_adjustment_total)
from backtest import SPREAD_THRESHOLD, TOTAL_THRESHOLD, game_poss

REPO = Path(__file__).resolve().parent.parent.parent
CSV = REPO / "data" / "ncaab" / "games.csv"


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


BINS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]


def fit_curve(records: list[tuple[float, bool]], label: str) -> list[tuple[float, float]]:
    pts = [(0.50, 0.50)]
    print(f"\n{label}:")
    for lo, hi in BINS:
        xs = [p for p, _ in records if lo <= p < hi]
        if not xs:
            print(f"  [{lo:.2f},{hi:.2f}): n=0 (skip)")
            continue
        hits = sum(1 for p, h in records if lo <= p < hi and h)
        n = len(xs)
        mean_p = sum(xs) / n
        rate = hits / n
        pts.append((round(mean_p, 3), round(rate, 3)))
        print(f"  [{lo:.2f},{hi:.2f}): n={n:>6,} mean_raw={mean_p:.3f} "
              f"empirical={rate:.3f}")
    return pts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True,
                    help="backtest --out JSON (params + residual SDs)")
    args = ap.parse_args()

    res = json.loads(Path(args.results).read_text())
    params = res["params"]
    m_sd = res["full"]["overall"]["model_margin_resid_sd"]
    t_sd = res["full"]["overall"]["model_total_resid_sd"]
    print(f"params={params} margin_sd={m_sd:.2f} total_sd={t_sd:.2f}")

    df = pd.read_csv(CSV, parse_dates=["date"])
    df = df.dropna(subset=["spread", "total"]).copy()
    df = df.sort_values("date").reset_index(drop=True)
    df = add_rest_days(df)

    model = NCAABEfficiency(team_alpha=params["team_alpha"],
                            carryover=params["carryover"],
                            home_edge=params["home_edge"])
    ats_recs: list[tuple[float, bool]] = []
    ou_recs: list[tuple[float, bool]] = []
    last_season = None
    for row in df.itertuples():
        season = int(row.season)
        if last_season is not None and season != last_season:
            for _ in range(season - last_season):
                model.new_season()
        last_season = season
        neutral = bool(int(row.neutral))
        saved = model.home_edge
        if neutral:
            model.home_edge = 0.0
        pm, pt = model.predict(row.home_team, row.away_team, neutral=neutral)
        model.home_edge = saved
        if params.get("rest_margin"):
            pm = apply_rest_adjustment(pm, row.home_rest, row.away_rest,
                                       pts_per_day=params["rest_margin"])
        if params.get("rest_total"):
            pt = apply_rest_adjustment_total(pt, row.home_rest, row.away_rest,
                                             pts_per_day=params["rest_total"])
        am = float(row.home_score) - float(row.away_score)
        at = float(row.home_score) + float(row.away_score)
        se, te = pm - float(row.spread), pt - float(row.total)
        if abs(se) >= SPREAD_THRESHOLD:
            raw = normal_cdf(abs(se) / m_sd)
            cover = am - float(row.spread)
            ats_recs.append((raw, (cover > 0) == (se > 0)))
        if abs(te) >= TOTAL_THRESHOLD:
            raw = normal_cdf(abs(te) / t_sd)
            diff = at - float(row.total)
            ou_recs.append((raw, (diff > 0) == (te > 0)))
        month = pd.to_datetime(row.date).month
        model.update(row.home_team, row.away_team, float(row.home_score),
                     float(row.away_score), game_poss(model, row), month)

    ats_pts = fit_curve(ats_recs, "NCAAB ATS calibration")
    ou_pts = fit_curve(ou_recs, "NCAAB totals calibration")
    print("\n# paste into src/recalibration.py _CURVES:")
    print(f'    ("ncaab", "ats"): {ats_pts},')
    print(f'    ("ncaab", "totals"): {ou_pts},')


if __name__ == "__main__":
    main()
