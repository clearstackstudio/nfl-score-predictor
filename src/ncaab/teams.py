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
