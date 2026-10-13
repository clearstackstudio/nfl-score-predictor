"""NFL special-teams inclusion — pre-registered test (2026-10-12).

Pre-registration: goals/ultimate-multi-sport-prediction-model/hidden_files/
special-teams-preregistration.md

Question: src/epa_ratings.load_team_games() builds ratings only from
pass/rush-attempt plays. Every special-teams play (punts, kickoffs,
field-goal attempts, extra points, and their returns) is excluded, so
kicking/punting/return quality contributes nothing to a team's rating.
Does folding ST EPA into the ratings help walk-forward prediction?

Design (fixed by the pre-registration; no search):
  Arm 0: baseline frame, load_team_games() as-is.
  Arm 1 (PRIMARY): ST EPA added to off/def EPA sums at full weight;
         play-count denominators unchanged (pass/rush counts only),
         mirroring the penalty study's primary construction.
  Arm 2 (ROBUSTNESS, labeled): as Arm 1, but ST plays are also counted
         in the denominators (true per-play averages over all included
         plays).
No damping weights are tested; if Arm 1 helps, a damping follow-up is
a separate study.

ST play operationalization (fixed in advance): nflverse play_type in
{"punt", "kickoff", "field_goal", "extra_point"} with epa populated
and posteam/defteam present. Verified on the 2021 parquet before
running: ST rows have zero epa/posteam/defteam nulls and ZERO overlap
with the pass/rush filter — disjoint by construction. The play's full
EPA is credited symmetrically (posteam -> offensive sum, defteam ->
defensive sum), exactly as pass/rush rows are treated; a return's
value stays inside its play's EPA. Penalty-flagged ST plays are
included once, as ST plays via their EPA (this does not revisit the
penalty study, which excluded them to isolate the penalty component).

Everything else (recency weighting, QB adjustment pool/formula,
thresholds, totals formula) is inherited unchanged from the live-EPA
backtest Config A: the walk-forward loop below is the penalty study's
replication of the baseline runner, verbatim except for the
team_games input. Grading functions are imported from the baseline
runner so semantics are shared.

One construction note, inherited from the penalty study's runner (the
named template for this study's primary arm): the loop's epa_const
calibration uses the passed frame's off_epa, i.e. the treated frame
in treated arms. The primary metrics (margin RMSE, ATS) do not
involve epa_const at all, so this choice cannot affect the verdict;
totals metrics are reported, not part of the bar.

Arm 0 must reproduce Config A bit-identically (checked with the
baseline runner's own verify_against_a); if it does not, this script
exits before any treated arm is trusted.

Adoption bar (pre-registered): adopt only if Arm 1 (1) improves
overall margin RMSE by >= 0.05, (2) improves or ties margin RMSE in
>= 3 of 4 seasons, and (3) does not worsen overall ATS.

Staged execution (per prior-study process lesson — a single long
process was killed mid-study by a runtime restart in a sibling run):
run stages in separate invocations; each writes its per-game CSV and
updates metrics.json immediately on completion.

  .venv-cfb/bin/python research/special_teams/run_special_teams.py --stage descr
  .venv-cfb/bin/python research/special_teams/run_special_teams.py --stage arm0
  .venv-cfb/bin/python research/special_teams/run_special_teams.py --stage arm1
  .venv-cfb/bin/python research/special_teams/run_special_teams.py --stage arm2

Measurement only: nothing in src/ or site/ is modified.
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
OUT = REPO / "research" / "special_teams"
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

ST_TYPES = ("punt", "kickoff", "field_goal", "extra_point")
ST_COLS = ["game_id", "week", "season", "posteam", "defteam",
           "epa", "play_type", "penalty"]


# --------------------------------------------------------------------------
# ST-play aggregates + frame variants (penalty-study construction)
# --------------------------------------------------------------------------

def load_st_plays() -> pd.DataFrame:
    """One row per special-teams play (see module docstring)."""
    frames = []
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=ST_COLS)
        st = pbp[pbp["play_type"].isin(ST_TYPES)
                 & pbp["epa"].notna()
                 & pbp["posteam"].notna()
                 & pbp["defteam"].notna()]
        frames.append(st)
    return pd.concat(frames, ignore_index=True)


def st_aggregates(st: pd.DataFrame) -> pd.DataFrame:
    """Per (game_id, team): ST EPA credited on offense (as posteam),
    charged on defense (as defteam), and play counts for each side."""
    off = (st.groupby(["game_id", "posteam"])["epa"]
           .agg(["sum", "count"]).reset_index()
           .rename(columns={"posteam": "team", "sum": "st_off_epa",
                            "count": "st_off_n"}))
    deff = (st.groupby(["game_id", "defteam"])["epa"]
            .agg(["sum", "count"]).reset_index()
            .rename(columns={"defteam": "team", "sum": "st_def_epa",
                             "count": "st_def_n"}))
    agg = off.merge(deff, on=["game_id", "team"], how="outer").fillna(0.0)
    return agg


def variant_frame(tg0: pd.DataFrame, agg: pd.DataFrame,
                  add_to_denom: bool) -> pd.DataFrame:
    """tg0 with ST EPA folded into the sums (row order, opp, and all
    other columns preserved from tg0 by construction)."""
    tg = tg0.copy()
    m = tg[["game_id", "team"]].merge(agg, on=["game_id", "team"],
                                      how="left")
    # merge(how='left') preserves left row order; assert alignment anyway
    assert (m["game_id"].values == tg["game_id"].values).all()
    assert (m["team"].values == tg["team"].values).all()
    tg["off_epa"] = tg["off_epa"] + m["st_off_epa"].fillna(0.0).to_numpy()
    tg["def_epa"] = tg["def_epa"] + m["st_def_epa"].fillna(0.0).to_numpy()
    if add_to_denom:
        tg["off_plays"] = (tg["off_plays"]
                           + m["st_off_n"].fillna(0).to_numpy())
        tg["def_plays"] = (tg["def_plays"]
                           + m["st_def_n"].fillna(0).to_numpy())
    tg["off_epa_play"] = tg["off_epa"] / tg["off_plays"]
    tg["def_epa_play"] = tg["def_epa"] / tg["def_plays"]
    return tg


# --------------------------------------------------------------------------
# Walk-forward loop: the penalty study's replication of the baseline
# runner, verbatim except for the team_games input.
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
# Metrics (same quantities as the sibling studies' tables)
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
# Descriptive statistics (pre-registered: reported regardless of outcome)
# --------------------------------------------------------------------------

def descriptive_stats(tg0: pd.DataFrame, agg: pd.DataFrame,
                      st: pd.DataFrame) -> dict:
    # |EPA| mass of the pass/rush pool (the current model's universe),
    # computed with the identical filter epa_ratings.load_team_games uses.
    pr_abs = 0.0
    pr_plays = 0
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=["epa", "pass_attempt", "rush_attempt",
                                       "posteam"])
        f = pbp[((pbp["pass_attempt"] == 1) | (pbp["rush_attempt"] == 1))
                & pbp["epa"].notna() & pbp["posteam"].notna()]
        pr_abs += float(f["epa"].abs().sum())
        pr_plays += int(len(f))
    st_abs = float(st["epa"].abs().sum())

    m = tg0[["game_id", "season", "team"]].merge(agg, on=["game_id", "team"],
                                                 how="left").fillna(0.0)
    m["net_st_epa"] = m["st_off_epa"] - m["st_def_epa"]  # benefit terms
    n_games = m["game_id"].nunique()

    # Combined absolute ST EPA per game: both teams' |posteam-attributed
    # ST EPA| summed per game (penalty-study construction).
    per_game_abs = (m.groupby("game_id")["st_off_epa"]
                    .agg(lambda s: float(np.abs(s).sum())))

    # Season-to-season persistence of team net ST EPA per game.
    season_team = m.groupby(["season", "team"]).agg(
        games=("game_id", "nunique"),
        net_st=("net_st_epa", "sum"),
        off_st=("st_off_epa", "sum"),
        def_benefit=("st_def_epa", lambda s: -s.sum()),  # positive = good
    ).reset_index()
    for c in ("net_st", "off_st", "def_benefit"):
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

    net_pg = season_team["net_st_pg"]
    best = season_team.loc[net_pg.idxmax()]
    worst = season_team.loc[net_pg.idxmin()]

    return {
        "frame": "ST plays: play_type in {punt, kickoff, field_goal, "
                 "extra_point}, epa populated, 2021-2024",
        "st_plays_total": int(len(st)),
        "st_plays_per_season": {str(s): int(n) for s, n in
                                st.groupby("season").size().items()},
        "st_plays_by_type": {str(t): int(n) for t, n in
                             st.groupby("play_type").size().items()},
        "st_epa_null_rows": int(st["epa"].isna().sum()),
        "st_penalty_flagged_rows": int((st["penalty"] == 1).sum()),
        "games_in_frame": int(n_games),
        "team_games": int(len(m)),
        "st_plays_per_game_both_teams": float(len(st) / n_games),
        "st_plays_per_team_game": {
            "posteam_attributed_mean": float(m["st_off_n"].mean()),
            "defteam_attributed_mean": float(m["st_def_n"].mean()),
            "total_involvements_mean": float((m["st_off_n"] + m["st_def_n"]).mean()),
        },
        "abs_epa_share": {
            "st_abs_epa": st_abs,
            "pass_rush_abs_epa": pr_abs,
            "st_share_of_pool_abs_epa": st_abs / (st_abs + pr_abs),
            "pass_rush_plays": pr_plays,
        },
        "st_epa_per_team_game": {
            "mean_abs_off_attribution": float(m["st_off_epa"].abs().mean()),
            "mean_abs_def_attribution": float(m["st_def_epa"].abs().mean()),
            "mean_net_benefit_terms": float(m["net_st_epa"].mean()),
            "sd_net_benefit_terms": float(m["net_st_epa"].std()),
        },
        "abs_st_epa_both_teams_per_game": {
            "mean": float(per_game_abs.mean()),
            "p95": float(per_game_abs.quantile(0.95)),
        },
        "persistence_net_st_epa_per_game": {
            "correlations": corr_series("net_st"),
            "off_component_correlations": corr_series("off_st"),
            "def_benefit_component_correlations": corr_series("def_benefit"),
            "team_season_net_st_epa_pg_sd": float(net_pg.std()),
            "team_season_net_st_epa_pg_range": [float(net_pg.min()),
                                                float(net_pg.max())],
            "best_team_season": {"season": int(best["season"]),
                                 "team": str(best["team"]),
                                 "net_st_epa_pg": float(best["net_st_pg"])},
            "worst_team_season": {"season": int(worst["season"]),
                                  "team": str(worst["team"]),
                                  "net_st_epa_pg": float(worst["net_st_pg"])},
        },
    }


# --------------------------------------------------------------------------
# Staged execution
# --------------------------------------------------------------------------

ARMS = {
    "arm0": ("Baseline (current model, pass/rush only)", False),
    "arm1": ("PRIMARY: ST EPA in sums, denominators unchanged", False),
    "arm2": ("ROBUSTNESS: ST EPA in sums + ST plays in denominators", True),
}


def _load_metrics() -> dict:
    p = OUT / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _save_metrics(results: dict) -> None:
    (OUT / "metrics.json").write_text(json.dumps(results, indent=2, default=str))


def _frames():
    tg0 = load_team_games()
    st = load_st_plays()
    agg = st_aggregates(st)
    return tg0, st, agg


def stage_descr() -> None:
    print("[descr] building frames + descriptive stats ...", flush=True)
    tg0, st, agg = _frames()
    print(f"      team_games rows: {len(tg0)}; ST plays: {len(st)}", flush=True)
    desc = descriptive_stats(tg0, agg, st)
    (OUT / "descriptives.json").write_text(json.dumps(desc, indent=2, default=str))
    print("[descr] saved descriptives.json", flush=True)
    print(json.dumps({k: desc[k] for k in
                      ("st_plays_total", "st_plays_per_game_both_teams",
                       "abs_epa_share")}, indent=2, default=str), flush=True)


def stage_arm(name: str) -> None:
    label, add_denom = ARMS[name]
    print(f"[{name}] {label}", flush=True)
    tg0, st, agg = _frames()
    qb_plays = load_qb_plays()
    frame = tg0 if name == "arm0" else variant_frame(tg0, agg, add_denom)
    t0 = time.time()
    df = walk_forward(frame, qb_plays)
    df.to_csv(OUT / f"per_game_{name}.csv", index=False)
    if name == "arm0":
        config_a = json.loads((BASE / "config_a.json").read_text())
        ver = verify_against_a(df, config_a)
        (OUT / "arm0_verification.json").write_text(
            json.dumps(ver, indent=2, default=str))
        print("[arm0 verification]", "PASS" if ver["ok"] else "FAIL",
              json.dumps(ver["abs_diffs"]), flush=True)
        if not ver["ok"]:
            print("STOP: Arm 0 does not reproduce Config A (per pre-reg). "
                  "No treated arm is trustworthy on this frame.")
            sys.exit(2)
    results = _load_metrics()
    results[name] = {"label": label, **arm_metrics(df)}
    _save_metrics(results)
    o = results[name]["overall"]
    print(f"[{name}] n={o['games']} "
          f"marginRMSE={o['margin_rmse_ours']:.3f} (line {o['margin_rmse_line']:.3f}) "
          f"ATS={o['ats_pct']:.4f} {o['ats_wlp']} "
          f"totalRMSE={o['total_rmse_ours']:.3f} "
          f"OU={o['ou_pct']:.4f} {o['ou_wlp']} "
          f"[{time.time() - t0:.0f}s] — saved", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["descr", "arm0", "arm1", "arm2"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.stage == "descr":
        stage_descr()
    else:
        stage_arm(args.stage)
