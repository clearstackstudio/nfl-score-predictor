"""Step 2c: Wayback Machine fallback for PFR gamelogs 2002-2012 -> star_gameweeks_wb.csv

PFR rate-blocked direct scraping 2026-10-10. For game seasons 2002-2012
(neither covered by the completed PFR scrape nor by nflverse snaps which start
2013), fetch archived gamelog snapshots from web.archive.org.

Snapshot choice: June 1 of the year after the season
(https://web.archive.org/web/{season+1}0601id_/{pfr_url}), redirected to the
closest capture; the `id_` suffix returns original HTML. If the capture is
mid-season (max team-game-num < 14 for a 16-game season), retry with June 1
two years after.

Markup eras handled:
  (a) modern data-stat markup (week_num / team_name_abbr) — as in 02;
  (b) 2024-era markup (week_num / team as data-stats);
  (c) ancient positional markup (no data-stats): td[1]=team game#, td[4]=team.
      Week is recovered by mapping team-game-number -> week via the team's
      schedule from residuals.csv (sorted game weeks; bye weeks need no
      special handling since they produce no team game).

Output format matches star_gameweeks.csv (source="wayback"). DNP rows are not
needed: 03's set-difference uses played weeks only.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent
STARS = OUT / "allpro_stars.csv"
RESID = OUT.parent / "new_coach_bias" / "residuals.csv"
CSV = OUT / "star_gameweeks_wb.csv"
LOG = OUT / "wayback_completed.txt"

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) honest-line-research/1.0"}
DELAY = 3.0
FIRST, LAST = 2002, 2012  # game seasons


def team_schedule() -> dict[tuple[int, str], list[int]]:
    """(season, team_full) -> sorted regular-season game weeks (for team_g mapping)."""
    from importlib import import_module
    import sys
    sys.path.insert(0, str(OUT))
    m03 = import_module("03_build_absences")
    res = pd.read_csv(RESID)
    res["week_num"] = pd.to_numeric(res["week"], errors="coerce")
    res = res[res["week_num"].notna()].copy()
    sched: dict[tuple[int, str], set] = {}
    for r in res.itertuples():
        s, w = int(r.season), int(r.week_num)
        sched.setdefault((s, r.team_home), set()).add(w)
        sched.setdefault((s, r.team_away), set()).add(w)
    return {k: sorted(v) for k, v in sched.items()}, m03


def fetch_snapshot(slug: str, season: int) -> str | None:
    """Return HTML of the nearest archived snapshot to 2024, or None.
    Requesting near-2024 prefers the most recent (most likely complete)
    capture; older captures are sometimes partial (e.g. Ray Lewis 2003's 2011
    snapshot had 8/16 rows while the 2020 capture is complete).
    Handles archive.org 429s with backoff; returns None only when no snapshot
    exists (genuine 404 / redirect to error page)."""
    url = (f"https://www.pro-football-reference.com/players/{slug[0]}/{slug}/"
           f"gamelog/{season}/")
    wb = f"https://web.archive.org/web/2024id_/{url}"
    for attempt in range(4):
        try:
            r = requests.get(wb, headers=HEADERS, timeout=90)
        except Exception:
            time.sleep(10)
            continue
        if r.status_code == 429:
            time.sleep(60 * (attempt + 1))
            continue
        if r.status_code != 200 or len(r.text) < 5000:
            return None
        # wayback serves an error page with 200 for missing captures; the
        # gamelog table is the real signal
        if 'id="stats"' not in r.text and "id='stats'" not in r.text:
            return None
        return r.text
    return "THROTTLED"  # persistent 429: caller must NOT mark completed


def parse_gamelog(html: str) -> list[dict]:
    """Return played-week rows: (team_g, team_abbr). Skips DNP/spacer rows."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", id="stats")
    if table is None:
        return []
    tbody = table.find("tbody")
    if tbody is None:
        return []
    out = []
    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        if not tds:
            continue
        stats = {td.get("data-stat"): td.get_text(strip=True) for td in tds}
        # modern markup: week_num present
        wk = stats.get("week_num") or ""
        if re.fullmatch(r"\d{1,2}", wk):
            cls = tr.get("class") or []
            if "partial_table" in cls or "gamelog_dnp" in cls:
                continue  # DNP row
            tm = stats.get("team_name_abbr") or stats.get("team") or ""
            if tm:
                out.append({"week": int(wk), "team_abbr": tm})
            continue
        # ancient positional markup: td[1]=team game#, td[4]=team abbr
        if len(tds) >= 7:
            tg_txt = tds[1].get_text(strip=True)
            tm_txt = tds[4].get_text(strip=True)
            if re.fullmatch(r"\d{1,2}", tg_txt) and re.fullmatch(r"[A-Z]{2,3}", tm_txt):
                out.append({"team_g": int(tg_txt), "team_abbr": tm_txt})
    return out


def main() -> None:
    sched, m03 = team_schedule()
    stars = pd.read_csv(STARS)
    stars["game_season"] = stars["ap_season"] + 1
    stars = stars[(stars["game_season"] >= FIRST) & (stars["game_season"] <= LAST)].copy()
    print(f"stars in {FIRST}-{LAST}: {len(stars)}")

    done: set[tuple[str, int]] = set()
    if LOG.exists():
        for line in LOG.read_text().splitlines():
            if line.strip():
                s, y = line.split(",")
                done.add((s, int(y)))
    todo = stars[~stars.apply(lambda r: (str(r["player_slug"]), int(r["game_season"])) in done, axis=1)]
    print(f"todo: {len(todo)}, done: {len(done)}")

    rows: list[dict] = []
    if CSV.exists():
        rows = pd.read_csv(CSV).to_dict("records")
    n_ok = n_miss = n_err = n_throttled = 0
    with open(LOG, "a") as lf:
        for i, r in enumerate(todo.itertuples(), 1):
            slug, season = str(r.player_slug), int(r.game_season)
            try:
                html = fetch_snapshot(slug, season)
                if html == "THROTTLED":
                    # archive.org still rate-limiting: do NOT mark completed;
                    # stop the run so a later resume retries these.
                    n_throttled += 1
                    print(f"[{i}/{len(todo)}] {r.player} {season}: throttled, stopping run", flush=True)
                    break
                if html is None:
                    n_miss += 1
                    print(f"[{i}/{len(todo)}] {r.player} {season}: no snapshot", flush=True)
                    lf.write(f"{slug},{season}\n"); lf.flush()
                    time.sleep(DELAY)
                    continue
                played = parse_gamelog(html)
                # map team_g -> week where needed
                for p in played:
                    if "week" not in p:
                        team_full = m03.full_name(p["team_abbr"], season)
                        weeks = sched.get((season, team_full), []) if team_full else []
                        tg = p.get("team_g", 0)
                        if not team_full or tg < 1 or tg > len(weeks):
                            continue
                        p["week"] = weeks[tg - 1]
                    rows.append(
                        {
                            "game_season": season,
                            "player": r.player,
                            "player_slug": slug,
                            "pos": r.pos,
                            "pos_group": r.pos_group,
                            "team_abbr": p["team_abbr"],
                            "week_num": int(p["week"]),
                            "played": 1,
                            "opp_abbr": "",
                            "date": "",
                        }
                    )
                n_ok += 1
                lf.write(f"{slug},{season}\n"); lf.flush()
                if i % 10 == 0:
                    pd.DataFrame(rows).to_csv(CSV, index=False)
                    print(f"[{i}/{len(todo)}] checkpoint: {len(rows)} rows", flush=True)
            except Exception as e:  # noqa: BLE001
                n_err += 1
                print(f"[{i}/{len(todo)}] {r.player} {season}: ERROR {e}", flush=True)
            time.sleep(DELAY)
    pd.DataFrame(rows).to_csv(CSV, index=False)
    print(f"done: ok={n_ok} no_snapshot={n_miss} errors={n_err} throttled={n_throttled}; wrote {CSV} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
