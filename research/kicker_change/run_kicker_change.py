"""NFL kicker-change term — pre-registered test (2026-10-12).

Pre-registration: goals/ultimate-multi-sport-prediction-model/hidden_files/
kicker-change-preregistration.md

Question: the special-teams study found team-level ST EPA does not
persist (r ~ +0.12) and folding ST plays into the ratings is a clean
null. This test asks the distinct personnel question: when a team
changes kickers, do its games come out systematically different from
the model's walk-forward expectation — a priceable kicker-change
effect analogous to the validated star-QB effect?

Design (fixed by the pre-registration; no search):
  - Frame: Config A walk-forward per-game predictions, reused from the
    special-teams study's verified Arm 0 (per_game_arm0.csv, whose
    arm0_verification.json shows bit-identical reproduction of Config
    A). Stage 'baseline' re-verifies that CSV against config_a.json
    using the baseline runner's own grading functions; if it fails,
    every later stage refuses to run.
  - Primary kicker (per team-game): kicker_player_id with the most
    FG+XP attempts for that team in that game (kickoffs excluded).
  - Change game: primary kicker differs from the primary over the
    team's previous 4 team-games (majority holder of attempts across
    those games; ties -> most recent game's primary among the tied).
  - Quality direction: incoming kicker's career-to-date FG-play EPA
    per attempt entering the game minus the outgoing kicker's, each
    requiring >= 10 career FG attempts to classify.
  - Metric: margin residual from the flagged team's perspective and
    the game's total residual, mean / 95% CI / n, for (a) all change
    games pooled, (b) split by quality direction, (c) second game
    with the new kicker.

Disclosed data notes (deviations/implementation choices the
pre-registration leaves implicit):
  - Career-to-date is within the available PBP window (2021-2024);
    play-by-play files before 2021 are not in data/, so veteran
    kickers' careers are left-truncated at 2021 and early-2021
    classifications rest on in-window attempts only.
  - 6 of 9,574 FG+XP plays have a null kicker_player_id; they cannot
    be attributed to a kicker and are excluded from attribution.
  - Within-game primary ties (equal FG+XP attempts): primary is the
    tied kicker with more FG attempts, then lowest kicker_player_id
    (deterministic). Ties are counted and reported.
  - A change flag requires at least one attributed attempt in the
    previous-4 window (else no previous primary exists: unflaggable);
    a team-game with zero attributed FG+XP attempts has no primary
    kicker and is unflaggable. Both counts are disclosed.
  - The previous-4 window spans season boundaries (a team's previous
    4 team-games, including playoffs, in chronological order).
  - "Second game with the new kicker": the flagged team's next
    team-game, if it is in the 1,107-game frame and its primary
    kicker is still the incoming kicker. Overlap with set (a) is
    possible (the 4-game majority window can lag a real change) and
    is counted and disclosed.
  - Consecutive-season persistence uses kickers with >= 10 FG
    attempts in both seasons (the pre-registration's classification
    threshold); the split-half test requires >= 15 attempts in each
    half, i.e. >= 30 career in-window FG attempts.

Adoption bar (pre-registered): a candidate term requires ALL of
(1) pooled or direction-split mean margin residual >= 1.0 pt in the
direction the quality split predicts, (2) its 95% CI excludes zero,
(3) sign consistent between pooled and direction split. Inconclusive
(wide CI straddling zero) is a legitimate verdict.

Staged execution (per prior-study process lesson):
  .venv-cfb/bin/python research/kicker_change/run_kicker_change.py --stage baseline
  .venv-cfb/bin/python research/kicker_change/run_kicker_change.py --stage build
  .venv-cfb/bin/python research/kicker_change/run_kicker_change.py --stage descr
  .venv-cfb/bin/python research/kicker_change/run_kicker_change.py --stage test

Measurement only: nothing in src/ or site/ is modified.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from bisect import bisect_left
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "kicker_change"
BASE = REPO / "research" / "epa_live_backtest"
ST = REPO / "research" / "special_teams"
sys.path.insert(0, str(SRC))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

from epa_ratings import DATA, PBP_YEARS  # noqa: E402

# Grading imported from the baseline study's runner so the baseline
# check grades IDENTICALLY to Config A by construction.
_spec = importlib.util.spec_from_file_location(
    "epa_live_runner", BASE / "run_epa_live_backtest.py")
_base_runner = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base_runner)
grade_ats = _base_runner.grade_ats
grade_ou = _base_runner.grade_ou

KICK_TYPES = ("field_goal", "extra_point")
KICK_COLS = ["game_id", "week", "season", "game_date", "play_id",
             "posteam", "home_team", "away_team", "play_type",
             "kicker_player_id", "kicker_player_name", "epa"]


# --------------------------------------------------------------------------
# Stage: baseline — re-verify the reused Config A predictions
# --------------------------------------------------------------------------

def stage_baseline() -> None:
    df = pd.read_csv(ST / "per_game_arm0.csv")
    config_a = json.loads((BASE / "config_a.json").read_text())
    n = len(df)
    w, l, p = grade_ats(df)
    ow, ol, op = grade_ou(df, "our_total", None)[:3]
    got = {
        "games": n,
        "straight_up_pct": float(
            ((df["our_margin"] > 0) == (df["actual_margin"] > 0)).mean()),
        "our_margin_rmse": float(np.sqrt(
            ((df["our_margin"] - df["actual_margin"]) ** 2).mean())),
        "line_margin_rmse": float(np.sqrt(
            ((df["line_margin"] - df["actual_margin"]) ** 2).mean())),
        "ats": [int(w), int(l), int(p)],
        "our_total_rmse": float(np.sqrt(
            ((df["our_total"] - df["actual_total"]) ** 2).mean())),
        "line_total_rmse": float(np.sqrt(
            ((df["line_total"] - df["actual_total"]) ** 2).mean())),
        "ou": [int(ow), int(ol), int(op)],
    }
    diffs = {k: (abs(got[k] - config_a[k]) if not isinstance(got[k], list)
                 else max(abs(a - b) for a, b in zip(got[k], config_a[k])))
             for k in got}
    ok = all(d < 1e-9 for d in diffs.values())
    ver = {"ok": bool(ok), "recomputed": got, "abs_diffs_vs_config_a": diffs,
           "targets": {"games": 1107, "margin_rmse": 14.444,
                       "ats": [399, 441, 26], "ats_pct": 0.4750,
                       "total_rmse": 15.169, "ou": [376, 386, 13],
                       "ou_pct": 0.4934}}
    (OUT / "baseline_verification.json").write_text(
        json.dumps(ver, indent=2, default=str))
    df.to_csv(OUT / "per_game_baseline.csv", index=False)
    print("[baseline]", "PASS" if ok else "FAIL",
          f"games={n} marginRMSE={got['our_margin_rmse']:.4f} "
          f"ATS={got['ats']} totalRMSE={got['our_total_rmse']:.4f} "
          f"OU={got['ou']}", flush=True)
    if not ok:
        print("STOP: baseline does not reproduce Config A; no result "
              "from this frame is trustworthy (per pre-reg).")
        sys.exit(2)


def _require_baseline() -> None:
    p = OUT / "baseline_verification.json"
    if not p.exists() or not json.loads(p.read_text())["ok"]:
        print("STOP: run --stage baseline first and pass it.")
        sys.exit(2)


# --------------------------------------------------------------------------
# Stage: build — games, team-game sequence, kick plays, flags
# --------------------------------------------------------------------------

def _load_kick_plays() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (games, kick plays). Games: one row per game 2021-2024
    with a chronological order key. Kick plays: FG+XP rows."""
    games_frames, kick_frames = [], []
    for year in PBP_YEARS:
        pbp = pd.read_parquet(DATA / f"play_by_play_{year}.parquet",
                              columns=KICK_COLS)
        g = (pbp[["game_id", "season", "week", "game_date",
                  "home_team", "away_team"]]
             .drop_duplicates("game_id"))
        games_frames.append(g)
        k = pbp[pbp["play_type"].isin(KICK_TYPES)].copy()
        kick_frames.append(k)
    games = pd.concat(games_frames, ignore_index=True)
    games["game_date"] = games["game_date"].astype(str)
    games["okey"] = list(zip(games["season"], games["week"],
                             games["game_date"], games["game_id"]))
    kicks = pd.concat(kick_frames, ignore_index=True)
    kicks["game_date"] = kicks["game_date"].astype(str)
    kicks = kicks.merge(games[["game_id", "okey"]], on="game_id",
                        how="left")
    return games, kicks


def stage_build() -> None:
    _require_baseline()
    games, kicks = _load_kick_plays()
    n_kick_rows = len(kicks)
    kicks = kicks[kicks["kicker_player_id"].notna()].copy()
    n_null_id = n_kick_rows - len(kicks)
    print(f"[build] games={len(games)} kick plays={n_kick_rows} "
          f"(null kicker id excluded: {n_null_id})", flush=True)

    # --- team-game sequence -------------------------------------------
    home = games[["game_id", "okey", "season", "week",
                  "home_team"]].rename(columns={"home_team": "team"})
    home["is_home"] = True
    away = games[["game_id", "okey", "season", "week",
                  "away_team"]].rename(columns={"away_team": "team"})
    away["is_home"] = False
    tg = pd.concat([home, away], ignore_index=True)
    tg = tg.sort_values(["team", "okey"]).reset_index(drop=True)
    tg["seq"] = tg.groupby("team").cumcount()

    # --- attempts per (game, team, kicker) -----------------------------
    kicks["team"] = kicks["posteam"]
    att = (kicks.groupby(["game_id", "team", "kicker_player_id"])
           .agg(n_att=("play_type", "size"),
                n_fg=("play_type", lambda s: int((s == "field_goal").sum())),
                name=("kicker_player_name", "first"))
           .reset_index())

    # --- primary kicker per team-game ----------------------------------
    att_sorted = att.sort_values(
        ["game_id", "team", "n_att", "n_fg", "kicker_player_id"],
        ascending=[True, True, False, False, True])
    primary = att_sorted.drop_duplicates(["game_id", "team"],
                                         keep="first").copy()
    # within-game ties at the max attempt count
    mx = att.groupby(["game_id", "team"])["n_att"].transform("max")
    tie_games = (att[att["n_att"] == mx]
                 .groupby(["game_id", "team"]).size())
    n_tie_games = int((tie_games > 1).sum())
    primary = primary.rename(columns={"kicker_player_id": "primary_id",
                                      "name": "primary_name"})
    tg = tg.merge(primary[["game_id", "team", "primary_id",
                           "primary_name"]],
                  on=["game_id", "team"], how="left")
    tg["has_primary"] = tg["primary_id"].notna()

    # attempts lookup: (game_id, team) -> {kicker: n_att}
    att_map: dict[tuple, dict] = {}
    for r in att.itertuples():
        att_map.setdefault((r.game_id, r.team), {})[r.kicker_player_id] \
            = int(r.n_att)

    # --- previous-4 window primary + change flags -----------------------
    rows = []
    tg_by_team = {t: g.reset_index(drop=True)
                  for t, g in tg.groupby("team")}
    for team, g in tg_by_team.items():
        prim = g["primary_id"].tolist()
        for i, r in g.iterrows():
            rec = {"game_id": r["game_id"], "season": int(r["season"]),
                   "week": int(r["week"]), "team": team,
                   "is_home": bool(r["is_home"]),
                   "primary_id": r["primary_id"],
                   "primary_name": r["primary_name"],
                   "flag_status": None, "outgoing_id": None}
            if not r["has_primary"]:
                rec["flag_status"] = "unflaggable_zero_attempts"
                rows.append(rec)
                continue
            window = g.iloc[max(0, i - 4):i]
            wcounts: dict[str, int] = {}
            for gid in window["game_id"]:
                for kid, n in att_map.get((gid, team), {}).items():
                    wcounts[kid] = wcounts.get(kid, 0) + n
            if not wcounts:
                rec["flag_status"] = "unflaggable_no_previous_primary"
                rows.append(rec)
                continue
            top = max(wcounts.values())
            tied = [k for k, v in wcounts.items() if v == top]
            if len(tied) == 1:
                outgoing = tied[0]
            else:
                outgoing = None
                for j in range(len(window) - 1, -1, -1):
                    pj = window.iloc[j]["primary_id"]
                    if pj in tied:
                        outgoing = pj
                        break
                if outgoing is None:  # no tied kicker was a game primary
                    outgoing = sorted(tied)[0]
            rec["outgoing_id"] = outgoing
            rec["flag_status"] = ("change" if r["primary_id"] != outgoing
                                  else "same")
            rows.append(rec)
    flags = pd.DataFrame(rows)

    # --- career FG EPA/attempt entering each game -----------------------
    fg = kicks[kicks["play_type"] == "field_goal"].copy()
    fg_game = (fg.groupby(["kicker_player_id", "game_id", "okey"])
               .agg(fg_epa=("epa", "sum"), fg_n=("epa", "size"))
               .reset_index().sort_values("okey"))
    career: dict[str, tuple[list, list, list]] = {}
    for kid, grp in fg_game.groupby("kicker_player_id"):
        keys = list(grp["okey"])
        cs = np.concatenate([[0.0], np.cumsum(grp["fg_epa"].to_numpy())])
        cn = np.concatenate([[0], np.cumsum(grp["fg_n"].to_numpy())])
        career[kid] = (keys, list(cs), list(cn))

    def career_before(kid: str, okey) -> tuple[float, int]:
        if kid not in career:
            return 0.0, 0
        keys, cs, cn = career[kid]
        idx = bisect_left(keys, okey)
        return float(cs[idx]), int(cn[idx])

    okey_map = dict(zip(games["game_id"], games["okey"]))
    name_map = (kicks.drop_duplicates("kicker_player_id")
                .set_index("kicker_player_id")["kicker_player_name"]
                .to_dict())

    def quality(row) -> tuple:
        if row["flag_status"] != "change":
            return (np.nan, np.nan, np.nan, "n/a")
        okey = okey_map[row["game_id"]]
        in_sum, in_n = career_before(row["primary_id"], okey)
        out_sum, out_n = career_before(row["outgoing_id"], okey)
        if in_n < 10 or out_n < 10:
            return (in_sum / in_n if in_n else np.nan,
                    out_sum / out_n if out_n else np.nan,
                    np.nan, "unclassified")
        diff = in_sum / in_n - out_sum / out_n
        cls = ("incoming_better" if diff > 0 else
               "incoming_worse" if diff < 0 else "unclassified")
        return (in_sum / in_n, out_sum / out_n, diff, cls)

    q = flags.apply(quality, axis=1, result_type="expand")
    flags["in_career_fg_epa_att"] = q[0]
    flags["out_career_fg_epa_att"] = q[1]
    flags["quality_diff"] = q[2]
    flags["quality_class"] = q[3]
    flags["outgoing_name"] = flags["outgoing_id"].map(name_map)

    flags.to_csv(OUT / "flags.csv", index=False)
    kicks.to_csv(OUT / "kick_plays.csv", index=False)
    counts = {
        "games_total": int(len(games)),
        "team_games_total": int(len(flags)),
        "null_kicker_id_plays_excluded": int(n_null_id),
        "within_game_primary_tie_games": n_tie_games,
        "flag_status_counts": {k: int(v) for k, v in
                               flags["flag_status"].value_counts().items()},
        "change_games_all_pbp": int((flags["flag_status"] == "change").sum()),
        "change_quality_class_counts": {
            k: int(v) for k, v in flags.loc[
                flags["flag_status"] == "change", "quality_class"]
            .value_counts().items()},
    }
    (OUT / "build_counts.json").write_text(json.dumps(counts, indent=2))
    print("[build] saved flags.csv / kick_plays.csv / build_counts.json",
          flush=True)
    print(json.dumps(counts, indent=2), flush=True)


# --------------------------------------------------------------------------
# Stage: descr — kicker-level persistence descriptives
# --------------------------------------------------------------------------

def stage_descr() -> None:
    _require_baseline()
    kicks = pd.read_csv(OUT / "kick_plays.csv")
    fg = kicks[kicks["play_type"] == "field_goal"].copy()
    # Chronological attempt order per kicker (the CSV's tuple 'okey'
    # column does not survive serialization; sort on its components).
    fg = fg.sort_values(["kicker_player_id", "season", "week",
                         "game_date", "game_id", "play_id"])

    # Split-half: first vs second half of each kicker's FG attempts.
    halves = []
    for kid, grp in fg.groupby("kicker_player_id"):
        t = len(grp)
        h1 = grp.iloc[: t // 2]
        h2 = grp.iloc[t // 2:]
        if len(h1) >= 15 and len(h2) >= 15:
            halves.append({
                "kicker": kid,
                "name": grp["kicker_player_name"].iloc[0],
                "n1": len(h1), "n2": len(h2),
                "epa_att_h1": float(h1["epa"].mean()),
                "epa_att_h2": float(h2["epa"].mean()),
            })
    hdf = pd.DataFrame(halves)
    split_half = {
        "n_kickers": int(len(hdf)),
        "r": float(hdf["epa_att_h1"].corr(hdf["epa_att_h2"]))
        if len(hdf) >= 3 else None,
        "mean_n_per_half": float(hdf[["n1", "n2"]].mean().mean())
        if len(hdf) else None,
    }

    # Consecutive-season correlations (>= 10 FG attempts both seasons).
    ks = (fg.groupby(["kicker_player_id", "season"])
          .agg(n=("epa", "size"), epa_att=("epa", "mean"),
               name=("kicker_player_name", "first"))
          .reset_index())
    pairs = {}
    all_pairs = []
    for a, b in ((2021, 2022), (2022, 2023), (2023, 2024)):
        pa = ks[(ks["season"] == a) & (ks["n"] >= 10)]
        pb = ks[(ks["season"] == b) & (ks["n"] >= 10)]
        m = pa.merge(pb, on="kicker_player_id", suffixes=("_a", "_b"))
        r = float(m["epa_att_a"].corr(m["epa_att_b"])) if len(m) >= 3 \
            else None
        pairs[f"{a}->{b}"] = {"n_kickers": int(len(m)), "r": r}
        all_pairs += [r] if r is not None else []
    season_corr = {"pairs": pairs,
                   "mean_consecutive_r": float(np.mean(all_pairs))
                   if all_pairs else None}

    # Season-to-season within-kicker spread context: overall volume.
    vol = {
        "fg_plays_total": int(len(fg)),
        "xp_plays_total": int((kicks["play_type"] == "extra_point").sum()),
        "distinct_kickers_fg": int(fg["kicker_player_id"].nunique()),
        "fg_epa_per_attempt_overall": float(fg["epa"].mean()),
        "fg_epa_per_attempt_sd_across_kickers_min15": float(
            fg.groupby("kicker_player_id")["epa"]
            .agg(["mean", "size"]).query("size >= 15")["mean"].std()),
    }
    desc = {"split_half_fg_epa_per_attempt": split_half,
            "consecutive_season_fg_epa_per_attempt": season_corr,
            "volume": vol}
    (OUT / "descriptives.json").write_text(json.dumps(desc, indent=2,
                                                      default=str))
    hdf.to_csv(OUT / "split_half.csv", index=False)
    ks.to_csv(OUT / "kicker_seasons.csv", index=False)
    print("[descr] saved descriptives.json", flush=True)
    print(json.dumps(desc, indent=2, default=str), flush=True)


# --------------------------------------------------------------------------
# Stage: test — residual tables for flagged team-games in the frame
# --------------------------------------------------------------------------

def _summ(vals: pd.Series) -> dict:
    v = vals.dropna().to_numpy(dtype=float)
    n = len(v)
    if n == 0:
        return {"n": 0, "mean": None, "sd": None, "ci95": [None, None]}
    mean = float(v.mean())
    if n < 2:
        return {"n": n, "mean": mean, "sd": None, "ci95": [None, None]}
    sd = float(v.std(ddof=1))
    half = float(stats.t.ppf(0.975, n - 1) * sd / np.sqrt(n))
    return {"n": n, "mean": mean, "sd": sd, "ci95": [mean - half,
                                                     mean + half]}


def stage_test() -> None:
    _require_baseline()
    flags = pd.read_csv(OUT / "flags.csv")
    base = pd.read_csv(OUT / "per_game_baseline.csv")
    base["margin_res_home"] = base["actual_margin"] - base["our_margin"]
    base["total_res"] = base["actual_total"] - base["our_total"]
    bidx = base.set_index(["season", "week", "home", "away"])

    # map team-game -> its frame row via (season, week, home, away):
    # flags rows carry team + is_home; the opponent comes from games data.
    games, _ = _load_kick_plays()
    gmap = games.set_index("game_id")
    recs = []
    chg = flags[flags["flag_status"] == "change"].copy()
    for _, r in chg.iterrows():
        g = gmap.loc[r["game_id"]]
        home, away = g["home_team"], g["away_team"]
        key = (int(r["season"]), int(r["week"]), home, away)
        if key not in bidx.index:
            continue
        brow = bidx.loc[key]
        mr = float(brow["margin_res_home"])
        team_mr = mr if r["is_home"] else -mr
        recs.append({
            "game_id": r["game_id"], "season": int(r["season"]),
            "week": int(r["week"]), "team": r["team"],
            "is_home": bool(r["is_home"]),
            "incoming_id": r["primary_id"],
            "incoming_name": r["primary_name"],
            "outgoing_id": r["outgoing_id"],
            "outgoing_name": r["outgoing_name"],
            "quality_diff": r["quality_diff"],
            "quality_class": r["quality_class"],
            "margin_residual": team_mr,
            "total_residual": float(brow["total_res"]),
        })
    res = pd.DataFrame(recs)

    # Second game with the new kicker: next team-game in sequence.
    games2, _ = _load_kick_plays()
    home = games2[["game_id", "season", "week",
                   "home_team"]].rename(columns={"home_team": "team"})
    home["is_home"] = True
    away = games2[["game_id", "season", "week",
                   "away_team"]].rename(columns={"away_team": "team"})
    away["is_home"] = False
    tg = pd.concat([home, away], ignore_index=True)
    # chronological ordering key from the games table
    okey_map = dict(zip(games2["game_id"],
                        zip(games2["season"], games2["week"],
                            games2["game_date"].astype(str),
                            games2["game_id"])))
    tg["okey"] = tg["game_id"].map(okey_map)
    tg = tg.sort_values(["team", "okey"]).reset_index(drop=True)
    tg["seq"] = tg.groupby("team").cumcount()
    prim = flags.set_index(["game_id", "team"])["primary_id"].to_dict()
    seq_of = {(r.team, r.game_id): int(r.seq) for r in tg.itertuples()}
    tg_idx = tg.set_index(["team", "seq"])

    second = []
    seen = set()
    flagged_pairs = {(r["game_id"], r["team"]) for _, r in chg.iterrows()}
    for _, r in chg.iterrows():
        s = seq_of.get((r["team"], r["game_id"]))
        if s is None or (r["team"], s + 1) not in tg_idx.index:
            continue
        nxt = tg_idx.loc[(r["team"], s + 1)]
        gid2 = nxt["game_id"]
        if prim.get((gid2, r["team"])) != r["primary_id"]:
            continue
        g = gmap.loc[gid2]
        key = (int(g["season"]), int(g["week"]),
               g["home_team"], g["away_team"])
        if key not in bidx.index or (r["team"], gid2) in seen:
            continue
        seen.add((r["team"], gid2))
        brow = bidx.loc[key]
        mr = float(brow["margin_res_home"])
        second.append({
            "game_id": gid2, "season": int(g["season"]),
            "week": int(g["week"]), "team": r["team"],
            "is_home": bool(nxt["is_home"]),
            "incoming_id": r["primary_id"],
            "quality_class": r["quality_class"],
            "margin_residual": mr if nxt["is_home"] else -mr,
            "total_residual": float(brow["total_res"]),
            "also_flagged_change": (gid2, r["team"]) in flagged_pairs,
        })
    sec = pd.DataFrame(second)

    res.to_csv(OUT / "flagged_residuals.csv", index=False)
    sec.to_csv(OUT / "second_game_residuals.csv", index=False)

    def table(df: pd.DataFrame) -> dict:
        return {"margin_residual": _summ(df["margin_residual"]),
                "total_residual": _summ(df["total_residual"])}

    out = {
        "n_change_team_games_all_pbp": int(len(chg)),
        "n_change_team_games_in_frame": int(len(res)),
        "n_games_with_both_teams_flagged": int(
            res.groupby("game_id")["team"].nunique().eq(2).sum())
        if len(res) else 0,
        "a_pooled": table(res) if len(res) else None,
        "b_incoming_worse": table(res[res["quality_class"]
                                      == "incoming_worse"])
        if len(res) else None,
        "b_incoming_better": table(res[res["quality_class"]
                                       == "incoming_better"])
        if len(res) else None,
        "b_unclassified": table(res[res["quality_class"]
                                    == "unclassified"])
        if len(res) else None,
        "c_second_game": table(sec) if len(sec) else None,
        "c_second_game_n_also_flagged": int(sec["also_flagged_change"]
                                            .sum()) if len(sec) else 0,
    }
    (OUT / "metrics.json").write_text(json.dumps(out, indent=2,
                                                 default=str))
    print("[test] saved flagged_residuals.csv / second_game_residuals.csv"
          " / metrics.json", flush=True)
    print(json.dumps(out, indent=2, default=str), flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["baseline", "build", "descr", "test"])
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    {"baseline": stage_baseline, "build": stage_build,
     "descr": stage_descr, "test": stage_test}[args.stage]()
