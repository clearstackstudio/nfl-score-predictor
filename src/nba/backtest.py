"""Walk-forward backtest: does the NBA model beat the closing line?

Method (leakage-safe, same honesty rules as the NFL model):
  - Games processed in chronological order.
  - For each game, the model predicts home margin and total from ratings
    built ONLY on games already played (prediction precedes update).
  - The closing spread/total is NEVER a model input -- only the benchmark.

Neutral-site games:
  - The 2020 COVID bubble seeding games (2020-07-30 .. 2020-08-14, 88
    games) were played on a neutral court. games.csv has no neutral flag
    (NBAElo.predict_margin has none either), so for these games the home
    edge is removed from both prediction AND update by temporarily setting
    elo.home_edge = 0.0 around that game, then restoring it.
  - NBATotals carries no home-court term (home/away scoring effects net
    to ~0 on the total), so it needs no neutral handling.

Metrics (on the same games for model vs line):
  - ATS record: "bet" only when |model_margin - spread| >= 1.5, report
    wins/losses/pushes and win% on decided games.
  - Margin RMSE of the model vs RMSE of the closing spread as a predictor.
  - Total RMSE of the model vs RMSE of the closing total.
  - Over/under record: "bet" only when |model_total - total| >= 3.0.
  - Straight-up win%.
Breakdowns by season and by era (2008-2012, 2013-2017, 2018-2023).

Rest adjustment: run twice -- baseline predictions, then predictions with
apply_rest_adjustment / apply_rest_adjustment_total. Keep only if
walk-forward RMSE improves.

Usage:
    python3 src/nba/backtest.py [--seasons 2008 2023] [--out results.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from elo import NBAElo, HOME_EDGE_PTS
from totals import NBATotals
from features import add_rest_days, apply_rest_adjustment, apply_rest_adjustment_total

REPO = Path(__file__).resolve().parent.parent.parent
CSV = REPO / "data" / "nba" / "games.csv"

SPREAD_THRESHOLD = 1.5  # only "bet" ATS when we differ from the line by this much
TOTAL_THRESHOLD = 3.0   # analogous threshold for totals betting

# 2020 COVID bubble: neutral-site seeding games (dates checked in games.csv:
# 88 games, 2020-07-30 .. 2020-08-14, all labelled season 2020).
BUBBLE_START = "2020-07-30"
BUBBLE_END = "2020-10-31"  # end of the 2020 Finals window (no regular-season games here)

ERAS = [
    ("2008-2012", 2008, 2012),
    ("2013-2017", 2013, 2017),
    ("2018-2023", 2018, 2023),
]


def era_of(season: int) -> str:
    for name, lo, hi in ERAS:
        if lo <= season <= hi:
            return name
    return "other"


class Metrics:
    def __init__(self) -> None:
        self.n = 0
        self.neutral_n = 0
        self.su_w = 0
        self.model_margin_se = 0.0
        self.line_margin_se = 0.0
        self.ats_w = self.ats_l = self.ats_p = 0
        self.model_total_se = 0.0
        self.line_total_se = 0.0
        self.ou_w = self.ou_l = self.ou_p = 0

    def add(self, our_margin, line_margin, our_total, line_total,
            actual_margin, actual_total, neutral) -> None:
        self.n += 1
        if neutral:
            self.neutral_n += 1
        self.su_w += (our_margin > 0) == (actual_margin > 0)
        self.model_margin_se += (our_margin - actual_margin) ** 2
        self.line_margin_se += (line_margin - actual_margin) ** 2
        self.model_total_se += (our_total - actual_total) ** 2
        self.line_total_se += (line_total - actual_total) ** 2

        edge = our_margin - line_margin
        if abs(edge) >= SPREAD_THRESHOLD:
            picked_home = edge > 0
            result = actual_margin - line_margin  # >0 home covers
            if abs(result) < 0.01:
                self.ats_p += 1
            elif (result > 0) == picked_home:
                self.ats_w += 1
            else:
                self.ats_l += 1

        t_edge = our_total - line_total
        if abs(t_edge) >= TOTAL_THRESHOLD:
            picked_over = t_edge > 0
            t_result = actual_total - line_total  # >0 over hits
            if abs(t_result) < 0.01:
                self.ou_p += 1
            elif (t_result > 0) == picked_over:
                self.ou_w += 1
            else:
                self.ou_l += 1

    def summary(self) -> dict:
        decided = self.ats_w + self.ats_l
        ou_decided = self.ou_w + self.ou_l
        n = self.n
        return {
            "games": n,
            "neutral_games": self.neutral_n,
            "su_pct": self.su_w / n if n else float("nan"),
            "model_margin_rmse": math.sqrt(self.model_margin_se / n) if n else float("nan"),
            "line_margin_rmse": math.sqrt(self.line_margin_se / n) if n else float("nan"),
            "ats": (self.ats_w, self.ats_l, self.ats_p),
            "ats_pct": self.ats_w / decided if decided else float("nan"),
            "ats_decided": decided,
            "model_total_rmse": math.sqrt(self.model_total_se / n) if n else float("nan"),
            "line_total_rmse": math.sqrt(self.line_total_se / n) if n else float("nan"),
            "ou": (self.ou_w, self.ou_l, self.ou_p),
            "ou_pct": self.ou_w / ou_decided if ou_decided else float("nan"),
            "ou_decided": ou_decided,
        }


def load_games() -> pd.DataFrame:
    df = pd.read_csv(CSV, parse_dates=["date"])
    df = df.dropna(subset=["spread", "total"]).copy()
    df = df.sort_values("date").reset_index(drop=True)
    df = add_rest_days(df)
    dates = pd.to_datetime(df["date"])
    df["neutral"] = (dates >= BUBBLE_START) & (dates <= BUBBLE_END)
    return df


def run_backtest(games: pd.DataFrame, use_rest: bool,
                 seasons: tuple[int, int] | None = None) -> dict:
    elo = NBAElo()
    totals = NBATotals()

    overall = Metrics()
    by_season: dict[int, Metrics] = {}
    by_era: dict[str, Metrics] = {}
    last_season = None
    n_neutral = 0

    for row in games.itertuples():
        season = int(row.season)
        if seasons and not (seasons[0] <= season <= seasons[1]):
            continue
        if last_season is not None and season != last_season:
            elo.new_season()
            totals.new_season()
        last_season = season

        neutral = bool(row.neutral)
        n_neutral += neutral

        # Predict BEFORE updating: this is the whole honesty of the backtest.
        saved_edge = elo.home_edge
        if neutral:
            elo.home_edge = 0.0  # neutral court: no home-court edge anywhere
        our_margin = elo.predict_margin(row.home_team, row.away_team)
        our_total = totals.predict_total(row.home_team, row.away_team)
        elo.home_edge = saved_edge

        if use_rest:
            our_margin = apply_rest_adjustment(our_margin, row.home_rest, row.away_rest)
            our_total = apply_rest_adjustment_total(our_total, row.home_rest, row.away_rest)

        actual_margin = float(row.home_score) - float(row.away_score)
        actual_total = float(row.home_score) + float(row.away_score)
        line_margin = float(row.spread)
        line_total = float(row.total)

        overall.add(our_margin, line_margin, our_total, line_total,
                    actual_margin, actual_total, neutral)
        by_season.setdefault(season, Metrics()).add(
            our_margin, line_margin, our_total, line_total,
            actual_margin, actual_total, neutral)
        by_era.setdefault(era_of(season), Metrics()).add(
            our_margin, line_margin, our_total, line_total,
            actual_margin, actual_total, neutral)

        # NOW learn from the game.
        if neutral:
            elo.home_edge = 0.0  # neutral update: no home edge in expectation
        elo.update(row.home_team, row.away_team,
                   float(row.home_score), float(row.away_score))
        elo.home_edge = saved_edge
        totals.update(row.home_team, row.away_team,
                      float(row.home_score), float(row.away_score))

    return {
        "use_rest": use_rest,
        "neutral_games": n_neutral,
        "overall": overall.summary(),
        "by_season": {s: m.summary() for s, m in sorted(by_season.items())},
        "by_era": {e: m.summary() for e, m in by_era.items() if e != "other"},
    }


def fmt_summary(s: dict) -> str:
    w, l, p = s["ats"]
    ow, ol, op = s["ou"]
    return (f"games={s['games']:>5,}  SU={s['su_pct']:7.1%}  "
            f"margRMSE {s['model_margin_rmse']:6.2f} vs line {s['line_margin_rmse']:6.2f}  "
            f"ATS {w}-{l}-{p} ({s['ats_pct']:.1%} on {s['ats_decided']:,})  "
            f"totRMSE {s['model_total_rmse']:6.2f} vs line {s['line_total_rmse']:6.2f}  "
            f"O/U {ow}-{ol}-{op} ({s['ou_pct']:.1%} on {s['ou_decided']:,})")


def print_report(r: dict) -> None:
    label = "WITH rest adjustment" if r["use_rest"] else "BASELINE (no rest adjustment)"
    print(f"=== NBA walk-forward backtest: {label} ===")
    print(f"Neutral (bubble) games: {r['neutral_games']}")
    print("\nOverall")
    print(fmt_summary(r["overall"]))
    print("\nBy era")
    for name, _, _ in ERAS:
        if name in r["by_era"]:
            print(f"  {name}: {fmt_summary(r['by_era'][name])}")
    print("\nBy season")
    for season, s in r["by_season"].items():
        w, l, p = s["ats"]
        print(f"  {season}: n={s['games']:>5,} SU={s['su_pct']:.1%} "
              f"mRMSE {s['model_margin_rmse']:.2f}/{s['line_margin_rmse']:.2f} "
              f"ATS {w}-{l}-{p} ({s['ats_pct']:.1%}) "
              f"tRMSE {s['model_total_rmse']:.2f}/{s['line_total_rmse']:.2f} "
              f"O/U {s['ou'][0]}-{s['ou'][1]}-{s['ou'][2]} ({s['ou_pct']:.1%})")


def main() -> None:
    ap = argparse.ArgumentParser(description="NBA walk-forward backtest")
    ap.add_argument("--seasons", nargs=2, type=int, metavar=("FROM", "TO"),
                    help="restrict to seasons FROM..TO (ending years)")
    ap.add_argument("--out", type=str, default=None,
                    help="write JSON results (both runs) to this path")
    args = ap.parse_args()

    games = load_games()
    print(f"Loaded {len(games):,} games, {games['date'].min().date()} .. "
          f"{games['date'].max().date()}")

    base = run_backtest(games, use_rest=False,
                        seasons=tuple(args.seasons) if args.seasons else None)
    rest = run_backtest(games, use_rest=True,
                        seasons=tuple(args.seasons) if args.seasons else None)

    print_report(base)
    print()
    print_report(rest)

    print("\n=== Rest-adjustment decision ===")
    b, r_ = base["overall"], rest["overall"]
    print(f"Margin RMSE: baseline {b['model_margin_rmse']:.3f} vs rest {r_['model_margin_rmse']:.3f} "
          f"-> {'KEEP rest adjustment' if r_['model_margin_rmse'] < b['model_margin_rmse'] else 'DROP rest adjustment'}")
    print(f"Total  RMSE: baseline {b['model_total_rmse']:.3f} vs rest {r_['model_total_rmse']:.3f} "
          f"-> {'KEEP rest adjustment' if r_['model_total_rmse'] < b['model_total_rmse'] else 'DROP rest adjustment'}")

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"baseline": base, "rest": rest}, f, indent=2)
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
