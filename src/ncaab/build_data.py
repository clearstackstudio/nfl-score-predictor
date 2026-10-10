"""Pull NCAAB games + box scores + closing lines from CollegeBasketballData.

Writes:
  data/ncaab/raw/games_<season>.jsonl      (GameInfo rows, all pages)
  data/ncaab/raw/box_<season>.jsonl        (GameBoxScoreTeam rows, all pages)
  data/ncaab/raw/lines_<season>.jsonl      (GameLines rows, all pages)
  data/ncaab/games.csv                     (built from raw: one row per game)

games.csv columns:
  date, season, season_type, home_team, away_team, home_score, away_score,
  neutral, poss, spread, total, n_books

  - date: game start date (YYYY-MM-DD, PT)
  - season: ending year (2026 = 2025-26 season)
  - spread: closing consensus spread in HOME-margin convention
    (positive = home favored); median across books of -raw_spread
  - total: closing consensus total (median across books)
  - poss: possessions, from the box-score `pace` field (RAW -- see note)
  - only final, D1-vs-D1, non-exhibition games

  NOTE on poss: the raw box-score pace has known data-quality issues the
  model guards against (see efficiency.sanitize_poss): the 2013 season's
  pace field is on an inflated scale (mean 75.7, implying 0.875 PPP vs
  ~1.05 in every other season), and early seasons contain garbage values
  (e.g. 7.0 for a 130-point game). games.csv keeps the raw values; the
  model sanitizes them.

Exhibition handling (documented): season_type='preseason' games (which carry
game_type='EXH') are excluded entirely -- from training AND the backtest.
Regular-season game_type values are STD and TRNMNT (early-season multi-team
events and holiday tournaments); both are included. Postseason (conference
tournaments + NCAA/NIT) is included.

D1-only (mirrors the CFB FBS-only rule): a game is kept only when both teams
appear in TeamsApi.get_teams for that season.

Usage:
    TZ=America/Los_Angeles .venv-cfb/bin/python src/ncaab/build_data.py \
        [--seasons 2010 2026] [--raw-only] [--build-only]
"""
from __future__ import annotations

import argparse
import csv
import datetime
import json
import os
import statistics
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
from dynamic_credentials import dynamic_credential_entry  # noqa: E402

import cbbd  # noqa: E402

REPO = Path(__file__).resolve().parent.parent.parent
RAW = REPO / "data" / "ncaab" / "raw"
OUT = REPO / "data" / "ncaab" / "games.csv"
PT = ZoneInfo("America/Los_Angeles")

# Season windows: Nov 1 of (season-1) through Apr 30 of season.
WINDOWS = [(11, 1), (12, 1), (1, 1), (2, 1), (3, 1), (4, 1)]


def client() -> cbbd.ApiClient:
    entry = dynamic_credential_entry("custom.collegebasketballdata")
    cfg = cbbd.Configuration(access_token=entry["surrogate"])
    cfg.proxy = os.environ["HTTPS_PROXY"]
    return cbbd.ApiClient(cfg)


def month_windows(season: int):
    for m, _day in WINDOWS:
        year = season - 1 if m >= 11 else season
        start = datetime.datetime(year, m, 1)
        if m == 12:
            end = datetime.datetime(year + 1, 1, 1)
        elif m == 4:
            end = datetime.datetime(year, 5, 1)
        else:
            end = datetime.datetime(year, m + 1, 1)
        yield start, end


def _to_plain(o):
    import datetime as _dt
    if isinstance(o, (_dt.datetime, _dt.date)):
        return o.isoformat()
    if isinstance(o, (list, tuple)):
        return [_to_plain(x) for x in o]
    if isinstance(o, dict):
        return {k: _to_plain(v) for k, v in o.items()}
    if hasattr(o, "__dict__") and not isinstance(o, (str, int, float, bool)):
        return _to_plain(vars(o))
    if isinstance(o, (str, int, float, bool)) or o is None:
        return o
    return str(o)


def dump_rows(path: Path, rows) -> int:
    n = 0
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(_to_plain(r.__dict__)) + "\n")
            n += 1
    return n


def pull_raw(seasons: list[int]) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    gapi = cbbd.GamesApi(client())
    lapi = cbbd.LinesApi(client())
    tapi = cbbd.TeamsApi(client())
    for season in seasons:
        all_games, all_box, all_lines = [], [], []
        seen_g, seen_b, seen_l = set(), set(), set()
        for start, end in month_windows(season):
            games = gapi.get_games(season=season, start_date_range=start,
                                   end_date_range=end)
            for g in games:
                if g.id not in seen_g:
                    seen_g.add(g.id)
                    all_games.append(g)
            box = gapi.get_game_teams(season=season, start_date_range=start,
                                      end_date_range=end)
            for b in box:
                kk = (b.game_id, b.team_id)
                if kk not in seen_b:
                    seen_b.add(kk)
                    all_box.append(b)
            lines = lapi.get_lines(season=season, start_date_range=start,
                                   end_date_range=end)
            for ln in lines:
                if ln.game_id not in seen_l:
                    seen_l.add(ln.game_id)
                    all_lines.append(ln)
            time.sleep(0.2)
        ng = dump_rows(RAW / f"games_{season}.jsonl", all_games)
        nb = dump_rows(RAW / f"box_{season}.jsonl", all_box)
        nl = dump_rows(RAW / f"lines_{season}.jsonl", all_lines)
        # D1 membership for the season
        teams = tapi.get_teams(season=season)
        d1 = sorted({t.school for t in teams} if teams else set())
        (RAW / f"d1_{season}.json").write_text(json.dumps(d1))
        print(f"season {season}: games={ng} boxrows={nb} lines={nl} d1={len(d1)}",
              flush=True)


def _pace_of(b: dict) -> float | None:
    p = b.get("pace")
    return float(p) if p else None


def _points_of(stats: dict) -> float | None:
    pts = (stats or {}).get("points") or {}
    t = pts.get("total")
    return float(t) if t is not None else None


def build_games_csv(seasons: list[int]) -> None:
    fieldnames = ["date", "season", "season_type", "home_team", "away_team",
                  "home_score", "away_score", "neutral", "poss",
                  "spread", "total", "n_books"]
    n_in, n_d1, n_lines = 0, 0, 0
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for season in seasons:
            d1 = set(json.loads((RAW / f"d1_{season}.json").read_text()))
            games = {}
            for line in (RAW / f"games_{season}.jsonl").read_text().splitlines():
                g = json.loads(line)
                games[g["id"]] = g
            pace: dict[int, dict[str, float]] = {}
            for line in (RAW / f"box_{season}.jsonl").read_text().splitlines():
                b = json.loads(line)
                p = _pace_of(b)
                if p is None:
                    continue
                pace.setdefault(b["game_id"], {})[b["team"]] = p
            lines: dict[int, list[dict]] = {}
            for line in (RAW / f"lines_{season}.jsonl").read_text().splitlines():
                ln = json.loads(line)
                lines[ln["game_id"]] = ln["lines"]
            for gid, g in sorted(games.items(),
                                 key=lambda kv: kv[1]["start_date"]):
                n_in += 1
                if g.get("status") != "final":
                    continue
                if str(g.get("season_type", "")).lower() == "preseason":
                    continue  # exhibitions never train or backtest the model
                home, away = g["home_team"], g["away_team"]
                if home not in d1 or away not in d1:
                    continue  # D1-only, mirrors the CFB FBS-only rule
                n_d1 += 1
                hs, aws = g.get("home_points"), g.get("away_points")
                if hs is None or aws is None:
                    continue
                paces = pace.get(gid, {})
                poss_vals = [v for k, v in paces.items()
                             if k in (home, away) and v > 0]
                poss = (sum(poss_vals) / len(poss_vals)
                        if poss_vals else None)
                spreads, totals = [], []
                for ln in lines.get(gid, []):
                    if ln.get("spread") is not None:
                        # CBBD sign: positive raw = AWAY favored -> negate
                        # once for the home-margin convention.
                        spreads.append(-float(ln["spread"]))
                    if ln.get("over_under") is not None:
                        totals.append(float(ln["over_under"]))
                spread = (statistics.median(spreads) if spreads else None)
                total = (statistics.median(totals) if totals else None)
                n_books = len(lines.get(gid, []))
                if spread is not None:
                    n_lines += 1
                dt = datetime.datetime.fromisoformat(
                    g["start_date"]).astimezone(PT)
                w.writerow({
                    "date": dt.date().isoformat(),
                    "season": season,
                    "season_type": str(g.get("season_type", "")).lower(),
                    "home_team": home, "away_team": away,
                    "home_score": hs, "away_score": aws,
                    "neutral": "1" if g.get("neutral_site") else "0",
                    "poss": f"{poss:.1f}" if poss else "",
                    "spread": f"{spread:.1f}" if spread is not None else "",
                    "total": f"{total:.1f}" if total is not None else "",
                    "n_books": n_books,
                })
    print(f"games.csv: {n_in} raw finals -> {n_d1} D1 finals, "
          f"{n_lines} with closing lines -> {OUT}")


def parse_seasons(spec: str) -> list[int]:
    seasons: list[int] = []
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            seasons.extend(range(int(lo), int(hi) + 1))
        elif part:
            seasons.append(int(part))
    return seasons


def main() -> None:
    ap = argparse.ArgumentParser(description="Pull CBBD data, build games.csv")
    ap.add_argument("--seasons", default="2010-2026",
                    help="season ranges, e.g. '2010-2021,2025-2026' "
                         "(ending years)")
    ap.add_argument("--raw-only", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    args = ap.parse_args()
    seasons = parse_seasons(args.seasons)
    if not args.build_only:
        pull_raw(seasons)
    if not args.raw_only:
        build_games_csv(seasons)


if __name__ == "__main__":
    main()
