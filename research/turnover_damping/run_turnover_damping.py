"""Turnover-EPA damping test (pre-registered 2026-10-12).

Pre-registration: goals/ultimate-multi-sport-prediction-model/hidden_files/
turnover-damping-preregistration.md

Design (per pre-reg):
  - Frame identical to the 2026-10-12 live-EPA backtest: walk-forward
    2021-2024, same games, closing lines as benchmark only.
  - A turnover play is a play inside the current pass/rush filter with
    interception == 1 or fumble_lost == 1 (nflverse PBP). Its EPA is
    scaled by w in {1.0, 0.5, 0.25} in the team-ratings aggregation
    (load_team_games equivalent), symmetrically for off/def sums (both
    derive from the same play rows). Play counts are NOT scaled.
  - QB adjustment stays as-is in the primary arms. One labeled robustness
    arm (w=0.5 + QB pool damped) also scales turnover-play EPA inside
    load_qb_plays.
  - No wind, no circuit breaker, no threshold changes.

Implementation notes:
  - The walk-forward loop is the EPA backtest's Part B replication loop
    (research/epa_live_backtest/run_epa_live_backtest.py) copied verbatim,
    minus venue/wind emission, with team_games parametrized. Arm 0
    (w=1.0) is verified bit-identical against that study's Config A
    before any other arm is trusted.
  - One documented interpretation: the loop's epa_const calibration uses
    each completed game's UNDAMPED combined offensive EPA
    (team_games.iloc[idxs]["off_epa"].sum() on the undamped frame).
    Rationale: the pre-reg holds the totals formula exactly as in
    Config A and scopes damping to the ratings aggregation; epa_const
    is a totals-formula calibration constant, not a rating. The
    primary metrics (margin RMSE, ATS) do not involve epa_const at all
    and are identical under either interpretation. At w=1.0 the two
    interpretations coincide, so Arm 0 verification is unaffected.

Measurement only: nothing in src/ or site/ is modified.

Run with the repo venv:
  .venv-cfb/bin/python research/turnover_damping/run_turnover_damping.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "turnover_damping"
BASE = REPO / "research" / "epa_live_backtest"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(BASE))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from backtest import closing_home_spread, load_games  # noqa: E402
import epa_ratings as er  # noqa: E402
from epa_ratings import (  # noqa: E402
    ABBR_TO_FULL, CARRYOVER, DATA, HOME_EDGE_PTS, PBP_YEARS, PLAYS_PER_GAME,
    adjusted_ratings, load_qb_plays, load_team_games, qb_adjustments,
    week_int,
)
import run_epa_live_backtest as basemod  # noqa: E402

PBP_COLS = ["game_id", "week", "season", "posteam", "defteam", "epa",
            "pass_attempt", "rush_attempt", "home_team", "away_team",
            "interception", "fumble_lost"]


# --------------------------------------------------------------------------
# Damped data loaders (mirror src/epa_ratings.py, with EPA scaling)
# --------------------------------------------------------------------------

def _scale_to_epa(plays: pd.DataFrame, w: float) -> pd.DataFrame:
    """Scale EPA of turnover plays (interception==1 or fumble_lost==1) by w.
    At w=1.0, epa * 1.0 is exact, so the frame is identical to baseline."""
    if w == 1.0:
        return plays
    to = (plays["interception"] == 1) | (plays["fumble_lost"] == 1)
    plays = plays.copy()
    plays.loc[to, "epa"] = plays.loc[to, "epa"] * w
    return plays


def load_team_games_damped(w: float, years: list[int] | None = None) -> pd.DataFrame:
    """Verbatim copy of epa_ratings.load_team_games, plus interception /
    fumble_lost columns and turnover-EPA scaling before aggregation."""
    years = years or PBP_YEARS
    frames = []
    for year in years:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=PBP_COLS)
        plays = pbp[
            ((pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1))
            & pbp["epa"].notna()
            & pbp["posteam"].notna()
        ]
        plays = _scale_to_epa(plays, w)
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
    tg = pd.concat(frames, ignore_index=True)
    return tg.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def load_qb_plays_damped(w: float, years: list[int] | None = None) -> pd.DataFrame:
    """Verbatim copy of epa_ratings.load_qb_plays, plus turnover-EPA
    scaling. Used ONLY by the labeled robustness arm."""
    years = years or PBP_YEARS
    frames = []
    for year in years:
        pbp = pd.read_parquet(
            DATA / f"play_by_play_{year}.parquet",
            columns=["game_id", "week", "season", "posteam", "passer",
                     "passer_id", "pass_attempt", "sack", "epa",
                     "interception", "fumble_lost"])
        q = pbp[pbp["passer_id"].notna() & pbp["epa"].notna()
                & ((pbp["pass_attempt"] == 1) | (pbp["sack"] == 1))]
        q = _scale_to_epa(q, w)
        frames.append(
            q[["game_id", "week", "season", "posteam", "passer_id", "epa"]])
    qb = pd.concat(frames, ignore_index=True)
    return qb.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


# --------------------------------------------------------------------------
# Walk-forward (Part B replication loop, venue/wind emission removed;
# epa_const calibration reads the UNDAMPED frame — see module docstring)
# --------------------------------------------------------------------------

def walk_forward(team_games: pd.DataFrame, qb_plays: pd.DataFrame,
                 undamped_tg: pd.DataFrame) -> pd.DataFrame:
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

        # epa_const calibration: UNDAMPED combined offensive EPA (see
        # module docstring). Row indices align: damping changes values
        # only, never rows or order.
        game_epa = undamped_tg.iloc[idxs]["off_epa"].sum()
        epa_const_hist.append(actual_total - game_epa)

        off2, def2, _pace = adjusted_ratings(team_games, idxs[-1] + 1, season, prior)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Descriptive statistics (pre-reg context, not decision inputs)
# --------------------------------------------------------------------------

def descriptive_stats() -> dict:
    frames = []
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=PBP_COLS)
        plays = pbp[
            ((pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1))
            & pbp["epa"].notna()
            & pbp["posteam"].notna()
        ]
        frames.append(plays)
    p = pd.concat(frames, ignore_index=True)
    p["is_to"] = (p["interception"] == 1) | (p["fumble_lost"] == 1)
    to = p[p["is_to"]]
    n_games = p["game_id"].nunique()

    stats: dict = {
        "frame": "filtered PBP plays (pass/rush attempts, epa present), 2021-2024",
        "plays": int(len(p)),
        "games_in_pbp": int(n_games),
        "to_plays": int(len(to)),
        "to_plays_per_game": float(len(to) / n_games),
        "to_int_flagged": int((p["interception"] == 1).sum()),
        "to_fumble_lost_flagged": int((p["fumble_lost"] == 1).sum()),
        "to_both_flags": int(((p["interception"] == 1)
                              & (p["fumble_lost"] == 1)).sum()),
        "to_mean_epa": float(to["epa"].mean()),
        "to_mean_epa_int": float(p[p["interception"] == 1]["epa"].mean()),
        "to_mean_epa_fumble_lost": float(p[p["fumble_lost"] == 1]["epa"].mean()),
        "non_to_mean_epa": float(p[~p["is_to"]]["epa"].mean()),
        "abs_epa_share": float(to["epa"].abs().sum() / p["epa"].abs().sum()),
    }

    # Per team-game turnover EPA (offense: own TO plays; defense: TO plays
    # faced, in raw epa terms where negative = good for the defense).
    off_to = (to.groupby(["game_id", "posteam"])["epa"].sum()
              .rename("off_to_epa"))
    def_to = (to.groupby(["game_id", "defteam"])["epa"].sum()
              .rename("def_to_epa"))
    tg = load_team_games()
    m = tg.merge(off_to.reset_index().rename(columns={"posteam": "team"}),
                 on=["game_id", "team"], how="left")
    m = m.merge(def_to.reset_index().rename(columns={"defteam": "team"}),
                on=["game_id", "team"], how="left")
    m[["off_to_epa", "def_to_epa"]] = m[["off_to_epa", "def_to_epa"]].fillna(0.0)
    stats["team_game"] = {
        "mean_abs_off_to_epa": float(m["off_to_epa"].abs().mean()),
        "mean_abs_def_to_epa": float(m["def_to_epa"].abs().mean()),
        "mean_abs_off_epa": float(m["off_epa"].abs().mean()),
        "mean_abs_def_epa": float(m["def_epa"].abs().mean()),
        "mean_off_to_epa": float(m["off_to_epa"].mean()),
        "mean_def_to_epa": float(m["def_to_epa"].mean()),
    }

    # Season-to-season persistence of team turnover EPA (per game).
    ms = m.copy()
    ms["net_to_epa"] = ms["off_to_epa"] - ms["def_to_epa"]  # benefit terms
    season_team = ms.groupby(["season", "team"]).agg(
        games=("game_id", "nunique"),
        net_to=("net_to_epa", "sum"),
        giveaway=("off_to_epa", "sum"),     # negative = costly
        takeaway_benefit=("def_to_epa", lambda s: -s.sum()),  # positive = good
    ).reset_index()
    for c in ("net_to", "giveaway", "takeaway_benefit"):
        season_team[c + "_pg"] = season_team[c] / season_team["games"]

    def corr_series(col: str) -> dict:
        piv = season_team.pivot(index="team", columns="season",
                                values=col + "_pg")
        out = {}
        rs = []
        for a, b in ((2021, 2022), (2022, 2023), (2023, 2024)):
            r = float(piv[a].corr(piv[b]))
            out[f"{a}->{b}"] = r
            rs.append(r)
        out["mean_consecutive_r"] = float(np.mean(rs))
        return out

    stats["persistence"] = {
        "net_to_epa_per_game": corr_series("net_to"),
        "giveaway_epa_per_game": corr_series("giveaway"),
        "takeaway_benefit_per_game": corr_series("takeaway_benefit"),
        "team_season_net_to_epa_pg_sd": float(season_team["net_to_pg"].std()),
        "team_season_net_to_epa_pg_range": [
            float(season_team["net_to_pg"].min()),
            float(season_team["net_to_pg"].max())],
    }
    return stats


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def arm_block(df: pd.DataFrame) -> dict:
    return {
        "overall": basemod.block_metrics(df, "our_total", None),
        "per_season": {str(s): basemod.block_metrics(g, "our_total", None)
                       for s, g in df.groupby("season")},
    }


def _load_results() -> dict:
    p = OUT / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _save_results(results: dict) -> None:
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2, default=str))


def stage_arm0() -> None:
    config_a = json.loads((BASE / "config_a.json").read_text())
    print("[arm0] building undamped team_games (baseline loader) ...", flush=True)
    tg0 = load_team_games()
    qb0 = load_qb_plays()
    print("[arm0] structural check: damped(w=1.0) == baseline ...", flush=True)
    tg_w1 = load_team_games_damped(1.0)
    same = tg_w1.equals(tg0)
    print(f"      frames equal: {same}", flush=True)
    if not same:
        print("STOP: damped loader at w=1.0 does not reproduce baseline frame.")
        sys.exit(2)
    results = _load_results()
    results["structural_check_w1_equals_baseline"] = bool(same)
    print("[arm0] walk-forward (w=1.00) + verification vs Config A ...",
          flush=True)
    t0 = time.time()
    df0 = walk_forward(tg_w1, qb0, tg0)
    ver = basemod.verify_against_a(df0, config_a)
    print(f"      {len(df0)} games in {time.time() - t0:.0f}s; verification: "
          f"{'PASS' if ver['ok'] else 'FAIL'} {json.dumps(ver['abs_diffs'])}",
          flush=True)
    results["arm0_verification"] = ver
    if not ver["ok"]:
        _save_results(results)
        print("STOP: Arm 0 does not reproduce Config A (per pre-reg).")
        sys.exit(2)
    results["arm_w1.00"] = arm_block(df0)
    df0.to_csv(OUT / "per_game_w1.00.csv", index=False)
    _save_results(results)
    print("[arm0] saved to metrics.json", flush=True)


def stage_arm(w: float) -> None:
    print(f"[arm w={w:.2f}] walk-forward ...", flush=True)
    tg0 = load_team_games()
    qb0 = load_qb_plays()
    t0 = time.time()
    tg_w = load_team_games_damped(w)
    df_w = walk_forward(tg_w, qb0, tg0)
    results = _load_results()
    results[f"arm_w{w:.2f}"] = arm_block(df_w)
    df_w.to_csv(OUT / f"per_game_w{w:.2f}.csv", index=False)
    _save_results(results)
    o = results[f"arm_w{w:.2f}"]["overall"]
    print(f"      {len(df_w)} games in {time.time() - t0:.0f}s; "
          f"margin RMSE {o['margin_rmse_ours']:.3f}, "
          f"ATS {o['ats_pct']:.3f}, total RMSE {o['total_rmse_ours']:.3f}, "
          f"OU {o['ou_pct']:.3f} — saved", flush=True)


def stage_robust() -> None:
    print("[robustness] w=0.50 + QB pool damped (labeled, not primary) ...",
          flush=True)
    tg0 = load_team_games()
    t0 = time.time()
    tg_r = load_team_games_damped(0.5)
    qb_r = load_qb_plays_damped(0.5)
    df_r = walk_forward(tg_r, qb_r, tg0)
    results = _load_results()
    results["robustness_w0.50_qb_damped"] = arm_block(df_r)
    df_r.to_csv(OUT / "per_game_robustness_w0.50_qb.csv", index=False)
    _save_results(results)
    o = results["robustness_w0.50_qb_damped"]["overall"]
    print(f"      {len(df_r)} games in {time.time() - t0:.0f}s; "
          f"margin RMSE {o['margin_rmse_ours']:.3f}, ATS {o['ats_pct']:.3f}, "
          f"total RMSE {o['total_rmse_ours']:.3f}, OU {o['ou_pct']:.3f} — saved",
          flush=True)


def stage_descr() -> None:
    print("[descriptives] turnover-play statistics ...", flush=True)
    results = _load_results()
    results["descriptives"] = descriptive_stats()
    _save_results(results)
    print("[descriptives] saved", flush=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage",
                    choices=["arm0", "w050", "w025", "robust", "descr"],
                    required=True)
    args = ap.parse_args()
    if args.stage == "arm0":
        stage_arm0()
    elif args.stage == "w050":
        stage_arm(0.5)
    elif args.stage == "w025":
        stage_arm(0.25)
    elif args.stage == "robust":
        stage_robust()
    elif args.stage == "descr":
        stage_descr()
