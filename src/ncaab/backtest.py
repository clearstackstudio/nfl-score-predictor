"""Walk-forward backtest: does the NCAAB efficiency model beat the closing line?

Method (leakage-safe, same honesty rules as the NBA model):
  - Games processed in chronological order from data/ncaab/games.csv.
  - For each game, the model predicts home margin and total from ratings
    built ONLY on games already played (prediction precedes update).
  - The closing spread/total is NEVER a model input -- only the benchmark.
  - Neutral-site games get no home-court edge in prediction or update.

Tuning protocol (anti-overfit):
  - Hyperparameters (team_alpha, carryover, home_edge, rest slopes) are
    fitted on the 2013-2019 TUNING split by walk-forward margin/total RMSE.
    (Historical closing lines only exist from the 2012-13 season on.)
  - Seasons 2020-2026 are never touched during tuning; the final report
    shows tuning-split, holdout, and full-sample numbers separately.

Metrics (on the same games for model vs line):
  - ATS record: "bet" only when |model_margin - spread| >= 1.5, report
    wins/losses/pushes and win% on decided games.
  - Margin RMSE of the model vs RMSE of the closing spread as a predictor.
  - Total RMSE of the model vs RMSE of the closing total.
  - Over/under record: "bet" only when |model_total - total| >= 3.0.
  - Straight-up win%.
Breakdowns by season and by era (2013-2016, 2017-2020, 2021-2026).

Usage:
    TZ=America/Los_Angeles .venv-cfb/bin/python src/ncaab/backtest.py \
        [--out results.json]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from efficiency import (NCAABEfficiency, TEAM_ALPHA, SEASON_CARRYOVER,
                        HOME_EDGE_PTS, sanitize_poss)
from features import (add_rest_days, apply_rest_adjustment,
                      apply_rest_adjustment_total, REST_CAP_DAYS)

REPO = Path(__file__).resolve().parent.parent.parent
CSV = REPO / "data" / "ncaab" / "games.csv"

SPREAD_THRESHOLD = 1.5  # only "bet" ATS when we differ from the line by this much
TOTAL_THRESHOLD = 3.0   # analogous threshold for totals betting

# Rest-day adjustment: DROPPED (not fitted into the final model). On the
# tuning split the walk-forward residual slopes were margin -0.16 pts/day
# and total +0.15 pts/day, improving RMSE by 0.006 / 0.014 -- far inside
# noise (SE ~0.05 / ~0.08) -- and the negative margin slope is implausible
# (likely confounded by MTE scheduling: good teams play 0-rest games
# against cupcakes). See data/ncaab/backtest_results.md.
USE_REST = False

TUNE_SEASONS = (2013, 2019)   # hyperparameters fitted here only
HOLDOUT_SEASONS = (2020, 2026)  # never touched during tuning

ERAS = [
    ("2013-2016", 2013, 2016),
    ("2017-2020", 2017, 2020),
    ("2021-2026", 2021, 2026),
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
        self.margin_resid: list[float] = []
        self.total_resid: list[float] = []

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
        self.margin_resid.append(our_margin - actual_margin)
        self.total_resid.append(our_total - actual_total)

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
        import statistics as _st
        return {
            "games": n,
            "neutral_games": self.neutral_n,
            "su_pct": self.su_w / n if n else float("nan"),
            "model_margin_rmse": math.sqrt(self.model_margin_se / n) if n else float("nan"),
            "line_margin_rmse": math.sqrt(self.line_margin_se / n) if n else float("nan"),
            "model_margin_resid_sd": _st.pstdev(self.margin_resid) if n > 1 else float("nan"),
            "ats": (self.ats_w, self.ats_l, self.ats_p),
            "ats_pct": self.ats_w / decided if decided else float("nan"),
            "ats_decided": decided,
            "model_total_rmse": math.sqrt(self.model_total_se / n) if n else float("nan"),
            "line_total_rmse": math.sqrt(self.line_total_se / n) if n else float("nan"),
            "model_total_resid_sd": _st.pstdev(self.total_resid) if n > 1 else float("nan"),
            "ou": (self.ou_w, self.ou_l, self.ou_p),
            "ou_pct": self.ou_w / ou_decided if ou_decided else float("nan"),
            "ou_decided": ou_decided,
        }


def load_games() -> pd.DataFrame:
    df = pd.read_csv(CSV, parse_dates=["date"])
    df = df.dropna(subset=["spread", "total"]).copy()
    df = df.sort_values("date").reset_index(drop=True)
    df = add_rest_days(df)
    return df


def game_poss(model: NCAABEfficiency, row) -> float:
    """Possessions for the update step: sanitized box-score pace when
    usable, else the model's own tempo estimate (leakage-safe, pre-update).
    See efficiency.sanitize_poss for the data-quality guards."""
    p = sanitize_poss(getattr(row, "poss", None), int(row.season))
    if p is not None:
        return p
    return model.predict_poss(row.home_team, row.away_team)


def run_backtest(games: pd.DataFrame, team_alpha: float = TEAM_ALPHA,
                 carryover: float = SEASON_CARRYOVER,
                 home_edge: float = HOME_EDGE_PTS,
                 rest_margin: float = 0.0, rest_total: float = 0.0,
                 rest_mean: float = 3.0,
                 seasons: tuple[int, int] | None = None) -> dict:
    model = NCAABEfficiency(team_alpha=team_alpha, carryover=carryover,
                            home_edge=home_edge)

    overall = Metrics()
    by_season: dict[int, Metrics] = {}
    by_era: dict[str, Metrics] = {}
    last_season = None

    for row in games.itertuples():
        season = int(row.season)
        if seasons and not (seasons[0] <= season <= seasons[1]):
            continue
        if last_season is not None and season != last_season:
            for _ in range(season - last_season):
                model.new_season()
        last_season = season

        neutral = bool(int(row.neutral))
        saved_edge = model.home_edge
        if neutral:
            model.home_edge = 0.0
        # Predict BEFORE updating: this is the whole honesty of the backtest.
        our_margin, our_total = model.predict(row.home_team, row.away_team,
                                              neutral=neutral)
        model.home_edge = saved_edge

        if rest_margin:
            our_margin = apply_rest_adjustment(our_margin, row.home_rest,
                                               row.away_rest,
                                               pts_per_day=rest_margin)
        if rest_total:
            our_total = apply_rest_adjustment_total(our_total, row.home_rest,
                                                    row.away_rest,
                                                    pts_per_day=rest_total,
                                                    mean_days=rest_mean)

        actual_margin = float(row.home_score) - float(row.away_score)
        actual_total = float(row.home_score) + float(row.away_score)

        overall.add(our_margin, float(row.spread), our_total,
                    float(row.total), actual_margin, actual_total, neutral)
        by_season.setdefault(season, Metrics()).add(
            our_margin, float(row.spread), our_total, float(row.total),
            actual_margin, actual_total, neutral)
        by_era.setdefault(era_of(season), Metrics()).add(
            our_margin, float(row.spread), our_total, float(row.total),
            actual_margin, actual_total, neutral)

        # NOW learn from the game.
        model.update(row.home_team, row.away_team, float(row.home_score),
                     float(row.away_score), game_poss(model, row))

    return {
        "params": {"team_alpha": team_alpha, "carryover": carryover,
                   "home_edge": home_edge, "rest_margin": rest_margin,
                   "rest_total": rest_total},
        "overall": overall.summary(),
        "by_season": {s: m.summary() for s, m in sorted(by_season.items())},
        "by_era": {e: m.summary() for e, m in by_era.items() if e != "other"},
    }


def fit_home_edge(games: pd.DataFrame) -> float:
    """Mean home margin on non-neutral games (tuning split only)."""
    df = games[(games["season"] >= TUNE_SEASONS[0])
               & (games["season"] <= TUNE_SEASONS[1])
               & (games["neutral"] == 0)]
    return float((df["home_score"] - df["away_score"]).mean())


def tune(games: pd.DataFrame) -> dict:
    """Grid-search alpha/carryover on the tuning split by walk-forward
    margin RMSE. The holdout split is never touched here.

    The surface is flat near the minimum (12.015-12.071 across the grid),
    so the final values are the plateau center (alpha 0.10, carry 0.6),
    not the sharp grid minimum -- documented, not cherry-picked.
    """
    tune_games = games[(games["season"] >= TUNE_SEASONS[0])
                       & (games["season"] <= TUNE_SEASONS[1])].copy()
    home_edge = fit_home_edge(games)
    print(f"tuning split: {len(tune_games):,} games, "
          f"fitted home edge {home_edge:.2f} pts")
    results = []
    for alpha in (0.08, 0.10, 0.12):
        for carry in (0.5, 0.6, 0.67):
            r = run_backtest(tune_games, team_alpha=alpha, carryover=carry,
                             home_edge=home_edge,
                             seasons=TUNE_SEASONS)
            rmse = r["overall"]["model_margin_rmse"]
            trmse = r["overall"]["model_total_rmse"]
            results.append((rmse, alpha, carry, trmse))
            print(f"  alpha={alpha} carry={carry}: "
                  f"mRMSE {rmse:.3f} tRMSE {trmse:.3f}")
    results.sort()
    print(f"grid minimum: alpha={results[0][1]} carry={results[0][2]} "
          f"(mRMSE {results[0][0]:.3f})")
    # Plateau-center pick: the whole grid is within ~0.06 RMSE (noise), so
    # take the center of the flat region rather than the sharp minimum.
    alpha, carry = 0.10, 0.6
    print(f"plateau-center pick: alpha={alpha} carry={carry} "
          f"home_edge={home_edge:.2f}")
    return {"team_alpha": alpha, "carryover": carry, "home_edge": home_edge}


def fit_rest_slopes(games: pd.DataFrame, params: dict) -> tuple[float, float]:
    """Fit rest-day slopes on tuning-split walk-forward residuals."""
    tune_games = games[(games["season"] >= TUNE_SEASONS[0])
                       & (games["season"] <= TUNE_SEASONS[1])].copy()
    model = NCAABEfficiency(team_alpha=params["team_alpha"],
                            carryover=params["carryover"],
                            home_edge=params["home_edge"])
    m_res, m_rd, t_res, t_rd = [], [], [], []
    last_season = None
    for row in tune_games.itertuples():
        season = int(row.season)
        if last_season is not None and season != last_season:
            model.new_season()
        last_season = season
        neutral = bool(int(row.neutral))
        saved = model.home_edge
        if neutral:
            model.home_edge = 0.0
        pm, pt = model.predict(row.home_team, row.away_team, neutral=neutral)
        model.home_edge = saved
        am = float(row.home_score) - float(row.away_score)
        at = float(row.home_score) + float(row.away_score)
        hr, ar = row.home_rest, row.away_rest
        if hr == hr and ar == ar:  # not NaN
            m_res.append(am - pm)
            m_rd.append(min(max(hr - ar, -REST_CAP_DAYS), REST_CAP_DAYS))
            t_res.append(at - pt)
            t_rd.append(min(max(hr + ar, -2 * REST_CAP_DAYS),
                            2 * REST_CAP_DAYS))
        model.update(row.home_team, row.away_team, float(row.home_score),
                     float(row.away_score), game_poss(model, row))
    import numpy as np
    m_slope = float(np.polyfit(m_rd, m_res, 1)[0]) if m_res else 0.0
    t_slope = float(np.polyfit(t_rd, t_res, 1)[0]) if t_res else 0.0
    print(f"rest slopes (tuning residuals): margin {m_slope:+.3f} pts/day "
          f"(n={len(m_res):,}), total {t_slope:+.3f} pts/day (n={len(t_res):,})")
    return m_slope, t_slope


def fmt_summary(s: dict) -> str:
    w, l, p = s["ats"]
    ow, ol, op = s["ou"]
    return (f"games={s['games']:>6,}  SU={s['su_pct']:7.1%}  "
            f"margRMSE {s['model_margin_rmse']:6.2f} vs line {s['line_margin_rmse']:6.2f}  "
            f"ATS {w}-{l}-{p} ({s['ats_pct']:.1%} on {s['ats_decided']:,})  "
            f"totRMSE {s['model_total_rmse']:6.2f} vs line {s['line_total_rmse']:6.2f}  "
            f"O/U {ow}-{ol}-{op} ({s['ou_pct']:.1%} on {s['ou_decided']:,})")


def print_report(title: str, r: dict) -> None:
    print(f"=== {title} ===")
    print("Overall")
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
    ap = argparse.ArgumentParser(description="NCAAB walk-forward backtest")
    ap.add_argument("--out", type=str, default=None,
                    help="write JSON results to this path")
    ap.add_argument("--skip-tune", action="store_true",
                    help="use module defaults instead of tuning")
    args = ap.parse_args()

    games = load_games()
    print(f"Loaded {len(games):,} games with lines+poss, "
          f"{games['date'].min().date()} .. {games['date'].max().date()}")

    if args.skip_tune:
        params = {"team_alpha": TEAM_ALPHA, "carryover": SEASON_CARRYOVER,
                  "home_edge": HOME_EDGE_PTS}
    else:
        params = tune(games)

    rest_m, rest_t = fit_rest_slopes(games, params)

    base = run_backtest(games, seasons=TUNE_SEASONS, **params)
    print_report(f"tuning split {TUNE_SEASONS[0]}-{TUNE_SEASONS[1]} "
                 f"(baseline, no rest)", base)

    rest = run_backtest(games, seasons=TUNE_SEASONS, rest_margin=rest_m,
                        rest_total=rest_t, **params)
    b, r_ = base["overall"], rest["overall"]
    print(f"\nrest decision: margin {b['model_margin_rmse']:.3f} -> "
          f"{r_['model_margin_rmse']:.3f}; total {b['model_total_rmse']:.3f} -> "
          f"{r_['model_total_rmse']:.3f}")
    print("rest adjustment DROPPED per USE_REST (see note at top): the "
          "improvements are inside noise and the margin slope sign is "
          "implausible.")
    final_params = dict(params, rest_margin=0.0, rest_total=0.0)

    full = run_backtest(games, **final_params)
    print()
    print_report("FULL SAMPLE 2013-2026 (final params)", full)
    hold = run_backtest(games, seasons=HOLDOUT_SEASONS, **final_params)
    print()
    print_report(f"HOLDOUT {HOLDOUT_SEASONS[0]}-{HOLDOUT_SEASONS[1]} "
                 f"(never tuned on)", hold)

    if args.out:
        with open(args.out, "w") as f:
            json.dump({"params": final_params, "tuning": base,
                       "full": full, "holdout": hold}, f, indent=2)
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
