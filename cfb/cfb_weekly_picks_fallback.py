"""Week 8 fallback CFB picks (2026-10-24, Bryant-approved one-off).

The normal generator (cfb_weekly_picks.py) pulls the schedule + lines from
the CFBD API, which hit its monthly quota (429) until ~Nov 1 — the board
 froze at Week 6. This fallback changes ONLY the data sources:

  - Ratings: local data, exactly as cfb_weekly_picks.current_ratings does
    (PPA through Week 6 — the last week CFBD delivered).
  - Schedule: ESPN's public scoreboard (FBS group 80), pre-kickoff only.
  - Lines: The Odds API (americanfootball_ncaaf, spreads + totals),
    median across US books. The Odds API spread for a team is that team's
    points (negative = favored), so the home-margin line is
    -median(home points) — cross-checked against ESPN's own odds details
    on 6 games before use (signs and magnitudes agreed).

Model math, thresholds, recalibration, total circuit breaker, wind hinge,
and output schema are the normal pipeline's, imported unchanged. The
parlay stays unpublished (PUBLISH_PARLAY=False upstream). Nothing here
calls CFBD.
"""
from __future__ import annotations

import json
import statistics
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.append(str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")

from cfb_ratings import REPO, load_team_games, predict  # noqa: E402
from cfb_weekly_picks import (  # noqa: E402
    TOTAL_CIRCUIT, _gameday_et, current_ratings, normal_cdf,
    pick_spread_label, pick_total_label, wind_adjustment)
from recalibration import recalibrate  # noqa: E402
from dynamic_credentials import (  # noqa: E402
    read_json_response, url_with_surrogate_query_param)

DATA = REPO / "data" / "cfb"
SEASON = 2026
WEEK = 8

# Odds API full names that the generic prefix matcher cannot resolve to
# the model's (CFBD) team names. Verified identities, 2026-10-24.
ODDS_ALIASES = {
    "Hawaii Rainbow Warriors": "Hawai'i",
    "Southern Mississippi Golden Eagles": "Southern Miss",
}


def norm(name: str) -> str:
    """Same normalization the ESPN backfill proved against model names."""
    import re
    import unicodedata
    s = unicodedata.normalize("NFKD", str(name))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower().replace("&", "and")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def fetch_espn_pre_games() -> list:
    """Week 8 games ESPN still marks pre-kickoff, today and tomorrow (ET)."""
    now_et = pd.Timestamp.now("America/New_York")
    out, seen = [], set()
    for day in (now_et, now_et + pd.Timedelta(days=1)):
        url = ("https://site.api.espn.com/apis/site/v2/sports/football/"
               "college-football/scoreboard?dates="
               f"{day.strftime('%Y%m%d')}&groups=80&limit=300")
        with urllib.request.urlopen(url, timeout=30) as r:
            d = json.load(r)
        for e in d.get("events", []):
            if e["id"] in seen:
                continue
            seen.add(e["id"])
            wk = (e.get("week") or {}).get("number")
            if wk is not None and wk != WEEK:
                continue
            if e["status"]["type"]["state"] != "pre":
                continue
            out.append(e)
    return out


def fetch_odds() -> list:
    base = ("https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf"
            "/odds/?regions=us&markets=spreads,totals&oddsFormat=american")
    url = url_with_surrogate_query_param(
        base, "custom.the-odds-api", allowed_hosts=("api.the-odds-api.com",))
    req = urllib.request.Request(url, headers={"User-Agent": "honest-line/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return read_json_response(resp)


def main() -> None:
    build_start = pd.Timestamp.now("UTC")
    team_games = load_team_games()
    off, deff, pace = current_ratings(team_games, SEASON)

    g26 = team_games[team_games["season"] == SEASON]
    ratings_note = (f"weeks {sorted(g26['week'].unique())} in local data; "
                    f"last PPA week = {int(g26['week'].max())}")
    print(f"ratings input: {ratings_note}")

    cfg = json.loads((DATA / "cfb_backtest.json").read_text())
    margin_sd, total_sd = cfg["margin_sd"], cfg.get("total_sd", 12.0)

    done = pd.read_parquet(DATA / "cfb_games.parquet")
    done = done[(done["season"] == SEASON) & done["home_score"].notna()]
    epa_const = float((done["home_score"] + done["away_score"]).mean()) \
        if len(done) else 58.0

    model_teams = sorted(set(done["home_team"]) | set(done["away_team"])
                         | set(pd.read_parquet(DATA / "cfb_games.parquet")
                               .query("season < 2026")["home_team"]))
    all_games = pd.read_parquet(DATA / "cfb_games.parquet")
    model_teams = sorted(set(all_games["home_team"]) | set(all_games["away_team"]))
    by_norm = {}
    for t in model_teams:
        by_norm.setdefault(norm(t), t)

    def match_odds_name(full: str):
        if full in ODDS_ALIASES:
            return ODDS_ALIASES[full]
        n = norm(full)
        cands = [t for t in model_teams
                 if n == norm(t) or n.startswith(norm(t) + " ")]
        return max(cands, key=lambda t: len(norm(t))) if cands else None

    odds_events = fetch_odds()
    odds_by_pair = {}
    for g in odds_events:
        h, a = match_odds_name(g["home_team"]), match_odds_name(g["away_team"])
        if h and a:
            odds_by_pair[(a, h)] = g

    espn_games = fetch_espn_pre_games()
    print(f"ESPN pre-kickoff week {WEEK} games: {len(espn_games)}")

    picks, drops = [], []
    for e in espn_games:
        comp = e["competitions"][0]
        by = {c["homeAway"]: c for c in comp["competitors"]}
        home = by_norm.get(norm(by["home"]["team"]["location"]))
        away = by_norm.get(norm(by["away"]["team"]["location"]))
        label = f"{by['away']['team']['location']} @ {by['home']['team']['location']}"
        if not home or not away:
            drops.append((label, "ESPN name did not match a model team"))
            continue
        og = odds_by_pair.get((away, home))
        if og is None:
            drops.append((label, "no Odds API lines"))
            continue
        home_pts, totals = [], []
        for b in og.get("bookmakers", []):
            for m in b.get("markets", []):
                for o in m.get("outcomes", []):
                    if m["key"] == "spreads" and o["name"] == og["home_team"]:
                        home_pts.append(float(o["point"]))
                    if m["key"] == "totals" and o["name"] == "Over":
                        totals.append(float(o["point"]))
        if not home_pts or not totals:
            drops.append((label, "books missing spread or total"))
            continue
        # Home-margin convention (positive = home favored), verified
        # against ESPN's odds details: line = -median(home team points).
        line_margin = -statistics.median(home_pts)
        line_total = statistics.median(totals)
        neutral = bool(comp.get("neutralSite"))
        pr = predict(off, deff, pace, home, away, neutral, epa_const)
        if pr is None:
            drops.append((label, "no model rating for a team (FBS scope)"))
            continue
        our_margin, our_total = pr
        wind_mph, wind_adj = wind_adjustment(home, neutral, e.get("date", ""))
        our_total += wind_adj
        spread_edge = our_margin - line_margin
        total_edge = our_total - line_total
        pick_side = ("home" if spread_edge > 0 else "away") \
            if abs(spread_edge) >= 0.5 else None
        pick_total = ("over" if total_edge > 0 else "under") \
            if abs(total_edge) >= 1.0 else None
        cover_prob = recalibrate(normal_cdf(abs(spread_edge) / margin_sd),
                                 "cfb", "ats")
        ou_prob = recalibrate(normal_cdf(abs(total_edge) / total_sd),
                              "cfb", "totals")
        total_note = None
        if pick_total and abs(total_edge) > TOTAL_CIRCUIT:
            pick_total = None
            ou_prob = None
            total_note = ("No play — our total is too far from the market "
                          "to trust.")
        picks.append({
            "away": away, "home": home,
            "away_abbr": away, "home_abbr": home,
            **_gameday_et(e.get("date", "")),
            "neutral": neutral,
            "line_spread": round(line_margin, 1),
            "line_total": line_total,
            "our_spread": round(our_margin, 1),
            "our_total": round(our_total, 1),
            "wind_mph": wind_mph,
            "wind_adj_pts": wind_adj,
            "spread_edge": round(spread_edge, 1),
            "total_edge": round(total_edge, 1),
            "pick_spread": pick_side,
            "pick_total": pick_total,
            "pick_spread_label": pick_spread_label(pick_side, line_margin, home, away),
            "pick_total_label": pick_total_label(pick_total, line_total),
            "pick_total_note": total_note,
            "spread_labels": {
                "home": pick_spread_label("home", line_margin, home, away),
                "away": pick_spread_label("away", line_margin, home, away),
            },
            "cover_prob": round(cover_prob, 3) if pick_side else None,
            "ou_prob": round(ou_prob, 3) if pick_total else None,
            "_kickoff_utc": e.get("date", ""),
        })

    # Final pre-kickoff guard at write time: a game that kicked off while
    # we built the board is not picked — nothing retroactive, ever.
    now_utc = pd.Timestamp.now("UTC")
    kept = []
    for p in picks:
        if pd.Timestamp(p.pop("_kickoff_utc")) > now_utc:
            kept.append(p)
        else:
            drops.append((f"{p['away']} @ {p['home']}",
                          "kicked off during build"))
    picks = kept
    picks.sort(key=lambda p: (p["gameday"], p["away"], p["home"]))

    disclosure = (
        "Week 8 board, published from fallback data: our primary college "
        "feed hit its monthly limit, so team ratings run through Week 6, "
        "the schedule is ESPN's, and market lines come via The Odds API. "
        "Games that had already kicked off are not picked — nothing here "
        "was published after a kickoff. The normal feed resumes around "
        "Nov 1.")
    out = {
        "sport": "cfb", "season": SEASON, "week": WEEK,
        "generated": pd.Timestamp.now("America/Los_Angeles").strftime("%Y-%m-%d %H:%M %Z"),
        "stale_notice": disclosure,
        "disclaimer": ("Model probabilities for entertainment. Our backtest shows "
                       "no proven edge vs the closing line — track record published openly."),
        "parlay": None,
        "picks": picks,
    }
    dest = REPO / "site" / "data" / "cfb_picks.json"
    dest.write_text(json.dumps(out, indent=2))
    print(f"Week {WEEK}: {len(picks)} games -> {dest}")
    print(f"build window: {build_start} .. {now_utc}")
    for lbl, why in drops:
        print(f"  dropped: {lbl} — {why}")


if __name__ == "__main__":
    main()
