"""NBA team name normalization for Honest Line's NBA model data.

Canonical names are The Odds API full team names (e.g. "Los Angeles Lakers"),
because games.csv must join directly with the nightly merged odds files in
data/nba/merged/*.json, which use exactly these names.

Spread convention (games.csv):
    spread = closing spread expressed as the HOME team's margin,
    positive = home team favored.
The raw Kaggle file stores spread from each row's team perspective with
negative = that team favored (e.g. Houston @ LA Lakers: Houston's row has
spread=-5, the Lakers' row has spread=5). So:
    home_spread = -1 * (home team's row spread)
and it must equal the away team's row spread exactly. The build script
verifies this agreement game-by-game.
"""

# The 30 current NBA franchises, in Odds API canonical form.
CANONICAL_TEAMS = [
    "Atlanta Hawks", "Boston Celtics", "Brooklyn Nets", "Charlotte Hornets",
    "Chicago Bulls", "Cleveland Cavaliers", "Dallas Mavericks", "Denver Nuggets",
    "Detroit Pistons", "Golden State Warriors", "Houston Rockets",
    "Indiana Pacers", "Los Angeles Clippers", "Los Angeles Lakers",
    "Memphis Grizzlies", "Miami Heat", "Milwaukee Bucks",
    "Minnesota Timberwolves", "New Orleans Pelicans", "New York Knicks",
    "Oklahoma City Thunder", "Orlando Magic", "Philadelphia 76ers",
    "Phoenix Suns", "Portland Trail Blazers", "Sacramento Kings",
    "San Antonio Spurs", "Toronto Raptors", "Utah Jazz",
    "Washington Wizards",
]

# Raw-name variants -> canonical name.
#
# The historical Kaggle file (2007-10-30 .. 2023-01-16) uses city-only names.
# Franchise continuity decisions (deliberate, for modeling — a model trained on
# this data should see one continuous franchise, not a reset at each move):
#   Seattle SuperSonics -> Oklahoma City Thunder  (franchise moved in 2008)
#   New Jersey Nets     -> Brooklyn Nets          (moved to Brooklyn in 2012)
#   New Orleans Hornets -> New Orleans Pelicans   (renamed in 2013)
#   Charlotte Bobcats   -> Charlotte Hornets      (renamed back in 2014)
# NOTE on Charlotte: the 2007-2014 "Charlotte" rows were the Bobcats, an
# expansion franchise; the pre-2002 Charlotte Hornets history belongs to the
# New Orleans franchise. For this dataset they are still mapped to
# "Charlotte Hornets" per the project spec (one franchise identity).
_TEAM_ALIASES_RAW = {
    "Atlanta": "Atlanta Hawks",
    "Boston": "Boston Celtics",
    "Brooklyn": "Brooklyn Nets",
    "Charlotte": "Charlotte Hornets",
    "Chicago": "Chicago Bulls",
    "Cleveland": "Cleveland Cavaliers",
    "Dallas": "Dallas Mavericks",
    "Denver": "Denver Nuggets",
    "Detroit": "Detroit Pistons",
    "Golden State": "Golden State Warriors",
    "Houston": "Houston Rockets",
    "Indiana": "Indiana Pacers",
    "LA Clippers": "Los Angeles Clippers",
    "LA Lakers": "Los Angeles Lakers",
    "Memphis": "Memphis Grizzlies",
    "Miami": "Miami Heat",
    "Milwaukee": "Milwaukee Bucks",
    "Minnesota": "Minnesota Timberwolves",
    "New Jersey": "Brooklyn Nets",          # Nets moved to Brooklyn 2012
    "New Orleans": "New Orleans Pelicans",  # Hornets renamed Pelicans 2013
    "New York": "New York Knicks",
    "Oklahoma City": "Oklahoma City Thunder",
    "Orlando": "Orlando Magic",
    "Philadelphia": "Philadelphia 76ers",
    "Phoenix": "Phoenix Suns",
    "Portland": "Portland Trail Blazers",
    "Sacramento": "Sacramento Kings",
    "San Antonio": "San Antonio Spurs",
    "Seattle": "Oklahoma City Thunder",     # Sonics moved to OKC 2008
    "Toronto": "Toronto Raptors",
    "Utah": "Utah Jazz",
    "Washington": "Washington Wizards",
}

# Extra defensive aliases (full names, nicknames, historical names, dotted forms).
_EXTRA_ALIASES_RAW = {
    "Atlanta Hawks": "Atlanta Hawks",
    "Boston Celtics": "Boston Celtics",
    "Brooklyn Nets": "Brooklyn Nets",
    "Charlotte Hornets": "Charlotte Hornets",
    "Chicago Bulls": "Chicago Bulls",
    "Cleveland Cavaliers": "Cleveland Cavaliers",
    "Dallas Mavericks": "Dallas Mavericks",
    "Denver Nuggets": "Denver Nuggets",
    "Detroit Pistons": "Detroit Pistons",
    "Golden State Warriors": "Golden State Warriors",
    "Houston Rockets": "Houston Rockets",
    "Indiana Pacers": "Indiana Pacers",
    "Los Angeles Clippers": "Los Angeles Clippers",
    "Los Angeles Lakers": "Los Angeles Lakers",
    "Memphis Grizzlies": "Memphis Grizzlies",
    "Miami Heat": "Miami Heat",
    "Milwaukee Bucks": "Milwaukee Bucks",
    "Minnesota Timberwolves": "Minnesota Timberwolves",
    "New Orleans Pelicans": "New Orleans Pelicans",
    "New York Knicks": "New York Knicks",
    "Oklahoma City Thunder": "Oklahoma City Thunder",
    "Orlando Magic": "Orlando Magic",
    "Philadelphia 76ers": "Philadelphia 76ers",
    "Phoenix Suns": "Phoenix Suns",
    "Portland Trail Blazers": "Portland Trail Blazers",
    "Sacramento Kings": "Sacramento Kings",
    "San Antonio Spurs": "San Antonio Spurs",
    "Toronto Raptors": "Toronto Raptors",
    "Utah Jazz": "Utah Jazz",
    "Washington Wizards": "Washington Wizards",
    # historical / relocated names
    "New Jersey Nets": "Brooklyn Nets",
    "Seattle Supersonics": "Oklahoma City Thunder",
    "Seattle Super Sonics": "Oklahoma City Thunder",
    "Charlotte Bobcats": "Charlotte Hornets",
    "New Orleans Hornets": "New Orleans Pelicans",
    # dotted / spaced variants
    "L.A. Lakers": "Los Angeles Lakers",
    "L.A. Clippers": "Los Angeles Clippers",
    "LA Lakers": "Los Angeles Lakers",
    "LA Clippers": "Los Angeles Clippers",
    # nicknames
    "Hawks": "Atlanta Hawks", "Celtics": "Boston Celtics",
    "Nets": "Brooklyn Nets", "Hornets": "Charlotte Hornets",
    "Bulls": "Chicago Bulls", "Cavaliers": "Cleveland Cavaliers",
    "Cavs": "Cleveland Cavaliers", "Mavericks": "Dallas Mavericks",
    "Mavs": "Dallas Mavericks", "Nuggets": "Denver Nuggets",
    "Pistons": "Detroit Pistons", "Warriors": "Golden State Warriors",
    "Rockets": "Houston Rockets", "Pacers": "Indiana Pacers",
    "Clippers": "Los Angeles Clippers", "Lakers": "Los Angeles Lakers",
    "Grizzlies": "Memphis Grizzlies", "Grizz": "Memphis Grizzlies",
    "Heat": "Miami Heat", "Bucks": "Milwaukee Bucks",
    "Timberwolves": "Minnesota Timberwolves", "Wolves": "Minnesota Timberwolves",
    "Pelicans": "New Orleans Pelicans", "Knicks": "New York Knicks",
    "Thunder": "Oklahoma City Thunder", "Magic": "Orlando Magic",
    "76ers": "Philadelphia 76ers", "Sixers": "Philadelphia 76ers",
    "Suns": "Phoenix Suns", "Blazers": "Portland Trail Blazers",
    "Trail Blazers": "Portland Trail Blazers", "Kings": "Sacramento Kings",
    "Spurs": "San Antonio Spurs", "Raptors": "Toronto Raptors",
    "Jazz": "Utah Jazz", "Wizards": "Washington Wizards",
}


def _key(name: str) -> str:
    """Lowercase, collapse whitespace, strip periods — punctuation-insensitive."""
    return " ".join(name.strip().lower().replace(".", "").split())


# Public mapping dict: normalized (lowered, punctuation-free) key -> canonical.
TEAM_NAME_MAP = {}
for _raw_map in (_TEAM_ALIASES_RAW, _EXTRA_ALIASES_RAW):
    for _raw, _canon in _raw_map.items():
        _k = _key(_raw)
        if _k in TEAM_NAME_MAP and TEAM_NAME_MAP[_k] != _canon:
            raise ValueError(f"conflicting alias {_raw!r}")
        TEAM_NAME_MAP[_k] = _canon


def normalize_team(name: str) -> str:
    """Return the Odds API canonical full team name for any known variant.

    Raises KeyError for unknown names (fail loud, never silently mislabel).
    """
    return TEAM_NAME_MAP[_key(name)]
