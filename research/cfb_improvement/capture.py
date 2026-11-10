"""Walk-forward per-game capture for the CFB improvement study.

Modes:
  A  : stock ordering (season, week, date) + ratings clone (min_games=4).
       Replication check: aggregates must match data/cfb/cfb_backtest.json
       (the published record) on 2014-2025.
  B  : chronological ordering (season, date, game_id), min_games=4.
       The published harness sorts by (season, week, date); CFBD postseason
       week numbers restart at 1, so bowl games sort into early-season
       positions (look-ahead / stale-ratings contamination). Frame B is the
       honest walk-forward frame used for hypothesis tests.
  B8 : chronological ordering, min_games=8 (H-S3 stronger-shrinkage variant).

adjusted_ratings below is a verbatim copy of cfb/cfb_ratings.py's function
with MIN_GAMES parameterized (study-local; live code untouched). Two
semantics-preserving speedups: (1) ratings are computed on the two-season
slice the function actually uses (it filters to season >= season-1
internally); (2) season_final is computed once per season from the last
predicted game instead of after every game (intermediate values are never
read -- prior updates only at season change). Mode A matching the published
aggregates validates both.

Usage: .venv-cfb/bin/python research/cfb_improvement/capture.py A|B|B8
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO / "cfb"))
import cfb_ratings as CR  # noqa: E402

WINDOW_GAMES = CR.WINDOW_GAMES
_RECENCY_DECAY = CR._RECENCY_DECAY
CARRYOVER = CR.CARRYOVER
PLAYS_PER_GAME = CR.PLAYS_PER_GAME
HOME_EDGE_PTS = CR.HOME_EDGE_PTS


def adjusted_ratings_p(team_games, upto_idx, season, prior, min_games):
    """Verbatim copy of cfb_ratings.adjusted_ratings, MIN_GAMES -> param."""
    hist = team_games.iloc[:upto_idx]
    hist = hist[hist["season"] >= season - 1]
    recent = hist.groupby("team").tail(WINDOW_GAMES)
    if recent.empty:
        return {}, {}, {}

    raw_off, raw_def, pace, opps, opp_w = {}, {}, {}, {}, {}
    for team, gg in recent.groupby("team"):
        gg = gg.sort_values(["season", "week", "date", "game_id"])
        n = len(gg)
        w = _RECENCY_DECAY ** np.arange(n - 1, -1, -1)
        raw_off[team] = float(np.average(gg["off_ppa_play"], weights=w))
        raw_def[team] = float(np.average(gg["def_ppa_play"], weights=w))
        pace[team] = float(np.average(gg["plays"], weights=w))
        opps[team] = list(gg["opp"])
        opp_w[team] = list(w)
        n_eff = w.sum() ** 2 / (w ** 2).sum()
        if n_eff < min_games and team in prior:
            b = n_eff / min_games
            raw_off[team] = b * raw_off[team] + (1 - b) * prior[team][0]
            raw_def[team] = b * raw_def[team] + (1 - b) * prior[team][1]

    lg_off = sum(raw_off.values()) / len(raw_off)
    lg_def = sum(raw_def.values()) / len(raw_def)

    off, deff = {}, {}
    for t in raw_off:
        pairs_d = [(raw_def[o] - lg_def, wt)
                   for o, wt in zip(opps[t], opp_w[t]) if o in raw_def]
        pairs_o = [(raw_off[o] - lg_off, wt)
                   for o, wt in zip(opps[t], opp_w[t]) if o in raw_off]
        adj_d = (sum(v * wt for v, wt in pairs_d) / sum(wt for _, wt in pairs_d)
                 if pairs_d else 0.0)
        adj_o = (sum(v * wt for v, wt in pairs_o) / sum(wt for _, wt in pairs_o)
                 if pairs_o else 0.0)
        off[t] = (raw_off[t] - lg_off) - adj_d
        deff[t] = (raw_def[t] - lg_def) - adj_o
    return off, deff, pace


def build_team_games(mode):
    tg = CR.load_team_games()
    if mode in ("B", "B8"):
        tg = tg.sort_values(["season", "date", "game_id"],
                            kind="stable").reset_index(drop=True)
    return tg


def build_games(mode):
    games = pd.read_parquet(REPO / "data" / "cfb" / "cfb_games.parquet")
    games = games.dropna(subset=["line_spread", "line_total"]).copy()
    if mode == "A":
        games = games.sort_values(["season", "week", "date"])
    else:
        games = games.sort_values(["season", "date", "game_id"], kind="stable")
    return games.reset_index(drop=True)


def capture(mode, min_games):
    tg = build_team_games(mode)
    games = build_games(mode)

    gid_first = {}
    for i, r in tg.iterrows():
        gid_first.setdefault(int(r["game_id"]), i)

    # Per-season two-season slices of tg (rows the ratings fn can see),
    # with the original row positions for cutoff remapping.
    slices = {}
    for season in sorted(tg["season"].unique()):
        sub = tg[tg["season"].isin([season - 1, season])]
        slices[season] = (sub.reset_index(drop=True),
                          np.sort(sub.index.to_numpy()))

    # Per (season, team): sorted tg positions of that team's games that
    # season -> games-played-prior via searchsorted.
    team_pos = {}
    for (season, team), idx in tg.groupby(["season", "team"]).groups.items():
        team_pos[(int(season), team)] = np.sort(np.asarray(idx))

    prior = {}
    season_final = {}
    last_season = None
    last_cutoff = None      # last predicted game's cutoff in current season
    last_prior_used = {}
    epa_hist = []
    rows = []

    def roll_prior(season_that_ended):
        nonlocal season_final
        if last_cutoff is None:
            return
        off2, def2, _ = adjusted_ratings_p(tg, last_cutoff + 2,
                                           season_that_ended,
                                           last_prior_used, min_games)
        season_final = {t: (off2[t], def2[t]) for t in off2}

    for _, row in games.iterrows():
        season = int(row["season"])
        if last_season is not None and season != last_season:
            roll_prior(last_season)
            prior = {t: (CARRYOVER * v[0], CARRYOVER * v[1])
                     for t, v in season_final.items()}
            last_cutoff = None
        last_season = season

        cutoff = gid_first.get(int(row["game_id"]))
        if cutoff is None:
            continue
        sub, sub_pos = slices[season]
        sub_cutoff = int(np.searchsorted(sub_pos, cutoff))
        off, deff, pace = adjusted_ratings_p(sub, sub_cutoff, season, prior,
                                             min_games)
        epa_const = (sum(epa_hist) / len(epa_hist)) if epa_hist else 58.0
        home, away = row["home_team"], row["away_team"]
        pr = CR.predict(off, deff, pace, home, away, bool(row["neutral"]),
                        epa_const)
        if pr is None:
            continue
        our_margin, our_total = pr
        # Components (identical math to predict()) for hypothesis tests.
        exp_home_off = off[home] + deff[away]
        exp_away_off = off[away] + deff[home]
        pace_home = pace.get(home, PLAYS_PER_GAME)
        pace_away = pace.get(away, PLAYS_PER_GAME)
        exp_plays = (pace_home + pace_away) / 2

        def gp(team):
            arr = team_pos.get((season, team))
            return int(np.searchsorted(arr, cutoff)) if arr is not None else 0

        rows.append({
            "game_id": int(row["game_id"]), "season": season,
            "week": int(row["week"]) if pd.notna(row["week"]) else 99,
            "date": str(row["date"]), "home": home, "away": away,
            "neutral": bool(row["neutral"]),
            "our_margin": our_margin, "our_total": our_total,
            "epa_const": epa_const,
            "ppa_sum": exp_home_off + exp_away_off,
            "ppa_diff": exp_home_off - exp_away_off,
            "exp_plays": exp_plays, "pace_home": pace_home,
            "pace_away": pace_away,
            "line_margin": float(row["line_spread"]),
            "line_total": float(row["line_total"]),
            "actual_margin": float(row["home_score"]) - float(row["away_score"]),
            "actual_total": float(row["home_score"]) + float(row["away_score"]),
            "home_gp": gp(home), "away_gp": gp(away),
        })
        epa_hist.append(float(row["home_score"]) + float(row["away_score"]))
        last_cutoff = cutoff
        last_prior_used = prior

    return pd.DataFrame(rows)


def aggregates(df, seasons):
    d = df[df["season"].isin(seasons)]
    n = len(d)
    out = {"games": n}
    if n == 0:
        return out
    out["straight_up_pct"] = round(float(((d.our_margin > 0)
                                           == (d.actual_margin > 0)).mean()), 4)
    out["our_margin_rmse"] = round(float(np.sqrt(((d.our_margin - d.actual_margin) ** 2).mean())), 2)
    out["line_margin_rmse"] = round(float(np.sqrt(((d.line_margin - d.actual_margin) ** 2).mean())), 2)
    out["our_total_rmse"] = round(float(np.sqrt(((d.our_total - d.actual_total) ** 2).mean())), 2)
    out["line_total_rmse"] = round(float(np.sqrt(((d.line_total - d.actual_total) ** 2).mean())), 2)
    for name, edge, actual in (("ats", d.our_margin - d.line_margin,
                                d.actual_margin - d.line_margin),
                               ("ou", d.our_total - d.line_total,
                                d.actual_total - d.line_total)):
        thr = 0.5 if name == "ats" else 1.0
        m = edge.abs() >= thr
        r = actual[m]
        e = edge[m]
        w = int(((r.abs() >= 0.01) & ((r > 0) == (e > 0))).sum())
        p_ = int((r.abs() < 0.01).sum())
        l_ = int(len(r) - w - p_)
        out[name] = [w, l_, p_]
        out[name + "_pct"] = round(w / (w + l_), 4) if (w + l_) else None
    return out


def main():
    mode = sys.argv[1]
    min_games = 8 if mode == "B8" else 4
    df = capture(mode, min_games)
    dest = HERE / f"frame_{mode}.parquet"
    df.to_parquet(dest, index=False)
    print(f"frame {mode}: {len(df)} games -> {dest}")
    agg = aggregates(df, list(range(2014, 2026)))
    print(json.dumps(agg, indent=1))
    if mode == "A":
        pub = json.loads((REPO / "data" / "cfb" / "cfb_backtest.json").read_text())
        print("published:", json.dumps(pub["overall"]))
        checks = [
            ("games", agg["games"], pub["games"]),
            ("straight_up_pct", agg["straight_up_pct"], pub["overall"]["straight_up_pct"]),
            ("our_margin_rmse", agg["our_margin_rmse"], pub["overall"]["our_margin_rmse"]),
            ("line_margin_rmse", agg["line_margin_rmse"], pub["overall"]["line_margin_rmse"]),
            ("our_total_rmse", agg["our_total_rmse"], pub["overall"]["our_total_rmse"]),
            ("line_total_rmse", agg["line_total_rmse"], pub["overall"]["line_total_rmse"]),
            ("ats", agg["ats"], pub["overall"]["ats"]),
            ("ou", agg["ou"], pub["overall"]["ou"]),
        ]
        ok = True
        for name, mine, theirs in checks:
            match = mine == theirs
            ok &= match
            print(f"  {'OK ' if match else 'DIFF'} {name}: mine={mine} published={theirs}")
        print("REPLICATION:", "PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
