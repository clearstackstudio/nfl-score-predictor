"""Turnover-damping placebo (specificity) test — pre-registered 2026-10-12.

Pre-registration: goals/ultimate-multi-sport-prediction-model/hidden_files/
turnover-placebo-preregistration.md

Design (per pre-reg):
  - Frame identical to the turnover-damping study: walk-forward 2021-2024,
    same 1,107 games, closing lines as benchmark only, ATS @ |edge| >= 1.5,
    OU @ |edge| >= 3.0, no wind, no circuit.
  - Placebo selection (done once, before any walk-forward run): from the
    same pass/rush pool used to build ratings, EXCLUDING turnover plays
    (interception == 1 or fumble_lost == 1), randomly select whole plays
    until the selected set's total |EPA| matches the turnover plays' total
    |EPA| in the pool within +/-2%. 5 replicates, seeds fixed in advance:
    1101, 2202, 3303, 4404, 5505. Selected play IDs (game_id, play_id) are
    saved per seed so the arms are exactly reproducible.
  - Damping mechanics identical to the turnover arms: selected play EPA x w,
    symmetric in off/def sums (same rows), play counts unscaled, QB
    untouched, epa_const calibrated on the undamped frame. Primary w=0.50,
    secondary w=0.25. Turnover arms are NOT re-run; comparison targets are
    the published numbers in research/turnover_damping/metrics.json
    (w=0.50 margin RMSE 14.143686, improvement over baseline 0.300224;
    baseline 14.443910).
  - Baseline gate: the placebo loader at w=1.0 must equal the baseline
    frame, and the Arm 0 walk-forward must reproduce Config A bit-identical
    (basemod.verify_against_a) before any placebo number is trusted.

Measurement only: nothing in src/ or site/ is modified. Executed as staged
single-arm processes (per the prior study's process lesson); each stage
appends to metrics.json incrementally.

Run with the repo venv:
  .venv-cfb/bin/python research/turnover_placebo/run_turnover_placebo.py \
      --stage select|arm0|rep<seed>_w050|rep<seed>_w025
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
BASE = REPO / "research" / "epa_live_backtest"
TD_DIR = REPO / "research" / "turnover_damping"
OUT = REPO / "research" / "turnover_placebo"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(TD_DIR))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import run_turnover_damping as td  # noqa: E402
from epa_ratings import DATA, PBP_YEARS, load_qb_plays, load_team_games  # noqa: E402

SEEDS = [1101, 2202, 3303, 4404, 5505]
PBP_COLS_SEL = ["game_id", "play_id", "week", "season", "posteam",
                "defteam", "epa", "pass_attempt", "rush_attempt",
                "home_team", "away_team", "interception", "fumble_lost"]
PBP_COLS_LOAD = td.PBP_COLS + ["play_id"]

# Published comparison targets (research/turnover_damping/metrics.json).
BASELINE_MARGIN_RMSE = 14.44391015835516
TO_W050_MARGIN_RMSE = 14.143686009400012
TO_W050_IMPROVEMENT = BASELINE_MARGIN_RMSE - TO_W050_MARGIN_RMSE  # 0.300224
TO_W025_MARGIN_RMSE = 14.091402028206439


def _pool() -> pd.DataFrame:
    """The exact filtered play pool the ratings are built from, all years,
    with play_id retained for selection identity."""
    frames = []
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=PBP_COLS_SEL)
        plays = pbp[
            ((pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1))
            & pbp["epa"].notna()
            & pbp["posteam"].notna()
        ]
        frames.append(plays)
    return pd.concat(frames, ignore_index=True)


def stage_select() -> None:
    pool = _pool()
    is_to = (pool["interception"] == 1) | (pool["fumble_lost"] == 1)
    target = float(pool.loc[is_to, "epa"].abs().sum())
    nonto = pool.loc[~is_to].reset_index(drop=True)
    absvals = nonto["epa"].abs().to_numpy()
    print(f"[select] pool plays {len(pool)}; turnover plays {int(is_to.sum())}; "
          f"target |EPA| mass {target:.2f}; non-TO pool {len(nonto)}", flush=True)
    info = {"pool_plays": int(len(pool)),
            "turnover_plays": int(is_to.sum()),
            "target_abs_epa": target,
            "nonto_pool_plays": int(len(nonto)),
            "nonto_abs_epa": float(absvals.sum()),
            "seeds": {}}
    for seed in SEEDS:
        rng = np.random.RandomState(seed)
        perm = rng.permutation(len(nonto))
        cs = np.cumsum(absvals[perm])
        k = int(np.searchsorted(cs, target)) + 1  # first crossing of target
        chosen = nonto.iloc[perm[:k]]
        achieved = float(chosen["epa"].abs().sum())
        match_pct = 100.0 * achieved / target
        ids = [[str(g), int(p)] for g, p in
               zip(chosen["game_id"], chosen["play_id"])]
        (OUT / f"selection_seed{seed}.json").write_text(json.dumps(ids))
        info["seeds"][str(seed)] = {
            "n_selected": int(k),
            "achieved_abs_epa": achieved,
            "match_pct": match_pct,
            "within_pm2pct": bool(abs(match_pct - 100.0) <= 2.0),
        }
        print(f"  seed {seed}: {k} plays, |EPA| {achieved:.2f}, "
              f"match {match_pct:.3f}%", flush=True)
        if abs(match_pct - 100.0) > 2.0:
            print("STOP: selection outside the pre-registered +/-2% band.")
            sys.exit(2)
    (OUT / "selection_info.json").write_text(json.dumps(info, indent=2))
    print("[select] saved selection IDs + selection_info.json", flush=True)


def _selected_keys(seed: int) -> set:
    ids = json.loads((OUT / f"selection_seed{seed}.json").read_text())
    return {f"{g}#{p}" for g, p in ids}


def load_team_games_placebo(selected: set | None, w: float,
                            expect_n: int | None = None) -> pd.DataFrame:
    """Mirror of td.load_team_games_damped, scaling EPA of the selected
    placebo plays (identity (game_id, play_id)) by w instead of turnover
    plays. At w == 1.0 the frame is the baseline frame by construction.

    NOTE: play_id is float64 in the parquet (1.0, 40.0, ...); keys must be
    built from int(play_id) to match the saved selection IDs. An earlier
    version built keys from str(float) ('...#1.0'), matched zero plays,
    and silently reproduced the baseline — stage_rep now hard-asserts the
    scaled-play count against the saved selection size."""
    frames = []
    n_scaled = 0
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=PBP_COLS_LOAD)
        plays = pbp[
            ((pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1))
            & pbp["epa"].notna()
            & pbp["posteam"].notna()
        ]
        if w != 1.0:
            keys = (plays["game_id"].astype(str) + "#"
                    + plays["play_id"].round().astype("Int64").astype(str))
            mask = keys.isin(selected)
            n_scaled += int(mask.sum())
            plays = plays.copy()
            plays.loc[mask, "epa"] = plays.loc[mask, "epa"] * w
        off = (plays.groupby(["game_id", "week", "season", "posteam",
                              "home_team", "away_team"])["epa"]
               .agg(["sum", "count"]).reset_index())
        off = off.rename(columns={"posteam": "team", "sum": "off_epa",
                                  "count": "off_plays"})
        deff = (plays.groupby(["game_id", "defteam"])["epa"]
                .agg(["sum", "count"]).reset_index())
        deff = deff.rename(columns={"defteam": "team", "sum": "def_epa",
                                    "count": "def_plays"})
        g = off.merge(deff, on=["game_id", "team"], how="outer")
        g["off_epa_play"] = g["off_epa"] / g["off_plays"]
        g["def_epa_play"] = g["def_epa"] / g["def_plays"]
        g["opp"] = g.apply(
            lambda r: r["away_team"] if r["team"] == r["home_team"]
            else r["home_team"], axis=1)
        frames.append(g)
    if w != 1.0 and expect_n is not None and n_scaled != expect_n:
        raise AssertionError(
            f"scaled {n_scaled} plays but selection has {expect_n} — "
            "key mismatch, refusing to record a no-op arm")
    tg = pd.concat(frames, ignore_index=True)
    return tg.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def _load_results() -> dict:
    p = OUT / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _save_results(results: dict) -> None:
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2, default=str))


def stage_arm0() -> None:
    config_a = json.loads((BASE / "config_a.json").read_text())
    print("[arm0] structural check: placebo loader (w=1.0, seed 1101 "
          "selection loaded) == baseline ...", flush=True)
    tg0 = load_team_games()
    sel = _selected_keys(SEEDS[0])
    tg_p1 = load_team_games_placebo(sel, 1.0)
    same = tg_p1.equals(tg0)
    print(f"      frames equal: {same}", flush=True)
    if not same:
        print("STOP: placebo loader at w=1.0 does not reproduce baseline frame.")
        sys.exit(2)
    results = _load_results()
    results["structural_check_w1_equals_baseline"] = bool(same)
    print("[arm0] walk-forward (baseline) + verification vs Config A ...",
          flush=True)
    qb0 = load_qb_plays()
    t0 = time.time()
    df0 = td.walk_forward(tg_p1, qb0, tg0)
    ver = td.basemod.verify_against_a(df0, config_a)
    print(f"      {len(df0)} games in {time.time() - t0:.0f}s; verification: "
          f"{'PASS' if ver['ok'] else 'FAIL'} {json.dumps(ver['abs_diffs'])}",
          flush=True)
    results["arm0_verification"] = ver
    if not ver["ok"]:
        _save_results(results)
        print("STOP: Arm 0 does not reproduce Config A (per pre-reg).")
        sys.exit(2)
    results["arm_w1.00"] = td.arm_block(df0)
    df0.to_csv(OUT / "per_game_w1.00.csv", index=False)
    _save_results(results)
    print("[arm0] saved to metrics.json", flush=True)


def stage_rep(seed: int, w: float) -> None:
    tag = f"rep{seed}_w{w:.2f}"
    print(f"[{tag}] walk-forward ...", flush=True)
    tg0 = load_team_games()
    qb0 = load_qb_plays()
    sel = _selected_keys(seed)
    info = json.loads((OUT / "selection_info.json").read_text())
    expect_n = int(info["seeds"][str(seed)]["n_selected"])
    t0 = time.time()
    tg_w = load_team_games_placebo(sel, w, expect_n=expect_n)
    df_w = td.walk_forward(tg_w, qb0, tg0)
    results = _load_results()
    results[tag] = td.arm_block(df_w)
    df_w.to_csv(OUT / f"per_game_{tag}.csv", index=False)
    _save_results(results)
    o = results[tag]["overall"]
    print(f"      {len(df_w)} games in {time.time() - t0:.0f}s; "
          f"margin RMSE {o['margin_rmse_ours']:.4f} "
          f"(improvement vs baseline {BASELINE_MARGIN_RMSE - o['margin_rmse_ours']:+.4f}), "
          f"ATS {o['ats_pct']:.4f}, total RMSE {o['total_rmse_ours']:.4f}, "
          f"OU {o['ou_pct']:.4f} — saved", flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    help="select | arm0 | rep<seed>_w050 | rep<seed>_w025")
    args = ap.parse_args()
    if args.stage == "select":
        stage_select()
    elif args.stage == "arm0":
        stage_arm0()
    elif args.stage.startswith("rep"):
        seed_s, w_s = args.stage[3:].split("_w")
        stage_rep(int(seed_s), int(w_s) / 100.0)
    else:
        ap.error(f"unknown stage {args.stage}")
