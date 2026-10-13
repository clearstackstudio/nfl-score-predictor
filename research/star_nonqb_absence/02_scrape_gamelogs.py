"""Step 2: scrape PFR gamelogs for each star-season -> star_absences.csv

For each (ap_season, player_slug) in allpro_stars.csv, fetch the gamelog for
the FOLLOWING season (game_season = ap_season + 1):

  https://www.pro-football-reference.com/players/{X}/{slug}/gamelog/{YYYY}/

A missed game = <tr class="partial_table"> with a numeric week_num.
Played rows carry id="stats.N". Bye weeks produce no row at all.

Output: star_gameweeks.csv — one row per star player-season team-game week:
  game_season, player, player_slug, pos, pos_group, team_abbr (PFR abbr that
  week), week_num, played (1/0), opp_abbr, date
A missed game = <tr class="partial_table"> with a numeric week_num (played=0);
played rows carry id="stats.N" (played=1). Bye weeks produce no row at all.

Resume-safe: skips (slug, season) already in gamelog_completed.txt.
Run with --fresh to restart.

Rate: 3s between requests (~950 player-seasons -> ~50 min).
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent
STARS = OUT / "allpro_stars.csv"
CSV = OUT / "star_gameweeks.csv"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) honest-line-research/1.0"}
DELAY = 6.0  # raised after 2026-10-10 PFR 403 block; be extra polite
CHECKPOINT_EVERY = 10


def scrape_gamelog(slug: str, season: int) -> list[dict]:
    """All team-game weeks for this player-season. played=1 for played rows,
    played=0 for partial_table (DNP) rows."""
    letter = slug[0]
    url = f"https://www.pro-football-reference.com/players/{letter}/{slug}/gamelog/{season}/"
    r = requests.get(url, headers=HEADERS, timeout=60)
    if r.status_code == 404:
        return []  # no gamelog (retired / did not play that season)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table", id="stats")
    if table is None:
        # No gamelog table: player did not play that season (retired, or
        # season-long absence with no page). Treated as no season; the
        # player-season contributes no absence rows. Logged by the caller.
        print(f"  note: no #stats table for {slug} {season} (did not play)", flush=True)
        return []
    weeks = []
    for tr in table.find("tbody").find_all("tr"):
        tds = {td.get("data-stat"): td for td in tr.find_all("td")}
        wk = tds.get("week_num")
        week_txt = wk.get_text(strip=True) if wk is not None else ""
        if not re.fullmatch(r"\d{1,2}", week_txt):
            continue  # header-ish / non-week row
        classes = tr.get("class") or []
        played = 0 if "partial_table" in classes else 1
        tm = tds.get("team_name_abbr")
        opp = tds.get("opp_name_abbr")
        dt = tds.get("date")
        weeks.append(
            {
                "team_abbr": tm.get_text(strip=True) if tm is not None else "",
                "week_num": int(week_txt),
                "played": played,
                "opp_abbr": opp.get_text(strip=True) if opp is not None else "",
                "date": dt.get_text(strip=True) if dt is not None else "",
            }
        )
    return weeks


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args()

    stars = pd.read_csv(STARS)
    stars["game_season"] = stars["ap_season"] + 1

    done: set[tuple[str, int]] = set()
    rows: list[dict] = []
    completed_path = OUT / "gamelog_completed.txt"
    if CSV.exists() and not args.fresh:
        prev = pd.read_csv(CSV)
        rows = prev.to_dict("records")
        csv_done = set(zip(prev["player_slug"].astype(str), prev["game_season"].astype(int)))
    else:
        csv_done = set()
    # Resume is safe only for players present in BOTH the completed log and the
    # CSV (a kill between the per-player log flush and the CSV checkpoint would
    # otherwise silently drop that player's rows). Players in the log but not
    # the CSV are re-scraped.
    completed: set[tuple[str, int]] = set()
    if completed_path.exists() and not args.fresh:
        for line in completed_path.read_text().splitlines():
            if not line.strip():
                continue
            s, y = line.split(",")
            completed.add((s, int(y)))
    done = completed & csv_done
    n_rescrape = len(completed - csv_done)
    if n_rescrape:
        print(f"re-scraping {n_rescrape} players logged-but-not-checkpointed")

    todo = stars[~stars.apply(lambda r: (str(r["player_slug"]), int(r["game_season"])) in done, axis=1)]
    print(f"stars: {len(stars)}, todo: {len(todo)}, already done: {len(done)}", flush=True)

    n_new = 0
    with open(completed_path, "a") as comp_f:
        for i, r in enumerate(todo.itertuples(), 1):
            slug = str(r.player_slug)
            season = int(r.game_season)
            try:
                if not slug:
                    gameweeks = []
                else:
                    gameweeks = scrape_gamelog(slug, season)
            except Exception as e:  # noqa: BLE001 - log and continue; rerun resumes
                print(f"[{i}/{len(todo)}] {r.player} {season}: ERROR {e}")
                time.sleep(DELAY)
                continue
            for m in gameweeks:
                rows.append(
                    {
                        "game_season": season,
                        "player": r.player,
                        "player_slug": slug,
                        "pos": r.pos,
                        "pos_group": r.pos_group,
                        "team_abbr": m["team_abbr"],
                        "week_num": m["week_num"],
                        "played": m["played"],
                        "opp_abbr": m["opp_abbr"],
                        "date": m["date"],
                    }
                )
                n_new += 1
            comp_f.write(f"{slug},{season}\n")
            comp_f.flush()
            if i % CHECKPOINT_EVERY == 0:
                pd.DataFrame(rows).to_csv(CSV, index=False)
                print(f"[{i}/{len(todo)}] checkpoint: {len(rows)} gameweek rows", flush=True)
            time.sleep(DELAY)

    pd.DataFrame(rows).to_csv(CSV, index=False)
    print(f"wrote {CSV} ({len(rows)} gameweek rows, {n_new} new this run)")


if __name__ == "__main__":
    main()
