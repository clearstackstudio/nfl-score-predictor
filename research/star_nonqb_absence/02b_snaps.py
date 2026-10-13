"""Step 2b: nflverse snap counts for star-seasons 2012-2024 -> star_gameweeks_snaps.csv

Fallback for the PFR gamelog scrape (PFR rate-blocked us 2026-10-10 after ~500
players). nflverse snap counts (2012+) list weekly snaps per player; a star
with no snap row (or 0 snaps) for a week his team played did not play.

Source: https://github.com/nflverse/nflverse-data/releases/download/snap_counts/snap_counts_{YYYY}.csv
Join to allpro_stars on pfr_player_id == player_slug.

Output format matches star_gameweeks.csv:
  game_season, player, player_slug, pos, pos_group, team_abbr (nflverse),
  week_num, played (1 = snaps>0), opp_abbr (""), date ("")
Only REG game_type weeks. Bye weeks have no row (same as gamelogs).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
STARS = OUT / "allpro_stars.csv"
CSV = OUT / "star_gameweeks_snaps.csv"
CACHE = OUT / "snaps_cache"
CACHE.mkdir(exist_ok=True)

FIRST, LAST = 2013, 2024


def fetch(year: int) -> pd.DataFrame:
    path = CACHE / f"snap_counts_{year}.csv"
    if not path.exists():
        url = (f"https://github.com/nflverse/nflverse-data/releases/download/"
               f"snap_counts/snap_counts_{year}.csv")
        subprocess.run(["curl", "-sL", "--max-time", "180", url, "-o", str(path)],
                       check=True)
    return pd.read_csv(path, low_memory=False)


def main() -> None:
    stars = pd.read_csv(STARS)
    stars["game_season"] = stars["ap_season"] + 1
    stars = stars[(stars["game_season"] >= FIRST) & (stars["game_season"] <= LAST)].copy()
    print(f"stars in {FIRST}-{LAST}: {len(stars)}")

    rows: list[dict] = []
    for year in range(FIRST, LAST + 1):
        df = fetch(year)
        reg = df[df["game_type"] == "REG"].copy()
        sub = stars[stars["game_season"] == year]
        slugs = set(sub["player_slug"].astype(str))
        hit = reg[reg["pfr_player_id"].astype(str).isin(slugs)]
        print(f"{year}: {len(reg)} reg rows, {hit['pfr_player_id'].nunique()} stars found")
        meta = sub.set_index("player_slug")
        for r in hit.itertuples():
            slug = str(r.pfr_player_id)
            m = meta.loc[slug]
            if isinstance(m, pd.DataFrame):  # same slug twice (shouldn't happen)
                m = m.iloc[0]
            snaps = float(r.offense_snaps or 0) + float(r.defense_snaps or 0) + float(r.st_snaps or 0)
            rows.append(
                {
                    "game_season": year,
                    "player": m["player"],
                    "player_slug": slug,
                    "pos": m["pos"],
                    "pos_group": m["pos_group"],
                    "team_abbr": str(r.team),
                    "week_num": int(r.week),
                    "played": int(snaps > 0),
                    "opp_abbr": "",
                    "date": "",
                }
            )
    out = pd.DataFrame(rows)
    # stars with no snap rows at all (retired / no 2012+ season) -> nothing to record
    found = set(out["player_slug"].astype(str)) if len(out) else set()
    missing = set(stars["player_slug"].astype(str)) - found
    print(f"gameweek rows: {len(out)}; stars with no snap rows: {len(missing)}")
    out.to_csv(CSV, index=False)
    print(f"wrote {CSV}")


if __name__ == "__main__":
    main()
