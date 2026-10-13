"""Step 1: scrape PFR yearly All-Pro pages -> allpro_stars.csv

One row per (season, player): AP 1st-team All-Pros at non-QB, non-specialist
positions. The `season` here is the All-Pro season; the player counts as a
"star" for the FOLLOWING season's games (knowable pre-season, no lookahead).

Source: https://www.pro-football-reference.com/years/{YYYY}/allpro.htm
Filter: data-stat="all_pro_string" contains "AP: 1st Tm".

Position groups:
  skill   = RB, FB, WR, TE
  ol      = T, G, C
  defense = DE, DT, NT, LB, EDGE, OLB, ILB, CB, S, DB
Excluded (documented): QB (already modeled), K, P, KR, PR, LS, ST.

Output columns: ap_season, player, pos, pos_group, team_abbr, player_slug
(player_slug like /players/M/McCaCh01.htm -> McCaCh01 for gamelog scraping).
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent
CSV = OUT / "allpro_stars.csv"

AP_FIRST = 1979   # stars for 1980 games
AP_LAST = 2023    # stars for 2024 games

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) honest-line-research/1.0"}

SKILL = {"RB", "FB", "WR", "TE"}
OL = {"T", "G", "C", "OT", "OG"}
DEF = {"DE", "DT", "NT", "LB", "EDGE", "OLB", "ILB", "CB", "S", "DB", "SS", "FS"}
EXCLUDE = {"QB", "K", "P", "KR", "PR", "LS", "ST"}


def pos_group(pos: str) -> str | None:
    p = pos.strip().upper()
    # normalize sided/era variants: LT/RT->T, LG/RG->G, LDE/RDE->DE, etc.
    # MLB here = Middle LineBacker (not baseball)
    p = (p.replace("LDE", "DE").replace("RDE", "DE")
          .replace("LDT", "DT").replace("RDT", "DT")
          .replace("LCB", "CB").replace("RCB", "CB")
          .replace("LT", "T").replace("RT", "T")
          .replace("LG", "G").replace("RG", "G")
          .replace("MLB", "LB").replace("LILB", "LB").replace("RILB", "LB")
          .replace("LLB", "LB").replace("RLB", "LB")
          .replace("LOLB", "LB").replace("ROLB", "LB"))
    p = p.replace("CB/SS", "DB").replace("SS", "S").replace("FS", "S")
    # compound slash positions (era variants): map by first known component
    if "/" in p:
        for part in p.split("/"):
            g = pos_group(part)
            if g is not None:
                return g
        return None
    if p in SKILL:
        return "skill"
    if p in OL:
        return "ol"
    if p in DEF:
        return "defense"
    if p in EXCLUDE:
        return None
    return None  # unknown -> excluded, logged


def scrape_year(year: int) -> list[dict]:
    url = f"https://www.pro-football-reference.com/years/{year}/allpro.htm"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table", id="all_pro")
    if table is None:
        raise RuntimeError(f"no #all_pro table for {year}")
    rows = []
    unknown_pos: set[str] = set()
    for tr in table.find("tbody").find_all("tr"):
        tds = {td.get("data-stat"): td for td in tr.find_all("td")}
        ap_str = tds.get("all_pro_string")
        if ap_str is None or "AP: 1st Tm" not in ap_str.get_text():
            continue
        pos_th = tr.find("th", {"data-stat": "pos"})
        pos = pos_th.get_text(strip=True) if pos_th else ""
        grp = pos_group(pos)
        if grp is None:
            if pos not in EXCLUDE:
                unknown_pos.add(pos)
            continue
        ptd = tds.get("player")
        a = ptd.find("a") if ptd is not None else None
        href = a.get("href", "") if a is not None else ""
        m = re.search(r"/players/[A-Z]/([A-Za-z0-9.]+)\.htm", href)
        slug = m.group(1) if m else ""
        ttd = tds.get("team")
        rows.append(
            {
                "ap_season": year,
                "player": ptd.get_text(strip=True) if ptd is not None else "",
                "pos": pos,
                "pos_group": grp,
                "team_abbr": ttd.get_text(strip=True) if ttd is not None else "",
                "player_slug": slug,
            }
        )
    if unknown_pos:
        print(f"  {year}: unknown positions excluded: {sorted(unknown_pos)}")
    return rows


def main() -> None:
    all_rows: list[dict] = []
    for year in range(AP_FIRST, AP_LAST + 1):
        rows = scrape_year(year)
        print(f"{year}: {len(rows)} AP 1st-team non-QB/non-specialist stars")
        all_rows.extend(rows)
        time.sleep(2)  # be polite
    df = pd.DataFrame(all_rows)
    # dedupe: same player listed twice at one position (shouldn't happen for AP 1st team)
    before = len(df)
    df = df.drop_duplicates(subset=["ap_season", "player_slug"]).reset_index(drop=True)
    if len(df) != before:
        print(f"deduped {before - len(df)} rows")
    missing_slug = int((df["player_slug"] == "").sum())
    print(f"rows missing player slug: {missing_slug}")
    df.to_csv(CSV, index=False)
    print(f"wrote {CSV} ({len(df)} rows)")
    print(df["pos_group"].value_counts().to_string())


if __name__ == "__main__":
    main()
