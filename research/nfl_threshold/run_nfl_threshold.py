"""NFL publish-threshold test — run of the 2026-10-23 preregistration.

Executes research/nfl_threshold/PREREGISTRATION.md exactly as written:

  Phase 0  Baseline gate (STOP rule): src/epa_ratings.run_backtest()
           as-is must return ATS 47.29% (393-438-29), margin RMSE
           14.131, n = 1,107 (2021-2024), tolerances |dATS| <= 0.15 pp,
           |dRMSE| <= 0.02. On mismatch: STOP, no re-pinning.
  Phase 1  Walk-forward predictions 2021-2025 under the LIVE EPA config
           (damped turnovers, half-life 8), built with the QB-recency
           harness pattern (research/qb_recency/run_qb_recency.py):
           same imported functions, same loop order, same game frame.
           The 2021-2024 rows are verified against the damping study's
           robustness per-game file before anything else is trusted.
  Phase 2  The frozen table: for tau in {0.5, 1.5, 2.5, 3.5, 4.5, 5.5}
           points of |spread_edge|, per split (discovery 2021-2023,
           validation 2024-2025): plays n, ATS W-L-P, ATS win% (pushes
           excluded), flat-bet ROI at -110. Then the frozen decision
           rule (see PREREGISTRATION.md).

Play definition (frozen, "as the generator does"): the live generator
(src/weekly_picks.py) rounds spread_edge to 0.1 BEFORE thresholding
("Round BEFORE thresholding: published edges are 0.1-rounded") and
publishes the side = sign of that rounded edge. The threshold table
therefore thresholds the 0.1-rounded edge; per_game.csv carries both
the raw and the rounded edge so either convention can be recomputed.
2026 is excluded entirely. Measurement only — nothing live changes.

Run: .venv-cfb/bin/python research/nfl_threshold/run_nfl_threshold.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "nfl_threshold"
sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import epa_ratings  # noqa: E402
from backtest import closing_home_spread, load_games  # noqa: E402
from epa_ratings import (  # noqa: E402
    ABBR_TO_FULL, CARRYOVER, DATA, HOME_EDGE_PTS, PLAYS_PER_GAME,
    adjusted_ratings, load_qb_plays, load_team_games, qb_adjustments,
    run_backtest, week_int,
)

YEARS = [2021, 2022, 2023, 2024, 2025]
DISCOVERY = [2021, 2022, 2023]
VALIDATION = [2024, 2025]
TAUS = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5]
PIN_ATS_PCT = 47.29        # baseline gate pin (damped live config)
PIN_RMSE = 14.131          # baseline gate pin
PIN_N = 1107               # baseline gate pin
PIN_ATS_WLP = (393, 438, 29)
REF_RMSE_2021_24 = 14.130860208614187  # damping-study per-game replication


def fail(results: dict, msg: str) -> None:
    results["status"] = "STOPPED"
    results["stop_reason"] = msg
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    (OUT / "RESULTS.md").write_text(
        "# NFL publish threshold — RESULTS\n\n"
        f"**STOPPED at the baseline gate: {msg}**\n\n"
        "Per the preregistration's stop rule, the test does not proceed "
        "on a mismatched baseline, and the pins are not re-pinned "
        "without a dated addendum approved by Bryant. No verdict is "
        "recorded and no model or publishing change is implied.\n")
    print("STOP:", msg)
    sys.exit(3)


# --------------------------------------------------------------------------
# Phase 0 — baseline gate
# --------------------------------------------------------------------------

def phase0(results: dict) -> None:
    t0 = time.time()
    r = run_backtest()
    results["baseline_gate"] = {
        "games": r["games"],
        "ats": list(r["ats"]),
        "ats_pct": r["ats_pct"],
        "our_margin_rmse": r["our_margin_rmse"],
        "seconds": round(time.time() - t0, 1),
    }
    print(f"[phase0] run_backtest: games={r['games']} ats={list(r['ats'])} "
          f"ats_pct={r['ats_pct'] * 100:.4f}% rmse={r['our_margin_rmse']:.4f} "
          f"({time.time() - t0:.0f}s)")
    problems = []
    if r["games"] != PIN_N:
        problems.append(f"n = {r['games']} vs pin {PIN_N}")
    if tuple(r["ats"]) != PIN_ATS_WLP:
        problems.append(f"ATS {tuple(r['ats'])} vs pin {PIN_ATS_WLP}")
    if abs(r["ats_pct"] * 100 - PIN_ATS_PCT) > 0.15:
        problems.append(f"ATS {r['ats_pct'] * 100:.2f}% vs pin "
                        f"{PIN_ATS_PCT}% (tol 0.15 pp)")
    if abs(r["our_margin_rmse"] - PIN_RMSE) > 0.02:
        problems.append(f"margin RMSE {r['our_margin_rmse']:.3f} vs pin "
                        f"{PIN_RMSE} (tol 0.02)")
    if problems:
        fail(results, "run_backtest() as-is does not match the frozen "
                      "baseline gate: " + "; ".join(problems))
    results["baseline_gate"]["passed"] = True
    print("[phase0] baseline gate PASSED")


# --------------------------------------------------------------------------
# Phase 1 — walk-forward predictions 2021-2025 (QB-recency harness pattern)
# --------------------------------------------------------------------------

def build_game_frame() -> pd.DataFrame:
    """Games to predict. 2021-2024 from spreadspoke (as the harness);
    2025 from nflverse schedules (spreadspoke ends at 2024). Verbatim
    from research/qb_recency/run_qb_recency.py."""
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


def walk_forward() -> pd.DataFrame:
    """The QB-recency harness loop, minus its QB features (features never
    feed the margin; adjusted_ratings + qb_adjustments are called
    identically, so margins are the harness's margins)."""
    epa_ratings.PBP_YEARS = YEARS  # extend the pipeline loaders to 2025
    team_games = load_team_games()
    qb_plays = load_qb_plays()

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

        spread_edge = our_margin - row["line_margin"]
        rows.append({
            "date": row["date"], "season": season, "week": int(row["week"]),
            "home": home, "away": away,
            "our_margin": our_margin,
            "line_margin": row["line_margin"],
            "actual_margin": row["actual_margin"],
            "margin_resid": row["actual_margin"] - our_margin,
            "spread_edge": spread_edge,
            # the generator thresholds the 0.1-rounded edge (weekly_picks.py)
            "spread_edge_rounded": round(float(spread_edge), 1),
        })

        off2, def2, _pace = adjusted_ratings(team_games, idxs[-1] + 1,
                                             season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    return pd.DataFrame(rows)


def verify_replication(df: pd.DataFrame, results: dict) -> None:
    """Harness-pattern verification: the 2021-2024 rows must replicate
    the damping study's verified per-game file exactly."""
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
        "games_2021_24": n, "ats_at_tau1.5_unrounded_wlp": [w, l, p],
        "margin_rmse": rmse,
        "merged_vs_harness_per_game": int(len(m)),
        "max_abs_margin_diff": max_diff,
    }
    print(f"[phase1] 2021-24 replication: n={n} ats@1.5={w}-{l}-{p} "
          f"rmse={rmse:.4f} max_diff_vs_harness={max_diff:.2e}")
    if not (n == PIN_N and (w, l, p) == PIN_ATS_WLP
            and abs(rmse - REF_RMSE_2021_24) < 1e-6
            and len(m) == PIN_N and max_diff < 1e-9):
        fail(results, "extended walk-forward does not reproduce the "
                      "verified 2021-24 damped-config rows; analysis halted")


# --------------------------------------------------------------------------
# Phase 2 — the frozen threshold table + decision rule
# --------------------------------------------------------------------------

def ats_at_tau(df: pd.DataFrame, tau: float) -> dict:
    """Plays at |rounded spread_edge| >= tau; side = sign of the edge
    (the generator's play). ROI: flat 1-unit bets at -110 (win pays
    100/110, push refunds), ROI = profit / plays (pushes in the base)."""
    plays = df[df["spread_edge_rounded"].abs() >= tau]
    w = l = p = 0
    for _, r in plays.iterrows():
        res = r["actual_margin"] - r["line_margin"]
        if abs(res) < 0.01:
            p += 1
        elif (res > 0) == (r["spread_edge_rounded"] > 0):
            w += 1
        else:
            l += 1
    n = w + l + p
    profit = w * (100.0 / 110.0) - l * 1.0
    return {
        "plays": n, "w": w, "l": l, "p": p,
        "win_pct": (w / (w + l)) if (w + l) else None,
        "roi": (profit / n) if n else None,
    }


def main() -> None:
    results: dict = {}
    phase0(results)

    t0 = time.time()
    df = walk_forward()
    print(f"[phase1] walk-forward 2021-2025: {len(df)} predicted games "
          f"in {time.time() - t0:.0f}s")
    verify_replication(df, results)

    disc = df[df["season"].isin(DISCOVERY)]
    val = df[df["season"].isin(VALIDATION)]
    results["coverage"] = {
        "discovery_2021_2023": {
            "games": int(len(disc)),
            "weeks": int(disc[["season", "week"]].drop_duplicates().shape[0]),
        },
        "validation_2024_2025": {
            "games": int(len(val)),
            "weeks": int(val[["season", "week"]].drop_duplicates().shape[0]),
        },
        "all_2021_2025": {"games": int(len(df))},
    }

    table: dict = {}
    for tau in TAUS:
        table[str(tau)] = {
            "discovery": ats_at_tau(disc, tau),
            "validation": ats_at_tau(val, tau),
        }
    results["threshold_table"] = table
    for tau in TAUS:
        d, v = table[str(tau)]["discovery"], table[str(tau)]["validation"]
        print(f"[phase2] tau={tau}: disc {d['w']}-{d['l']}-{d['p']} "
              f"({(d['win_pct'] or 0) * 100:.1f}%, n={d['plays']}) | "
              f"val {v['w']}-{v['l']}-{v['p']} "
              f"({(v['win_pct'] or 0) * 100:.1f}%, n={v['plays']})")

    # Frozen decision rule: candidate tau > 0.5 earns an ADOPT
    # recommendation iff on VALIDATION win% >= 52.4% AND n >= 100 AND
    # the same tau's DISCOVERY win% >= 51.5%. If several qualify, the
    # smallest qualifying tau is tau* (least deviation from current
    # publishing, largest volume) — disclosed in RESULTS.md.
    qualifying = []
    for tau in TAUS:
        if tau <= 0.5:
            continue
        d, v = table[str(tau)]["discovery"], table[str(tau)]["validation"]
        bars = {
            "bar1_validation_win_pct>=52.4": bool(
                v["win_pct"] is not None and v["win_pct"] * 100 >= 52.4),
            "bar2_validation_n>=100": bool(v["plays"] >= 100),
            "bar3_discovery_win_pct>=51.5": bool(
                d["win_pct"] is not None and d["win_pct"] * 100 >= 51.5),
        }
        if all(bars.values()):
            qualifying.append(tau)
        table[str(tau)]["decision_bars"] = bars
    tau_star = min(qualifying) if qualifying else None
    verdict = "ADOPT" if tau_star is not None else "KILL"
    results["decision"] = {
        "qualifying_taus": qualifying,
        "tau_star": tau_star,
        "verdict": verdict,
        "tiebreak_if_multiple": "smallest qualifying tau (disclosed rule)",
    }

    val_weeks = results["coverage"]["validation_2024_2025"]["weeks"]
    results["volume"] = {
        "validation_weeks": val_weeks,
        "plays_per_week_by_tau_validation": {
            str(tau): table[str(tau)]["validation"]["plays"] / val_weeks
            for tau in TAUS
        },
    }
    results["verdict"] = verdict
    results["status"] = "COMPLETED"
    print(f"[phase2] qualifying taus: {qualifying}; verdict: {verdict}")

    cols = ["date", "season", "week", "home", "away", "our_margin",
            "line_margin", "actual_margin", "margin_resid", "spread_edge",
            "spread_edge_rounded"]
    df[cols].to_csv(OUT / "per_game.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print("[done] per_game.csv + results.json written")


if __name__ == "__main__":
    main()
