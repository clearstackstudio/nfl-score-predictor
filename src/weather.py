"""Wind adjustment for NFL totals.

Calibrated 2026-10-01 on walk-forward 2021-2024 totals (leakage-safe):
outdoor games where our model was too high, by wind bucket:

    0-5 mph:    +0.63 pts (no effect)
    5-10 mph:   +0.33 pts (no effect)
    10-15 mph:  -2.61 pts
    15-20 mph:  -6.70 pts
    20+ mph:    -3.73 pts (n=13, noisy)

Fit: -1.0 pts per mph above 10, outdoor stadiums only, capped at -8.
Total RMSE 15.20 -> 15.11 on the 1,071-game sample (189 games adjusted).
Small aggregate gain; fixes a specific measured blind spot.

Live: uses the Open-Meteo forecast wind at kickoff (free, no key).
Calibrated on actual game-book wind, so forecast error adds noise —
documented on the methodology page.
"""
from __future__ import annotations

import json
import urllib.request

from stadiums import STADIUMS, is_outdoor

WIND_HINGE_MPH = 10.0
WIND_SLOPE = 1.0
WIND_MAX_ADJ = 8.0


def wind_total_adjustment(wind_mph: float | None, home_team: str) -> float:
    """Points to add to our total. Zero for domes/retractable roofs,
    unknown wind, or calm conditions."""
    if wind_mph is None or not is_outdoor(home_team):
        return 0.0
    return -min(WIND_MAX_ADJ, max(0.0, wind_mph - WIND_HINGE_MPH) * WIND_SLOPE)


def fetch_kickoff_winds(games: list[dict]) -> dict[tuple[str, str], float | None]:
    """Forecast wind (mph) at kickoff for each (home_team, gameday).

    games: dicts with home_team, gameday (YYYY-MM-DD), gametime (HH:MM ET).
    Returns {(home_team, gameday): wind_mph or None}. One API call per
    stadium-date; failures degrade to None (no adjustment), never raise.
    """
    # group by stadium so one request covers every game there that day
    keys: dict[tuple[float, float, str], list[tuple[str, str]]] = {}
    for g in games:
        home = g["home_team"]
        if not is_outdoor(home):
            continue
        lat, lon, _ = STADIUMS[home]
        keys.setdefault((lat, lon, g["gameday"]), []).append(
            (home, g["gameday"]))

    out: dict[tuple[str, str], float | None] = {}
    for (lat, lon, day), teams in keys.items():
        winds = _fetch_day(lat, lon, day)
        for home, gameday in teams:
            out[(home, gameday)] = _at_kickoff(
                winds, _kickoff_hour(gameday, _gametime_for(home, gameday, games)))
    return out


def _gametime_for(home: str, gameday: str, games: list[dict]) -> str:
    for g in games:
        if g["home_team"] == home and g["gameday"] == gameday:
            return g.get("gametime") or "13:00"
    return "13:00"


def _kickoff_hour(gameday: str, gametime: str) -> str:
    """'2026-10-11','13:00' -> '2026-10-11T13:00' (forecast is in ET)."""
    hhmm = (gametime or "13:00")[:5]
    return f"{gameday}T{hhmm}"


def _fetch_day(lat: float, lon: float, day: str) -> list[tuple[str, float]]:
    url = ("https://api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}"
           "&hourly=wind_speed_10m&wind_speed_unit=mph"
           f"&start_date={day}&end_date={day}"
           "&timezone=America%2FNew_York")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            d = json.load(r)
        times = d["hourly"]["time"]
        winds = d["hourly"]["wind_speed_10m"]
        return list(zip(times, winds))
    except Exception:
        return []


def _at_kickoff(winds: list[tuple[str, float]],
                kickoff_iso: str) -> float | None:
    """Wind at the forecast hour at or just before kickoff."""
    best = None
    for t, w in winds:
        if t[:16] <= kickoff_iso and w is not None:
            best = float(w)
    return best


INDOOR_TOTAL_ADJ = 3.0


def indoor_total_adjustment(home_team: str) -> float:
    """Points to add to our total for indoor games.

    Calibrated 2026-10-02 on walk-forward 2021-2024 totals (leakage-safe,
    wind hinge already applied): indoor games (dome + retractable, via
    is_outdoor()) scored E[actual_total - our_total] = +3.13, stable all
    four seasons (+2.37/+4.26/+3.60/+2.22, n=329, t ~= 3.6). Perfect
    conditions / fast track systematically beat the model. Outdoor games
    and unknown stadiums: 0.
    """
    s = STADIUMS.get(home_team)
    if s is None or s[2] == "outdoor":
        return 0.0
    return INDOOR_TOTAL_ADJ
