"""Post-adoption audit of CFB TOTAL_SHRINKAGE = 0.7.

Implements research/cfb_totals_shrinkage/PREREGISTRATION.md exactly:
  Q1 reproduction of the adopted walk-forward headline numbers
  Q2 play-basis OU comparison, s=0.7 vs s=1.0 (live generator's rule)
  Q3 recalibration refit (fit 2014-2023, evaluate 2024-2025, bootstrap)

Data: research/cfb_improvement/frame_B.parquet only (8,947 games,
2014-2025, FBS). No CFBD calls. Nothing outside this directory is
written. Run under the repo venv:

    .venv-cfb/bin/python research/cfb_totals_shrinkage/audit.py [--only q1|q2|q3]

Sections accumulate into results.json in this directory.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
FRAME = REPO / "research" / "cfb_improvement" / "frame_B.parquet"
RESULTS_JSON = HERE / "results.json"

sys.path.insert(0, str(REPO / "src"))
from recalibration import _CURVES, recalibrate  # noqa: E402  (live code, read-only)

TEST_SEASONS = list(range(2014, 2026))
LIVE_SD = json.loads((REPO / "data" / "cfb" / "cfb_backtest.json")
                     .read_text())["total_sd"]  # live generator's total_sd

# ---- recorded adoption evidence (research/cfb_improvement/out_main.txt,
# ---- RESULTS.md H-T3, cfb/cfb_ratings.py header) -------------------------
REC_POOLED_RMSE = {1.0: 18.73, 0.7: 17.73}
REC_RAW_RMSE_SEASON = {2014: 19.69, 2015: 19.42, 2016: 18.22, 2017: 19.73,
                       2018: 18.62, 2019: 18.13, 2020: 18.74, 2021: 18.45,
                       2022: 18.65, 2023: 18.13, 2024: 18.62, 2025: 18.45}
REC_WF_SHRUNK_RMSE = {2015: 18.52, 2016: 17.63, 2017: 18.76, 2018: 17.76,
                      2019: 17.17, 2020: 17.93, 2021: 17.24, 2022: 17.64,
                      2023: 17.16, 2024: 17.48, 2025: 17.25}
REC_LIVE_RULE_OU = {1.0: (2513, 2469, 62), 0.7: (2906, 2850, 67)}


def load_frame() -> pd.DataFrame:
    df = pd.read_parquet(FRAME)
    df = df[df.season.isin(TEST_SEASONS)].copy()
    df["tresid"] = df.actual_total - df.line_total
    for s in (1.0, 0.7):
        df[f"total_{s}"] = df.epa_const + s * (df.our_total - df.epa_const)
        df[f"edge_{s}"] = df[f"total_{s}"] - df.line_total
    return df


def rmse(pred: pd.Series, actual: pd.Series) -> float:
    return float(np.sqrt(((pred - actual) ** 2).mean()))


def grade(edge: pd.Series, resid: pd.Series):
    """Same convention as research/cfb_improvement/analyze_main.grade."""
    e, r = edge, resid
    w = int(((r.abs() >= 0.01) & ((r > 0) == (e > 0))).sum())
    p = int((r.abs() < 0.01).sum())
    return w, int(len(r) - w - p), p


def save_section(name: str, payload: dict) -> None:
    doc = {}
    if RESULTS_JSON.exists():
        doc = json.loads(RESULTS_JSON.read_text())
    doc[name] = payload
    RESULTS_JSON.write_text(json.dumps(doc, indent=2))
    print(f"[saved {name} -> results.json]")


# --------------------------------------------------------------------- Q1
def q1(df: pd.DataFrame) -> dict:
    print("=== Q1: reproduction of adopted walk-forward numbers ===")
    pooled = {s: rmse(df[f"total_{s}"], df.actual_total) for s in (1.0, 0.7)}
    per_season = {}
    for s in (1.0, 0.7):
        per_season[s] = {int(y): rmse(g[f"total_{s}"], g.actual_total)
                         for y, g in df.groupby("season")}
    # Walk-forward selection reproduction (grid + rule from analyze_main.h_t3)
    grid = [1.0, 0.95, 0.9, 0.85, 0.8, 0.7]
    wf = {}
    for y in sorted(df.season.unique()):
        if y == df.season.min():
            continue
        hist = df[df.season < y]
        d = df[df.season == y]
        best = min(grid, key=lambda s_: rmse(
            hist.epa_const + s_ * (hist.our_total - hist.epa_const),
            hist.actual_total))
        wf[int(y)] = {"s_star": best,
                      "rmse_raw": rmse(d.our_total, d.actual_total),
                      "rmse_shrunk": rmse(
                          d.epa_const + best * (d.our_total - d.epa_const),
                          d.actual_total)}
    checks = {
        "pooled_rmse_s1.0_matches": round(pooled[1.0], 2) == REC_POOLED_RMSE[1.0],
        "pooled_rmse_s0.7_matches": round(pooled[0.7], 2) == REC_POOLED_RMSE[0.7],
        "per_season_raw_rmse_all_match": all(
            round(per_season[1.0][y], 2) == v
            for y, v in REC_RAW_RMSE_SEASON.items()),
        "wf_s_star_0.7_all_11": all(v["s_star"] == 0.7 for v in wf.values())
                                and len(wf) == 11,
        "wf_shrunk_rmse_all_match": all(
            round(wf[y]["rmse_shrunk"], 2) == v
            for y, v in REC_WF_SHRUNK_RMSE.items()),
        "wf_improved_11_of_11": sum(
            v["rmse_shrunk"] < v["rmse_raw"] for v in wf.values()) == 11,
        "fixed_s0.7_improved_eval_seasons": sum(
            per_season[0.7][y] < per_season[1.0][y]
            for y in range(2015, 2026)),
    }
    print(f"  pooled RMSE  s=1.0 {pooled[1.0]:.4f} (recorded 18.73)   "
          f"s=0.7 {pooled[0.7]:.4f} (recorded 17.73)")
    for y in TEST_SEASONS:
        line = (f"  {y}: raw {per_season[1.0][y]:6.2f}  "
                f"s0.7 {per_season[0.7][y]:6.2f}")
        if y in wf:
            line += (f"   WF s*={wf[y]['s_star']}  "
                     f"shrunk {wf[y]['rmse_shrunk']:.2f} "
                     f"(recorded {REC_WF_SHRUNK_RMSE[y]})")
        print(line)
    for k, v in checks.items():
        print(f"  check {k}: {v}")
    verdict = "CONFIRMED" if all(checks.values()) else "FLAGGED"
    print(f"  Q1 VERDICT: {verdict}")
    return {
        "verdict": verdict,
        "n_games": int(len(df)),
        "pooled_total_rmse": {str(s): pooled[s] for s in (1.0, 0.7)},
        "pooled_total_rmse_recorded": {str(s): REC_POOLED_RMSE[s]
                                       for s in (1.0, 0.7)},
        "per_season_total_rmse": {
            str(s): {str(y): per_season[s][y] for y in TEST_SEASONS}
            for s in (1.0, 0.7)},
        "walk_forward": {str(y): wf[y] for y in sorted(wf)},
        "checks": checks,
    }


# --------------------------------------------------------------------- Q2
def live_rule_ou(df: pd.DataFrame, s: float):
    e = df[f"edge_{s}"]
    m = (e.abs() >= 1.0) & (e.abs() <= 8.5)  # generator: >=1.0, circuit 8.5
    return grade(e[m], df.tresid[m]), int(m.sum())


def q2(df: pd.DataFrame, q1_payload: dict) -> dict:
    print("=== Q2: play-basis OU, live generator rule (1.0 <= |edge| <= 8.5) ===")
    out = {}
    for s in (1.0, 0.7):
        (w, l, p), n = live_rule_ou(df, s)
        win_pct = w / (w + l)
        out[s] = {"w": w, "l": l, "p": p, "n_picks": n, "win_pct": win_pct,
                  "dist_from_50pp": abs(win_pct - 0.5) * 100,
                  "recorded_wlp": REC_LIVE_RULE_OU[s],
                  "reproduces_recorded": (w, l, p) == REC_LIVE_RULE_OU[s]}
        print(f"  s={s}: {w}-{l}-{p}  win% {win_pct:.4f}  "
              f"|win%-50| {abs(win_pct - 0.5) * 100:.3f} pp  "
              f"(recorded {REC_LIVE_RULE_OU[s]}, "
              f"match={out[s]['reproduces_recorded']})")
    rmse_lower = (q1_payload["pooled_total_rmse"]["0.7"]
                  < q1_payload["pooled_total_rmse"]["1.0"])
    closer = out[0.7]["dist_from_50pp"] <= out[1.0]["dist_from_50pp"]
    supported = bool(closer and rmse_lower)
    print(f"  s=0.7 at least as close to 50%: {closer}; "
          f"totals RMSE lower: {rmse_lower}")
    print(f"  Q2 VERDICT: {'SUPPORTED on play basis' if supported else 'NOT SUPPORTED on play basis'}")
    return {"verdict": "supported" if supported else "not_supported",
            "rule": "1.0 <= |total_edge| <= 8.5 (cfb_weekly_picks.py: "
                    "pick at |edge|>=1.0, TOTAL_CIRCUIT=8.5)",
            "s_1.0": out[1.0], "s_0.7": out[0.7],
            "dist_from_50pp": {"1.0": out[1.0]["dist_from_50pp"],
                               "0.7": out[0.7]["dist_from_50pp"]},
            "rmse_condition_s0.7_lower": bool(rmse_lower)}


# --------------------------------------------------------------------- Q3
def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def interp_curve(points, prob: float) -> float:
    """Byte-for-byte semantics of src/recalibration.recalibrate, with the
    curve points passed in (the live function hard-codes its curves)."""
    pts = points
    if prob <= pts[0][0]:
        cal = pts[0][1]
    elif prob >= pts[-1][0]:
        cal = pts[-1][1]
    else:
        cal = pts[-1][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= prob <= x1:
                t = (prob - x0) / (x1 - x0)
                cal = y0 + t * (y1 - y0)
                break
    return min(0.99, max(0.50, cal))


BINS = [(0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 1.01)]


def fit_curve(records: pd.DataFrame):
    """src/ncaab/fit_recalibration.py fit_curve, same bins/anchoring.
    records: raw prob + hit flag for decided (non-push) totals picks."""
    pts = [(0.50, 0.50)]
    table = []
    for lo, hi in BINS:
        sel = records[(records.raw >= lo) & (records.raw < hi)]
        if sel.empty:
            table.append({"bin": [lo, hi], "n": 0})
            continue
        mean_p = float(sel.raw.mean())
        rate = float(sel.hit.mean())
        pts.append((round(mean_p, 3), round(rate, 3)))
        table.append({"bin": [lo, hi], "n": int(len(sel)),
                      "mean_raw": mean_p, "empirical": rate})
    return pts, table


def pick_records(df: pd.DataFrame, seasons) -> pd.DataFrame:
    d = df[df.season.isin(seasons)]
    e = d["edge_0.7"]
    m = (e.abs() >= 1.0) & (e.abs() <= 8.5) & (d.tresid.abs() >= 0.01)
    d = d[m]
    raw = np.array([normal_cdf(abs(x) / LIVE_SD) for x in d["edge_0.7"]])
    hit = ((d.tresid > 0) == (d["edge_0.7"] > 0)).to_numpy()
    return pd.DataFrame({"raw": raw, "hit": hit,
                         "edge": d["edge_0.7"].to_numpy(),
                         "over": (d.tresid > 0).astype(float).to_numpy()})


def p_over(edge: float, points) -> float:
    p_pick = interp_curve(points, normal_cdf(abs(edge) / LIVE_SD))
    return p_pick if edge > 0 else 1.0 - p_pick


def calib_slope(p: np.ndarray, y: np.ndarray):
    """Logistic calibration intercept/slope on logit(p), Newton-Raphson."""
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    x = np.log(pc / (1 - pc))
    X = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(100):
        z = X @ beta
        mu = 1 / (1 + np.exp(-z))
        W = mu * (1 - mu)
        grad = X.T @ (y - mu)
        hess = X.T @ (X * W[:, None])
        step = np.linalg.solve(hess + 1e-9 * np.eye(2), grad)
        beta = beta + step
        if np.max(np.abs(step)) < 1e-10:
            break
    return float(beta[0]), float(beta[1])


def q3(df: pd.DataFrame) -> dict:
    print("=== Q3: recalibration refit (fit 2014-2023, eval 2024-2025) ===")
    stale_pts = [tuple(p) for p in _CURVES[("cfb", "totals")]]
    # self-check: local interp == live recalibrate() for the stale curve
    grid = np.linspace(0.5, 0.99, 50)
    assert all(abs(interp_curve(stale_pts, float(g)) - recalibrate(float(g), "cfb", "totals")) < 1e-12
               for g in grid), "interp replica diverges from live recalibrate()"
    print("  interp replica == live recalibrate() on grid: True")
    print(f"  live total_sd (data/cfb/cfb_backtest.json): {LIVE_SD:.4f}")

    fit = pick_records(df, range(2014, 2024))
    refit_pts, fit_table = fit_curve(fit)
    print(f"  fit records (2014-2023, decided live-rule picks): {len(fit)}")
    for row in fit_table:
        print(f"    bin {row['bin']}: n={row['n']}"
              + (f" mean_raw={row['mean_raw']:.3f} emp={row['empirical']:.3f}"
                 if row["n"] else ""))
    print(f"  refit curve points: {refit_pts}")
    print(f"  stale curve points: {stale_pts}")

    ev = pick_records(df, [2024, 2025])
    y = ev["over"].to_numpy()
    p_raw = np.array([normal_cdf(e / LIVE_SD) for e in ev.edge])
    p_stale = np.array([p_over(e, stale_pts) for e in ev.edge])
    p_refit = np.array([p_over(e, refit_pts) for e in ev.edge])
    b_raw = float(np.mean((p_raw - y) ** 2))
    b_stale = float(np.mean((p_stale - y) ** 2))
    b_refit = float(np.mean((p_refit - y) ** 2))
    slopes = {name: calib_slope(p, y)
              for name, p in (("raw", p_raw), ("stale", p_stale),
                              ("refit", p_refit))}
    print(f"  eval games (2024-2025, decided live-rule picks): {len(ev)}")
    print(f"  Brier  raw {b_raw:.4f}   stale {b_stale:.4f}   refit {b_refit:.4f}")
    for name, (a, b) in slopes.items():
        print(f"  calibration ({name}): intercept {a:+.3f}  slope {b:.3f}")

    rng = np.random.default_rng(20261023)
    d = (p_refit - y) ** 2 - (p_stale - y) ** 2
    n = len(d)
    boot = np.array([d[rng.integers(0, n, n)].mean() for _ in range(10_000)])
    lo, hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))
    recommend = hi < 0
    print(f"  paired bootstrap Brier diff (refit-stale): mean "
          f"{float(d.mean()):+.5f}  95% CI [{lo:+.5f}, {hi:+.5f}]")
    print(f"  Q3 VERDICT: {'RECOMMEND' if recommend else 'NOT'}")
    fit_sd = float(np.std(
        (df[df.season.between(2014, 2023)]["total_0.7"]
         - df[df.season.between(2014, 2023)].actual_total), ddof=1))
    return {
        "verdict": "RECOMMEND" if recommend else "NOT",
        "live_total_sd_used": LIVE_SD,
        "fit_window_resid_sd_s0.7_note": fit_sd,
        "fit_seasons": [2014, 2023], "eval_seasons": [2024, 2025],
        "fit_n_decided_picks": int(len(fit)),
        "eval_n_decided_picks": int(len(ev)),
        "refit_curve_points": [list(p) for p in refit_pts],
        "stale_curve_points": [list(p) for p in stale_pts],
        "fit_bins": fit_table,
        "brier": {"raw": b_raw, "stale": b_stale, "refit": b_refit,
                  "refit_minus_stale": b_refit - b_stale},
        "calibration_slope": {k: {"intercept": v[0], "slope": v[1]}
                              for k, v in slopes.items()},
        "bootstrap": {"resamples": 10_000, "seed": 20261023,
                      "ci95": [lo, hi], "ci_below_zero": bool(recommend)},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["q1", "q2", "q3"], default=None)
    args = ap.parse_args()
    df = load_frame()
    doc = (json.loads(RESULTS_JSON.read_text())
           if RESULTS_JSON.exists() else {})

    if args.only in (None, "q1"):
        payload = q1(df)
        save_section("q1", payload)
        if payload["verdict"] == "FLAGGED":
            print("Q1 FLAGGED -> stop per preregistration decision rule.")
            return
        doc["q1"] = payload
    if args.only in (None, "q2"):
        if "q1" not in doc:
            print("Q2 needs Q1 results; run --only q1 first.")
            return
        save_section("q2", q2(df, doc["q1"]))
    if args.only in (None, "q3"):
        save_section("q3", q3(df))


if __name__ == "__main__":
    main()
