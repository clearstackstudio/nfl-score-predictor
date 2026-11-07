"""Team-name normalization for Honest Line's NCAAB model.

Canonical names are the CBBD team names (e.g. "Duke"), because games.csv
(training data) uses exactly these. The nightly odds snapshots from The
Odds API use full names with mascots (e.g. "Duke Blue Devils"), so
``normalize_team`` maps those to canonical CBBD names.

Strategy: exact match first; otherwise strip trailing words (the mascot)
one at a time until a canonical name matches ("North Carolina Tar Heels"
-> "North Carolina"). KNOWN_OVERRIDES covers names the heuristic gets
wrong -- extend it as misses surface (fail loud: normalize_team raises on
an unmappable name so a silent mis-join can never train the model).
"""
from __future__ import annotations

# Odds API full name -> canonical CBBD name, for names the trailing-word
# heuristic cannot reach (abbreviations like "St"/"CSU", renamed schools,
# shortened forms). The heuristic handles the common "<School> <Mascot>"
# pattern; only the exceptions live here.
KNOWN_OVERRIDES: dict[str, str] = {
    # November 2026 odds-logging shakeout misses (each target verified
    # against the CBBD D1 list in data/ncaab/raw/ and games.csv):
    "East Tennessee St Buccaneers": "East Tennessee State",
    "Seattle Redhawks": "Seattle U",
    "Cleveland St Vikings": "Cleveland State",
    "Coppin St Eagles": "Coppin State",
    "CSU Fullerton Titans": "Cal State Fullerton",
    "Cal Baptist Lancers": "California Baptist",
    "Fort Wayne Mastodons": "Purdue Fort Wayne",
    # November 4, 2026: the Nov 1-3 finals backfill (full D1 board) surfaced
    # 27 more unmappable names in merged finals / logged odds. Each target
    # verified against the CBBD D1 list in data/ncaab/raw/ and games.csv.
    "Alcorn St Braves": "Alcorn State",
    "American Eagles": "American University",
    "Appalachian St Mountaineers": "App State",
    "Arkansas-Little Rock Trojans": "Little Rock",
    "Boston Univ. Terriers": "Boston University",
    "CSU Northridge Matadors": "Cal State Northridge",
    "Chicago St Cougars": "Chicago State",
    "GW Revolutionaries": "George Washington",
    "Jackson St Tigers": "Jackson State",
    "LIU Sharks": "Long Island University",
    "Long Beach St 49ers": "Long Beach State",
    "Loyola (Chi) Ramblers": "Loyola Chicago",
    "Loyola (MD) Greyhounds": "Loyola Maryland",
    "Maryland-Eastern Shore Hawks": "Maryland Eastern Shore",
    "Mississippi St Bulldogs": "Mississippi State",
    "Morehead St Eagles": "Morehead State",
    "Mt. St. Mary's Mountaineers": "Mount St. Mary's",
    "Murray St Racers": "Murray State",
    "SE Missouri St Redhawks": "Southeast Missouri State",
    "San José St Spartans": "San José State",
    "St. Thomas (MN) Tommies": "St. Thomas-Minnesota",
    "Tenn-Martin Skyhawks": "UT Martin",
    "UMKC Kangaroos": "Kansas City",
    "Wichita St Shockers": "Wichita State",
    "Wright St Raiders": "Wright State",
    "Youngstown St Penguins": "Youngstown State",
    "Albany Great Danes": "UAlbany",
    # "X St" names where the trailing-word heuristic silently lands on a
    # DIFFERENT school ("Michigan St Spartans" -> "Michigan"). Explicit
    # overrides so they map to their real CBBD names (all verified as
    # above). Correct-by-heuristic exceptions -- canonical drops "State"
    # itself -- are Grambling, Sam Houston and Central Connecticut; do
    # NOT add overrides for those.
    "Alabama St Hornets": "Alabama State",
    "Arizona St Sun Devils": "Arizona State",
    "Arkansas St Red Wolves": "Arkansas State",
    "Colorado St Rams": "Colorado State",
    "Delaware St Hornets": "Delaware State",
    "Florida St Seminoles": "Florida State",
    "Georgia St Panthers": "Georgia State",
    "Illinois St Redbirds": "Illinois State",
    "Indiana St Sycamores": "Indiana State",
    "Jacksonville St Gamecocks": "Jacksonville State",
    "Kansas St Wildcats": "Kansas State",
    "Michigan St Spartans": "Michigan State",
    "Montana St Bobcats": "Montana State",
    "North Dakota St Bison": "North Dakota State",
    "Northwestern St Demons": "Northwestern State",
    "Oklahoma St Cowboys": "Oklahoma State",
    "Oregon St Beavers": "Oregon State",
    "San Diego St Aztecs": "San Diego State",
    "South Dakota St Jackrabbits": "South Dakota State",
    "Tennessee St Tigers": "Tennessee State",
    "Washington St Cougars": "Washington State",
    # November 6, 2026: Nov 5 finals backfill surfaced 3 more unmappable
    # names. Each target verified against the CBBD D1 list in
    # data/ncaab/raw/ and games.csv.
    "Kennesaw St Owls": "Kennesaw State",
    "N Colorado Bears": "Northern Colorado",
    "UT-Arlington Mavericks": "UT Arlington",
}


def normalize_team(name: str, canonical: set[str]) -> str:
    """Map an Odds API team name to its canonical CBBD name.

    Raises ValueError when no mapping is found -- a silent mis-join would
    corrupt training, so unknown names fail loudly.
    """
    name = " ".join(name.split())
    if name in canonical:
        return name
    if name in KNOWN_OVERRIDES:
        return KNOWN_OVERRIDES[name]
    words = name.split()
    for i in range(len(words) - 1, 0, -1):
        cand = " ".join(words[:i])
        if cand in canonical:
            return cand
    raise ValueError(f"cannot map team name {name!r} to a CBBD team")
