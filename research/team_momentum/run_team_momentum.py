"""NFL team-momentum diagnostic — run of the frozen 2026-10-19
preregistration in research/team_momentum/PREREGISTRATION.md.

Phases:
  0. Reproduce the live EPA baseline exactly as-is (2021-2024). STOP on
     any mismatch with ATS 47.29% (393-438-29), margin RMSE 14.131,
     n = 1,107.
  1. Build one walk-forward frame for 2021-2025 using the live EPA
     configuration and the QB-recency runner's loop structure. Verify
     the 2021-2024 rows against
     research/turnover_damping/per_game_robustness_w0.50_qb.csv before
     fitting anything.
  2. Compute the single frozen momentum feature: for each team, the OLS
     slope of net EPA/play (off_epa_play - def_epa_play) over its last
     four prior games in the current season. Eligibility requires four
     prior in-season games for both teams. The season-to-date mean is
     retained as the registered interpretive baseline; because it is
     constant over the four-game window, it does not alter the slope.
  3. Fit gamma by OLS of margin_resid on momentum_diff using discovery
     seasons 2021-2023 only. Evaluate the three frozen validation bars
     on 2024-2025, calculate the paired-bootstrap RMSE-difference CI
     (10,000 resamples, seed 20261019), and report the mandatory market
     mechanism diagnostic.

No live model code or configuration is changed. An ADOPT result is a
recommendation only, per the preregistration.

Run: .venv-cfb/bin/python research/team_momentum/run_team_momentum.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "team_momentum"
sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import epa_ratings  # noqa: E402
from backtest import closing_home_spread, load_games  # noqa: E402
from epa_ratings import (  # noqa: E402
    ABBR_TO_FULL, CARRYOVER, DATA, HOME_EDGE_PTS, PLAYS_PER_GAME,
    WINDOW_GAMES, adjusted_ratings, load_qb_plays, load_team_games,
    qb_adjustments, run_backtest, week_int,
)

YEARS = [2021, 2022, 2023, 2024, 2025]
DISCOVERY = [2021, 2022, 2023]
VALIDATION = [2024, 2025]
PUBLISHED_ATS_PCT = 47.29
PUBLISHED_RMSE = 14.131
PUBLISHED_ATS = (393, 438, 29)
REFERENCE_RMSE = 14.130860208614187
BOOTSTRAP_SEED = 20261019
BOOTSTRAP_RESAMPLES = 10_000


def fail(results: dict, msg: str) -> None:
    """Stop-rule handler: write the halt state and do not proceed."""
    results["status"] = "STOPPED"
    results["stop_reason"] = msg
    results["verdict"] = None
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    (OUT / "RESULTS.md").write_text(
        "# Team momentum — RESULTS\n\n"
        f"**STOPPED at the baseline gate: {msg}**\n\n"
        "Per the frozen preregistration, the test does not proceed on a "
        "mismatched baseline or unverified per-game replication. No "
        "verdict is recorded, no gamma was fitted, and no model change "
        "is implied. A pin correction requires a dated, approved "
        "addendum to PREREGISTRATION.md before any re-run.\n")
    print("STOP:", msg)
    sys.exit(3)


# ---------------------------------------------------------------------------
# Phase 0 — baseline gate
# ---------------------------------------------------------------------------

def phase0(results: dict) -> None:
    t0 = time.time()
    r = run_backtest()
    results["baseline_reproduced"] = {
        "games": r["games"],
        "ats": list(r["ats"]),
        "ats_pct": r["ats_pct"],
        "our_margin_rmse": r["our_margin_rmse"],
        "seconds": round(time.time() - t0, 1),
    }
    print(f"[phase0] reproduced: games={r['games']} ats_pct={r['ats_pct']:.4f} "
          f"rmse={r['our_margin_rmse']:.4f} ({time.time() - t0:.0f}s)")
    if (r["games"] != 1107 or tuple(r["ats"]) != PUBLISHED_ATS
            or abs(r["ats_pct"] * 100 - PUBLISHED_ATS_PCT) > 0.15
            or abs(r["our_margin_rmse"] - PUBLISHED_RMSE) > 0.02):
        fail(results,
             f"reproduced 2021-24 baseline does not match the frozen pins "
             f"(games {r['games']} vs 1,107; ATS {tuple(r['ats'])} vs "
             f"{PUBLISHED_ATS}; ATS% {r['ats_pct'] * 100:.2f} vs "
             f"{PUBLISHED_ATS_PCT}; margin RMSE {r['our_margin_rmse']:.3f} "
             f"vs {PUBLISHED_RMSE})")


# ---------------------------------------------------------------------------
# Phase 1 — game frame, momentum features, walk-forward predictions
# ---------------------------------------------------------------------------

def build_game_frame() -> pd.DataFrame:
    """Games to predict. 2021-2024 from spreadspoke (as the harness);
    2025 from nflverse schedules (spreadspoke ends at 2024)."""
    inv = {v: k for k, v in ABBR_TO_FULL.items()}
    g = load_games()
    g = g[g["schedule_season"].isin([2021, 2022, 2023, 2024])].copy()
    rows = []
    for _, r in g.iterrows():
        ha, aa = inv.get(r["team_home"]), inv.get(r["team_away"])
        if ha is None or aa is None:
            continue
        rows.append({
            "date": str(r["schedule_date"].date()),
            "season": int(r["schedule_season"]),
            "week": week_int(r["schedule_week"]),
            "home": ha, "away": aa,
            "neutral": bool(r["stadium_neutral"]),
            "line_margin": closing_home_spread(r),
            "actual_margin": float(r["score_home"]) - float(r["score_away"]),
            "game_id": None,
        })
    s = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "gameday", "home_team", "away_team",
                 "home_score", "away_score", "location", "spread_line",
                 "game_id"])
    s = s[s["season"] == 2025]
    for _, r in s.iterrows():
        rows.append({
            "date": str(r["gameday"]),
            "season": 2025,
            "week": int(r["week"]),
            "home": r["home_team"], "away": r["away_team"],
            "neutral": str(r["location"]) == "Neutral",
            "line_margin": float(r["spread_line"]),
            "actual_margin": float(r["home_score"]) - float(r["away_score"]),
            "game_id": str(r["game_id"]),
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(["date", "game_id"], kind="stable").reset_index(drop=True)
    return df


class MomentumFeatures:
    """Frozen per-team momentum from the pipeline's own team-games frame.

    Each team-game's performance is p = off_epa_play - def_epa_play.
    At a prediction cutoff, only team-games rows strictly before the
    cutoff and in the predicted game's season are used. Baseline B is
    the unweighted mean of p over all those prior in-season games. The
    momentum is the OLS slope of the last four p values on indices
    1..4 (equivalently, of p-B, because B is window-constant).
    """

    def __init__(self, team_games: pd.DataFrame):
        self.logs: dict[str, dict] = {}
        grouped: dict[str, list[dict]] = {}
        for pos, r in team_games.iterrows():
            p = float(r["off_epa_play"] - r["def_epa_play"])
            grouped.setdefault(str(r["team"]), []).append({
                "pos": int(pos),
                "season": int(r["season"]),
                "p": p,
            })
        for team, entries in grouped.items():
            entries.sort(key=lambda e: e["pos"])
            self.logs[team] = {
                "positions": [e["pos"] for e in entries],
                "entries": entries,
            }

    def feature(self, team: str, season: int, cutoff: int) -> dict:
        log = self.logs.get(team)
        if log is None:
            return {"defined": False, "prior_games": 0,
                    "baseline": None, "momentum": None,
                    "last4_p": None}
        k = bisect.bisect_left(log["positions"], cutoff)
        entries = [e for e in log["entries"][:k] if e["season"] == season]
        if len(entries) < 4:
            return {"defined": False, "prior_games": int(len(entries)),
                    "baseline": None, "momentum": None,
                    "last4_p": None}
        p_all = np.array([e["p"] for e in entries], dtype=float)
        baseline = float(p_all.mean())
        last4 = p_all[-4:]
        x = np.array([1.0, 2.0, 3.0, 4.0])
        slope = float(np.cov(last4, x, ddof=0)[0, 1] / np.var(x))
        return {"defined": True, "prior_games": int(len(entries)),
                "baseline": baseline, "momentum": slope,
                "last4_p": [float(v) for v in last4]}


def walk_forward() -> pd.DataFrame:
    epa_ratings.PBP_YEARS = YEARS  # extend the pipeline loaders to 2025
    team_games = load_team_games()
    qb_plays = load_qb_plays()
    momentum = MomentumFeatures(team_games)

    sched_qb = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "home_team", "away_team",
                 "home_qb_id", "away_qb_id"])
    qb_lookup = {(int(r.season), int(r.week), r.home_team, r.away_team):
                 (r.home_qb_id, r.away_qb_id) for r in sched_qb.itertuples()}

    games = build_game_frame()
    tg_lookup: dict[tuple, list[int]] = {}
    for i, r in team_games[["season", "week", "home_team", "away_team"]].iterrows():
        tg_lookup.setdefault((int(r["season"]), int(r["week"]),
                              r["home_team"], r["away_team"]), []).append(i)

    prior: dict = {}
    last_season = None
    season_final: dict = {}
    rows: list[dict] = []

    for _, row in games.iterrows():
        season = int(row["season"])
        if last_season is not None and season != last_season:
            prior = {t: (CARRYOVER * v[0], CARRYOVER * v[1])
                     for t, v in season_final.items()}
        last_season = season

        home, away = row["home"], row["away"]
        key = (season, int(row["week"]), home, away)
        idxs = tg_lookup.get(key, [])
        if not idxs:
            continue
        cutoff = idxs[0]
        off, deff, pace = adjusted_ratings(team_games, cutoff, season, prior)
        if home not in off or away not in off:
            continue

        hq, aq = qb_lookup.get(key, (None, None))
        qadj = qb_adjustments(qb_plays, team_games, cutoff, season,
                              [(home, away, hq, aq)])
        exp_home_off = off[home] + deff[away] + qadj.get(home, 0.0)
        exp_away_off = off[away] + deff[home] + qadj.get(away, 0.0)
        edge_pts = 0.0 if row["neutral"] else HOME_EDGE_PTS
        exp_plays = (pace.get(home, PLAYS_PER_GAME)
                     + pace.get(away, PLAYS_PER_GAME)) / 2
        our_margin = (exp_home_off - exp_away_off) * exp_plays + edge_pts

        hf = momentum.feature(home, season, cutoff)
        af = momentum.feature(away, season, cutoff)
        eligible = bool(hf["defined"] and af["defined"])
        momentum_diff = (float(hf["momentum"] - af["momentum"])
                         if eligible else np.nan)

        rows.append({
            "date": row["date"], "season": season, "week": int(row["week"]),
            "home": home, "away": away,
            "our_margin": our_margin,
            "line_margin": row["line_margin"],
            "actual_margin": row["actual_margin"],
            "margin_resid": row["actual_margin"] - our_margin,
            "spread_edge": our_margin - row["line_margin"],
            "home_prior_games": hf["prior_games"],
            "away_prior_games": af["prior_games"],
            "home_baseline": hf["baseline"],
            "away_baseline": af["baseline"],
            "home_momentum": hf["momentum"],
            "away_momentum": af["momentum"],
            "momentum_diff": momentum_diff,
            "in_sample": eligible,
            "eligible": eligible,
        })

        off2, def2, _pace = adjusted_ratings(team_games, idxs[-1] + 1,
                                             season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    return pd.DataFrame(rows)


def verify_replication(df: pd.DataFrame, results: dict) -> None:
    sub = df[df["season"] <= 2024]
    n = len(sub)
    rmse = float(np.sqrt(((sub["our_margin"] - sub["actual_margin"]) ** 2).mean()))
    w = l = p = 0
    for _, r in sub.iterrows():
        e = r["spread_edge"]
        if abs(e) >= 1.5:
            res = r["actual_margin"] - r["line_margin"]
            if abs(res) < 0.01:
                p += 1
            elif (res > 0) == (e > 0):
                w += 1
            else:
                l += 1
    ref = pd.read_csv(REPO / "research" / "turnover_damping"
                      / "per_game_robustness_w0.50_qb.csv")
    m = sub.merge(ref, on=["season", "week", "home", "away"],
                  suffixes=("", "_ref"))
    max_diff = float((m["our_margin"] - m["our_margin_ref"]).abs().max()) \
        if len(m) else float("nan")
    results["replication_check"] = {
        "games_2021_24": n, "ats_wlp": [w, l, p], "margin_rmse": rmse,
        "merged_vs_reference": int(len(m)), "max_abs_margin_diff": max_diff,
    }
    print(f"[phase1] 2021-24 replication: n={n} ats={w}-{l}-{p} "
          f"rmse={rmse:.6f} max_diff={max_diff:.2e}")
    if not (n == 1107 and (w, l, p) == PUBLISHED_ATS
            and abs(rmse - REFERENCE_RMSE) < 1e-6
            and len(m) == 1107 and max_diff < 1e-9):
        fail(results, "extended walk-forward does not replicate the "
                      "verified 2021-24 damped-config per-game rows; "
                      "analysis halted before fitting")


# ---------------------------------------------------------------------------
# Phase 2 — frozen regressions, bootstrap, and descriptive outputs
# ---------------------------------------------------------------------------

def ols_multi(y: np.ndarray, xs: dict[str, np.ndarray]) -> dict:
    names = list(xs)
    X = np.column_stack([np.ones(len(y))] + [xs[n] for n in names])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(y) - X.shape[1]
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    out = {"intercept": float(beta[0]), "n": int(len(y)), "coefficients": {}}
    for j, name in enumerate(names, start=1):
        se = float(np.sqrt(cov[j, j]))
        out["coefficients"][name] = {
            "estimate": float(beta[j]), "se": se,
            "z": float(beta[j] / se) if se > 0 else float("nan"),
        }
    return out


def ols(y: np.ndarray, x: np.ndarray, x_name: str = "momentum_diff") -> dict:
    full = ols_multi(y, {x_name: x})
    c = full["coefficients"][x_name]
    return {"intercept": full["intercept"], "slope": c["estimate"],
            "se_slope": c["se"], "z": c["z"], "n": full["n"]}


def rmse(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.sqrt(np.mean((pred - actual) ** 2)))


def bootstrap_rmse_ci(val: pd.DataFrame, gamma: float) -> dict:
    """Paired bootstrap of candidate-minus-baseline validation RMSE."""
    actual = val["actual_margin"].to_numpy()
    base_pred = val["our_margin"].to_numpy()
    cand_pred = base_pred + gamma * val["momentum_diff"].to_numpy()
    base_se = (base_pred - actual) ** 2
    cand_se = (cand_pred - actual) ** 2
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    n = len(val)
    diffs = np.empty(BOOTSTRAP_RESAMPLES)
    for i in range(BOOTSTRAP_RESAMPLES):
        idx = rng.integers(0, n, size=n)
        diffs[i] = np.sqrt(cand_se[idx].mean()) - np.sqrt(base_se[idx].mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    return {
        "resamples": BOOTSTRAP_RESAMPLES,
        "seed": BOOTSTRAP_SEED,
        "rmse_difference_candidate_minus_baseline": float(
            rmse(cand_pred, actual) - rmse(base_pred, actual)),
        "ci95_percentile": [float(lo), float(hi)],
    }


def ats_record(df: pd.DataFrame, edge_col: str) -> dict:
    picks = df[df[edge_col].abs() >= 1.5]
    w = l = p = 0
    for _, r in picks.iterrows():
        res = r["actual_margin"] - r["line_margin"]
        if abs(res) < 0.01:
            p += 1
        elif (res > 0) == (r[edge_col] > 0):
            w += 1
        else:
            l += 1
    return {"wlp": [w, l, p], "picks": int(w + l + p),
            "win_pct": float(w / (w + l)) if (w + l) else None}


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def main() -> None:
    results: dict = {}
    phase0(results)

    t0 = time.time()
    df = walk_forward()
    print(f"[phase1] walk-forward 2021-2025: {len(df)} predicted games "
          f"in {time.time() - t0:.0f}s")
    verify_replication(df, results)

    sample = df[df["in_sample"]].copy()
    disc = sample[sample["season"].isin(DISCOVERY)]
    val = sample[sample["season"].isin(VALIDATION)]

    coverage = {}
    for name, seasons in (("discovery_2021_2023", DISCOVERY),
                          ("validation_2024_2025", VALIDATION),
                          ("all_2021_2025", YEARS)):
        allg = df[df["season"].isin(seasons)]
        samp = allg[allg["in_sample"]]
        coverage[name] = {
            "predicted_games": int(len(allg)),
            "eligible_games": int(len(samp)),
            "eligible_pct": float(len(samp) / len(allg)) if len(allg) else None,
        }
    for season in YEARS:
        allg = df[df["season"] == season]
        samp = allg[allg["in_sample"]]
        coverage[f"season_{season}"] = {
            "predicted_games": int(len(allg)),
            "eligible_games": int(len(samp)),
            "eligible_pct": float(len(samp) / len(allg)) if len(allg) else None,
        }
    results["coverage"] = coverage
    print("[phase2] coverage:", json.dumps(coverage, default=str))

    fit_d = ols(disc["margin_resid"].to_numpy(),
                disc["momentum_diff"].to_numpy())
    gamma = fit_d["slope"]
    fit_v = ols(val["margin_resid"].to_numpy(),
                val["momentum_diff"].to_numpy())

    df["candidate_margin"] = df["our_margin"] + gamma * df["momentum_diff"]
    df["candidate_spread_edge"] = df["candidate_margin"] - df["line_margin"]
    sample = df[df["in_sample"]].copy()
    disc = sample[sample["season"].isin(DISCOVERY)]
    val = sample[sample["season"].isin(VALIDATION)]

    base_rmse = rmse(val["our_margin"].to_numpy(),
                     val["actual_margin"].to_numpy())
    cand_rmse = rmse(val["candidate_margin"].to_numpy(),
                     val["actual_margin"].to_numpy())
    boot = bootstrap_rmse_ci(val, gamma)

    per_season = {}
    for s in VALIDATION:
        v = val[val["season"] == s]
        b = rmse(v["our_margin"].to_numpy(), v["actual_margin"].to_numpy())
        c = rmse(v["candidate_margin"].to_numpy(),
                 v["actual_margin"].to_numpy())
        per_season[str(s)] = {
            "n": int(len(v)), "rmse_unadjusted": b,
            "rmse_adjusted": c, "rmse_difference": float(c - b),
            "does_not_worsen": bool(c <= b),
        }

    bar1 = bool(fit_v["slope"] > 0 and fit_v["z"] >= 1.96)
    bar2 = bool(cand_rmse < base_rmse)
    bar3 = bool(all(v["does_not_worsen"] for v in per_season.values()))
    verdict = "ADOPT" if (bar1 and bar2 and bar3) else "KILL"

    market_resid = val["actual_margin"].to_numpy() - val["line_margin"].to_numpy()
    mech_single = ols(market_resid, val["momentum_diff"].to_numpy())
    mech_joint = ols_multi(
        val["margin_resid"].to_numpy(),
        {"momentum_diff": val["momentum_diff"].to_numpy(),
         "line_margin": val["line_margin"].to_numpy()})
    mechanism = {
        "market_residual_regression": mech_single,
        "joint_regression": mech_joint,
        "interpretation": (
            "A near-zero market-residual slope and/or a momentum slope "
            "that collapses in the joint regression indicate that the "
            "closing line already contains the trajectory signal."),
    }

    results["primary"] = {
        "gamma_discovery_slope": gamma,
        "discovery_fit": fit_d,
        "validation_fit": fit_v,
        "validation_rmse_unadjusted": base_rmse,
        "validation_rmse_adjusted": cand_rmse,
        "validation_rmse_difference_candidate_minus_baseline": float(
            cand_rmse - base_rmse),
        "bootstrap_rmse_difference": boot,
        "validation_rmse_per_season": per_season,
        "bar1_validation_slope_positive_z>=1.96": bar1,
        "bar2_pooled_validation_rmse_reduced": bar2,
        "bar3_neither_validation_season_worsens": bar3,
    }
    results["mechanism_diagnostic"] = mechanism
    results["secondary"] = {
        "ats_validation_live": ats_record(val, "spread_edge"),
        "ats_validation_adjusted": ats_record(val, "candidate_spread_edge"),
        "ats_discovery_live": ats_record(disc, "spread_edge"),
        "ats_discovery_adjusted": ats_record(disc, "candidate_spread_edge"),
        "ats_note": ("Each model is scored on its own |edge| >= 1.5 "
                     "picks within the same eligible game sample. "
                     "2021-2024 lines are spreadspoke closing spreads; "
                     "2025 lines are schedules_games.parquet spread_line."),
    }
    results["verdict"] = verdict
    results["status"] = "COMPLETED"
    print(f"[phase2] gamma={gamma:+.6f}; validation slope={fit_v['slope']:+.6f} "
          f"z={fit_v['z']:+.2f}; RMSE {base_rmse:.3f} -> {cand_rmse:.3f}; "
          f"verdict {verdict}")

    cols = ["date", "season", "week", "home", "away", "our_margin",
            "candidate_margin", "line_margin", "actual_margin",
            "margin_resid", "spread_edge", "candidate_spread_edge",
            "home_prior_games", "away_prior_games", "home_baseline",
            "away_baseline", "home_momentum", "away_momentum",
            "momentum_diff", "in_sample", "eligible"]
    df[cols].to_csv(OUT / "per_game.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))

    c = coverage
    ps = per_season
    ms = mechanism["market_residual_regression"]
    mj = mechanism["joint_regression"]["coefficients"]
    ats_l = results["secondary"]["ats_validation_live"]
    ats_a = results["secondary"]["ats_validation_adjusted"]
    bar1_txt = "PASS" if bar1 else "FAIL"
    bar2_txt = "PASS" if bar2 else "FAIL"
    bar3_txt = "PASS" if bar3 else "FAIL"
    if verdict == "ADOPT":
        implication = (
            "This earns a recommendation only. Nothing live changes on "
            "this result: the next step is a separate implementation "
            "test against the live generator, and any live-model change "
            "still requires Bryant's separate explicit approval. The "
            "mechanism diagnostic above must accompany that "
            "recommendation.")
    else:
        implication = (
            "The live model is unchanged. Under the standing honesty "
            "rule, this KILL is the tested-and-rejected result for this "
            "exact momentum definition; a different window, baseline, "
            "or performance series would require a new preregistration "
            "before any results are computed.")

    md = f"""# Team momentum — RESULTS

**Run:** 2026-10-23, on Bryant's explicit approval to run the full test
package. **Preregistration:** `PREREGISTRATION.md` in this directory
(frozen 2026-10-19, before any momentum-trajectory results were
computed). Runner: `run_team_momentum.py`; numbers: `results.json`;
per-game rows: `per_game.csv`. Measurement only — no live model code,
constant, config, generator, or site data was changed.

## Verdict: {verdict}

Per the frozen three-bar rule, ADOPT requires all three bars:

- **Bar 1 — validation slope > 0 with z ≥ 1.96: {bar1_txt}.**
  Discovery gamma (2021–2023, n = {fit_d['n']}): **γ = {gamma:+.4f}**
  (SE {fit_d['se_slope']:.4f}, z = {fit_d['z']:+.2f}). On validation
  (2024–2025, n = {fit_v['n']}), the slope is **{fit_v['slope']:+.4f}**
  (SE {fit_v['se_slope']:.4f}, z = **{fit_v['z']:+.2f}**).
- **Bar 2 — frozen adjustment reduces pooled validation RMSE: {bar2_txt}.**
  Applying `our_margin + γ · momentum_diff`: validation RMSE
  **{base_rmse:.3f} → {cand_rmse:.3f}** (Δ **{cand_rmse - base_rmse:+.3f}**).
  Paired bootstrap (10,000 game resamples, seed 20261019): 95% CI for
  candidate-minus-baseline RMSE = **[{boot['ci95_percentile'][0]:+.3f}, {boot['ci95_percentile'][1]:+.3f}]**.
- **Bar 3 — neither validation season worsens: {bar3_txt}.**
  2024: {ps['2024']['rmse_unadjusted']:.3f} → {ps['2024']['rmse_adjusted']:.3f}
  (Δ {ps['2024']['rmse_difference']:+.3f}, n = {ps['2024']['n']});
  2025: {ps['2025']['rmse_unadjusted']:.3f} → {ps['2025']['rmse_adjusted']:.3f}
  (Δ {ps['2025']['rmse_difference']:+.3f}, n = {ps['2025']['n']}).

{implication}

## Baseline gate (passed before fitting)

1. **Reproduction.** `run_backtest()` exactly as-is returned ATS
   **47.29%** (393-438-29) and margin RMSE **14.131** on **1,107**
   games (2021–2024), matching the frozen pins within tolerances.
2. **Per-game replication.** The extended walk-forward's 2021–2024
   rows replicate
   `research/turnover_damping/per_game_robustness_w0.50_qb.csv`:
   {results['replication_check']['merged_vs_reference']} of 1,107
   games merge, ATS tuple {tuple(results['replication_check']['ats_wlp'])},
   RMSE {results['replication_check']['margin_rmse']:.6f}, and max
   |Δ our_margin| = {results['replication_check']['max_abs_margin_diff']:.1e}.

## Mechanism diagnostic (mandatory; no verdict power)

On the validation eligible sample (n = {fit_v['n']}):

- **Momentum slope against the market residual:** regressing
  `actual_margin − line_margin` on `momentum_diff` gives slope
  **{ms['slope']:+.4f}** (SE {ms['se_slope']:.4f}, z = {ms['z']:+.2f}).
- **Joint regression with the line:** regressing `margin_resid` on
  both `momentum_diff` and `line_margin` gives a momentum slope of
  **{mj['momentum_diff']['estimate']:+.4f}** (SE {mj['momentum_diff']['se']:.4f},
  z = {mj['momentum_diff']['z']:+.2f}); the line coefficient is
  {mj['line_margin']['estimate']:+.4f} (SE {mj['line_margin']['se']:.4f},
  z = {mj['line_margin']['z']:+.2f}).

Read plainly: the market-residual slope is the first check on whether
the closing line already contains the trajectory; the joint regression
is the check on whether any model-residual momentum slope survives
once the line is in the same regression (in M1, it did not).

## Coverage

| Split | Predicted games | Eligible games | Eligible share |
|---|---:|---:|---:|
| Discovery 2021–2023 | {c['discovery_2021_2023']['predicted_games']} | {c['discovery_2021_2023']['eligible_games']} | {pct(c['discovery_2021_2023']['eligible_pct'])} |
| Validation 2024–2025 | {c['validation_2024_2025']['predicted_games']} | {c['validation_2024_2025']['eligible_games']} | {pct(c['validation_2024_2025']['eligible_pct'])} |
| All 2021–2025 | {c['all_2021_2025']['predicted_games']} | {c['all_2021_2025']['eligible_games']} | {pct(c['all_2021_2025']['eligible_pct'])} |

Eligible = both teams had played at least four prior games in the
current season. Per-season eligible shares: 2021 {pct(c['season_2021']['eligible_pct'])},
2022 {pct(c['season_2022']['eligible_pct'])}, 2023 {pct(c['season_2023']['eligible_pct'])},
2024 {pct(c['season_2024']['eligible_pct'])}, 2025 {pct(c['season_2025']['eligible_pct'])}.

## Per-season validation RMSE table

| Season | n | Live model | γ-adjusted | Δ |
|---|---:|---:|---:|---:|
| 2024 | {ps['2024']['n']} | {ps['2024']['rmse_unadjusted']:.3f} | {ps['2024']['rmse_adjusted']:.3f} | {ps['2024']['rmse_difference']:+.3f} |
| 2025 | {ps['2025']['n']} | {ps['2025']['rmse_unadjusted']:.3f} | {ps['2025']['rmse_adjusted']:.3f} | {ps['2025']['rmse_difference']:+.3f} |
| Pooled | {fit_v['n']} | {base_rmse:.3f} | {cand_rmse:.3f} | {cand_rmse - base_rmse:+.3f} |

## Secondary descriptive output (no verdict power)

- **Validation ATS on model picks (|edge| ≥ 1.5), eligible games:**
  live model {ats_l['wlp']} ({pct(ats_l['win_pct'])} on {ats_l['picks']}
  picks); γ-adjusted model {ats_a['wlp']} ({pct(ats_a['win_pct'])} on
  {ats_a['picks']} picks). Each model is scored on its own pick set,
  as in the recency-weighting diagnostic. 2021–2024 lines are the
  spreadspoke closing spreads; 2025 lines are
  `schedules_games.parquet` (`spread_line`), per the ratified
  precedent. The primary test uses no lines.

## Method notes

1. The feature was computed exactly once under the frozen definition:
   net EPA/play from `load_team_games()` (turnover EPA damped at the
   live w = 0.50), one four-game window, one season-to-date baseline,
   one additive `γ · momentum_diff` form. No alternative window,
   weighting, series, split, threshold, or interaction was tried.
2. Cutoff safety follows the pipeline convention: the cutoff is the
   first `team_games` row index for the predicted game, and only team
   rows strictly before that index enter either team's baseline or
   window. Same-week games cannot leak through a (season, week)
   cutoff because no such cutoff is used.
3. The baseline is constant across a team's four-game window, so the
   registered slope of `(p_i − B)` is numerically the slope of `p_i`;
   B is reported per game in `per_game.csv` as the interpretive anchor
   and was not replaced with any pre-window variant.
4. 2026 is excluded entirely. The primary test is margin-only and
   line-free; lines enter only the mandatory mechanism diagnostic and
   the descriptive ATS context.
5. OLS uses an intercept and applies only the fitted slope as the
   adjustment, per the registration and the house convention.
"""
    (OUT / "RESULTS.md").write_text(md)
    print(f"[done] RESULTS.md written; verdict {verdict}")


if __name__ == "__main__":
    main()
