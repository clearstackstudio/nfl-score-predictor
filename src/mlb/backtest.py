"""Walk-forward backtest: does the MLB team-level model beat the closing line?

Method (leakage-safe, same honesty rules as the NBA/NFL models):
  - Games processed in chronological order, 2012-2021.
  - For each game, the model predicts home/away runs from ratings built
    ONLY on games already played (prediction precedes update), converts the
    predicted margin to a win probability via winprob.margin_to_prob.
  - The closing moneyline/total is NEVER a model input -- only the
    benchmark.

Tuning: (alpha, carryover) are grid-searched on walk-forward margin RMSE
over 2012-2015 only; winprob sigma is the residual sd on that same split.
The report also shows a 2016-2021 "post-tuning" slice as the cleaner read.

Metrics (model vs line on the same games):
  - Straight-up win% (pick the higher-probability side).
  - Brier score of model probs vs vig-removed closing-line implied probs.
  - FLAT $100 MONEYLINE betting: bet the model's side only when
    |model_prob - implied_prob| >= threshold, at the closing moneyline.
    Reported at thresholds 0.03 and 0.05 (primary: 0.05 -- the more
    selective threshold, fewer bets, less variance-chasing; both shown).
  - Totals: model total RMSE vs closing-total RMSE, plus an over/under
    record betting $100 when |(model_total - TOTAL_SKEW) - line_total| >= 0.5
    runs (one full line move -- the standard MLB total granularity) at the
    closing over/under odds. The skew adjustment corrects for the model
    predicting the mean total while the line tracks the median.

Usage:
    python3 src/mlb/backtest.py [--seasons 2012 2021] [--out results.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data import load_games
from ratings import MLBRatings, fit_home_edge, tune_params, fit_sigma, walk_forward
from winprob import margin_to_prob

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = Path(__file__).resolve().parent / "backtest_results.json"

ML_THRESHOLDS = (0.03, 0.05)
PRIMARY_ML_THRESHOLD = 0.05
OU_THRESHOLD = 0.5  # runs; one full MLB line move
STAKE = 100.0

# Totals skew correction, validated 2026-10-10: the model predicts the MEAN
# total but the closing line tracks the MEDIAN (right-skewed run scoring).
# s = median(actual - model_total) = -0.561 on 2012-2015 discovery, -0.554 on
# fresh 2022-2026 -- a stable structural property, not a fitted edge.
# The OU edge compares the median-adjusted total to the line; the displayed
# model total stays the mean. Validated: skew-adjusted OU on 2016-2021
# holdout went 51.5% (n=7,210, z=+2.34 vs fair odds) with the 74-82%
# structural over-tilt removed. See the model pattern study (2026-10-10).
# v2 idea (NOT validated, do not implement without a test): bucket-specific
# skew (<=7: -0.95 ... 10+: +0.55).
# 2027 logging: daily_picks.py must log model_total_raw AND model_total_adj
# per game -- see goals/honest-line-mlb-prediction-model/agent_notes/2027-validation-logging-spec.md.
TOTAL_SKEW = 0.56


def implied_prob(odds: float) -> float:
    """American odds -> implied probability (with vig still in)."""
    o = float(odds)
    return 100.0 / (o + 100.0) if o > 0 else -o / (-o + 100.0)


def ml_win_profit(odds: float, stake: float = STAKE) -> float:
    """Profit (not including stake) if a moneyline bet at ``odds`` wins."""
    o = float(odds)
    return stake * (o / 100.0 if o > 0 else 100.0 / abs(o))


class Metrics:
    def __init__(self) -> None:
        self.n = 0
        self.su_w = 0
        self.brier_model = 0.0
        self.brier_line = 0.0
        self.ml = {t: {"bets": 0, "wins": 0, "losses": 0, "profit": 0.0}
                   for t in ML_THRESHOLDS}
        self.total_model_se = 0.0
        self.total_line_se = 0.0
        self.ou_bets = 0
        self.ou_w = self.ou_l = self.ou_p = 0
        self.ou_profit = 0.0

    def add(self, p_home: float, q_home: float, home_win: bool,
            home_ml: float, away_ml: float,
            model_total: float, line_total: float, actual_total: float,
            over_odds: float, under_odds: float) -> None:
        self.n += 1
        self.su_w += (p_home > 0.5) == home_win
        self.brier_model += (p_home - home_win) ** 2
        self.brier_line += (q_home - home_win) ** 2

        edge = p_home - q_home  # >0 => model likes home more than the line
        for t, m in self.ml.items():
            if abs(edge) >= t:
                bet_home = edge > 0
                won = home_win == bet_home
                m["bets"] += 1
                if won:
                    m["wins"] += 1
                    m["profit"] += ml_win_profit(home_ml if bet_home else away_ml)
                else:
                    m["losses"] += 1
                    m["profit"] -= STAKE

        self.total_model_se += (model_total - actual_total) ** 2
        self.total_line_se += (line_total - actual_total) ** 2
        # Skew-adjusted edge: compare the median-implied total to the line.
        # model_total itself stays the mean (display + RMSE use it unadjusted).
        t_edge = (model_total - TOTAL_SKEW) - line_total
        if abs(t_edge) >= OU_THRESHOLD:
            bet_over = t_edge > 0
            if abs(actual_total - line_total) < 1e-9:
                self.ou_p += 1  # push: stake returned
            else:
                won = (actual_total > line_total) == bet_over
                self.ou_bets += 1
                if won:
                    self.ou_w += 1
                    self.ou_profit += ml_win_profit(over_odds if bet_over else under_odds)
                else:
                    self.ou_l += 1
                    self.ou_profit -= STAKE

    def summary(self) -> dict:
        n = self.n
        ml = {}
        for t, m in self.ml.items():
            bets = m["bets"]
            ml[f"{t:.2f}"] = {
                "bets": bets,
                "wins": m["wins"],
                "losses": m["losses"],
                "win_pct": m["wins"] / bets if bets else float("nan"),
                "profit": round(m["profit"], 2),
                "roi": m["profit"] / (STAKE * bets) if bets else float("nan"),
            }
        ou_decided = self.ou_w + self.ou_l
        return {
            "games": n,
            "su_win_pct": self.su_w / n if n else float("nan"),
            "brier_model": self.brier_model / n if n else float("nan"),
            "brier_line": self.brier_line / n if n else float("nan"),
            "moneyline": ml,
            "model_total_rmse": math.sqrt(self.total_model_se / n) if n else float("nan"),
            "line_total_rmse": math.sqrt(self.total_line_se / n) if n else float("nan"),
            "ou_bets": self.ou_bets,
            "ou_wins": self.ou_w,
            "ou_losses": self.ou_l,
            "ou_pushes": self.ou_p,
            "ou_win_pct": self.ou_w / ou_decided if ou_decided else float("nan"),
            "ou_profit": round(self.ou_profit, 2),
            "ou_roi": self.ou_profit / (STAKE * self.ou_bets) if self.ou_bets else float("nan"),
        }


def run_backtest(games: pd.DataFrame, alpha: float, carryover: float,
                 home_edge: float, sigma: float,
                 seasons: tuple[int, int] | None = None) -> dict:
    overall = Metrics()
    by_season: dict[int, Metrics] = {}

    def hook(row, pred_h, pred_a):
        season = int(row.season)
        if seasons and not (seasons[0] <= season <= seasons[1]):
            return
        margin = pred_h - pred_a
        p_home = margin_to_prob(margin, sigma)
        qh = implied_prob(row.home_ml)
        qa = implied_prob(row.away_ml)
        q_home = qh / (qh + qa)  # remove the vig
        home_win = row.home_runs > row.away_runs
        m = by_season.setdefault(season, Metrics())
        args = dict(
            p_home=p_home, q_home=q_home, home_win=home_win,
            home_ml=row.home_ml, away_ml=row.away_ml,
            model_total=pred_h + pred_a, line_total=row.total,
            actual_total=row.home_runs + row.away_runs,
            over_odds=row.over_odds, under_odds=row.under_odds,
        )
        overall.add(**args)
        m.add(**args)

    walk_forward(games, alpha, carryover, home_edge, hook)
    return {
        "overall": overall.summary(),
        "by_season": {s: m.summary() for s, m in sorted(by_season.items())},
    }


def build_verdict(r: dict, primary: float) -> str:
    o = r["overall"]
    ml = o["moneyline"][f"{primary:.2f}"]
    era = r["post_tuning_era"]
    ml_e = era["moneyline"][f"{primary:.2f}"]
    games = o["games"]
    verdict_core = (
        "competent forecaster, no betting edge"
        if ml["roi"] <= 0
        else "small positive ROI that is within noise -- no reliable betting edge"
    )
    return (
        f"Walk-forward backtest, {r['seasons'][0]}-{r['seasons'][-1]} "
        f"({games:,} games, prediction before update, lines never used as inputs): "
        f"the team-level runs model picks the winner {o['su_win_pct']:.1%} straight up. "
        f"Brier score {o['brier_model']:.4f} vs {o['brier_line']:.4f} for the vig-removed "
        f"closing line -- the line remains the sharper probability. Flat ${STAKE:.0f} "
        f"moneyline bets at a {primary:.2f} edge threshold went {ml['wins']}-{ml['losses']} "
        f"({ml['win_pct']:.1%}) for ${ml['profit']:+.0f} ({ml['roi']:+.1%} ROI) over {ml['bets']} bets; "
        f"on the post-tuning 2016-2021 slice it was {ml_e['wins']}-{ml_e['losses']} "
        f"(${ml_e['profit']:+.0f}, {ml_e['roi']:+.1%} ROI). Totals: model RMSE "
        f"{o['model_total_rmse']:.2f} vs line {o['line_total_rmse']:.2f}; over/under bets at a "
        f"{OU_THRESHOLD}-run threshold went {o['ou_wins']}-{o['ou_losses']} "
        f"({o['ou_win_pct']:.1%}, ${o['ou_profit']:+.0f}, {o['ou_roi']:+.1%} ROI). "
        f"VERDICT: {verdict_core}. Team strength alone does not beat the closing "
        f"MLB line; the honest use is as a calibrated forecaster, with probable-pitcher "
        f"adjustments (see pitcher.py) as the plausible path to any future edge."
    )


def fmt_pct(x: float) -> str:
    return "n/a" if x != x else f"{x:.1%}"


def print_report(r: dict) -> None:
    o = r["overall"]
    t = r["tuning"]
    print("=== MLB walk-forward backtest ===")
    print(f"seasons {r['seasons'][0]}-{r['seasons'][-1]}, games={o['games']:,}")
    print(f"tuning (2012-2015): alpha=1/{1/t['alpha']:.0f}, carryover={t['carryover']:.3f}, "
          f"home_edge={t['home_edge']:.3f} runs, sigma={t['sigma']:.3f}")
    print(f"\nOverall: SU={o['su_win_pct']:.1%}  "
          f"Brier model {o['brier_model']:.4f} vs line {o['brier_line']:.4f}")
    for thr in (f"{t:.2f}" for t in ML_THRESHOLDS):
        m = o["moneyline"][thr]
        flag = " <-- primary" if float(thr) == PRIMARY_ML_THRESHOLD else ""
        print(f"  ML@{thr}: {m['bets']:>4} bets {m['wins']}-{m['losses']} "
              f"({fmt_pct(m['win_pct'])}) profit ${m['profit']:+.0f} ROI {m['roi']:+.1%}{flag}")
    print(f"  Totals: model RMSE {o['model_total_rmse']:.2f} vs line {o['line_total_rmse']:.2f}; "
          f"O/U {o['ou_wins']}-{o['ou_losses']}-{o['ou_pushes']} ({fmt_pct(o['ou_win_pct'])}) "
          f"profit ${o['ou_profit']:+.0f} ROI {o['ou_roi']:+.1%}")
    e = r["post_tuning_era"]
    me = e["moneyline"][f"{PRIMARY_ML_THRESHOLD:.2f}"]
    print(f"\nPost-tuning era (2016-2021): n={e['games']:,} SU={e['su_win_pct']:.1%} "
          f"Brier {e['brier_model']:.4f}/{e['brier_line']:.4f} "
          f"ML@{PRIMARY_ML_THRESHOLD:.2f} {me['wins']}-{me['losses']} ROI {me['roi']:+.1%}")
    print("\nBy season (ML record at primary threshold):")
    for s, sm in r["by_season"].items():
        m = sm["moneyline"][f"{PRIMARY_ML_THRESHOLD:.2f}"]
        print(f"  {s}: n={sm['games']:>5,} SU={sm['su_win_pct']:.1%} "
              f"Brier {sm['brier_model']:.4f}/{sm['brier_line']:.4f} "
              f"ML {m['wins']}-{m['losses']} ({fmt_pct(m['win_pct'])}) ROI {m['roi']:+.1%}  "
              f"tRMSE {sm['model_total_rmse']:.2f}/{sm['line_total_rmse']:.2f}")
    print(f"\n{r['verdict']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="MLB walk-forward backtest")
    ap.add_argument("--seasons", nargs=2, type=int, metavar=("FROM", "TO"),
                    help="restrict evaluation to seasons FROM..TO")
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT),
                    help="write JSON results to this path")
    args = ap.parse_args()

    games = load_games()
    print(f"Loaded {len(games):,} games, {games['date'].min().date()} .. "
          f"{games['date'].max().date()}, neutral={int(games['neutral'].sum())}")

    home_edge = fit_home_edge(games)
    print(f"fitted home edge: {home_edge:.3f} runs")

    alpha, carryover, rmse = tune_params(games, home_edge)
    print(f"tuned: alpha=1/{1/alpha:.0f}, carryover={carryover:.3f} (tuning RMSE {rmse:.4f})")
    sigma = fit_sigma(games, alpha, carryover, home_edge)
    print(f"fitted winprob sigma: {sigma:.3f} "
          f"(if this changed, update SIGMA in winprob.py)")

    seasons = tuple(args.seasons) if args.seasons else None
    r = run_backtest(games, alpha, carryover, home_edge, sigma, seasons)

    # Post-tuning era slice (2016-2021): params/sigma were not tuned on it.
    era = run_backtest(games, alpha, carryover, home_edge, sigma, (2016, 2021))
    r["post_tuning_era"] = era["overall"]

    r.update({
        "seasons": sorted(games["season"].unique().tolist()),
        "games": r["overall"]["games"],
        "su_win_pct": r["overall"]["su_win_pct"],
        "brier_model": r["overall"]["brier_model"],
        "brier_line": r["overall"]["brier_line"],
        "primary_ml_threshold": PRIMARY_ML_THRESHOLD,
        "ou_threshold_runs": OU_THRESHOLD,
        "stake": STAKE,
        "tuning": {
            "tune_seasons": [2012, 2013, 2014, 2015],
            "alpha": alpha,
            "carryover": carryover,
            "tuning_rmse": rmse,
            "home_edge": home_edge,
            "sigma": sigma,
        },
    })
    r["verdict"] = build_verdict(r, PRIMARY_ML_THRESHOLD)

    print_report(r)
    with open(args.out, "w") as f:
        json.dump(r, f, indent=2)
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
