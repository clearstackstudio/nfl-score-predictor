"""NHL shadow picks: freeze v1.1 model picks + market lines nightly.

SHADOW MODE — nothing is published. Each run appends one frozen record
per game to data/nhl/shadow/picks.jsonl (append-only, never rewritten):
model expected goals and win probabilities (raw + calibrated) from the
frozen v1.1 spec (src/nhl/ratings.py, home-ice 0.20 and the calibration
map fitted on discovery, as recorded in data/nhl/backtest_summary.json),
the rest term active, and consensus market lines from The Odds API
(median across US bookmakers — the house convention from the NBA
pipeline). Totals plays are flagged at the pre-registered
|model - market| >= 0.5-goal threshold; in shadow the flag is just a
flag. Grading lives in shadow_grade.py.

Ratings snapshots replicate backtest.walk_forward exactly: the prior
chain is derived season by season from end-of-season snapshots
(cached in data/nhl/ratings_state.json, fingerprinted by row count)
and each snapshot uses only games strictly before the target date.
--verify-snapshots proves the machinery against the frozen backtest's
own predictions parquet.
"""
import argparse
import json
import statistics
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.special import expit, logit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from market_eval import NAME_TO_ABBR, implied  # noqa: E402
from ratings import expected_goals, ratings_snapshot, win_prob  # noqa: E402
from scores_api import ABBR_FIX, fetch  # noqa: E402

sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
from dynamic_credentials import (  # noqa: E402
    read_json_response, url_with_surrogate_query_param)

DATA = Path(__file__).resolve().parents[2] / "data" / "nhl"
SHADOW = DATA / "shadow"
PICKS = SHADOW / "picks.jsonl"
STATE = DATA / "ratings_state.json"
PT = ZoneInfo("America/Los_Angeles")
TOTALS_FLAG = 0.5          # pre-registered publishing threshold (goals)
MODEL_VERSION = "v1.1"     # v1 + rest term (adopted 2026-10-20)


# ---------------------------------------------------------------- state
def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE.write_text(json.dumps(state))


def _jsonable_snap(snap: dict) -> dict:
    return {
        "off": {t: float(v) for t, v in snap["off"].items()},
        "def": {t: float(v) for t, v in snap["def"].items()},
        "raw_off": {t: float(v) for t, v in snap["raw_off"].items()},
        "raw_def": {t: float(v) for t, v in snap["raw_def"].items()},
        "lg_x": float(snap["lg_x"]), "lg_goals": float(snap["lg_goals"]),
    }


def _derive_prior(end_snap: dict) -> dict:
    """walk_forward's season-change prior: last season's raw ratings,
    regressed halfway to the league mean (CARRYOVER = 0.5)."""
    lg = end_snap["lg_x"]
    return {t: (lg + 0.5 * (end_snap["raw_off"][t] - lg),
                lg + 0.5 * (end_snap["raw_def"][t] - lg))
            for t in end_snap["raw_off"]}


def end_snapshot(tg: pd.DataFrame, season: int, prior: dict,
                 state: dict) -> dict:
    """Snapshot walk_forward holds when the season flips: computed on
    the season's last date from games strictly before it."""
    ends = state.setdefault("season_end_snaps", {})
    key = str(season)
    n = int((tg["season"] == season).sum())
    if key in ends and ends[key].get("tg_rows") == n:
        return ends[key]["snap"]
    last_date = tg.loc[tg["season"] == season, "date"].max()
    hist = tg[(tg["date"] < last_date) & (tg["season"] >= season - 1)]
    snap = ratings_snapshot(hist, prior)
    js = _jsonable_snap(snap)
    ends[key] = {"tg_rows": n, "snap": js}
    return js


def season_prior(tg: pd.DataFrame, season: int, state: dict) -> dict:
    priors = state.setdefault("priors", {})
    key = str(season)
    if key in priors:
        return {t: (float(v[0]), float(v[1]))
                for t, v in priors[key].items()}
    first = int(tg.loc[tg["season"] >= 2018, "season"].min())
    if season <= first:
        priors[key] = {}
        return {}
    prev_prior = season_prior(tg, season - 1, state)
    end = end_snapshot(tg, season - 1, prev_prior, state)
    p = _derive_prior(end)
    priors[key] = {t: [float(v[0]), float(v[1])] for t, v in p.items()}
    return p


def snapshot_for(tg: pd.DataFrame, target: pd.Timestamp, season: int,
                 state: dict) -> dict:
    """The exact snapshot walk_forward computes on `target`'s date."""
    prior = season_prior(tg, season, state)
    hist = tg[(tg["date"] < target) & (tg["season"] >= season - 1)]
    return ratings_snapshot(hist, prior)


def verify_snapshots(per_season: int = 8) -> tuple[int, float]:
    """Rebuild lambdas for sampled backtest games; max |diff| vs the
    frozen predictions parquet must be ~0."""
    from ratings import rest_days_map
    tg = pd.read_parquet(DATA / "team_games.parquet")
    tg = tg[tg["season"] >= 2018]
    pred = pd.read_parquet(DATA / "backtest_predictions.parquet")
    rest = rest_days_map(tg)
    state = load_state()
    worst, checked = 0.0, 0
    for season, grp in pred.groupby("season"):
        sample = grp.sample(n=min(per_season, len(grp)), random_state=7)
        for r in sample.itertuples():
            snap = snapshot_for(tg, pd.Timestamp(r.date), int(season),
                                state)
            lam = expected_goals(snap, r.home, r.away, home_ice=0.0,
                                 rest_d=rest.get(int(r.game_id), 0))
            assert lam is not None, f"unrated team in game {r.game_id}"
            worst = max(worst, abs(lam[0] - r.lam_h0),
                        abs(lam[1] - r.lam_a))
            checked += 1
    save_state(state)
    return checked, worst


# ---------------------------------------------------------------- feeds
def fetch_schedule(target: date) -> list[dict]:
    data = fetch(f"https://api-web.nhle.com/v1/schedule/{target.isoformat()}")
    for day in data.get("gameWeek", []):
        if day["date"] == target.isoformat():
            return [g for g in day.get("games", []) if g.get("gameType") == 2]
    return []


def season_schedule(team: str, season: int) -> list[dict]:
    season_id = season * 10000 + season + 1
    data = fetch(f"https://api-web.nhle.com/v1/club-schedule-season/"
                 f"{team}/{season_id}")
    return [g for g in data.get("games", []) if g.get("gameType") == 2]


def rest_days(team: str, season: int, target: date,
              cache: dict) -> int:
    """Days since the team's previous regular-season game (NHL API
    schedule — authoritative dates); first game of a season = 3."""
    if team not in cache:
        cache[team] = season_schedule(team, season)
    prev = [g["gameDate"] for g in cache[team]
            if g["gameDate"] < target.isoformat()]
    if not prev:
        return 3
    return (target - date.fromisoformat(max(prev))).days


def fetch_odds() -> list[dict]:
    base = ("https://api.the-odds-api.com/v4/sports/icehockey_nhl/odds/"
            "?regions=us&markets=h2h,totals&oddsFormat=american")
    url = url_with_surrogate_query_param(
        base, "custom.the-odds-api",
        allowed_hosts=("api.the-odds-api.com",))
    req = urllib.request.Request(url, headers={"User-Agent": "honest-line/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return read_json_response(resp)


def consensus_lines(game: dict) -> dict:
    """Median moneyline/total across bookmakers (house convention)."""
    ml: dict[str, list[float]] = {}
    tot_pts: list[float] = []
    over_by_pt: dict[float, list[float]] = {}
    under_by_pt: dict[float, list[float]] = {}
    over_all: list[float] = []
    under_all: list[float] = []
    n_ml = n_tot = 0
    for bm in game.get("bookmakers", []):
        for m in bm.get("markets", []):
            if m.get("key") == "h2h":
                n_ml += 1
                for o in m.get("outcomes", []):
                    ml.setdefault(o["name"], []).append(float(o["price"]))
            elif m.get("key") == "totals":
                n_tot += 1
                for o in m.get("outcomes", []):
                    pt = float(o["point"])
                    if o["name"] == "Over":
                        tot_pts.append(pt)
                        over_by_pt.setdefault(pt, []).append(float(o["price"]))
                        over_all.append(float(o["price"]))
                    elif o["name"] == "Under":
                        under_by_pt.setdefault(pt, []).append(float(o["price"]))
                        under_all.append(float(o["price"]))
    out: dict = {"n_books_ml": n_ml, "n_books_totals": n_tot}
    home, away = game["home_team"], game["away_team"]
    if ml.get(home) and ml.get(away):
        out["home_ml"] = statistics.median(ml[home])
        out["away_ml"] = statistics.median(ml[away])
    if tot_pts:
        line = statistics.median(tot_pts)
        out["total_line"] = line
        out["over_price"] = statistics.median(
            over_by_pt.get(line, over_all)) if over_all else None
        out["under_price"] = statistics.median(
            under_by_pt.get(line, under_all)) if under_all else None
    return out


# ---------------------------------------------------------------- picks
def build_picks(target: date) -> tuple[list[dict], dict]:
    tg = pd.read_parquet(DATA / "team_games.parquet")
    tg = tg[tg["season"] >= 2018]
    summary = json.loads((DATA / "backtest_summary.json").read_text())
    home_ice = float(summary["home_ice_goals"])
    cal_a = float(summary["calibration"]["a"])
    cal_b = float(summary["calibration"]["b"])

    games = fetch_schedule(target)
    if not games:
        return [], {}
    season = int(str(games[0]["id"])[:4])
    state = load_state()
    snap = snapshot_for(tg, pd.Timestamp(target), season, state)
    save_state(state)
    assert snap is not None, "ratings snapshot unavailable"

    events = {}
    for ev in fetch_odds():
        try:
            key = (NAME_TO_ABBR[ev["away_team"]],
                   NAME_TO_ABBR[ev["home_team"]])
        except KeyError:
            continue
        if key not in events or ev["commence_time"] < events[key]["commence_time"]:
            events[key] = ev

    rest_cache: dict = {}
    frozen_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for g in games:
        home = ABBR_FIX.get(g["homeTeam"]["abbrev"], g["homeTeam"]["abbrev"])
        away = ABBR_FIX.get(g["awayTeam"]["abbrev"], g["awayTeam"]["abbrev"])
        r_h = rest_days(home, season, target, rest_cache)
        r_a = rest_days(away, season, target, rest_cache)
        d = max(-3, min(3, r_h - r_a))
        lam = expected_goals(snap, home, away, home_ice=home_ice, rest_d=d)
        assert lam is not None, f"unrated team: {away} @ {home}"
        lam_h, lam_a = lam
        p_raw = win_prob(lam_h, lam_a)
        p_cal = float(expit(cal_a + cal_b * logit(
            min(max(p_raw, 1e-6), 1 - 1e-6))))
        model_total = lam_h + lam_a
        row = {
            "date": target.isoformat(),
            "game_id": int(g["id"]),
            "start_time_utc": g.get("startTimeUTC"),
            "home": home, "away": away,
            "lam_home": round(lam_h, 4), "lam_away": round(lam_a, 4),
            "p_home_raw": round(p_raw, 4), "p_home_cal": round(p_cal, 4),
            "model_total": round(model_total, 4),
            "rest_home": r_h, "rest_away": r_a, "rest_d": d,
            "home_ml": None, "away_ml": None, "total_line": None,
            "over_price": None, "under_price": None,
            "n_books_ml": 0, "n_books_totals": 0,
            "market_p_home": None, "ml_disagree_pp": None,
            "totals_flag": False, "totals_side": None,
            "model_version": MODEL_VERSION,
            "frozen_at": frozen_at,
        }
        ev = events.get((away, home))
        if ev is not None:
            row.update({k: v for k, v in consensus_lines(ev).items()})
        if row["home_ml"] is not None and row["away_ml"] is not None:
            ph = implied(row["home_ml"])
            pa = implied(row["away_ml"])
            row["market_p_home"] = round(ph / (ph + pa), 4)
            row["ml_disagree_pp"] = round(
                abs(p_cal - row["market_p_home"]) * 100, 1)
        if row["total_line"] is not None:
            edge = model_total - row["total_line"]
            if abs(edge) >= TOTALS_FLAG:
                row["totals_flag"] = True
                row["totals_side"] = "over" if edge > 0 else "under"
        rows.append(row)

    ranking = sorted(
        ((t, snap["off"][t] - snap["def"][t]) for t in snap["off"]),
        key=lambda x: x[1], reverse=True)
    info = {
        "season": season, "home_ice": home_ice,
        "top5": [(t, round(v, 3)) for t, v in ranking[:5]],
        "bottom5": [(t, round(v, 3)) for t, v in ranking[-5:]],
        "lg_goals": round(snap["lg_goals"], 3),
    }
    return rows, info


def main() -> None:
    ap = argparse.ArgumentParser(description="Freeze NHL shadow picks")
    ap.add_argument("--date", default=None,
                    help="slate date YYYY-MM-DD (default: tomorrow PT)")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute and print, do not append to the log")
    ap.add_argument("--verify-snapshots", action="store_true",
                    help="check snapshot machinery vs the frozen backtest")
    args = ap.parse_args()

    if args.verify_snapshots:
        checked, worst = verify_snapshots()
        print(f"snapshot verify: {checked} games, max |lambda diff| "
              f"= {worst:.2e}")
        return

    if args.date:
        target = date.fromisoformat(args.date)
    else:
        target = datetime.now(PT).date() + timedelta(days=1)
    rows, info = build_picks(target)
    print(f"shadow picks for {target}: {len(rows)} games "
          f"(model {MODEL_VERSION}, home_ice {info.get('home_ice')}, "
          f"league goals/g {info.get('lg_goals')})")
    print(f"ratings top5: {info.get('top5')}")
    print(f"ratings bottom5: {info.get('bottom5')}")
    for r in rows:
        print(f"  {r['away']} @ {r['home']}: lam {r['lam_away']:.2f}/"
              f"{r['lam_home']:.2f} p_cal {r['p_home_cal']:.3f} "
              f"total {r['model_total']:.2f} | ML {r['away_ml']}/"
              f"{r['home_ml']} line {r['total_line']} "
              f"rest {r['rest_away']}/{r['rest_home']} (d={r['rest_d']}) "
              f"flag={r['totals_side'] if r['totals_flag'] else '-'}")
    missing = [f"{r['away']}@{r['home']}" for r in rows
               if r["home_ml"] is None or r["total_line"] is None]
    if missing:
        print(f"WARNING missing lines: {missing}")

    if args.dry_run:
        print("dry run — nothing appended")
        return
    SHADOW.mkdir(parents=True, exist_ok=True)
    existing = set()
    if PICKS.exists():
        for line in PICKS.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                existing.add((rec["date"], rec["game_id"]))
    new = [r for r in rows if (r["date"], r["game_id"]) not in existing]
    with PICKS.open("a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")
    print(f"appended {len(new)} frozen records to {PICKS} "
          f"({len(rows) - len(new)} already logged)")


if __name__ == "__main__":
    main()
