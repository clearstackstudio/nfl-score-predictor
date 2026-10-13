"""NFL explicit penalty term — pre-registered test (2026-10-12).

Pre-registration: goals/ultimate-multi-sport-prediction-model/hidden_files/
penalty-term-preregistration.md

Question: src/epa_ratings.load_team_games() builds ratings only from
pass/rush-attempt plays. Penalty-ONLY plays (nflverse play_type ==
'no_play' rows carrying a penalty: false starts, delay of game,
encroachment, DPI/holding on nullified plays, ...) are excluded entirely.
Does crediting their EPA to the ratings help walk-forward prediction?

Design (fixed by the pre-registration; no search):
  Arm 0: baseline frame, load_team_games() as-is.
  Arm 1: penalty-play EPA added to off/def EPA sums at 100% weight;
         play-count denominators unchanged.
  Arm 2: same at 50% weight.
  Arm R: robustness check ONLY — Arm 1 with penalty plays also added to
         the play-count denominators (labeled, not a candidate).
Everything else (recency weighting, QB adjustment, thresholds, totals
formula) is inherited unchanged from the live-EPA backtest Config A: the
walk-forward loop below is the baseline runner's replication, verbatim
except for the team_games input and the dropped wind block. Grading
functions are imported from the baseline runner so semantics are shared.

Arm 0 must reproduce Config A bit-identically (checked with the baseline
runner's own verify_against_a); if it does not, this script exits before
running any other arm and RESULTS.md must say so.

Penalty-play operationalization: play_type == 'no_play' AND penalty == 1
AND not a scrimmage attempt AND posteam/defteam present. Play value =
the nflverse `epa` column (non-null on 100% of these rows in 2021-2024,
so the pre-registered ep-difference fallback is never needed).
Attribution: credited to posteam's offensive sum and charged to
defteam's defensive sum, exactly like a scrimmage play.

Measurement only: nothing in src/ or site/ is modified.

Run with the repo venv:
  .venv-cfb/bin/python research/penalty_term/run_penalty_term.py --arm all
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "penalty_term"
BASE = REPO / "research" / "epa_live_backtest"
sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtest import closing_home_spread, load_games  # noqa: E402
from epa_ratings import (  # noqa: E402
    ABBR_TO_FULL, CARRYOVER, DATA, HOME_EDGE_PTS, PBP_YEARS, PLAYS_PER_GAME,
    adjusted_ratings, load_qb_plays, load_team_games, qb_adjustments,
    week_int,
)

# Grading + verification imported from the baseline study's runner so this
# study grades IDENTICALLY to Config A by construction.
_spec = importlib.util.spec_from_file_location(
    "epa_live_runner", BASE / "run_epa_live_backtest.py")
_base_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base_runner)
grade_ats = _base_runner.grade_ats
grade_ou = _base_runner.grade_ou
verify_against_a = _base_runner.verify_against_a

PEN_COLS = ["game_id", "week", "season", "posteam", "defteam",
            "epa", "ep", "pass_attempt", "rush_attempt",
            "play_type", "penalty"]


# --------------------------------------------------------------------------
# Penalty-play aggregates + frame variants
# --------------------------------------------------------------------------

def load_penalty_plays() -> pd.DataFrame:
    """One row per penalty-only play (see module docstring)."""
    frames = []
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=PEN_COLS)
        scrimmage = (pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1)
        pen = pbp[(pbp["play_type"] == "no_play")
                  & (pbp["penalty"] == 1)
                  & ~scrimmage
                  & pbp["posteam"].notna()
                  & pbp["defteam"].notna()]
        frames.append(pen)
    return pd.concat(frames, ignore_index=True)


def penalty_aggregates(pen: pd.DataFrame) -> pd.DataFrame:
    """Per (game_id, team): penalty EPA credited on offense (as posteam),
    charged on defense (as defteam), and play counts for each side."""
    off = (pen.groupby(["game_id", "posteam"])["epa"]
           .agg(["sum", "count"]).reset_index()
           .rename(columns={"posteam": "team", "sum": "pen_off_epa",
                            "count": "pen_off_n"}))
    deff = (pen.groupby(["game_id", "defteam"])["epa"]
            .agg(["sum", "count"]).reset_index()
            .rename(columns={"defteam": "team", "sum": "pen_def_epa",
                             "count": "pen_def_n"}))
    agg = off.merge(deff, on=["game_id", "team"], how="outer").fillna(0.0)
    return agg


def variant_frame(tg0: pd.DataFrame, agg: pd.DataFrame,
                  weight: float, add_to_denom: bool) -> pd.DataFrame:
    """tg0 with penalty EPA folded into the sums (row order, opp, and all
    other columns preserved from tg0 by construction)."""
    tg = tg0.copy()
    m = tg[["game_id", "team"]].merge(agg, on=["game_id", "team"],
                                      how="left")
    # merge(how='left') preserves left row order; assert alignment anyway
    assert (m["game_id"].values == tg["game_id"].values).all()
    assert (m["team"].values == tg["team"].values).all()
    pen_off = m["pen_off_epa"].fillna(0.0).to_numpy()
    pen_def = m["pen_def_epa"].fillna(0.0).to_numpy()
    tg["off_epa"] = tg["off_epa"] + weight * pen_off
    tg["def_epa"] = tg["def_epa"] + weight * pen_def
    if add_to_denom:
        tg["off_plays"] = tg["off_plays"] + m["pen_off_n"].fillna(0).to_numpy()
        tg["def_plays"] = tg["def_plays"] + m["pen_def_n"].fillna(0).to_numpy()
    tg["off_epa_play"] = tg["off_epa"] / tg["off_plays"]
    tg["def_epa_play"] = tg["def_epa"] / tg["def_plays"]
    return tg


# --------------------------------------------------------------------------
# Walk-forward loop: the baseline runner's replicate_walk_forward(),
# verbatim except the team_games input and the dropped venue/wind join.
# --------------------------------------------------------------------------

def walk_forward(team_games: pd.DataFrame, qb_plays: pd.DataFrame) -> pd.DataFrame:
    sched_qb = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "home_team", "away_team",
                 "home_qb_id", "away_qb_id"])
    qb_lookup = {(int(r.season), int(r.week), r.home_team, r.away_team):
                 (r.home_qb_id, r.away_qb_id) for r in sched_qb.itertuples()}

    games = load_games()
    games = games[games["schedule_season"].isin(PBP_YEARS)].copy()
    games["home_abbr"] = games["team_home"].map(
        {v: k for k, v in ABBR_TO_FULL.items()})
    games["away_abbr"] = games["team_away"].map(
        {v: k for k, v in ABBR_TO_FULL.items()})
    games = games.dropna(subset=["home_abbr", "away_abbr"]).copy()
    games = games.sort_values("schedule_date").reset_index(drop=True)

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
        season = int(row["schedule_season"])
        if last_season is not None and season != last_season:
            prior = {t: (CARRYOVER * v[0], CARRYOVER * v[1])
                     for t, v in season_final.items()}
        last_season = season

        home, away = row["home_abbr"], row["away_abbr"]
        neutral = bool(row["stadium_neutral"])

        key = (season, week_int(row["schedule_week"]), home, away)
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
        edge_pts = 0.0 if neutral else HOME_EDGE_PTS
        exp_plays = (pace.get(home, PLAYS_PER_GAME)
                     + pace.get(away, PLAYS_PER_GAME)) / 2
        our_margin = (exp_home_off - exp_away_off) * exp_plays + edge_pts
        epa_const = (sum(epa_const_hist) / len(epa_const_hist)) if epa_const_hist else 46.0
        our_total = (exp_home_off + exp_away_off) * exp_plays + epa_const

        actual_margin = float(row["score_home"]) - float(row["score_away"])
        actual_total = float(row["score_home"]) + float(row["score_away"])
        line_margin = closing_home_spread(row)
        line_total = float(row["over_under_line"])

        rows.append({
            "season": season,
            "week": key[1],
            "home": home,
            "away": away,
            "neutral": neutral,
            "our_margin": our_margin,
            "our_total": our_total,
            "line_margin": line_margin,
            "line_total": line_total,
            "actual_margin": actual_margin,
            "actual_total": actual_total,
        })

        game_epa = team_games.iloc[idxs]["off_epa"].sum()
        epa_const_hist.append(actual_total - game_epa)

        off2, def2, _pace = adjusted_ratings(team_games, idxs[-1] + 1, season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Metrics (same quantities as the baseline study's tables)
# --------------------------------------------------------------------------

def block_metrics(df: pd.DataFrame) -> dict:
    n = len(df)
    su = sum((r["our_margin"] > 0) == (r["actual_margin"] > 0)
             for _, r in df.iterrows())
    w, l, p = grade_ats(df)
    ow, ol, op = grade_ou(df, "our_total", None)[:3]
    return {
        "games": n,
        "su_pct": su / n if n else float("nan"),
        "margin_rmse_ours": math.sqrt(((df["our_margin"] - df["actual_margin"]) ** 2).mean()),
        "margin_rmse_line": math.sqrt(((df["line_margin"] - df["actual_margin"]) ** 2).mean()),
        "ats_wlp": [w, l, p],
        "ats_picks": w + l + p,
        "ats_pct": w / (w + l) if (w + l) else float("nan"),
        "total_rmse_ours": math.sqrt(((df["our_total"] - df["actual_total"]) ** 2).mean()),
        "total_rmse_line": math.sqrt(((df["line_total"] - df["actual_total"]) ** 2).mean()),
        "ou_wlp": [ow, ol, op],
        "ou_picks": ow + ol + op,
        "ou_pct": ow / (ow + ol) if (ow + ol) else float("nan"),
    }


def arm_metrics(df: pd.DataFrame) -> dict:
    return {
        "overall": block_metrics(df),
        "per_season": {str(s): block_metrics(g)
                       for s, g in df.groupby("season")},
    }


# --------------------------------------------------------------------------
# Descriptive context (pre-registered: size of the blind spot)
# --------------------------------------------------------------------------

def descriptive_stats(tg0: pd.DataFrame, agg: pd.DataFrame,
                      pen: pd.DataFrame) -> dict:
    m = tg0[["game_id", "season", "team"]].merge(agg, on=["game_id", "team"],
                                                 how="left").fillna(0.0)
    per_tg = m["pen_off_epa"]  # EPA per team-game, offensive attribution
    per_tg_n = m["pen_off_n"]
    # per team-season mean penalty EPA per game (offensive attribution)
    ts = (m.groupby(["season", "team"])["pen_off_epa"].mean()
          .rename("mean_pen_epa_per_game").reset_index())
    team_season_spread = {
        "sd_across_teams_within_season": {
            str(s): float(g["mean_pen_epa_per_game"].std())
            for s, g in ts.groupby("season")},
        "best_team_season": ts.loc[ts["mean_pen_epa_per_game"].idxmax()].to_dict(),
        "worst_team_season": ts.loc[ts["mean_pen_epa_per_game"].idxmin()].to_dict(),
        "overall_range": [float(ts["mean_pen_epa_per_game"].min()),
                          float(ts["mean_pen_epa_per_game"].max())],
    }
    # combined two-team magnitude per game
    per_game = (m.groupby("game_id")["pen_off_epa"]
                .agg(lambda s: float(np.abs(s).sum())))
    return {
        "penalty_only_plays_total": int(len(pen)),
        "plays_per_season": {str(s): int(n) for s, n in
                             pen.groupby("season").size().items()},
        "epa_null_rows": int(pen["epa"].isna().sum()),
        "team_games": int(len(m)),
        "pen_plays_per_team_game": {
            "mean": float(per_tg_n.mean()), "median": float(per_tg_n.median()),
            "max": float(per_tg_n.max())},
        "pen_epa_per_team_game_off_attribution": {
            "mean": float(per_tg.mean()), "median": float(per_tg.median()),
            "sd": float(per_tg.std()),
            "p5": float(per_tg.quantile(0.05)),
            "p95": float(per_tg.quantile(0.95)),
            "share_abs_ge_3": float((per_tg.abs() >= 3).mean()),
        },
        "abs_pen_epa_both_teams_per_game": {
            "mean": float(per_game.mean()),
            "p95": float(per_game.quantile(0.95)),
        },
        "team_season_spread": team_season_spread,
    }


# --------------------------------------------------------------------------

ARMS = {
    "arm0": ("Baseline (weight 0, current code)", 0.0, False),
    "arm1": ("Penalty EPA at 100%, denominators unchanged", 1.0, False),
    "arm2": ("Penalty EPA at 50%, denominators unchanged", 0.5, False),
    "armR": ("ROBUSTNESS: 100% + penalty plays in denominators", 1.0, True),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="all",
                    choices=["all", *ARMS.keys()])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    print("[loading frames]")
    tg0 = load_team_games()
    qb_plays = load_qb_plays()
    pen = load_penalty_plays()
    agg = penalty_aggregates(pen)
    print(f"  team_games rows: {len(tg0)}; penalty-only plays: {len(pen)}")

    desc = descriptive_stats(tg0, agg, pen)
    (OUT / "descriptives.json").write_text(json.dumps(desc, indent=2, default=str))
    print("[descriptives written]")

    config_a = json.loads((BASE / "config_a.json").read_text())
    results: dict = {}
    results_path = OUT / "metrics.json"
    if results_path.exists():
        results = json.loads(results_path.read_text())

    order = list(ARMS) if args.arm == "all" else [args.arm]
    for name in order:
        label, weight, denom = ARMS[name]
        t0 = time.time()
        frame = tg0 if name == "arm0" else variant_frame(tg0, agg, weight, denom)
        df = walk_forward(frame, qb_plays)
        df.to_csv(OUT / f"per_game_{name}.csv", index=False)
        if name == "arm0":
            ver = verify_against_a(df, config_a)
            print("[arm0 verification]", "PASS" if ver["ok"] else "FAIL",
                  json.dumps(ver["abs_diffs"]))
            (OUT / "arm0_verification.json").write_text(
                json.dumps(ver, indent=2, default=str))
            if not ver["ok"]:
                print("STOP: Arm 0 does not reproduce Config A. "
                      "No other arm is trustworthy on this frame.")
                sys.exit(2)
        results[name] = {"label": label, **arm_metrics(df)}
        results_path.write_text(json.dumps(results, indent=2, default=str))
        o = results[name]["overall"]
        print(f"[{name}: {label}] n={o['games']} "
              f"marginRMSE={o['margin_rmse_ours']:.3f} (line {o['margin_rmse_line']:.3f}) "
              f"ATS={o['ats_pct']:.3f} {o['ats_wlp']} "
              f"totalRMSE={o['total_rmse_ours']:.3f} "
              f"OU={o['ou_pct']:.3f} {o['ou_wlp']} "
              f"[{time.time() - t0:.0f}s]")
    print("[done]")


if __name__ == "__main__":
    main()
