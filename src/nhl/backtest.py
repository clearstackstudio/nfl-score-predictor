"""Walk-forward backtest, 2019-20 -> 2025-26 (MoneyPuck seasons 2019..2025).

Pre-registered design (scope doc, 2026-10-20):
- Discovery seasons 2019-2022: fit home-ice (Brier grid) + logistic
  calibration map. Validation seasons 2023-2025: frozen, untouched.
- Every prediction uses only games strictly before its date; ratings
  refresh nightly; 2018-19 serves as warmup history only.
- Market comparison lives in market_eval.py (needs the odds pull);
  this runner emits model-only metrics + a predictions parquet.
- Rest term integrated 2026-10-20 (v1.1): expected goals carry the
  REST_BETA rest adjustment from research/nhl_rest/ (pre-registered
  ADOPT verdict; Bryant approved adoption). Home-ice and the
  calibration map are still fitted on rest-free lambdas (beta = 0),
  exactly as the frozen v1 spec fitted them -- the rest term applies
  to the emitted predictions only. The integrated runner reproduces
  the research overlay's validation numbers (Brier 0.2394, totals
  RMSE 2.327); with REST_BETA = 0 it reproduces frozen v1 exactly
  (Brier 0.2401).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ratings import (expected_goals, ratings_snapshot, rest_days_map,  # noqa: E402
                     win_prob)

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"
WARMUP_SEASON = 2018
DISCOVERY = {2019, 2020, 2021, 2022}
VALIDATION = {2023, 2024, 2025}
HOME_ICE_GRID = np.round(np.arange(0.0, 0.401, 0.025), 3)


def walk_forward(tg: pd.DataFrame, rest: dict | None = None) -> pd.DataFrame:
    """One row per game in seasons 2019..2025 with lambda at home_ice=0.

    Expected goals include the rest term (ratings.REST_BETA, adopted
    2026-10-20), so lam_h0/lam_a in the output are post-rest values.
    rest maps game_id -> capped rest differential (see
    ratings.rest_days_map); computed from tg when not supplied.
    """
    if rest is None:
        rest = rest_days_map(tg)
    rows = []
    prior: dict = {}
    last_season = None
    last_snap = None
    dates = sorted(tg["date"].unique())
    for d in dates:
        day = tg[tg["date"] == d]
        season = int(day["season"].iloc[0])
        if season != last_season:
            if last_snap is not None:
                lg = last_snap["lg_x"]
                prior = {t: (lg + 0.5 * (last_snap["raw_off"][t] - lg),
                             lg + 0.5 * (last_snap["raw_def"][t] - lg))
                         for t in last_snap["raw_off"]}
            last_season = season
        hist = tg[(tg["date"] < d) & (tg["season"] >= season - 1)]
        snap = ratings_snapshot(hist, prior)
        last_snap = snap
        if season < 2019 or snap is None:
            continue
        games = day[day["home"] == 1]
        for g in games.itertuples():
            lam = expected_goals(snap, g.team, g.opp, home_ice=0.0,
                                 rest_d=rest.get(int(g.game_id), 0))
            if lam is None:
                continue
            away_row = day[(day["team"] == g.opp)].iloc[0]
            rows.append({
                "game_id": int(g.game_id), "season": season, "date": d,
                "home": g.team, "away": g.opp,
                "lam_h0": lam[0], "lam_a": lam[1],
                "home_goals": int(g.gf), "away_goals": int(away_row["gf"]),
                "home_win": int(g.gf > away_row["gf"]),
            })
    return pd.DataFrame(rows)


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def logloss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def fit_calibration(p: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    z = logit(np.clip(p, 1e-6, 1 - 1e-6))

    def nll(ab):
        a, b = ab
        q = expit(a + b * z)
        q = np.clip(q, 1e-9, 1 - 1e-9)
        return -np.sum(y * np.log(q) + (1 - y) * np.log(1 - q))

    r = minimize(nll, x0=[0.0, 1.0], method="Nelder-Mead")
    return float(r.x[0]), float(r.x[1])


def apply_cal(p: np.ndarray, a: float, b: float) -> np.ndarray:
    return expit(a + b * logit(np.clip(p, 1e-6, 1 - 1e-6)))


def main() -> None:
    tg = pd.read_parquet(DATA / "team_games.parquet")
    tg = tg[tg["season"] >= WARMUP_SEASON]
    rest = rest_days_map(tg)
    pred = walk_forward(tg, rest=rest)
    print(f"predicted games: {len(pred)}")

    # --- fit home ice + calibration on REST-FREE lambdas (beta = 0) ---
    # Frozen-spec fidelity: v1 fitted home-ice and the calibration map
    # with the rest term absent, and the pre-registered rest test judged
    # the term on top of those frozen fits (home-ice 0.20; see
    # research/nhl_rest/RESULTS.md). Fitting on post-rest lambdas would
    # silently change the spec -- the home-ice grid then selects 0.175,
    # an untested model nobody approved. So the fits below run on a
    # rest-free walk-forward; the fitted constants are applied to the
    # emitted predictions, which DO carry the rest term.
    free = walk_forward(tg, rest={})

    disc = free[free["season"].isin(DISCOVERY)]
    scores = {}
    for h in HOME_ICE_GRID:
        p = np.array([win_prob(r.lam_h0 + h, r.lam_a)
                      for r in disc.itertuples()])
        scores[float(h)] = brier(p, disc["home_win"].to_numpy())
    home_ice = min(scores, key=scores.get)
    print(f"home ice fitted: {home_ice} goals "
          f"(grid Brier {scores[home_ice]:.4f} vs 0.0 -> {scores[0.0]:.4f})")

    free["p_raw"] = [win_prob(r.lam_h0 + home_ice, r.lam_a)
                     for r in free.itertuples()]
    d = free[free["season"].isin(DISCOVERY)]
    a, b = fit_calibration(d["p_raw"].to_numpy(), d["home_win"].to_numpy())
    print(f"calibration fitted on discovery: a={a:.3f} b={b:.3f}")

    pred["lam_h"] = pred["lam_h0"] + home_ice
    pred["p_raw"] = [win_prob(r.lam_h, r.lam_a) for r in pred.itertuples()]
    pred["p_home"] = apply_cal(pred["p_raw"].to_numpy(), a, b)

    def metrics(df: pd.DataFrame) -> dict:
        y = df["home_win"].to_numpy()
        tot_pred = (df["lam_h"] + df["lam_a"]).to_numpy()
        tot_act = (df["home_goals"] + df["away_goals"]).to_numpy()
        return {
            "games": int(len(df)),
            "brier_raw": round(brier(df["p_raw"].to_numpy(), y), 4),
            "brier_cal": round(brier(df["p_home"].to_numpy(), y), 4),
            "logloss_cal": round(logloss(df["p_home"].to_numpy(), y), 4),
            "su_acc": round(float(np.mean((df["p_home"] > 0.5) == (y == 1))), 4),
            "total_rmse": round(float(np.sqrt(np.mean((tot_pred - tot_act) ** 2))), 3),
            "total_bias": round(float(np.mean(tot_pred - tot_act)), 3),
            "mean_pred_total": round(float(tot_pred.mean()), 2),
            "mean_actual_total": round(float(tot_act.mean()), 2),
        }

    summary = {
        "home_ice_goals": home_ice,
        "home_ice_grid_brier": {str(k): round(v, 4) for k, v in scores.items()},
        "calibration": {"a": round(a, 4), "b": round(b, 4)},
        "discovery": metrics(pred[pred["season"].isin(DISCOVERY)]),
        "validation": metrics(pred[pred["season"].isin(VALIDATION)]),
        "validation_by_season": {
            str(s): metrics(pred[pred["season"] == s]) for s in sorted(VALIDATION)
        },
    }
    pred.to_parquet(DATA / "backtest_predictions.parquet", index=False)
    (DATA / "backtest_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
