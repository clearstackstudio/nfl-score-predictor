"""Recency-weighting diagnostic — run of the 2026-10-19 preregistration.

Executes research/recency_weighting/PREREGISTRATION.md exactly as written:

  Phase 0  Baseline gate. Reproduce src/epa_ratings.run_backtest() exactly
           as-is (PBP_YEARS 2021-2024, live config: RECENCY_HALF_LIFE = 8,
           turnover damping w = 0.50). STOP unless ATS 47.29% (393-438-29),
           margin RMSE 14.131, n = 1,107 — the corrected damped-config pins
           (tolerances: |ATS% - 47.29| <= 0.15 pp, |RMSE - 14.131| <= 0.02).
  Phase 1  Walk-forward predictions 2021-2025 under all five frozen arms
           (RECENCY_HALF_LIFE in {4, 6, 8, 12, 16}; per-arm override of the
           module constant and its derived _RECENCY_DECAY only — both
           consumers, adjusted_ratings and qb_adjustments, move together,
           exactly as a live edit would). All other constants frozen at
           live values; damping ON in every arm; 2026 excluded. The
           baseline arm's 2021-2024 rows must replicate
           research/turnover_damping/per_game_robustness_w0.50_qb.csv
           per-game (all 1,107 merge; ATS tuple (393, 438, 29); RMSE
           within 1e-6 of 14.130860208614187; max |d margin| < 1e-9),
           else STOP. Scored game sets are verified identical across arms.
  Phase 2  Frozen selection on discovery 2021-2023 (lowest pooled margin
           RMSE; ties |d| < 0.001 break toward closest to 8 in log2 ratio,
           then toward the smaller half-life; if 8 is selected the verdict
           is KILL by the pre-registered degenerate rule). The frozen
           candidate is evaluated once on validation 2024-2025:
             ADOPT iff (1) pooled validation margin RMSE delta < 0 with the
             paired-bootstrap 95% CI (10,000 resamples, seed 20261019,
             percentile) lying entirely below 0, AND (2) the candidate
             worsens margin RMSE in NEITHER validation season, AND
             (3) pooled validation totals RMSE delta <= +0.10.
           Otherwise KILL. An ADOPT changes nothing live.

The walk-forward loop mirrors src/epa_ratings.run_backtest() and the
QB-recency runner, including the totals calibration (epa_const trailing
mean of actual_total - off_epa_raw), which the QB runner omitted because
totals were not a test input there; totals ARE a guardrail here.

Data note (ratified precedent): 2025 closing lines come from
data/schedules_games.parquet (spread_line) because spreadspoke ends at
2024 — used ONLY for the descriptive validation ATS context, which has
no verdict power. 2021-2024 lines come from spreadspoke via
backtest.closing_home_spread, as in run_backtest.

Run: .venv-cfb/bin/python research/recency_weighting/run_recency_weighting.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "recency_weighting"
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
GRID = [4, 6, 8, 12, 16]
LIVE_H = 8
PUBLISHED_ATS_PCT = 47.29
PUBLISHED_RMSE = 14.131
PUBLISHED_N = 1107
REF_RMSE_EXACT = 14.130860208614187
BOOT_N = 10_000
BOOT_SEED = 20261019
TOTALS_BOUND = 0.10


def fail(results: dict, msg: str) -> None:
    results["status"] = "STOPPED"
    results["stop_reason"] = msg
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    (OUT / "RESULTS.md").write_text(
        "# Recency-weighting diagnostic — RESULTS\n\n"
        f"**STOPPED before the test: {msg}**\n\n"
        "Per the preregistration's baseline gate, the diagnostic does not "
        "proceed on a mismatched baseline or unverified replication. No "
        "verdict is recorded and no model change is implied. A pin "
        "correction requires a dated addendum to PREREGISTRATION.md, "
        "approved by Bryant, written before any re-run.\n")
    print("STOP:", msg)
    sys.exit(3)


def rmse(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.sqrt(np.mean((pred - actual) ** 2)))


def ats_record(df: pd.DataFrame) -> dict:
    """House convention: picks at |our_margin - line_margin| >= 1.5."""
    w = l = p = 0
    for _, r in df.iterrows():
        e = r["our_margin"] - r["line_margin"]
        if abs(e) >= 1.5:
            res = r["actual_margin"] - r["line_margin"]
            if abs(res) < 0.01:
                p += 1
            elif (res > 0) == (e > 0):
                w += 1
            else:
                l += 1
    dec = w + l
    return {"wlp": [w, l, p],
            "win_pct": (w / dec) if dec else None,
            "picks": int(w + l + p)}


# --------------------------------------------------------------------------
# Phase 0 — baseline gate, part 1: reproduction
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
    print(f"[phase0] reproduced: games={r['games']} "
          f"ats={tuple(r['ats'])} ats_pct={r['ats_pct'] * 100:.4f} "
          f"rmse={r['our_margin_rmse']:.4f} ({time.time() - t0:.0f}s)")
    if (r["games"] != PUBLISHED_N
            or abs(r["ats_pct"] * 100 - PUBLISHED_ATS_PCT) > 0.15
            or abs(r["our_margin_rmse"] - PUBLISHED_RMSE) > 0.02):
        fail(results,
             f"reproduced 2021-24 baseline does not match the gate pins "
             f"(games {r['games']} vs {PUBLISHED_N}; ATS "
             f"{r['ats_pct'] * 100:.2f}% vs {PUBLISHED_ATS_PCT}%; margin "
             f"RMSE {r['our_margin_rmse']:.3f} vs {PUBLISHED_RMSE})")


# --------------------------------------------------------------------------
# Phase 1 — walk-forward predictions 2021-2025, one arm
# --------------------------------------------------------------------------

def build_game_frame() -> pd.DataFrame:
    """Games to predict. 2021-2024 from spreadspoke (as the harness);
    2025 from nflverse schedules (spreadspoke ends at 2024).
    Mirrors research/qb_recency/run_qb_recency.py, plus actual_total."""
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
            "actual_total": float(r["score_home"]) + float(r["score_away"]),
            "game_id": None,
        })
    s = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "gameday", "home_team", "away_team",
                 "home_score", "away_score", "location", "spread_line",
                 "game_id"])
    s = s[s["season"] == 2025]
    n_raw = len(s)
    s = s[s["home_score"].notna() & s["away_score"].notna()]
    print(f"[frame] 2025 schedules rows: {n_raw}, with final scores: {len(s)}")
    for _, r in s.iterrows():
        rows.append({
            "date": str(r["gameday"]),
            "season": 2025,
            "week": int(r["week"]),
            "home": r["home_team"], "away": r["away_team"],
            "neutral": str(r["location"]) == "Neutral",
            "line_margin": float(r["spread_line"]),
            "actual_margin": float(r["home_score"]) - float(r["away_score"]),
            "actual_total": float(r["home_score"]) + float(r["away_score"]),
            "game_id": str(r["game_id"]),
        })
    df = pd.DataFrame(rows)
    df = df.sort_values(["date", "game_id"], kind="stable").reset_index(drop=True)
    return df


def walk_forward(team_games: pd.DataFrame, qb_plays: pd.DataFrame,
                 sched_qb: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """The run_backtest loop, extended to the given frame, returning
    per-game our_margin AND our_total (totals calibration included,
    identical to run_backtest: trailing mean of actual_total minus the
    game's raw combined offensive EPA, evaluated after prediction)."""
    qb_lookup = {(int(r.season), int(r.week), r.home_team, r.away_team):
                 (r.home_qb_id, r.away_qb_id) for r in sched_qb.itertuples()}
    tg_lookup: dict[tuple, list[int]] = {}
    for i, r in team_games[["season", "week", "home_team", "away_team"]].iterrows():
        tg_lookup.setdefault((int(r["season"]), int(r["week"]),
                              r["home_team"], r["away_team"]), []).append(i)

    prior: dict = {}
    last_season = None
    season_final: dict = {}
    epa_const_hist: list[float] = []
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
        epa_const = (sum(epa_const_hist) / len(epa_const_hist)) \
            if epa_const_hist else 46.0
        our_total = (exp_home_off + exp_away_off) * exp_plays + epa_const

        rows.append({
            "date": row["date"], "season": season, "week": int(row["week"]),
            "home": home, "away": away,
            "our_margin": our_margin, "our_total": our_total,
            "line_margin": row["line_margin"],
            "actual_margin": row["actual_margin"],
            "actual_total": row["actual_total"],
        })

        game_epa = team_games.iloc[idxs]["off_epa_raw"].sum()
        epa_const_hist.append(row["actual_total"] - game_epa)

        off2, def2, _pace = adjusted_ratings(team_games, idxs[-1] + 1,
                                             season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    return pd.DataFrame(rows)


def set_half_life(h: int) -> None:
    epa_ratings.RECENCY_HALF_LIFE = h
    epa_ratings._RECENCY_DECAY = 0.5 ** (1.0 / h)


# --------------------------------------------------------------------------
# Phase 1 gate, part 2: baseline-arm per-game replication
# --------------------------------------------------------------------------

def verify_replication(base: pd.DataFrame, results: dict) -> None:
    sub = base[base["season"] <= 2024]
    n = len(sub)
    r = rmse(sub["our_margin"].to_numpy(), sub["actual_margin"].to_numpy())
    ats = ats_record(sub)
    w, l, p = ats["wlp"]
    ref = pd.read_csv(REPO / "research" / "turnover_damping"
                      / "per_game_robustness_w0.50_qb.csv")
    m = sub.merge(ref, on=["season", "week", "home", "away"],
                  suffixes=("", "_ref"))
    max_diff = float((m["our_margin"] - m["our_margin_ref"]).abs().max()) \
        if len(m) else float("nan")
    max_diff_total = float((m["our_total"] - m["our_total_ref"]).abs().max()) \
        if len(m) else float("nan")
    results["replication_check"] = {
        "games_2021_24": n, "ats_wlp": [w, l, p], "margin_rmse": r,
        "merged_vs_reference_per_game": int(len(m)),
        "max_abs_margin_diff": max_diff,
        "max_abs_total_diff": max_diff_total,
    }
    print(f"[gate] 2021-24 replication: n={n} ats={w}-{l}-{p} rmse={r:.6f} "
          f"max|d margin|={max_diff:.2e} max|d total|={max_diff_total:.2e}")
    if not (n == PUBLISHED_N and (w, l, p) == (393, 438, 29)
            and abs(r - REF_RMSE_EXACT) < 1e-6
            and len(m) == PUBLISHED_N and max_diff < 1e-9):
        fail(results, "baseline arm (H=8) of the extended walk-forward does "
                      "not replicate the verified 2021-24 damped-config "
                      "per-game rows; run halted before any other arm "
                      "was trusted")


# --------------------------------------------------------------------------
# Phase 2 — frozen selection and decision rule
# --------------------------------------------------------------------------

def select_candidate(disc_rmse: dict[int, float]) -> tuple[int, dict]:
    """Lowest pooled discovery margin RMSE; ties (|d| < 0.001) break
    toward closest to 8 in log2 ratio, then toward the smaller H."""
    best = min(disc_rmse.values())
    tied = [h for h, v in disc_rmse.items() if abs(v - best) < 0.001]
    if len(tied) > 1:
        tied.sort(key=lambda h: (abs(math.log2(h / LIVE_H)), h))
    cand = tied[0]
    info = {
        "winner": cand,
        "discovery_rmse_by_arm": {str(h): disc_rmse[h] for h in GRID},
        "margin_over_second_best": None,
        "tied_arms_within_0.001": tied,
        "at_grid_edge": cand in (GRID[0], GRID[-1]),
    }
    others = sorted(v for h, v in disc_rmse.items() if h != cand)
    if others:
        info["margin_over_second_best"] = float(others[0] - disc_rmse[cand])
    return cand, info


def main() -> None:
    results: dict = {}
    phase0(results)

    epa_ratings.PBP_YEARS = YEARS  # extend the pipeline loaders to 2025
    team_games = load_team_games()
    qb_plays = load_qb_plays()
    sched_qb = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "home_team", "away_team",
                 "home_qb_id", "away_qb_id"])
    games = build_game_frame()
    print(f"[frame] games to predict 2021-2025: {len(games)}")

    arms: dict[int, pd.DataFrame] = {}
    for h in GRID:
        t0 = time.time()
        set_half_life(h)
        arms[h] = walk_forward(team_games, qb_plays, sched_qb, games)
        arms[h]["half_life"] = h
        print(f"[arm H={h}] scored {len(arms[h])} games "
              f"in {time.time() - t0:.0f}s")

    set_half_life(LIVE_H)  # restore live constants in-process
    assert epa_ratings.RECENCY_HALF_LIFE == LIVE_H

    verify_replication(arms[LIVE_H], results)

    # Scored-set identity across arms (preregistration: verify + report)
    key = ["season", "week", "home", "away"]
    ref_keys = set(map(tuple, arms[LIVE_H][key].to_numpy()))
    set_check = {}
    for h in GRID:
        ks = set(map(tuple, arms[h][key].to_numpy()))
        set_check[str(h)] = {
            "n": int(len(arms[h])),
            "identical_to_baseline_set": bool(ks == ref_keys),
            "only_in_arm": int(len(ks - ref_keys)),
            "only_in_baseline": int(len(ref_keys - ks)),
        }
    results["scored_set_check"] = set_check
    print("[sets]", json.dumps(set_check))

    # Full sweep table (descriptive) + sample sizes
    table: dict[str, dict] = {}
    for h in GRID:
        df = arms[h]
        row = {}
        for name, seasons in (("discovery_2021_2023", DISCOVERY),
                              ("validation_2024_2025", VALIDATION),
                              ("all_2021_2025", YEARS),
                              ("season_2024", [2024]),
                              ("season_2025", [2025])):
            s = df[df["season"].isin(seasons)]
            row[name] = {
                "n": int(len(s)),
                "margin_rmse": rmse(s["our_margin"].to_numpy(),
                                    s["actual_margin"].to_numpy()),
                "totals_rmse": rmse(s["our_total"].to_numpy(),
                                    s["actual_total"].to_numpy()),
            }
        table[str(h)] = row
    results["sweep_table"] = table

    # Frozen selection on discovery
    disc_rmse = {h: table[str(h)]["discovery_2021_2023"]["margin_rmse"]
                 for h in GRID}
    cand, sel_info = select_candidate(disc_rmse)
    results["selection"] = sel_info
    print(f"[selection] candidate H={cand} "
          f"(discovery RMSE {disc_rmse[cand]:.4f}; "
          f"margin over 2nd best: {sel_info['margin_over_second_best']})")

    # Paired validation frame (candidate vs baseline on the same games)
    base_val = arms[LIVE_H][arms[LIVE_H]["season"].isin(VALIDATION)]
    cand_val = arms[cand][arms[cand]["season"].isin(VALIDATION)]
    paired = base_val.merge(
        cand_val, on=key, suffixes=("_base", "_cand"), how="inner")
    results["validation"] = {
        "paired_n": int(len(paired)),
        "baseline_n": int(len(base_val)),
        "candidate_n": int(len(cand_val)),
    }
    delta = rmse(paired["our_margin_cand"].to_numpy(),
                 paired["actual_margin_cand"].to_numpy()) \
        - rmse(paired["our_margin_base"].to_numpy(),
               paired["actual_margin_base"].to_numpy())

    # Paired bootstrap, seed frozen at 20261019, 10,000 resamples
    e_c = (paired["our_margin_cand"].to_numpy()
           - paired["actual_margin_cand"].to_numpy()) ** 2
    e_b = (paired["our_margin_base"].to_numpy()
           - paired["actual_margin_base"].to_numpy()) ** 2
    rng = np.random.default_rng(BOOT_SEED)
    n_p = len(paired)
    deltas = np.empty(BOOT_N)
    for i in range(BOOT_N):
        idx = rng.integers(0, n_p, n_p)
        deltas[i] = math.sqrt(e_c[idx].mean()) - math.sqrt(e_b[idx].mean())
    ci_lo, ci_hi = (float(np.percentile(deltas, 2.5)),
                    float(np.percentile(deltas, 97.5)))

    per_season = {}
    for s in VALIDATION:
        pb = base_val[base_val["season"] == s]
        pc = cand_val[cand_val["season"] == s]
        pp = pb.merge(pc, on=key, suffixes=("_base", "_cand"), how="inner")
        per_season[str(s)] = {
            "n_paired": int(len(pp)),
            "baseline_margin_rmse": rmse(pp["our_margin_base"].to_numpy(),
                                         pp["actual_margin_base"].to_numpy()),
            "candidate_margin_rmse": rmse(pp["our_margin_cand"].to_numpy(),
                                          pp["actual_margin_cand"].to_numpy()),
        }
        per_season[str(s)]["delta"] = (per_season[str(s)]["candidate_margin_rmse"]
                                       - per_season[str(s)]["baseline_margin_rmse"])

    tot_base = rmse(paired["our_total_base"].to_numpy(),
                    paired["actual_total_base"].to_numpy())
    tot_cand = rmse(paired["our_total_cand"].to_numpy(),
                    paired["actual_total_cand"].to_numpy())
    tot_delta = tot_cand - tot_base

    bar1 = bool(delta < 0 and ci_hi < 0)
    bar2 = bool(all(v["delta"] <= 0 for v in per_season.values()))
    bar3 = bool(tot_delta <= TOTALS_BOUND)
    degenerate = (cand == LIVE_H)
    verdict = "ADOPT" if (bar1 and bar2 and bar3 and not degenerate) else "KILL"

    results["validation"].update({
        "candidate_half_life": cand,
        "baseline_margin_rmse": rmse(paired["our_margin_base"].to_numpy(),
                                     paired["actual_margin_base"].to_numpy()),
        "candidate_margin_rmse": rmse(paired["our_margin_cand"].to_numpy(),
                                      paired["actual_margin_cand"].to_numpy()),
        "delta_margin_rmse": float(delta),
        "bootstrap_ci95": [ci_lo, ci_hi],
        "bootstrap_resamples": BOOT_N,
        "bootstrap_seed": BOOT_SEED,
        "per_season": per_season,
        "baseline_totals_rmse": tot_base,
        "candidate_totals_rmse": tot_cand,
        "delta_totals_rmse": float(tot_delta),
        "bar1_delta_neg_ci_below_0": bar1,
        "bar2_neither_season_worse": bar2,
        "bar3_totals_within_+0.10": bar3,
        "degenerate_candidate_is_live_setting": degenerate,
    })

    # Context (no verdict power): validation ATS, house convention
    results["validation_ats_context"] = {
        "baseline_H8": ats_record(base_val),
        "candidate": ats_record(cand_val),
        "note": "Picks at |our_margin - line_margin| >= 1.5. 2024 lines "
                "from spreadspoke closing spreads; 2025 lines from "
                "schedules_games.parquet spread_line (ratified by the "
                "2026-10-19 QB-recency addendum). Context only.",
    }
    results["verdict"] = verdict
    results["status"] = "COMPLETED"
    print(f"[verdict] {verdict}: cand H={cand} delta={delta:+.4f} "
          f"CI=[{ci_lo:+.4f}, {ci_hi:+.4f}] bars=({bar1}, {bar2}, {bar3}) "
          f"degenerate={degenerate}")

    all_arms = pd.concat([arms[h] for h in GRID], ignore_index=True)
    cols = ["half_life", "date", "season", "week", "home", "away",
            "our_margin", "our_total", "line_margin",
            "actual_margin", "actual_total"]
    # date exists only in the frame, not in walk_forward rows; re-attach
    date_map = games.set_index(key)["date"].to_dict()
    all_arms["date"] = [date_map[(r.season, r.week, r.home, r.away)]
                        for r in all_arms.itertuples()]
    all_arms[cols].sort_values(["half_life", "season", "week", "home"]) \
        .to_csv(OUT / "per_game.csv", index=False)
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    write_results_md(results, table, disc_rmse, cand)
    print("[done] RESULTS.md, results.json, per_game.csv written")


def write_results_md(r: dict, table: dict, disc_rmse: dict,
                     cand: int) -> None:
    v = r["validation"]
    sel = r["selection"]
    rep = r["replication_check"]
    br = r["baseline_reproduced"]
    ats_b = r["validation_ats_context"]["baseline_H8"]
    ats_c = r["validation_ats_context"]["candidate"]

    def pct(x):
        return "n/a" if x is None else f"{100 * x:.1f}%"

    rows = []
    for h in GRID:
        t = table[str(h)]
        mark = " ← live (baseline)" if h == LIVE_H else \
            (" ← selected candidate" if h == cand else "")
        rows.append(
            f"| {h}{mark} | {t['discovery_2021_2023']['n']} | "
            f"{t['discovery_2021_2023']['margin_rmse']:.3f} | "
            f"{t['discovery_2021_2023']['totals_rmse']:.3f} | "
            f"{t['validation_2024_2025']['n']} | "
            f"{t['validation_2024_2025']['margin_rmse']:.3f} | "
            f"{t['validation_2024_2025']['totals_rmse']:.3f} |")
    sweep_rows = "\n".join(rows)

    if sel["margin_over_second_best"] is not None:
        sel_margin_txt = f"{sel['margin_over_second_best']:.4f}"
    else:
        sel_margin_txt = "n/a"
    edge_txt = (" The winner sits on a grid edge; per the frozen edge "
                "rule this is reported as-is — the optimum may lie "
                "off-grid, and extending the grid requires a new "
                "pre-registration."
                if sel["at_grid_edge"] else "")
    ties_txt = (f" Arms within the 0.001 tie band of the winner: "
                f"{sel['tied_arms_within_0.001']} (tie-break applied per "
                f"the frozen rule)." if len(sel["tied_arms_within_0.001"]) > 1
                else "")

    sets_ok = all(s["identical_to_baseline_set"]
                  for s in r["scored_set_check"].values())
    sets_txt = ("All five arms scored the identical set of games "
                f"({r['scored_set_check'][str(LIVE_H)]['n']} games, "
                "2021–2025), as the preregistration expected."
                if sets_ok else
                "DISCREPANCY: scored sets differ across arms — "
                + json.dumps(r["scored_set_check"]) + ". The validation "
                "comparison uses the paired intersection, as registered.")

    if v["degenerate_candidate_is_live_setting"]:
        verdict_explain = (
            "Discovery selected the live setting itself (H = 8), so the "
            "candidate IS the baseline and the validation difference is "
            "identically zero by construction. Under the preregistration's "
            "pre-stated degenerate rule, the verdict is KILL — the current "
            "setting stands, confirmed by the sweep rather than merely "
            "unexamined. The validation numbers below are shown for the "
            "record; bar 1 cannot pass on a zero difference (its "
            "bootstrap CI is [0, 0], which does not lie below 0).")
    elif r["verdict"] == "ADOPT":
        verdict_explain = (
            "All three bars of the frozen decision rule passed (see the "
            "arithmetic below). Per the preregistration, an ADOPT is a "
            "recommendation only: it changes nothing live. Editing "
            "RECENCY_HALF_LIFE in src/epa_ratings.py requires Bryant's "
            "separate explicit approval, and — per the registered "
            "sequencing consequence — the team-momentum registration's "
            "baseline-gate pins would then need a dated, Bryant-approved "
            "addendum re-derived from the new baseline before that test "
            "may run.")
    else:
        verdict_explain = (
            "At least one bar of the frozen decision rule failed (see "
            "the arithmetic below). The live setting stands at "
            "RECENCY_HALF_LIFE = 8, unchanged.")

    ps = v["per_season"]
    md = f"""# Recency-weighting diagnostic — RESULTS

**Run:** 2026-10-19, on Bryant's explicit approval to run the diagnostic
scoped the same day. **Preregistration:** `PREREGISTRATION.md` in this
directory (written and committed before any sweep results were
computed). Runner: `run_recency_weighting.py`; numbers: `results.json`;
per-game rows for all five arms: `per_game.csv`. Measurement only — no
live model code, constant, config, generator, or site data was changed.
The live setting remains `RECENCY_HALF_LIFE = 8` in `src/epa_ratings.py`
regardless of the verdict below.

## Verdict: {r['verdict']}

{verdict_explain}

**The frozen decision rule** (ADOPT iff ALL THREE hold): (1) pooled
validation margin RMSE Δ < 0 with the paired-bootstrap 95% CI lying
entirely below 0; (2) the candidate worsens margin RMSE in neither
validation season; (3) pooled validation totals RMSE Δ ≤ +0.10.

## Baseline gate (passed before any arm was trusted)

1. **Reproduction.** `run_backtest()` exactly as-is returned ATS
   **{br['ats_pct'] * 100:.2f}%** ({br['ats'][0]}-{br['ats'][1]}-{br['ats'][2]})
   and margin RMSE **{br['our_margin_rmse']:.3f}** on **{br['games']}**
   games (2021–2024) — matching the corrected damped-config pins
   (47.29% / 14.131 / n = 1,107) within the registered tolerances.
2. **Per-game replication.** The baseline arm's (H = 8) extended
   walk-forward 2021–2024 rows replicate
   `research/turnover_damping/per_game_robustness_w0.50_qb.csv`:
   {rep['merged_vs_reference_per_game']} of {rep['games_2021_24']} games
   merge, ATS {rep['ats_wlp'][0]}-{rep['ats_wlp'][1]}-{rep['ats_wlp'][2]},
   margin RMSE {rep['margin_rmse']:.6f}, max |Δ our_margin| =
   {rep['max_abs_margin_diff']:.1e} (and max |Δ our_total| =
   {rep['max_abs_total_diff']:.1e} against the same file, verifying the
   totals calibration as well).

## The sweep — all five arms (descriptive table)

| Half-life | Disc. n | Disc. margin RMSE | Disc. totals RMSE | Val. n | Val. margin RMSE | Val. totals RMSE |
|---|---|---|---|---|---|---|
{sweep_rows}

{sets_txt}

## Selection (frozen rule, applied once)

Lowest pooled discovery (2021–2023) margin RMSE wins. Discovery margin
RMSE by arm: """ + ", ".join(f"H={h}: {disc_rmse[h]:.4f}" for h in GRID) + f""".
**Selected candidate: H = {cand}**, winning by {sel_margin_txt} RMSE
over the second-best arm.{ties_txt}{edge_txt}

## Validation — the candidate against each bar

Paired sample: {v['paired_n']} games (2024–2025) scored by both arms.

- **Bar 1 — Δ < 0 with bootstrap CI entirely below 0:
  {'PASS' if v['bar1_delta_neg_ci_below_0'] else 'FAIL'}.**
  Baseline (H = 8) margin RMSE {v['baseline_margin_rmse']:.3f} →
  candidate (H = {cand}) {v['candidate_margin_rmse']:.3f};
  Δ = {v['delta_margin_rmse']:+.4f}. Paired bootstrap (10,000 resamples
  of validation games, seed 20261019, percentile interval): 95% CI
  [{v['bootstrap_ci95'][0]:+.4f}, {v['bootstrap_ci95'][1]:+.4f}].
- **Bar 2 — neither validation season worsens:
  {'PASS' if v['bar2_neither_season_worse'] else 'FAIL'}.**
  2024 (n = {ps['2024']['n_paired']}): {ps['2024']['baseline_margin_rmse']:.3f} →
  {ps['2024']['candidate_margin_rmse']:.3f} (Δ {ps['2024']['delta']:+.4f});
  2025 (n = {ps['2025']['n_paired']}): {ps['2025']['baseline_margin_rmse']:.3f} →
  {ps['2025']['candidate_margin_rmse']:.3f} (Δ {ps['2025']['delta']:+.4f}).
  Any increase, however small, fails this bar.
- **Bar 3 — pooled validation totals RMSE Δ ≤ +0.10:
  {'PASS' if v['bar3_totals_within_+0.10'] else 'FAIL'}.**
  Baseline totals RMSE {v['baseline_totals_rmse']:.3f} → candidate
  {v['candidate_totals_rmse']:.3f}; Δ = {v['delta_totals_rmse']:+.4f}
  (bound: +0.10).

## Context (descriptive only — no verdict power)

**Validation ATS** at the house convention (|our_margin − line| ≥ 1.5;
2024 lines from spreadspoke, 2025 lines from
`schedules_games.parquet` `spread_line`, per the ratified precedent):
baseline H = 8: {ats_b['wlp'][0]}-{ats_b['wlp'][1]}-{ats_b['wlp'][2]}
({pct(ats_b['win_pct'])} on {ats_b['picks']} picks); candidate
H = {cand}: {ats_c['wlp'][0]}-{ats_c['wlp'][1]}-{ats_c['wlp'][2]}
({pct(ats_c['win_pct'])} on {ats_c['picks']} picks).

## Method notes

1. The sweep overrides only the module constant `RECENCY_HALF_LIFE`
   (and its derived `_RECENCY_DECAY`) per arm, so both consumers —
   `adjusted_ratings()` and `qb_adjustments()` — move together,
   exactly as a live edit would, per the registration's entanglement
   ruling. Every other constant stayed at its live value in every arm
   (`WINDOW_GAMES = 17`, `MIN_GAMES = 4`, `CARRYOVER = 0.5`,
   `TURNOVER_EPA_WEIGHT = 0.50` — damping ON in all arms — and the QB
   machinery constants).
2. The totals calibration (`epa_const` trailing mean) is arm-invariant
   — it depends only on game order and actual totals — and replicates
   the reference file's `our_total` column (max |Δ| above), so the
   totals guardrail compares like with like.
3. 2026 is excluded entirely, per the registration. No new data, no
   cost. The descriptive sweep table above carries no verdict standing:
   the verdict was computed only through the frozen
   selection-then-validation path.
"""
    (OUT / "RESULTS.md").write_text(md)


if __name__ == "__main__":
    main()
