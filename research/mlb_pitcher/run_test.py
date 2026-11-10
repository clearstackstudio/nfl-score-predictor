#!/usr/bin/env python3
"""MLB pitcher-layer test, per research/mlb_pitcher/PREREGISTRATION.md.

Extends the shipped team-level walk-forward (src/mlb) with the
src/mlb/pitcher.py design -- prior-season FIP, IP/(IP+50) regression,
STARTER_SHARE frozen at 0.6, league-average fallback -- and scores both
arms on the SAME 2023-2026 games:

  * team-only predictions: retrain.py configuration (alpha=1/40,
    carryover=0.25, home edge refit on the full span, sigma=4.135,
    Platt recalibration as shipped in winprob.margin_to_prob).
  * pitcher-adjusted: apply_pitcher_adjustment on the same predictions.

Verdict bars (frozen in the preregistration):
  1. paired Brier improvement, bootstrap 95% CI entirely below 0
     (10,000 game resamples, seed 20261023);
  2. margin RMSE does not worsen (delta <= 0);
  3. Brier worsens in at most one of the four seasons.
Seasons with < 90% both-probables coverage are dropped and reported.
ROI is descriptive-only in the preregistration and needs closing lines;
no 2023-2026 lines exist anywhere in the repo (the odds file ends
2021-10-03), so ROI is reported as not computable rather than invented.

Requires fetch_data.py to have populated cache/ first.

Usage:
    .venv-cfb/bin/python research/mlb_pitcher/run_test.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
CACHE = HERE / "cache"
sys.path.insert(0, str(REPO / "src" / "mlb"))

from ratings import fit_home_edge, walk_forward          # noqa: E402
from retrain import load_all_games, ALPHA, CARRYOVER     # noqa: E402
from winprob import margin_to_prob, SIGMA                # noqa: E402
from pitcher import apply_pitcher_adjustment, regress_pitcher_adj, STARTER_SHARE  # noqa: E402
from fetch_data import TEAM_ABBR, VERDICT_SEASONS, PRIOR_SEASONS  # noqa: E402

SEED = 20261023
N_BOOT = 10_000
COVERAGE_BAR = 0.90


# ---------------------------------------------------------------- FIP math
def ip_to_outs(ip) -> int:
    """Stats API inningsPitched ('200.2' = 200 2/3) -> outs."""
    if ip is None:
        return 0
    s = str(ip)
    whole, _, frac = s.partition(".")
    return int(whole) * 3 + (int(frac) if frac else 0)


def aggregate_splits(splits: list[dict], season: int) -> dict | None:
    """Sum one pitcher's stat components over a season's splits.

    Guards against a combined split double-counting team splits: if the
    largest split's outs equal the sum of the rest, it is the combined
    line and is dropped.
    """
    rows = []
    for sp in splits:
        if int(sp.get("season", -1)) != season:
            continue
        st = sp["stat"]
        rows.append({
            "outs": ip_to_outs(st.get("inningsPitched")),
            "hr": st.get("homeRuns"), "bb": st.get("baseOnBalls"),
            "hbp": st.get("hitBatsmen"), "k": st.get("strikeOuts"),
            "er": st.get("earnedRuns"),
        })
    if not rows:
        return None
    if len(rows) > 1:
        rows.sort(key=lambda r: r["outs"], reverse=True)
        if rows[0]["outs"] == sum(r["outs"] for r in rows[1:]) and rows[0]["outs"] > 0:
            rows = rows[1:]
    tot = {"outs": sum(r["outs"] for r in rows)}
    for k in ("hr", "bb", "hbp", "k", "er"):
        vals = [r[k] for r in rows]
        tot[k] = None if any(v is None for v in vals) else sum(vals)
    return tot


def league_totals(prior_season: int) -> dict:
    """League pitching totals for a season, aggregated over the 30 clubs."""
    tot = {"outs": 0, "hr": 0, "bb": 0, "hbp": 0, "k": 0, "er": 0}
    for tid in TEAM_ABBR:
        data = json.loads((CACHE / "league" / f"{prior_season}_{tid}.json").read_text())
        for st in data.get("stats", []):
            agg = aggregate_splits(st.get("splits", []), prior_season)
            if agg is None:
                continue
            for k in tot:
                assert agg[k] is not None, f"league {prior_season} team {tid} missing {k}"
                tot[k] += agg[k]
    ip = tot["outs"] / 3.0
    lg_era = tot["er"] * 9.0 / ip
    lg_fip_core = (13 * tot["hr"] + 3 * (tot["bb"] + tot["hbp"]) - 2 * tot["k"]) / ip
    return {"ip": ip, "era": lg_era, "fip_core": lg_fip_core,
            "cfip": lg_era - lg_fip_core}


def pitcher_adj(pitcher_id: int | None, prior_season: int,
                lg: dict) -> tuple[float, bool]:
    """Regressed ra9_vs_avg for a probable starter, from the PRIOR season.

    Returns (adj, has_prior_record). No prior record -> (0.0, False),
    the design's league-average fallback.
    """
    if pitcher_id is None or (isinstance(pitcher_id, float)
                              and math.isnan(pitcher_id)):
        return 0.0, False
    pitcher_id = int(pitcher_id)  # pandas may carry ids as floats (664353.0)
    path = CACHE / "people" / f"{pitcher_id}.json"
    if not path.exists():
        return 0.0, False
    data = json.loads(path.read_text())
    agg = None
    for st in data.get("stats", []):
        agg = aggregate_splits(st.get("splits", []), prior_season)
        if agg is not None:
            break
    if agg is None or agg["outs"] == 0:
        return 0.0, False
    ip = agg["outs"] / 3.0
    if all(agg[k] is not None for k in ("hr", "bb", "hbp", "k")):
        fip = (13 * agg["hr"] + 3 * (agg["bb"] + agg["hbp"]) - 2 * agg["k"]) / ip + lg["cfip"]
        ra9 = lg["era"] - fip            # league-avg FIP == league ERA by construction
    elif agg["er"] is not None:          # FIP unavailable -> ERA fallback (design)
        ra9 = lg["era"] - agg["er"] * 9.0 / ip
    else:
        return 0.0, False
    return regress_pitcher_adj(ra9, ip), True


# ------------------------------------------------------------- game matching
def load_probables() -> tuple[dict, dict]:
    """Map (date, home, away, home_runs, away_runs) -> probable pitcher ids,
    from the cached schedule responses. Returns (mapping, diagnostics)."""
    by_exact: dict[tuple, list[dict]] = {}
    team_ids_seen: set[int] = set()
    n_api_final = 0
    for path in sorted((CACHE / "schedule").glob("*.json")):
        fetch_date = path.stem
        data = json.loads(path.read_text())
        for day in data.get("dates", []):
            for g in day.get("games", []):
                if g.get("status", {}).get("abstractGameState") != "Final":
                    continue
                n_api_final += 1
                th, ta = g["teams"]["home"], g["teams"]["away"]
                team_ids_seen |= {th["team"]["id"], ta["team"]["id"]}
                entry = {
                    "gamePk": g["gamePk"], "officialDate": g.get("officialDate"),
                    "home_pp": (th.get("probablePitcher") or {}).get("id"),
                    "away_pp": (ta.get("probablePitcher") or {}).get("id"),
                }
                key = (fetch_date, TEAM_ABBR.get(th["team"]["id"]),
                       TEAM_ABBR.get(ta["team"]["id"]),
                       th.get("score"), ta.get("score"))
                by_exact.setdefault(key, []).append(entry)
    diag = {"api_final_games_on_verdict_dates": n_api_final,
            "unknown_team_ids": sorted(team_ids_seen - set(TEAM_ABBR))}
    return by_exact, diag


# ------------------------------------------------------------------- metrics
def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def rmse(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


def main() -> None:
    games = load_all_games()
    home_edge = fit_home_edge(games)
    print(f"games={len(games):,}  home_edge(refit full span)={home_edge:.4f}  "
          f"alpha={ALPHA} carryover={CARRYOVER} sigma={SIGMA} share={STARTER_SHARE}")

    # ---- team-model walk-forward; collect verdict-season predictions
    preds: list[dict] = []

    def hook(row, pred_h, pred_a):
        season = int(row.season)
        if season not in VERDICT_SEASONS:
            return
        preds.append({
            "date": row.date.strftime("%Y-%m-%d"), "season": season,
            "home": row.home, "away": row.away,
            "home_runs": int(row.home_runs), "away_runs": int(row.away_runs),
            "pred_h": pred_h, "pred_a": pred_a,
        })

    walk_forward(games, ALPHA, CARRYOVER, home_edge, hook)
    df = pd.DataFrame(preds)
    print(f"verdict-season predictions: {len(df):,}")

    # ---- join probables
    by_exact, diag = load_probables()
    used: dict[tuple, int] = {}
    home_pp, away_pp, game_pk = [], [], []
    for r in df.itertuples():
        key = (r.date, r.home, r.away, r.home_runs, r.away_runs)
        entries = by_exact.get(key, [])
        idx = used.get(key, 0)
        if idx < len(entries):
            used[key] = idx + 1
            e = entries[idx]
            home_pp.append(e["home_pp"]); away_pp.append(e["away_pp"])
            game_pk.append(e["gamePk"])
        else:
            home_pp.append(None); away_pp.append(None); game_pk.append(None)
    df["gamePk"] = game_pk
    df["home_pp"] = home_pp
    df["away_pp"] = away_pp
    df["matched"] = df["gamePk"].notna()
    df["both_pp"] = df["home_pp"].notna() & df["away_pp"].notna()

    coverage = {}
    for s in VERDICT_SEASONS:
        sub = df[df["season"] == s]
        cov = float(sub["both_pp"].mean())
        coverage[s] = {"games": int(len(sub)), "matched": int(sub["matched"].sum()),
                       "both_probables": int(sub["both_pp"].sum()),
                       "coverage": cov, "kept": cov >= COVERAGE_BAR}
        print(f"  {s}: games={len(sub)} matched={coverage[s]['matched']} "
              f"both_pp={coverage[s]['both_probables']} coverage={cov:.3f} "
              f"kept={coverage[s]['kept']}")
    kept_seasons = [s for s in VERDICT_SEASONS if coverage[s]["kept"]]
    dropped_seasons = [s for s in VERDICT_SEASONS if not coverage[s]["kept"]]

    # ---- pitcher adjustments (prior-season FIP; league constants per season)
    lg_by_prior = {s: league_totals(s) for s in PRIOR_SEASONS}
    print("league prior-season lines:",
          {s: f"ERA {v['era']:.3f} cFIP {v['cfip']:+.3f}" for s, v in lg_by_prior.items()})
    home_adj, away_adj = [], []
    for r in df.itertuples():
        lg = lg_by_prior[r.season - 1]
        ha, _ = pitcher_adj(r.home_pp, r.season - 1, lg)
        aa, _ = pitcher_adj(r.away_pp, r.season - 1, lg)
        home_adj.append(ha); away_adj.append(aa)
    df["home_adj"] = home_adj
    df["away_adj"] = away_adj
    adj_diag = {
        "games_with_any_adjustment": int(((df["home_adj"] != 0) | (df["away_adj"] != 0)).sum()),
        "mean_abs_home_adj": float(df["home_adj"].abs().mean()),
        "mean_abs_diff": float((df["home_adj"] - df["away_adj"]).abs().mean()),
        "max_abs_diff": float((df["home_adj"] - df["away_adj"]).abs().max()),
    }
    print("adjustment diagnostics:", adj_diag)
    assert adj_diag["games_with_any_adjustment"] > 0, "pitcher layer never fired"

    # ---- both arms' predictions
    df["team_margin"] = df["pred_h"] - df["pred_a"]
    df["team_total"] = df["pred_h"] + df["pred_a"]
    adj = [apply_pitcher_adjustment(m, t, h, a) for m, t, h, a in
           zip(df["team_margin"], df["team_total"], df["home_adj"], df["away_adj"])]
    df["adj_margin"] = [a[0] for a in adj]
    df["adj_total"] = [a[1] for a in adj]
    df["p_team"] = [margin_to_prob(m, SIGMA) for m in df["team_margin"]]
    df["p_adj"] = [margin_to_prob(m, SIGMA) for m in df["adj_margin"]]
    df["home_win"] = (df["home_runs"] > df["away_runs"]).astype(float)
    df["actual_margin"] = df["home_runs"] - df["away_runs"]
    df["actual_total"] = df["home_runs"] + df["away_runs"]

    def arm_metrics(sub: pd.DataFrame) -> dict:
        y = sub["home_win"].to_numpy()
        return {
            "games": int(len(sub)),
            "brier_team": brier(sub["p_team"].to_numpy(), y),
            "brier_adj": brier(sub["p_adj"].to_numpy(), y),
            "margin_rmse_team": rmse((sub["team_margin"] - sub["actual_margin"]).to_numpy()),
            "margin_rmse_adj": rmse((sub["adj_margin"] - sub["actual_margin"]).to_numpy()),
            "total_rmse_team": rmse((sub["team_total"] - sub["actual_total"]).to_numpy()),
            "total_rmse_adj": rmse((sub["adj_total"] - sub["actual_total"]).to_numpy()),
            "su_team": float(((sub["p_team"] > 0.5) == (y > 0.5)).mean()),
            "su_adj": float(((sub["p_adj"] > 0.5) == (y > 0.5)).mean()),
        }

    vdf = df[df["season"].isin(kept_seasons)].copy()
    per_season = {int(s): arm_metrics(vdf[vdf["season"] == s]) for s in kept_seasons}
    overall = arm_metrics(vdf)
    overall["brier_delta"] = overall["brier_adj"] - overall["brier_team"]
    overall["margin_rmse_delta"] = overall["margin_rmse_adj"] - overall["margin_rmse_team"]

    # ---- paired bootstrap on per-game Brier differences (verdict sample)
    d = ((vdf["p_adj"] - vdf["home_win"]) ** 2
         - (vdf["p_team"] - vdf["home_win"]) ** 2).to_numpy()
    rng = np.random.default_rng(SEED)
    n = len(d)
    boot = np.empty(N_BOOT)
    for i in range(0, N_BOOT, 500):
        m = min(500, N_BOOT - i)
        idx = rng.integers(0, n, size=(m, n))
        boot[i:i + m] = d[idx].mean(axis=1)
    ci_lo, ci_hi = float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))

    # ---- decision rule (frozen)
    seasons_worsened = sum(1 for s in kept_seasons
                           if per_season[s]["brier_adj"] > per_season[s]["brier_team"])
    bar1 = ci_hi < 0
    bar2 = overall["margin_rmse_delta"] <= 0
    bar3 = seasons_worsened <= 1
    if not kept_seasons:
        verdict = "DEFERRED"
    elif bar1 and bar2 and bar3:
        verdict = "ADOPT"
    else:
        verdict = "KILL"

    # ---- secondary descriptive: share fitted on 2023-24, frozen for 2025-26
    secondary = None
    fit_seasons = [s for s in (2023, 2024) if s in kept_seasons]
    eval_seasons = [s for s in (2025, 2026) if s in kept_seasons]
    if fit_seasons and eval_seasons:
        fdf = vdf[vdf["season"].isin(fit_seasons)]
        edf = vdf[vdf["season"].isin(eval_seasons)]
        y_f, y_e = fdf["home_win"].to_numpy(), edf["home_win"].to_numpy()

        def brier_at(sub, y, share):
            m = (sub["team_margin"] + share * (sub["home_adj"] - sub["away_adj"])).to_numpy()
            p = np.array([margin_to_prob(x, SIGMA) for x in m])
            return brier(p, y)

        grid = {round(s, 1): brier_at(fdf, y_f, s) for s in np.arange(0, 1.21, 0.1)}
        best_share = min(grid, key=grid.get)
        secondary = {
            "fit_seasons": fit_seasons, "eval_seasons": eval_seasons,
            "fitted_share": best_share, "fit_brier_by_share": grid,
            "eval_brier_delta_vs_team": brier_at(edf, y_e, best_share)
                - brier_at(edf, y_e, 0.0),
            "note": "descriptive only -- no verdict power (preregistration)",
        }

    results = {
        "test": "MLB starting-pitcher layer (src/mlb/pitcher.py design) vs team-only",
        "preregistration": "research/mlb_pitcher/PREREGISTRATION.md (2026-10-23)",
        "config": {
            "alpha": ALPHA, "carryover": CARRYOVER, "home_edge_refit": home_edge,
            "sigma": SIGMA, "starter_share_frozen": STARTER_SHARE,
            "pitcher_quality": "prior-season FIP (components + league cFIP); "
                               "ERA fallback; IP/(IP+50) regression; "
                               "no prior record -> 0.0 league average",
            "bootstrap": {"resamples": N_BOOT, "seed": SEED, "ci": "percentile 95%"},
        },
        "adjustment_diagnostics": adj_diag,
        "sample": {
            "verdict_seasons_kept": kept_seasons,
            "verdict_seasons_dropped_coverage": dropped_seasons,
            "verdict_games": int(len(vdf)),
            "coverage_by_season": {str(k): v for k, v in coverage.items()},
            "matching_diagnostics": diag,
        },
        "overall": overall,
        "brier_delta_bootstrap_ci95": [ci_lo, ci_hi],
        "per_season": {str(k): v for k, v in per_season.items()},
        "decision_rule": {
            "bar1_brier_ci_entirely_below_0": {"pass": bool(bar1), "ci": [ci_lo, ci_hi]},
            "bar2_margin_rmse_not_worse": {"pass": bool(bar2),
                                           "delta": overall["margin_rmse_delta"]},
            "bar3_brier_worsens_in_at_most_1_season": {
                "pass": bool(bar3), "seasons_worsened": seasons_worsened},
        },
        "verdict": verdict,
        "roi_descriptive": {
            "available": False,
            "reason": "No closing lines exist for 2023-2026 games anywhere in "
                      "the repo: the odds file (nba-data/mlb_bonus/"
                      "oddsDataMLB.csv) ends 2021-10-03 and the 2022-2026 "
                      "backfill is scores-only. Moneyline/totals ROI at "
                      "closing prices is therefore not computable for the "
                      "verdict sample; per the preregistration ROI carries "
                      "no verdict power.",
        },
        "secondary_share_fit_descriptive": secondary,
    }
    (HERE / "results.json").write_text(json.dumps(results, indent=2))

    out = df.rename(columns={"home_pp": "home_pp_id", "away_pp": "away_pp_id"})
    for c in ("home_pp_id", "away_pp_id"):
        out[c] = out[c].apply(lambda v: "" if v is None or (isinstance(v, float)
                                  and math.isnan(v)) else int(v))
    out[["date", "season", "gamePk", "home", "away", "home_runs", "away_runs",
         "home_pp_id", "away_pp_id", "home_adj", "away_adj",
         "team_margin", "adj_margin", "team_total", "adj_total",
         "p_team", "p_adj", "home_win"]].to_csv(HERE / "per_game.csv", index=False)

    print(json.dumps({k: results[k] for k in
                      ("verdict", "overall", "brier_delta_bootstrap_ci95",
                       "decision_rule")}, indent=2))
    print(f"wrote results.json + per_game.csv ({len(out):,} games incl. dropped seasons)")


if __name__ == "__main__":
    main()
