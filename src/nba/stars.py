"""Star-player absence adjustment for the NBA model (kept separate from the
core model, like the rest adjustment in features.py).

A sitting star is the largest known unmodeled effect in the NBA pipeline.
Phase 1 (Oct 2026, nba-star-phase1-results.md): walk-forward 2008-2023,
tuned 2008-2015, validated once on 2016-2023 --
  - margin RMSE: 13.1017 -> 13.0572 (delta -0.045, paired t=4.39, p<0.0001)
  - single constant: 1.5 points per star out (home-margin convention)
  - the All-NBA vs All-Star tier split did NOT separate in the residual
    data, so there is deliberately no tier logic -- one constant
  - totals: no adjustment (grid search found nothing)
  - ATS on the star-out subset: 50.2% -> 50.1% -- accuracy gain, not a
    betting edge, as expected

Star = prior-season All-Star (ex-ante definition, no leakage). For the
2026-27 season that is the 2026 All-Star selections below, hardcoded so the
picks script has no network dependency at runtime.
"""
from __future__ import annotations

import datetime
import json
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
STAR_OUT_PATH = REPO / "data" / "nba" / "star_out.json"


# Fitted default (see module docstring): margin points per star out.
STAR_OUT_PTS = 1.5


# 2026 NBA All-Star selections = prior-season All-Stars for the 2026-27
# season: the 24-man pool + commissioner's addition (Kawhi Leonard) +
# official injury replacements (Alperen Sengun for Gilgeous-Alexander,
# Brandon Ingram for Curry). Selected-not-played (Antetokounmpo,
# Gilgeous-Alexander, Curry) count -- the definition is selection-based.
# Sources: NBA announcement Feb 2026; basketball-reference box scores.
ALL_STARS_2026 = frozenset({
    "Scottie Barnes", "Devin Booker", "Cade Cunningham", "Jalen Duren",
    "Anthony Edwards", "Chet Holmgren", "Jalen Johnson", "Tyrese Maxey",
    "Jaylen Brown", "Jalen Brunson", "Stephen Curry", "Kevin Durant",
    "LeBron James", "Kawhi Leonard", "Donovan Mitchell", "Norman Powell",
    "Giannis Antetokounmpo", "Deni Avdija", "Luka Doncic",
    "Shai Gilgeous-Alexander", "Nikola Jokic", "Jamal Murray",
    "Pascal Siakam", "Karl-Anthony Towns", "Victor Wembanyama",
    "Alperen Sengun", "Brandon Ingram",
})

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def _canon_name(name: str) -> str:
    """Lowercased, diacritic-stripped, suffix-tolerant name key."""
    ascii_name = unicodedata.normalize("NFKD", str(name)).encode(
        "ascii", "ignore").decode("ascii")
    parts = [p for p in ascii_name.lower().replace(".", "").split()
             if p not in _SUFFIXES]
    return " ".join(parts)


_STAR_KEYS = {_canon_name(n) for n in ALL_STARS_2026}


def is_star(name: str) -> bool:
    """True if the name matches a 2026 All-Star selection (suffix- and
    diacritic-tolerant, e.g. 'Luka Doncic' == 'Luka Dončić')."""
    return _canon_name(name) in _STAR_KEYS


def apply_star_adjustment(predicted_margin: float,
                          home_stars_out: int,
                          away_stars_out: int,
                          pts_per_star: float = STAR_OUT_PTS) -> float:
    """Margin adjustment for absent stars (home-margin convention: positive
    favors home). Each home star out weakens home by pts_per_star; each away
    star out strengthens the home margin by the same.

    Pure function -- no I/O. Fitted value 1.5 (see module docstring).
    """
    return (predicted_margin
            - pts_per_star * home_stars_out
            + pts_per_star * away_stars_out)


def load_stars_out(season: int,
                   game_date: datetime.date,
                   path: Path = STAR_OUT_PATH) -> dict[str, list[str]]:
    """Read the nightly star-out designations file.

    Returns {canonical team name: [validated star names]}. Entries whose
    season or date don't match are stale and ignored. Unknown team names
    and non-All-Star player names are warn-and-skipped, never fatal --
    a bad nightly file must not break the picks run.
    """
    try:
        doc = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"  star_out: unreadable {path} ({e}) -- no star adjustment")
        return {}

    try:
        file_season = int(doc.get("season", -1))
    except (TypeError, ValueError):
        file_season = -1
    if file_season != season or str(doc.get("date")) != game_date.isoformat():
        return {}

    from teams import normalize_team  # same flat-import convention as daily_picks.py

    out: dict[str, list[str]] = {}
    entries = doc.get("stars_out") or {}
    if not isinstance(entries, dict):
        print("  star_out: 'stars_out' is not an object -- ignoring")
        return {}
    for team, names in entries.items():
        try:
            canon_team = normalize_team(team)
        except KeyError:
            print(f"  star_out: unknown team {team!r} -- skipping")
            continue
        if not isinstance(names, list):
            print(f"  star_out: names for {team!r} not a list -- skipping")
            continue
        kept = [n for n in names if isinstance(n, str) and is_star(n)]
        dropped = [n for n in names if isinstance(n, str) and not is_star(n)]
        for n in dropped:
            print(f"  star_out: {n!r} is not a 2026 All-Star -- skipping")
        if kept:
            out.setdefault(canon_team, []).extend(kept)
    if out:
        total = sum(len(v) for v in out.values())
        print(f"  star_out: {total} star(s) out "
              f"({', '.join(f'{t}: {len(v)}' for t, v in out.items())})")
    return out
