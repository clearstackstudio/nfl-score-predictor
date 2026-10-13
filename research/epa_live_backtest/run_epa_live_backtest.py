"""EPA live-model walk-forward backtest (pre-registered 2026-10-12).

Pre-registration: goals/ultimate-multi-sport-prediction-model/hidden_files/
epa-live-backtest-preregistration.md

Part A: call src/epa_ratings.run_backtest() exactly as-is -> config_a.json
Part B: replicate run_backtest's loop verbatim (same functions imported from
        src/, same order of operations), emitting one row per graded game;
        verify the pre-wind aggregates reproduce Config A exactly; fetch
        ERA5 historical wind (cached); apply the live totals rules post-hoc
        (weather.wind_total_adjustment + TOTAL_CIRCUIT = 7.0); write
        per_game.csv and metrics.json.

Measurement only: nothing in src/ or site/ is modified.

Run with the repo venv:  .venv-cfb/bin/python research/epa_live_backtest/run_epa_live_backtest.py --part a|b
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SRC = REPO / "src"
OUT = REPO / "research" / "epa_live_backtest"
sys.path.insert(0, str(SRC))

import pandas as pd  # noqa: E402

from backtest import closing_home_spread, load_games  # noqa: E402
from epa_ratings import (  # noqa: E402
    ABBR_TO_FULL, CARRYOVER, DATA, HOME_EDGE_PTS, PBP_YEARS, PLAYS_PER_GAME,
    adjusted_ratings, load_qb_plays, load_team_games, qb_adjustments,
    run_backtest, week_int,
)
from stadiums import STADIUMS, is_outdoor  # noqa: E402
from weather import wind_total_adjustment  # noqa: E402

TOTAL_CIRCUIT = 7.0  # src/weekly_picks.py


# --------------------------------------------------------------------------
# Part A
# --------------------------------------------------------------------------

def part_a() -> None:
    t0 = time.time()
    r = run_backtest()
    out = {k: (list(v) if isinstance(v, tuple) else v) for k, v in r.items()}
    out["_seconds"] = round(time.time() - t0, 1)
    (OUT / "config_a.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"[A done in {out['_seconds']}s]")


# --------------------------------------------------------------------------
# Part B: verbatim replication of run_backtest's loop + per-game emission
# --------------------------------------------------------------------------

def replicate_walk_forward() -> pd.DataFrame:
    """Copy of the loop in epa_ratings.run_backtest (2026-10-12), with the
    accumulator block replaced by per-game row emission. All model calls are
    the imported originals, in the original order."""
    team_games = load_team_games()
    qb_plays = load_qb_plays()
    sched_qb = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "home_team", "away_team",
                 "home_qb_id", "away_qb_id"])
    qb_lookup = {(int(r.season), int(r.week), r.home_team, r.away_team):
                 (r.home_qb_id, r.away_qb_id) for r in sched_qb.itertuples()}

    # venue/kickoff lookup from the same schedules file (research-only join)
    sched_full = pd.read_parquet(
        DATA / "schedules_games.parquet",
        columns=["season", "week", "home_team", "away_team",
                 "gameday", "gametime", "roof", "stadium"])
    venue_lookup = {}
    for r in sched_full.itertuples():
        venue_lookup[(int(r.season), int(r.week), r.home_team, r.away_team)] = (
            str(r.gameday), None if pd.isna(r.gametime) else str(r.gametime),
            None if pd.isna(r.roof) else str(r.roof),
            None if pd.isna(r.stadium) else str(r.stadium))

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

        gameday, gametime, roof, stadium = venue_lookup.get(
            key, (str(row["schedule_date"].date()), None, None, None))
        rows.append({
            "date": gameday,
            "season": season,
            "week": key[1],
            "home": home,
            "away": away,
            "neutral": neutral,
            "roof": roof,
            "stadium": stadium,
            "gametime_et": gametime,
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


def grade_ats(df: pd.DataFrame) -> tuple[int, int, int]:
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
    return w, l, p


def grade_ou(df: pd.DataFrame, total_col: str, circuit: float | None) -> tuple[int, int, int, int]:
    """Returns (w, l, p, circuit_excluded)."""
    w = l = p = cx = 0
    for _, r in df.iterrows():
        e = r[total_col] - r["line_total"]
        if abs(e) >= 3.0:
            if circuit is not None and abs(e) > circuit:
                cx += 1
                continue
            res = r["actual_total"] - r["line_total"]
            if abs(res) < 0.01:
                p += 1
            elif (res > 0) == (e > 0):
                w += 1
            else:
                l += 1
    return w, l, p, cx


def verify_against_a(df: pd.DataFrame, a: dict) -> dict:
    """Sequential accumulation in game order, mirroring run_backtest's float
    operations exactly, so aggregates should be bit-identical."""
    n = su = 0
    our_se = line_se = our_tse = line_tse = 0.0
    for _, r in df.iterrows():
        su += (r["our_margin"] > 0) == (r["actual_margin"] > 0)
        our_se += (r["our_margin"] - r["actual_margin"]) ** 2
        line_se += (r["line_margin"] - r["actual_margin"]) ** 2
        our_tse += (r["our_total"] - r["actual_total"]) ** 2
        line_tse += (r["line_total"] - r["actual_total"]) ** 2
        n += 1
    ats = grade_ats(df)
    ou = grade_ou(df, "our_total", None)[:3]
    got = {
        "games": n,
        "straight_up_pct": su / n,
        "our_margin_rmse": math.sqrt(our_se / n),
        "line_margin_rmse": math.sqrt(line_se / n),
        "ats": list(ats),
        "our_total_rmse": math.sqrt(our_tse / n),
        "line_total_rmse": math.sqrt(line_tse / n),
        "ou": list(ou),
    }
    diffs = {}
    ok = True
    for k, v in got.items():
        av = a[k]
        if isinstance(v, list):
            match = list(av) == v
            diffs[k] = 0 if match else (av, v)
            ok &= match
        else:
            d = abs(float(av) - float(v))
            diffs[k] = d
            ok &= d <= 1e-9
    return {"ok": ok, "replicated": got, "abs_diffs": diffs}


# --------------------------------------------------------------------------
# ERA5 wind (H1 method), cached
# --------------------------------------------------------------------------

def fetch_era5(lat: float, lon: float, d1: str, d2: str) -> dict[str, float]:
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}"
           "&hourly=wind_speed_10m&wind_speed_unit=mph"
           f"&start_date={d1}&end_date={d2}"
           "&timezone=America%2FNew_York")
    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "honest-line-research"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                d = json.load(resp)
            times = d["hourly"]["time"]
            winds = d["hourly"]["wind_speed_10m"]
            return {t: (None if w is None else float(w)) for t, w in zip(times, winds)}
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"ERA5 fetch failed for {lat},{lon} {d1}..{d2}: {last_err}")


def load_or_fetch_wind(df: pd.DataFrame) -> dict[str, dict[str, float | None]]:
    cache_path = OUT / "wind_cache.json"
    cache: dict = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    # stadium key per home team: STADIUMS directly, plus LA -> LAR coords
    # (fetch-only, so per-game wind at the Rams' actual stadium is recorded;
    # the applied adjustment still comes from the live function, which
    # resolves team keys itself).
    def coords_for(team: str):
        if team in STADIUMS:
            return STADIUMS[team][:2]
        if team == "LA":
            return STADIUMS["LAR"][:2]
        return None

    # needed (lat, lon, season) -> [min_date, max_date]
    need: dict[tuple, list[str]] = {}
    for _, r in df.iterrows():
        if coords_for(r["home"]) is None:
            continue
        if r["home"] != "LA" and not is_outdoor(r["home"]):
            continue
        lat, lon = coords_for(r["home"])
        ck = f"{lat:.3f},{lon:.3f}"
        key = (ck, int(r["season"]))
        cur = need.get(key)
        need[key] = [min(cur[0], r["date"]) if cur else r["date"],
                     max(cur[1], r["date"]) if cur else r["date"]]

    for (ck, season), (d1, d2) in sorted(need.items()):
        have = cache.get(ck, {})
        # coverage check: every date in range present at hour granularity is
        # overkill; check the specific game dates for this stadium-season
        dates = sorted({r["date"] for _, r in df.iterrows()
                        if coords_for(r["home"]) is not None
                        and f"{coords_for(r['home'])[0]:.3f},{coords_for(r['home'])[1]:.3f}" == ck
                        and int(r["season"]) == season
                        and (r["home"] == "LA" or is_outdoor(r["home"]))})
        if all(any(t.startswith(d + "T") for t in have) for d in dates):
            continue
        lat, lon = (float(x) for x in ck.split(","))
        print(f"  ERA5 fetch {ck} season {season}: {d1}..{d2}")
        series = fetch_era5(lat, lon, d1, d2)
        have.update(series)
        cache[ck] = have
        cache_path.write_text(json.dumps(cache))
    return cache


def kickoff_wind(cache: dict, lat: float, lon: float, date: str,
                 gametime: str | None) -> float | None:
    if gametime is None:
        return None
    try:
        hh = int(str(gametime).split(":")[0])
    except ValueError:
        return None
    series = cache.get(f"{lat:.3f},{lon:.3f}", {})
    return series.get(f"{date}T{hh:02d}:00")


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

def block_metrics(df: pd.DataFrame, total_col: str, circuit: float | None) -> dict:
    n = len(df)
    su = sum((r["our_margin"] > 0) == (r["actual_margin"] > 0)
             for _, r in df.iterrows())
    w, l, p = grade_ats(df)
    ow, ol, op, cx = grade_ou(df, total_col, circuit)
    dec, odec = w + l, ow + ol
    return {
        "games": n,
        "su_pct": su / n if n else float("nan"),
        "margin_rmse_ours": math.sqrt(((df["our_margin"] - df["actual_margin"]) ** 2).mean()),
        "margin_rmse_line": math.sqrt(((df["line_margin"] - df["actual_margin"]) ** 2).mean()),
        "ats_wlp": [w, l, p],
        "ats_picks": w + l + p,
        "ats_pct": w / dec if dec else float("nan"),
        "total_rmse_ours": math.sqrt(((df[total_col] - df["actual_total"]) ** 2).mean()),
        "total_rmse_line": math.sqrt(((df["line_total"] - df["actual_total"]) ** 2).mean()),
        "ou_wlp": [ow, ol, op],
        "ou_picks": ow + ol + op,
        "ou_pct": ow / odec if odec else float("nan"),
        "circuit_excluded": cx,
    }


def part_b() -> None:
    a = json.loads((OUT / "config_a.json").read_text())
    t0 = time.time()
    df = replicate_walk_forward()
    print(f"[replication: {len(df)} games in {time.time() - t0:.0f}s]")

    ver = verify_against_a(df, a)
    print("[verification]", "PASS" if ver["ok"] else "FAIL",
          json.dumps(ver["abs_diffs"]))
    if not ver["ok"]:
        (OUT / "verification_failed.json").write_text(json.dumps(ver, indent=2, default=str))
        print("STOP: replication does not reproduce Config A (see pre-reg).")
        sys.exit(2)

    # --- wind ---
    cache = load_or_fetch_wind(df)

    def coords_for(team: str):
        if team in STADIUMS:
            return STADIUMS[team][:2]
        if team == "LA":
            return STADIUMS["LAR"][:2]
        return None

    wind_mphs, wind_adjs, covered = [], [], []
    for _, r in df.iterrows():
        home = r["home"]
        needs_wind = home != "LA" and is_outdoor(home)
        w = None
        if coords_for(home) is not None and (needs_wind or home == "LA"):
            lat, lon = coords_for(home)
            w = kickoff_wind(cache, lat, lon, r["date"], r["gametime_et"])
        wind_mphs.append(w)
        # adjustment EXACTLY as the live path computes it
        wind_adjs.append(wind_total_adjustment(w, home))
        covered.append(bool(needs_wind and w is not None))
    df["wind_mph"] = wind_mphs
    df["wind_adj_pts"] = wind_adjs
    df["our_total_adj"] = df["our_total"] + df["wind_adj_pts"]
    df["wind_needed"] = [h != "LA" and is_outdoor(h) for h in df["home"]]
    df["wind_covered"] = covered

    outdoor_n = int(df["wind_needed"].sum())
    covered_n = int(df["wind_covered"].sum())
    coverage = covered_n / outdoor_n if outdoor_n else 1.0
    print(f"[wind coverage: {covered_n}/{outdoor_n} outdoor games "
          f"({coverage:.1%}); adjusted games: {int((df['wind_adj_pts'] != 0).sum())}]")

    # LA diagnostic: games where the live STADIUMS table silently skips a
    # stadium that IS listed outdoor (SoFi under LAR/LAC).
    la = df[df["home"] == "LA"]
    la_windy = la[la["wind_mph"].notna() & (la["wind_mph"] > 10.0)]
    la_diag = {
        "la_home_games": int(len(la)),
        "la_games_with_wind_over_10mph": int(len(la_windy)),
        "la_max_hindcast_hinge_pts": float(
            (-la_windy["wind_mph"].apply(lambda w: min(8.0, max(0.0, w - 10.0)))).min()
        ) if len(la_windy) else 0.0,
    }
    print("[LA diagnostic]", la_diag)

    metrics: dict = {"verification": ver, "wind_coverage": {
        "outdoor_games": outdoor_n, "covered": covered_n, "pct": coverage},
        "la_diagnostic": la_diag}

    b_scope = df if coverage >= 0.95 else df[~df["wind_needed"] | df["wind_covered"]]
    metrics["config_b_scope"] = "all games" if coverage >= 0.95 else "covered subset only"
    metrics["config_a"] = {
        "overall": block_metrics(df, "our_total", None),
        "per_season": {str(s): block_metrics(g, "our_total", None)
                       for s, g in df.groupby("season")},
    }
    metrics["config_b"] = {
        "overall": block_metrics(b_scope, "our_total_adj", TOTAL_CIRCUIT),
        "per_season": {str(s): block_metrics(g, "our_total_adj", TOTAL_CIRCUIT)
                       for s, g in b_scope.groupby("season")},
        # raw post-wind OU without circuit, for attribution
        "overall_no_circuit": block_metrics(b_scope, "our_total_adj", None),
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))

    cols = ["date", "season", "week", "home", "away", "neutral", "roof",
            "stadium", "gametime_et", "wind_mph", "wind_adj_pts",
            "our_margin", "our_total", "our_total_adj", "line_margin",
            "line_total", "actual_margin", "actual_total"]
    df[cols].to_csv(OUT / "per_game.csv", index=False)
    print(f"[B done: per_game.csv ({len(df)} rows), metrics.json]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=["a", "b"], required=True)
    args = ap.parse_args()
    if args.part == "a":
        part_a()
    else:
        part_b()
