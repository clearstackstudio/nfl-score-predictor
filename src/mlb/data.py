"""Game-level loader for the MLB odds dataset.

The raw CSV (``~/workspace/nba-data/mlb_bonus/oddsDataMLB.csv``) stores each
game TWICE -- one row per team perspective -- and has NO home/away column.
This module pairs the two rows into one game record and derives home/away
from the park:

  * Regular parks map to their tenant club. The mapping was derived
    empirically from the data itself (the one club that appears in every
    game at that park), and matches the known real-world tenants, including
    the Blue Jays' 2021 temporary homes (Sahlen Field, TD Ballpark) and the
    Braves'/Rangers' park moves mid-sample.
  * Neutral-site parks (Tokyo Dome, London Stadium, Sydney Cricket Ground,
    Estadio Hiram Bithorn/Monterrey, Field of Dreams, Fort Bragg Field,
    TD Ameritrade Park, BB&T Ballpark at Bowman Field = the Williamsport
    Little League Classic) get ``neutral=True``: the model zeroes the home
    edge for these games. The home/away designation there is
    arbitrary-but-consistent (first row in file order), which is harmless
    once every home term is zeroed -- predictions and updates are symmetric.
  * Six 2017 hurricane-relocation games (Rays-Yankees at Citi Field,
    2017-09-11..13; Rangers-Astros at Tropicana Field, 2017-08-29..31) are
    also flagged neutral: they were played in another club's park.

Doubleheaders (same date + same team pair = 4 rows) are paired by matching
swapped scores. The single 2016 doubleheader whose two games had identical
scores (2016-06-07 NYM@PIT, both 3-1) pairs arbitrarily in file order --
harmless, since the two games are indistinguishable in the data.

Output columns: date, season, home, away, home_runs, away_runs, home_ml,
away_ml, total, over_odds, under_odds, park, neutral. Rows are sorted
chronologically (stable: file order within a date).

The 2020 season is the 60-game COVID season (449 games in the file). It is
handled naturally -- fewer games, same code path -- not special-cased.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent.parent
CSV = Path("/home/hatch/workspace/nba-data/mlb_bonus/oddsDataMLB.csv")

# Park -> home club, derived empirically from the data (club present in every
# game at the park) and cross-checked against real-world tenants.
PARK_HOME = {
    "AT&T Park": "SF",
    "Angel Stadium": "LAA",
    "Busch Stadium": "STL",
    "Camden Yards": "BAL",
    "Chase Field": "ARI",
    "Citi Field": "NYM",
    "Citizens Bank Park": "PHI",
    "Comerica Park": "DET",
    "Coors Field": "COL",
    "Dodger Stadium": "LAD",
    "Fenway Park": "BOS",
    "Globe Life Field": "TEX",
    "Great American Ballpark": "CIN",
    "Guaranteed Rate Field": "CWS",
    "Kauffman Stadium": "KC",
    "Marlins Park": "MIA",
    "Miller Park": "MIL",
    "Minute Maid Park": "HOU",
    "Nationals Park": "WSH",
    "Oakland Coliseum": "OAK",
    "PETCO Park": "SD",
    "PNC Park": "PIT",
    "Progressive Field": "CLE",
    "Rangers Ballpark": "TEX",
    "Rogers Centre": "TOR",
    "Sahlen Field": "TOR",      # Blue Jays' 2021 temporary home (Buffalo)
    "Suntrust Park": "ATL",
    "T-Mobile Park": "SEA",
    "TD Ballpark": "TOR",       # Blue Jays' 2021 temporary home (Dunedin)
    "Target Field": "MIN",
    "Tropicana Field": "TB",
    "Turner Field": "ATL",
    "Wrigley Field": "CHC",
    "Yankee Stadium": "NYY",
}

# Neutral-site parks: international series, special events, classics.
NEUTRAL_PARKS = {
    "Tokyo Dome",            # 2012 + 2019 Japan openers
    "Sydney Cricket Ground",  # 2014 Australia series
    "Estadio Hiram Bithorn",  # 2018 Puerto Rico series
    "Estadio Monterrey",      # 2018-2019 Mexico series
    "London Stadium",         # 2019 London series
    "Field of Dreams",        # 2021 Iowa game
    "Fort Bragg Field",       # 2016 Fort Bragg game
    "TD Ameritrade Park",     # 2019 Omaha game
    "BB&T Ballpark at Bowman Field",  # MLB Little League Classic (Williamsport)
}

# Hurricane-relocation games, played in another club's park (neutral).
# (date, park) pairs; the tenant mapping must NOT apply to these.
RELOCATED = {
    ("2017-09-11", "Citi Field"),
    ("2017-09-12", "Citi Field"),
    ("2017-09-13", "Citi Field"),
    ("2017-08-29", "Tropicana Field"),
    ("2017-08-30", "Tropicana Field"),
    ("2017-08-31", "Tropicana Field"),
}


def _pair_rows(df: pd.DataFrame):
    """Yield (row_a, row_b) mirror pairs, one pair per game.

    Rows are grouped by date + unordered team pair. 2-row groups (98.5% of
    games) pair positionally after sorting -- fast path. Groups with 4 rows
    (doubleheaders) match each (team, opponent) row with the mirror
    (opponent, team) row whose runs/oppRuns are swapped, so each game keeps
    its own moneyline; identical-score doubleheaders fall back to file order.
    """
    df = df.copy()
    t1 = df["team"].where(df["team"] < df["opponent"], df["opponent"])
    t2 = df["opponent"].where(df["team"] < df["opponent"], df["team"])
    df["pairkey"] = (df["date"].dt.strftime("%Y-%m-%d") + "|" + t1 + "|" + t2)

    sizes = df.groupby("pairkey")["pairkey"].transform("size")
    assert set(sizes.unique()) <= {2, 4}, f"unexpected group sizes {sizes.unique()}"

    # Fast path: 2-row groups pair positionally.
    simple = df[sizes == 2].sort_values(["pairkey", "team"])
    rows = list(simple.itertuples())
    assert len(rows) % 2 == 0
    for i in range(0, len(rows), 2):
        r, m = rows[i], rows[i + 1]
        assert (r.pairkey == m.pairkey and r.team == m.opponent
                and r.opponent == m.team), f"mispaired {r.pairkey}"
        yield r, m

    # Slow path: doubleheaders (4 rows), paired by swapped scores.
    for key, g in df[sizes == 4].groupby("pairkey", sort=False):
        g = g.sort_index()  # file order
        ab = [r for r in g.itertuples() if r.team < r.opponent]
        ba = [r for r in g.itertuples() if r.team > r.opponent]
        assert len(ab) == len(ba) == 2, f"unpairable group {key}"
        used = [False, False]
        for r in ab:
            pick = None
            for i, m in enumerate(ba):
                if not used[i] and m.runs == r.oppRuns and m.oppRuns == r.runs:
                    pick = i
                    break
            if pick is None:  # identical-score doubleheader: file order
                pick = next(i for i, u in enumerate(used) if not u)
            used[pick] = True
            yield r, ba[pick]


def load_games(csv: str | Path = CSV) -> pd.DataFrame:
    """Load the CSV and return one chronological row per game."""
    df = pd.read_csv(csv, parse_dates=["date"])
    recs = []
    for r, m in _pair_rows(df):
        assert r.parkName == m.parkName, "park mismatch within a game pair"
        park = r.parkName
        date_s = r.date.strftime("%Y-%m-%d")
        neutral = park in NEUTRAL_PARKS or (date_s, park) in RELOCATED
        first = r if r.Index < m.Index else m  # file order
        if neutral:
            home, away = first.team, first.opponent  # arbitrary-but-consistent
        else:
            home = PARK_HOME.get(park)
            assert home is not None, f"unknown park: {park}"
            assert home in (r.team, r.opponent), f"tenant {home} not in game at {park}"
            away = r.opponent if r.team == home else r.team
        rows = {r.team: r, m.team: m}
        hr, ar = rows[home], rows[away]
        assert hr.moneyLine == ar.oppMoneyLine, "moneyline mirror mismatch"
        recs.append(
            {
                "date": r.date,
                "season": int(r.season),
                "home": home,
                "away": away,
                "home_runs": int(hr.runs),
                "away_runs": int(ar.runs),
                "home_ml": int(hr.moneyLine),
                "away_ml": int(ar.moneyLine),
                "total": float(r.total),
                "over_odds": int(r.overOdds),
                "under_odds": int(r.underOdds),
                "park": park,
                "neutral": neutral,
            }
        )
    games = pd.DataFrame(recs)
    games = games.sort_values("date", kind="stable").reset_index(drop=True)
    return games


if __name__ == "__main__":
    g = load_games()
    print(f"{len(g):,} games, {g['date'].min().date()} .. {g['date'].max().date()}")
    print(f"neutral games: {int(g['neutral'].sum())}")
    print(g.groupby("season").size().to_string())
