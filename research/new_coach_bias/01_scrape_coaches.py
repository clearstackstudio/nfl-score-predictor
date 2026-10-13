"""Step 1: scrape PFR franchise year-by-year tables -> coaches.csv

One row per (franchise, season): season opening-era team name, coach slugs in
PFR listed order, multi-coach flag. Does NOT decide new-coach status here;
that's step 2 (needs year-over-year comparison + manual corrections).

Source: https://www.pro-football-reference.com/teams/{franchise}/
PFR coach URL slugs (e.g. /coaches/kitcFr0.htm) uniquely identify people,
which also powers the first-timer-vs-retread split later.
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

OUT = Path(__file__).resolve().parent
CSV = OUT / "coaches_raw.csv"

# Current PFR franchise ids (era-spanning pages)
FRANCHISES = [
    "crd", "atl", "rav", "buf", "car", "chi", "cin", "cle", "dal", "den",
    "det", "gnb", "htx", "clt", "jax", "kan", "sdg", "ram", "rai", "mia",
    "min", "nwe", "nor", "nyg", "nyj", "phi", "pit", "sfo", "sea", "tam", "oti",
    "was",
]

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) honest-line-research/1.0"}


def scrape_franchise(f: str) -> list[dict]:
    url = f"https://www.pro-football-reference.com/teams/{f}/"
    r = requests.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    table = soup.find("table", id="team_index")
    if table is None:
        raise RuntimeError(f"no #teams table for {f}")
    rows = []
    for tr in table.find("tbody").find_all("tr"):
        year_th = tr.find("th", {"data-stat": "year_id"})
        if year_th is None:
            continue
        year = year_th.get_text(strip=True)
        if not re.fullmatch(r"\d{4}", year):
            continue  # header/repeat rows
        tm_td = tr.find("td", {"data-stat": "team"})
        team = tm_td.get_text(strip=True).rstrip("*") if tm_td else ""
        coach_td = tr.find("td", {"data-stat": "coaches"})
        coaches: list[tuple[str, str]] = []  # (slug, last_name) in PFR listed order
        if coach_td:
            for a in coach_td.find_all("a"):
                href = a.get("href", "")
                m = re.search(r"/coaches/([A-Za-z0-9]+)\.htm", href)
                if m:
                    coaches.append((m.group(1), a.get_text(strip=True)))
            if not coaches:
                # plain text, no links (rare) -> slug unknown
                txt = coach_td.get_text(strip=True)
                for last in [p.strip() for p in txt.split(",") if p.strip()]:
                    coaches.append(("", last))
        rows.append(
            {
                "franchise": f,
                "season": int(year),
                "team_name": team,
                "n_coaches": len(coaches),
                "coach_slugs": "|".join(s for s, _ in coaches),
                "coach_names": "|".join(n for _, n in coaches),
                "multi_coach": int(len(coaches) > 1),
            }
        )
    return rows


def main() -> None:
    all_rows: list[dict] = []
    for f in FRANCHISES:
        rows = scrape_franchise(f)
        print(f"{f}: {len(rows)} seasons ({min(r['season'] for r in rows)}-{max(r['season'] for r in rows)})")
        all_rows.extend(rows)
        time.sleep(2)  # be polite
    df = pd.DataFrame(all_rows).sort_values(["franchise", "season"]).reset_index(drop=True)
    df.to_csv(CSV, index=False)
    print(f"wrote {CSV} ({len(df)} rows)")
    print("multi-coach seasons:", int(df["multi_coach"].sum()))
    print("seasons missing slug:", int((df["coach_slugs"] == "").sum()))


if __name__ == "__main__":
    main()
