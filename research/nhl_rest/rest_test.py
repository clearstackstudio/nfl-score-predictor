"""NHL rest-effect add-on test.

Frozen design: research/nhl_rest/PREREGISTRATION.md (committed before
this script was run). Reuses src/nhl read-only: the frozen walk-forward
lambdas in data/nhl/backtest_predictions.parquet and ratings.win_prob.

- Feature: rest_days per team from data/nhl/team_games.parquet dates
  (same-season previous regular-season game; first game of a season = 3);
  d = clip(rest_home - rest_away, -3, +3).
- Term: lam_home' = lam_home + beta*d, lam_away' = lam_away - beta*d,
  floored at 0.5. Base lambdas are frozen v1 (home-ice +0.20 included).
- Fit: beta grid [-0.10, +0.10] step 0.01 on DISCOVERY only, minimizing
  raw moneyline Brier.
- Judge: validation frozen; ADOPT needs Brier < 0.2401 AND paired
  bootstrap 95% CI on per-game Brier diff (v1 - rest) excluding 0;
  guardrail: validation totals RMSE <= 2.327 + 0.01.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src" / "nhl"))
from ratings import win_prob  # noqa: E402

DATA = REPO / "data" / "nhl"
OUT = Path(__file__).resolve().parent / "rest_results.json"
DISCOVERY = {2019, 2020, 2021, 2022}
VALIDATION = {2023, 2024, 2025}
BETAS = np.round(np.arange(-0.10, 0.1001, 0.01), 2)
SEED = 20261020
N_BOOT = 10_000
V1_VAL_BRIER = 0.2401
V1_VAL_TOT_RMSE = 2.327


def compute_rest(tg: pd.DataFrame) -> pd.DataFrame:
    """One row per game: rest_h, rest_a, d (capped to [-3, +3])."""
    tg = tg.sort_values(["team", "season", "date"]).copy()
    prev = tg.groupby(["team", "season"])["date"].shift(1)
    tg["rest"] = (tg["date"] - prev).dt.days.fillna(3).astype(int)
    home = tg[tg["home"] == 1][["game_id", "rest"]].rename(
        columns={"rest": "rest_h"})
    away = tg[tg["home"] == 0][["game_id", "rest"]].rename(
        columns={"rest": "rest_a"})
    g = home.merge(away, on="game_id", how="inner")
    g["d"] = (g["rest_h"] - g["rest_a"]).clip(-3, 3)
    return g


def rest_probs(df: pd.DataFrame, beta: float) -> np.ndarray:
    """Win probs under the rest term at the given beta (raw pipeline)."""
    out = np.empty(len(df))
    for i, r in enumerate(df.itertuples()):
        lam_h = max(r.lam_h + beta * r.d, 0.5)
        lam_a = max(r.lam_a - beta * r.d, 0.5)
        out[i] = win_prob(lam_h, lam_a)
    return out


def total_rmse(df: pd.DataFrame, beta: float) -> float:
    lam_h = np.maximum(df["lam_h"].to_numpy() + beta * df["d"].to_numpy(), 0.5)
    lam_a = np.maximum(df["lam_a"].to_numpy() - beta * df["d"].to_numpy(), 0.5)
    pred = lam_h + lam_a
    act = (df["home_goals"] + df["away_goals"]).to_numpy()
    return float(np.sqrt(np.mean((pred - act) ** 2)))


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def main() -> None:
    tg = pd.read_parquet(DATA / "team_games.parquet")
    rest = compute_rest(tg)
    pred = pd.read_parquet(DATA / "backtest_predictions.parquet")
    pred = pred[pred["season"].isin(DISCOVERY | VALIDATION)]
    pred = pred.merge(rest, on="game_id", how="inner")
    assert len(pred) == 8508 and pred["d"].notna().all(), \
        f"merge broke: {len(pred)} rows"
    pred = pred.sort_values(["date", "game_id"]).reset_index(drop=True)

    disc = pred[pred["season"].isin(DISCOVERY)].reset_index(drop=True)
    val = pred[pred["season"].isin(VALIDATION)].reset_index(drop=True)
    y_d = disc["home_win"].to_numpy()
    y_v = val["home_win"].to_numpy()

    # --- sanity: frozen v1 baselines reproduce from the parquet ---
    v1_disc_brier = brier(disc["p_raw"].to_numpy(), y_d)
    v1_val_brier = brier(val["p_raw"].to_numpy(), y_v)
    assert round(v1_disc_brier, 4) == 0.2356, v1_disc_brier
    assert round(v1_val_brier, 4) == V1_VAL_BRIER, v1_val_brier
    print(f"sanity OK: v1 discovery Brier {v1_disc_brier:.4f}, "
          f"validation Brier {v1_val_brier:.4f}, n_val={len(val)}")

    # --- rest distribution (context for the writeup) ---
    dist = {
        "val_share_d_nonzero": round(float(np.mean(val["d"] != 0)), 4),
        "val_share_abs_d_ge2": round(float(np.mean(val["d"].abs() >= 2)), 4),
        "val_share_home_b2b_rest1": round(float(np.mean(val["rest_h"] == 1)), 4),
        "val_share_away_b2b_rest1": round(float(np.mean(val["rest_a"] == 1)), 4),
    }
    print("rest distribution (validation):", dist)

    # --- fit beta on discovery only ---
    grid = {}
    for beta in BETAS:
        grid[float(beta)] = brier(rest_probs(disc, float(beta)), y_d)
    beta_star = float(min(grid, key=grid.get))
    print(f"beta grid (discovery Brier): "
          + ", ".join(f"{b:+.2f}:{v:.4f}" for b, v in grid.items()))
    print(f"fitted beta = {beta_star:+.2f} "
          f"(discovery Brier {grid[beta_star]:.4f} vs beta=0 {grid[0.0]:.4f})")

    # --- judge on validation (frozen) ---
    p_rest = rest_probs(val, beta_star)
    rest_val_brier = brier(p_rest, y_v)
    v1_su = float(np.mean((val["p_raw"].to_numpy() > 0.5) == (y_v == 1)))
    rest_su = float(np.mean((p_rest > 0.5) == (y_v == 1)))
    v1_tot = total_rmse(val, 0.0)
    rest_tot = total_rmse(val, beta_star)
    assert round(v1_tot, 3) == V1_VAL_TOT_RMSE, v1_tot

    diff = (val["p_raw"].to_numpy() - y_v) ** 2 - (p_rest - y_v) ** 2
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(val), size=(N_BOOT, len(val)))
    boot_means = diff[idx].mean(axis=1)
    ci_lo, ci_hi = (float(np.percentile(boot_means, 2.5)),
                    float(np.percentile(boot_means, 97.5)))

    bar_a = rest_val_brier < V1_VAL_BRIER
    bar_b = ci_lo > 0.0 or ci_hi < 0.0
    guardrail = rest_tot <= V1_VAL_TOT_RMSE + 0.01
    verdict = "ADOPT" if (bar_a and bar_b and guardrail) else "KILL"

    results = {
        "beta_fitted_discovery": beta_star,
        "discovery_brier_grid": {f"{b:+.2f}": round(v, 4)
                                 for b, v in grid.items()},
        "discovery_brier_beta0": round(grid[0.0], 4),
        "discovery_brier_beta_star": round(grid[beta_star], 4),
        "validation": {
            "n": int(len(val)),
            "v1_brier_raw": round(v1_val_brier, 4),
            "rest_brier_raw": round(rest_val_brier, 4),
            "brier_diff_mean": round(float(diff.mean()), 5),
            "bootstrap_ci95": [round(ci_lo, 5), round(ci_hi, 5)],
            "v1_su_raw": round(v1_su, 4),
            "rest_su_raw": round(rest_su, 4),
            "v1_totals_rmse": round(v1_tot, 3),
            "rest_totals_rmse": round(rest_tot, 3),
        },
        "rest_distribution_validation": dist,
        "bar_a_brier_improves": bool(bar_a),
        "bar_b_ci_excludes_0": bool(bar_b),
        "guardrail_totals_ok": bool(guardrail),
        "verdict": verdict,
    }
    OUT.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
