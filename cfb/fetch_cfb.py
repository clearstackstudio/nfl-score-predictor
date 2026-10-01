"""Pull college football data from the CollegeFootballData API.

Writes raw snapshots to data/cfb/raw/ and a merged per-game table to
data/cfb/cfb_games.parquet. One row per game:

    game_id, season, week, date, home_team, away_team, neutral,
    home_score, away_score,
    home_off_ppa, home_def_ppa, away_off_ppa, away_def_ppa,  (garbage time excluded)
    home_plays, away_plays,
    line_spread, line_total   (closing consensus = median across providers)

The betting line is stored ONLY as a benchmark. It never enters the model.

Usage:
    # One-time: connect your free CFBD key via the Secure Vault
    # (custom.collegefootballdata connector), then:
    python3 cfb/fetch_cfb.py --seasons 2014-2026
    python3 cfb/fetch_cfb.py --seasons 2026 --refresh   # weekly update

API budget: per season — 1 games + 1 team PPA + 1 lines + ~15 weekly
team-stat calls ≈ ~19 calls/season. Weekly --refresh ≈ ~19 calls.
Check current free-tier limits at collegefootballdata.com/key; spread the
2014–2026 backfill (~250 calls) across two months if needed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW = REPO / "data" / "cfb" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SEASON_TYPES = ("regular", "postseason")


def get_client():
    """CFBD client authenticated via the Secure Vault connector.

    The key lives in the vault (custom.collegefootballdata); authd swaps
    the surrogate for the real key on egress. Never in env vars or files.
    """
    import sys
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import dynamic_credential_entry
    import cfbd
    entry = dynamic_credential_entry("custom.collegefootballdata")
    token = entry.get("access_token") or entry.get("api_key") or entry.get("token")
    if not token:
        raise RuntimeError("custom.collegefootballdata credential not connected yet")
    cfg = cfbd.Configuration(access_token=token)
    return cfbd.ApiClient(cfg)


def dump(name: str, objs) -> Path:
    p = RAW / f"{name}.json"
    p.write_text(json.dumps([o.to_dict() for o in objs], default=str))
    return p


def fetch_season(client, season: int) -> dict:
    import cfbd
    from cfbd.api import games_api, betting_api, metrics_api

    games = games_api.GamesApi(client)
    betting = betting_api.BettingApi(client)
    metrics = metrics_api.MetricsApi(client)

    out = {}
    # Games (all weeks, FBS). One call.
    g = games.get_games(year=season, classification="fbs")
    out["games"] = dump(f"games_{season}", g)
    print(f"  games: {len(g)}", flush=True)

    # Lines (all weeks). One call.
    ln = betting.get_lines(year=season)
    out["lines"] = dump(f"lines_{season}", ln)
    print(f"  lines: {len(ln)}", flush=True)

    # Per-game PPA, garbage time excluded. Try season-wide, fall back to weekly.
    try:
        ppa = metrics.get_predicted_points_added_by_game(
            year=season, exclude_garbage_time=True, classification="fbs")
    except Exception:
        ppa = []
        for st in SEASON_TYPES:
            for week in range(1, 18):
                try:
                    ppa += metrics.get_predicted_points_added_by_game(
                        year=season, week=week, season_type=st,
                        exclude_garbage_time=True, classification="fbs")
                except Exception:
                    pass
                time.sleep(0.2)
    out["ppa"] = dump(f"ppa_{season}", ppa)
    print(f"  ppa rows: {len(ppa)}", flush=True)

    # Per-game team stats (for play counts -> PPA/play). Weekly calls.
    tgs = []
    for st in SEASON_TYPES:
        for week in range(1, 18):
            try:
                tgs += games.get_game_team_stats(year=season, week=week,
                                                 season_type=st)
            except Exception:
                pass
            time.sleep(0.2)
    out["team_stats"] = dump(f"team_stats_{season}", tgs)
    print(f"  team_stats rows: {len(tgs)}", flush=True)
    return out


def plays_from_stats(stats: list[dict]) -> int | None:
    """rushing attempts + pass attempts from CFBD team-game stat blobs."""
    rush = pa = None
    for s in stats:
        cat = (s.get("category") or "").lower()
        name = (s.get("stat") or s.get("statName") or "").lower().replace(" ", "")
        try:
            v = int(float(s.get("statValue", 0)))
        except (TypeError, ValueError):
            continue
        if cat == "rushing" and name in ("rushingattempts", "attempts", "rushes", "carries"):
            rush = v
        elif cat == "passing" and name in ("passattempts", "attempts"):
            pa = v
    if rush is None or pa is None:
        return None
    return rush + pa


def merge_season(season: int):
    import pandas as pd

    games = json.loads((RAW / f"games_{season}.json").read_text())
    lines = {l["id"]: l for l in
             json.loads((RAW / f"lines_{season}.json").read_text())}
    ppa = json.loads((RAW / f"ppa_{season}.json").read_text())
    tstats = json.loads((RAW / f"team_stats_{season}.json").read_text())

    # game_id -> {team: plays}
    plays: dict[int, dict[str, int]] = {}
    for t in tstats:
        gid = t.get("id") or t.get("gameId")
        team = t.get("team")
        n = plays_from_stats(t.get("stats", []))
        if gid and team and n:
            plays.setdefault(gid, {})[team] = n

    # (game_id, team) -> (off_ppa, def_ppa)
    ppa_map: dict[tuple, tuple] = {}
    for r in ppa:
        try:
            ppa_map[(r["gameId"], r["team"])] = (
                float(r["offense"]["total"] if isinstance(r.get("offense"), dict)
                      else r.get("offense")),
                float(r["defense"]["total"] if isinstance(r.get("defense"), dict)
                      else r.get("defense")),
            )
        except (TypeError, KeyError):
            continue

    rows = []
    for g in games:
        if not g.get("completed"):
            continue
        if g.get("homeClassification") != "fbs" or g.get("awayClassification") != "fbs":
            continue  # FBS-only to start; FCS mismatches add noise, not signal
        gid = g["id"]
        home, away = g["homeTeam"], g["awayTeam"]
        line = lines.get(gid, {})
        spreads, totals = [], []
        for l in line.get("lines", []) or []:
            if l.get("spread") is not None:
                try:
                    spreads.append(float(l["spread"]))
                except (TypeError, ValueError):
                    pass
            if l.get("overUnder") is not None:
                try:
                    totals.append(float(l["overUnder"]))
                except (TypeError, ValueError):
                    pass
        # closing consensus = median across providers (robust to outliers)
        import statistics
        rows.append({
            "game_id": gid,
            "season": season,
            "week": g.get("week"),
            "date": g.get("startDate"),
            "home_team": home,
            "away_team": away,
            "neutral": bool(g.get("neutralSite")),
            "home_score": g.get("homePoints"),
            "away_score": g.get("awayPoints"),
            "home_off_ppa": ppa_map.get((gid, home), (None, None))[0],
            "home_def_ppa": ppa_map.get((gid, home), (None, None))[1],
            "away_off_ppa": ppa_map.get((gid, away), (None, None))[0],
            "away_def_ppa": ppa_map.get((gid, away), (None, None))[1],
            "home_plays": (plays.get(gid) or {}).get(home),
            "away_plays": (plays.get(gid) or {}).get(away),
            "line_spread": statistics.median(spreads) if spreads else None,
            "line_total": statistics.median(totals) if totals else None,
            "n_lines": len(spreads),
        })
    df = pd.DataFrame(rows)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seasons", default="2014-2026",
                    help="e.g. 2014-2026 or 2026")
    ap.add_argument("--refresh", action="store_true",
                    help="re-pull raw data even if cached")
    args = ap.parse_args()

    if "-" in args.seasons:
        a, b = args.seasons.split("-")
        seasons = list(range(int(a), int(b) + 1))
    else:
        seasons = [int(args.seasons)]

    import pandas as pd
    client = get_client()
    frames = []
    for season in seasons:
        cached = all((RAW / f"{n}_{season}.json").exists()
                     for n in ("games", "lines", "ppa", "team_stats"))
        if cached and not args.refresh:
            print(f"{season}: using cached raw data")
        else:
            print(f"{season}: fetching...", flush=True)
            fetch_season(client, season)
            time.sleep(1)
        df = merge_season(season)
        print(f"{season}: {len(df)} FBS-vs-FBS completed games, "
              f"{df['line_spread'].notna().sum()} with lines")
        frames.append(df)

    allg = pd.concat(frames, ignore_index=True)
    dest = REPO / "data" / "cfb" / "cfb_games.parquet"
    dest.parent.mkdir(parents=True, exist_ok=True)
    allg.to_parquet(dest, index=False)
    print(f"Wrote {len(allg)} games -> {dest}")


if __name__ == "__main__":
    main()
