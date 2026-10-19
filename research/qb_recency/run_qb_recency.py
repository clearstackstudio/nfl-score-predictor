"""QB recency diagnostic — run of the 2026-10-15 preregistration.

Executes research/qb_recency/PREREGISTRATION.md exactly as written:

  Phase 0  Reproduce the harness baseline (src/epa_ratings.run_backtest,
           PBP_YEARS 2021-2024 as-is). STOP if ATS != 47.29% or margin
           RMSE != 14.131 — the gate as re-pinned by the 2026-10-19
           ADDENDUM to PREREGISTRATION.md (live damped config, w = 0.50;
           published as the robustness arm of
           research/turnover_damping/RESULTS.md). The original pins
           (47.5% / 14.44) were pre-damping and halted the first attempt.
  Phase 1  Walk-forward predictions 2021-2025 under the live EPA config
           (same imported functions and loop order as
           research/epa_live_backtest Part B), with QB-recency features
           computed at each game's prediction cutoff from games strictly
           before it. The 2021-2024 rows are verified against the damping
           study's robustness per-game file
           (research/turnover_damping/per_game_robustness_w0.50_qb.csv,
           per the addendum) before anything else is trusted.
  Phase 2  The frozen test: OLS of margin_resid on qb_form_diff, slope fit
           on discovery 2021-2023, verdict bars evaluated on validation
           2024-2025. Plus the pre-registered descriptive outputs.

Data notes (deviations forced by the repo, flagged in RESULTS.md):
  * spreadspoke_scores.csv (the line store) ends at 2024. 2025 game
    frame / scores / closing spread come from data/schedules_games.parquet
    (nflverse), the same file the harness already uses for QB ids/venue.
    Its spread_line was verified against the spreadspoke closing spread
    on 2021-2024 (same sign convention, corr 0.996). The PRIMARY test
    uses no line at all; only the secondary ATS split touches it, and
    only for 2025 rows.

Run: .venv-cfb/bin/python research/qb_recency/run_qb_recency.py
"""
from __future__ import annotations

import bisect
import json
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "qb_recency"
sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import epa_ratings  # noqa: E402
from backtest import closing_home_spread, load_games  # noqa: E402
from epa_ratings import (  # noqa: E402
    ABBR_TO_FULL, CARRYOVER, DATA, HOME_EDGE_PTS, PLAYS_PER_GAME,
    QB_SAME_THRESHOLD, WINDOW_GAMES, _decayed_mean,
    adjusted_ratings, load_qb_plays, load_team_games, qb_adjustments,
    run_backtest, week_int,
)

YEARS = [2021, 2022, 2023, 2024, 2025]
DISCOVERY = [2021, 2022, 2023]
VALIDATION = [2024, 2025]
PUBLISHED_ATS_PCT = 47.29  # re-pinned by the 2026-10-19 addendum (damped config)
PUBLISHED_RMSE = 14.131    # re-pinned by the 2026-10-19 addendum (damped config)


def fail(results: dict, msg: str) -> None:
    results["status"] = "STOPPED"
    results["stop_reason"] = msg
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    (OUT / "RESULTS.md").write_text(
        "# QB recency diagnostic — RESULTS\n\n"
        f"**STOPPED before the test: {msg}**\n\n"
        "Per the preregistration, the diagnostic does not proceed on a "
        "mismatched baseline / unverified replication. No verdict is "
        "recorded and no model change is implied.\n")
    print("STOP:", msg)
    sys.exit(3)


# --------------------------------------------------------------------------
# Phase 0 — baseline reproduction
# --------------------------------------------------------------------------

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
    if (abs(r["ats_pct"] * 100 - PUBLISHED_ATS_PCT) > 0.15
            or abs(r["our_margin_rmse"] - PUBLISHED_RMSE) > 0.02):
        fail(results,
             f"reproduced 2021-24 baseline does not match published "
             f"(ATS {r['ats_pct'] * 100:.2f}% vs {PUBLISHED_ATS_PCT}%, "
             f"margin RMSE {r['our_margin_rmse']:.3f} vs {PUBLISHED_RMSE})")


# --------------------------------------------------------------------------
# Phase 1 — walk-forward predictions + QB features, 2021-2025
# --------------------------------------------------------------------------

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
            continue  # mirrors run_backtest's dropna on unmapped names
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


class QBFeatures:
    """Per-QB game logs and per-team window shares from load_qb_plays
    (the pipeline's own dropback construction, turnover-damped EPA),
    plus last-game INT counts taken with the identical play filter."""

    def __init__(self, team_games: pd.DataFrame, qb_plays: pd.DataFrame):
        # order key: first team_games row index of the game (the pipeline's
        # leakage-safe cutoff convention)
        self.game_order: dict[str, int] = {}
        for i, gid in enumerate(team_games["game_id"]):
            self.game_order.setdefault(gid, i)
        self.team_games = team_games

        # per (team, game) passer dropback counts -> window shares
        self.counts: dict[tuple, Counter] = {}
        for (team, gid), grp in qb_plays.groupby(["posteam", "game_id"]):
            self.counts[(team, gid)] = Counter(grp["passer_id"])

        # INTs per (passer, game) with load_qb_plays' exact filter
        frames = []
        for year in YEARS:
            pbp = pd.read_parquet(
                DATA / f"play_by_play_{year}.parquet",
                columns=["game_id", "passer_id", "pass_attempt", "sack",
                         "epa", "interception"])
            q = pbp[pbp["passer_id"].notna() & pbp["epa"].notna()
                    & ((pbp["pass_attempt"] == 1) | (pbp["sack"] == 1))]
            frames.append(q[["game_id", "passer_id", "interception"]])
        ints = (pd.concat(frames).groupby(["passer_id", "game_id"])
                ["interception"].sum().to_dict())

        # per-QB chronological game log
        agg = (qb_plays.groupby(["passer_id", "game_id"])
               .agg(n=("epa", "size"), epa_mean=("epa", "mean"))
               .reset_index())
        self.logs: dict[str, dict] = {}
        for pid, grp in agg.groupby("passer_id"):
            entries = []
            for _, r in grp.iterrows():
                gid = r["game_id"]
                if gid not in self.game_order:
                    continue
                entries.append({
                    "order": self.game_order[gid],
                    "n": int(r["n"]),
                    "epa_mean": float(r["epa_mean"]),
                    "ints": int(ints.get((pid, gid), 0)),
                })
            entries.sort(key=lambda e: e["order"])
            self.logs[str(pid)] = {
                "orders": [e["order"] for e in entries],
                "entries": entries,
            }

    def window_share(self, team: str, qb_id, cutoff: int, season: int) -> float | None:
        """Starter's share of the team's trailing-window dropbacks,
        replicating qb_adjustments' window (team_games before cutoff,
        seasons >= season-1, last WINDOW_GAMES games)."""
        if qb_id is None or (isinstance(qb_id, float) and np.isnan(qb_id)):
            return None
        tg = self.team_games.iloc[:cutoff]
        tg = tg[(tg["team"] == team) & (tg["season"] >= season - 1)]
        if tg.empty:
            return None
        window = list(tg.tail(WINDOW_GAMES)["game_id"])
        total = mine = 0
        for gid in window:
            c = self.counts.get((team, gid))
            if c:
                total += sum(c.values())
                mine += c.get(str(qb_id), 0)
        if total == 0:
            return None
        return mine / total

    def form(self, qb_id, cutoff: int) -> dict | None:
        """last_dev etc. for a QB, using only games with order < cutoff."""
        if qb_id is None or (isinstance(qb_id, float) and np.isnan(qb_id)):
            return None
        log = self.logs.get(str(qb_id))
        if log is None:
            return None
        k = bisect.bisect_left(log["orders"], cutoff)
        entries = log["entries"][:k]
        if not entries:
            return None
        career = sum(e["n"] for e in entries)
        last = entries[-1]
        trailing = entries[:-1]
        last_dev = None
        if trailing:
            vals = np.array([e["epa_mean"] for e in trailing])
            last_dev = last["epa_mean"] - _decayed_mean(vals, len(vals))
        return {
            "career_db": career,
            "last_n": last["n"],
            "last_epa": last["epa_mean"],
            "last_dev": last_dev,
            "last_int": last["ints"],
            "eligible": bool(last["n"] >= 15 and career >= 100
                             and last_dev is not None),
        }


def walk_forward() -> pd.DataFrame:
    epa_ratings.PBP_YEARS = YEARS  # extend the pipeline loaders to 2025
    team_games = load_team_games()
    qb_plays = load_qb_plays()
    feats = QBFeatures(team_games, qb_plays)

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

        # features at this game's cutoff (prior games only)
        h_share = feats.window_share(home, hq, cutoff, season)
        a_share = feats.window_share(away, aq, cutoff, season)
        h_form = feats.form(hq, cutoff)
        a_form = feats.form(aq, cutoff)
        both_cont = (h_share is not None and a_share is not None
                     and h_share >= QB_SAME_THRESHOLD
                     and a_share >= QB_SAME_THRESHOLD)
        in_sample = bool(both_cont and h_form and a_form
                         and h_form["eligible"] and a_form["eligible"])
        rows.append({
            "date": row["date"], "season": season, "week": int(row["week"]),
            "home": home, "away": away,
            "our_margin": our_margin,
            "line_margin": row["line_margin"],
            "actual_margin": row["actual_margin"],
            "margin_resid": row["actual_margin"] - our_margin,
            "spread_edge": our_margin - row["line_margin"],
            "home_share": h_share, "away_share": a_share,
            "both_continuing": bool(both_cont),
            "home_last_dev": h_form["last_dev"] if h_form else None,
            "away_last_dev": a_form["last_dev"] if a_form else None,
            "home_last_int": h_form["last_int"] if h_form else None,
            "away_last_int": a_form["last_int"] if a_form else None,
            "in_sample": in_sample,
            "qb_form_diff": (h_form["last_dev"] - a_form["last_dev"])
            if in_sample else None,
            "last_int_diff": (a_form["last_int"] - h_form["last_int"])
            if in_sample else None,
        })

        # (run_backtest also updates its totals calibration here; totals
        # are not a test input and cannot affect margins, so it is omitted.)
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
    m = sub.merge(ref, on=["season", "week", "home", "away"], suffixes=("", "_ref"))
    max_diff = float((m["our_margin"] - m["our_margin_ref"]).abs().max()) \
        if len(m) else float("nan")
    results["replication_check"] = {
        "games_2021_24": n, "ats_wlp": [w, l, p], "margin_rmse": rmse,
        "merged_vs_harness_per_game": int(len(m)), "max_abs_margin_diff": max_diff,
    }
    print(f"[phase1] 2021-24 replication: n={n} ats={w}-{l}-{p} "
          f"rmse={rmse:.4f} max_diff_vs_harness={max_diff:.2e}")
    if not (n == 1107 and (w, l, p) == (393, 438, 29)
            and abs(rmse - 14.130860208614187) < 1e-6
            and len(m) == 1107 and max_diff < 1e-9):
        fail(results, "extended walk-forward does not reproduce the "
                      "verified 2021-24 damped-config rows; analysis halted")


# --------------------------------------------------------------------------
# Phase 2 — the frozen test
# --------------------------------------------------------------------------

def ols(y: np.ndarray, x: np.ndarray) -> dict:
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    dof = len(x) - 2
    s2 = float(resid @ resid) / dof
    cov = s2 * np.linalg.inv(X.T @ X)
    se = float(np.sqrt(cov[1, 1]))
    return {"intercept": float(beta[0]), "slope": float(beta[1]),
            "se_slope": se, "z": float(beta[1] / se) if se > 0 else float("nan"),
            "n": int(len(x))}


def rmse(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.sqrt(np.mean((pred - actual) ** 2)))


def ats_split(df: pd.DataFrame) -> dict:
    """Descriptive: ATS win% on |spread_edge| >= 1.5 picks, split by
    whether qb_form_diff agrees with the model's pick side."""
    out = {}
    picks = df[df["spread_edge"].abs() >= 1.5]
    agree_mask = (((picks["qb_form_diff"] > 0) == (picks["spread_edge"] > 0))
                  & (picks["qb_form_diff"] != 0))
    for name, grp in {
        "agree": picks[agree_mask],
        "disagree": picks[~agree_mask],
    }.items():
        w = l = p = 0
        for _, r in grp.iterrows():
            res = r["actual_margin"] - r["line_margin"]
            if abs(res) < 0.01:
                p += 1
            elif (res > 0) == (r["spread_edge"] > 0):
                w += 1
            else:
                l += 1
        out[name] = {"wlp": [w, l, p],
                     "win_pct": (w / (w + l)) if (w + l) else None}
    return out


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
    results["coverage"] = {}
    for name, seasons in (("discovery_2021_2023", DISCOVERY),
                          ("validation_2024_2025", VALIDATION),
                          ("all_2021_2025", YEARS)):
        allg = df[df["season"].isin(seasons)]
        pop = allg[allg["both_continuing"]]
        samp = allg[allg["in_sample"]]
        results["coverage"][name] = {
            "predicted_games": int(len(allg)),
            "both_continuing": int(len(pop)),
            "both_continuing_pct": float(len(pop) / len(allg)) if len(allg) else None,
            "test_sample": int(len(samp)),
            "test_sample_pct": float(len(samp) / len(allg)) if len(allg) else None,
        }
    print("[phase2] coverage:", json.dumps(results["coverage"], default=str))

    # primary: discovery fit, validation bars
    fit_d = ols(disc["margin_resid"].to_numpy(), disc["qb_form_diff"].to_numpy())
    fit_v = ols(val["margin_resid"].to_numpy(), val["qb_form_diff"].to_numpy())
    b = fit_d["slope"]
    base_rmse = rmse(val["our_margin"].to_numpy(), val["actual_margin"].to_numpy())
    adj_rmse = rmse(val["our_margin"].to_numpy() + b * val["qb_form_diff"].to_numpy(),
                    val["actual_margin"].to_numpy())
    per_season = {}
    for s in VALIDATION:
        v = val[val["season"] == s]
        per_season[str(s)] = {
            "n": int(len(v)),
            "rmse_unadjusted": rmse(v["our_margin"].to_numpy(),
                                    v["actual_margin"].to_numpy()),
            "rmse_adjusted": rmse(v["our_margin"].to_numpy()
                                  + b * v["qb_form_diff"].to_numpy(),
                                  v["actual_margin"].to_numpy()),
        }
    bar1 = bool(fit_v["slope"] > 0 and fit_v["z"] >= 1.96)
    bar2 = bool(adj_rmse < base_rmse)
    both_worse = all(v["rmse_adjusted"] > v["rmse_unadjusted"]
                     for v in per_season.values())
    verdict = "KEEP" if (bar1 and bar2 and not both_worse) else "KILL"
    results["primary"] = {
        "discovery_fit": fit_d, "validation_fit": fit_v,
        "validation_rmse_unadjusted": base_rmse,
        "validation_rmse_adjusted": adj_rmse,
        "validation_rmse_per_season": per_season,
        "bar1_slope_positive_z>=1.96": bar1,
        "bar2_rmse_reduced": bar2,
        "guardrail_worse_in_both_seasons": bool(both_worse),
    }

    # secondary (descriptive only)
    results["secondary"] = {
        "int_regression_discovery": ols(disc["margin_resid"].to_numpy(),
                                        disc["last_int_diff"].to_numpy()),
        "int_regression_validation": ols(val["margin_resid"].to_numpy(),
                                         val["last_int_diff"].to_numpy()),
        "ats_split_validation": ats_split(val),
        "ats_split_discovery": ats_split(disc),
        "ats_split_note": "2025 rows use the nflverse schedules spread_line "
                          "(see header); 2021-2024 rows use spreadspoke "
                          "closing spreads, as in prior diagnostics.",
    }
    results["verdict"] = verdict
    results["status"] = "COMPLETED"
    print(f"[phase2] verdict: {verdict} (bar1={bar1}, bar2={bar2}, "
          f"guardrail_both_worse={both_worse})")

    cols = ["date", "season", "week", "home", "away", "our_margin",
            "line_margin", "actual_margin", "margin_resid", "spread_edge",
            "home_share", "away_share",
            "both_continuing", "in_sample", "home_last_dev", "away_last_dev",
            "qb_form_diff", "home_last_int", "away_last_int", "last_int_diff"]
    df[cols].to_csv(OUT / "per_game.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))

    c, r = results["coverage"], results
    fd, fv = r["primary"]["discovery_fit"], r["primary"]["validation_fit"]
    si_d, si_v = (r["secondary"]["int_regression_discovery"],
                  r["secondary"]["int_regression_validation"])
    av, ad = (r["secondary"]["ats_split_validation"],
              r["secondary"]["ats_split_discovery"])
    ps = r["primary"]["validation_rmse_per_season"]
    bar1_txt = "PASS" if r["primary"]["bar1_slope_positive_z>=1.96"] else "FAIL"
    bar2_txt = "PASS" if r["primary"]["bar2_rmse_reduced"] else "FAIL"
    md = f"""# QB recency diagnostic — RESULTS

**Run:** 2026-10-19, on Bryant's explicit approval to run the diagnostic
scoped 2026-10-15, under the 2026-10-19 addendum he approved after the
first attempt stopped at the stale pre-damping baseline pin (pins only;
protocol otherwise frozen). **Preregistration:** `PREREGISTRATION.md` in
this directory (written before any recency results were computed).
Runner:
`run_qb_recency.py`; numbers: `results.json`; per-game rows:
`per_game.csv`. Measurement only — no live model code was changed.

## Verdict: {verdict}

Per the frozen decision rule (KEEP iff both validation bars hold, with
the both-seasons-worse guardrail as an automatic KILL):

- **Bar 1 — validation slope > 0 with z ≥ 1.96: {bar1_txt}.**
  Validation slope: **{fv['slope']:+.3f}** (SE {fv['se_slope']:.3f}, z = {fv['z']:+.2f}) \
on n = {fv['n']} games (2024–2025).
- **Bar 2 — discovery-fitted adjustment reduces validation margin RMSE: {bar2_txt}.**
  Discovery slope (2021–2023, n = {fd['n']}): {fd['slope']:+.3f} \
(SE {fd['se_slope']:.3f}, z = {fd['z']:+.2f}). Applying \
`our_margin + {fd['slope']:+.3f} · qb_form_diff`: validation RMSE \
{r['primary']['validation_rmse_unadjusted']:.3f} → \
{r['primary']['validation_rmse_adjusted']:.3f} \
({r['primary']['validation_rmse_adjusted'] - r['primary']['validation_rmse_unadjusted']:+.3f}).
- **Guardrail — adjustment worsens RMSE in both validation seasons: \
{r['primary']['guardrail_worse_in_both_seasons']}.**
  2024: {ps['2024']['rmse_unadjusted']:.3f} → {ps['2024']['rmse_adjusted']:.3f} \
(n = {ps['2024']['n']}); 2025: {ps['2025']['rmse_unadjusted']:.3f} → \
{ps['2025']['rmse_adjusted']:.3f} (n = {ps['2025']['n']}).

## Baseline reproduction (stop rule — passed)

The live-config baseline was reproduced before anything else was run:
`run_backtest()` exactly as-is returned ATS **47.29%** (393-438-29) and
margin RMSE **14.131** on 1,107 games (2021–2024), matching the gate as
re-pinned by the 2026-10-19 addendum to the preregistration — the live
damped configuration's figures, published as the robustness arm of
`research/turnover_damping/RESULTS.md` (the original pins, 47.5% /
14.44 from `research/epa_live_backtest/`, were pre-damping and halted
the first run attempt). The extended walk-forward's 2021–2024 rows were
then verified bit-for-bit against the damping study's per-game
robustness file (max |Δmargin| = \
{r['replication_check']['max_abs_margin_diff']:.1e}), so the 2025
extension runs on a verified frame.

## Coverage

| Split | Predicted | Both continuing | Test sample |
|---|---|---|---|
| Discovery 2021–2023 | {c['discovery_2021_2023']['predicted_games']} | \
{c['discovery_2021_2023']['both_continuing']} ({c['discovery_2021_2023']['both_continuing_pct']:.1%}) | \
{c['discovery_2021_2023']['test_sample']} ({c['discovery_2021_2023']['test_sample_pct']:.1%}) |
| Validation 2024–2025 | {c['validation_2024_2025']['predicted_games']} | \
{c['validation_2024_2025']['both_continuing']} ({c['validation_2024_2025']['both_continuing_pct']:.1%}) | \
{c['validation_2024_2025']['test_sample']} ({c['validation_2024_2025']['test_sample_pct']:.1%}) |
| All 2021–2025 | {c['all_2021_2025']['predicted_games']} | \
{c['all_2021_2025']['both_continuing']} ({c['all_2021_2025']['both_continuing_pct']:.1%}) | \
{c['all_2021_2025']['test_sample']} ({c['all_2021_2025']['test_sample_pct']:.1%}) |

"Both continuing" = each listed starter threw ≥85% of his team's
trailing-window dropbacks (the model's own `qb_adj = 0` criterion,
replicated exactly). "Test sample" adds the feature eligibility rules
(≥15 dropbacks in the QB's last game, ≥100 career dropbacks entering
the game).

## Secondary outputs (descriptive only — no verdict power)

- **Last-game INT differential** (`last_int_diff` = away QB's last-game
  INTs − home QB's; the Darnold anecdote's exact shape):
  discovery slope {si_d['slope']:+.3f} (z = {si_d['z']:+.2f}, n = {si_d['n']});
  validation slope {si_v['slope']:+.3f} (z = {si_v['z']:+.2f}, n = {si_v['n']}).
- **ATS win% on model picks (|spread_edge| ≥ 1.5), split by whether
  `qb_form_diff` agrees with the pick:**
  validation — agree {av['agree']['wlp']} \
({('%.1f%%' % (100 * av['agree']['win_pct'])) if av['agree']['win_pct'] is not None else 'n/a'}), \
disagree {av['disagree']['wlp']} \
({('%.1f%%' % (100 * av['disagree']['win_pct'])) if av['disagree']['win_pct'] is not None else 'n/a'});
  discovery — agree {ad['agree']['wlp']} \
({('%.1f%%' % (100 * ad['agree']['win_pct'])) if ad['agree']['win_pct'] is not None else 'n/a'}), \
disagree {ad['disagree']['wlp']} \
({('%.1f%%' % (100 * ad['disagree']['win_pct'])) if ad['disagree']['win_pct'] is not None else 'n/a'}).

## Method notes and deviations (all flagged per house rules)

1. **2025 closing lines:** `spreadspoke_scores.csv`, the line store
   used by every prior diagnostic, ends at 2024 — it has no 2025 rows.
   The 2025 game frame, final scores, and closing spread therefore come
   from `data/schedules_games.parquet` (nflverse), a file the harness
   already loads for QB ids and venue. Its `spread_line` was checked
   against the spreadspoke closing spread on 2021–2024 first: same
   convention (positive = home favored), correlation 0.996, 66%
   identical, mean |difference| 0.24 pts; final scores agree 99.9%.
   The PRIMARY test never touches a line (it needs only our_margin and
   the actual margin); only the descriptive ATS split uses lines, and
   only its 2025 rows use the nflverse line.
2. **`last_dev` trailing mean:** the preregistration specifies the
   ratings' decay without specifying a game window for the QB's own
   history. Implemented as: per-game EPA/dropback for each of the QB's
   prior games, weighted by the ratings' per-game decay (half-life 8
   games, most recent = weight 1) via the pipeline's own
   `_decayed_mean`, over all his prior games in the data. Dropbacks and
   EPA are the pipeline's own construction (`load_qb_plays`:
   pass attempts + sacks, turnover-damped EPA) — reused, not redefined.
   A QB's games are his games for any team (as in `qb_adjustments`'
   treatment of a starter's own form).
3. **"Career dropbacks"** are counted within the test data (2021–2025
   play-by-play), the only data the preregistration names; pre-2021
   dropbacks are unobserved, which mainly delays eligibility for some
   veterans early in 2021.
4. OLS is fit with an intercept (the standard reading of "regress Y on
   X"); only the slope is applied as the adjustment, as specified.
5. The motivating 2026 season is excluded entirely, per the
   preregistration.

## What this does and doesn't mean

"""
    if verdict == "KILL":
        md += ("A KILL means: on the frozen test, a QB's most recent game "
               "adds no demonstrated signal on top of ratings that already "
               "decay-weight that game and a QB-change machinery that "
               "already prices replacement starters. The live model is "
               "unchanged. This says nothing about QB *changes* (owned by "
               "`qb_adjustments` and the override feed), and it does not "
               "mean \"form doesn't matter\" in general — it means this "
               "specific last-game deviation term did not earn its place.\n")
    else:
        md += ("A KEEP means only that the term earned a separate "
               "implementation test against the live generator — nothing "
               "ships on this result. Any live-model change still needs "
               "that test and Bryant's explicit approval.\n")
    (OUT / "RESULTS.md").write_text(md)
    print(f"[done] RESULTS.md written; verdict {verdict}")


if __name__ == "__main__":
    main()
