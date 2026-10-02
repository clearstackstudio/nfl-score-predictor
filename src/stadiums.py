"""NFL stadium coordinates + roof types for weather lookups.

Coordinates are approximate (stadium-level, good enough for weather —
conditions don't vary meaningfully within a metro area). Roof types:
'outdoor' = always exposed, 'dome' = always covered, 'retractable' =
roof status varies (treated as covered for forecasts: teams close it
in bad weather, so no weather adjustment applied).
"""
from __future__ import annotations

# team -> (lat, lon, roof)
STADIUMS: dict[str, tuple[float, float, str]] = {
    "ARI": (33.528, -112.263, "retractable"),  # State Farm Stadium, Glendale
    "ATL": (33.755, -84.401, "retractable"),   # Mercedes-Benz Stadium
    "BAL": (39.278, -76.623, "outdoor"),       # M&T Bank Stadium
    "BUF": (42.774, -78.787, "outdoor"),       # Highmark Stadium
    "CAR": (35.226, -80.853, "outdoor"),       # Bank of America Stadium
    "CHI": (41.863, -87.617, "outdoor"),       # Soldier Field
    "CIN": (39.095, -84.508, "outdoor"),       # Paycor Stadium
    "CLE": (41.506, -81.700, "outdoor"),       # Huntington Bank Field
    "DAL": (32.748, -97.094, "retractable"),   # AT&T Stadium
    "DEN": (39.744, -105.020, "outdoor"),      # Empower Field
    "DET": (42.340, -83.045, "dome"),          # Ford Field
    "GB": (44.501, -88.062, "outdoor"),        # Lambeau Field
    "HOU": (29.685, -95.411, "retractable"),   # NRG Stadium
    "IND": (39.760, -86.164, "retractable"),   # Lucas Oil Stadium
    "JAX": (30.324, -81.637, "outdoor"),       # EverBank Stadium
    "KC": (39.049, -94.484, "outdoor"),        # Arrowhead Stadium
    "LV": (36.090, -115.184, "dome"),          # Allegiant Stadium
    "LAC": (33.953, -118.339, "outdoor"),      # SoFi Stadium (open sides)
    "LAR": (33.953, -118.339, "outdoor"),      # SoFi Stadium (open sides)
    "MIA": (25.958, -80.239, "outdoor"),       # Hard Rock Stadium
    "MIN": (44.974, -93.258, "dome"),          # U.S. Bank Stadium
    "NE": (42.091, -71.264, "outdoor"),        # Gillette Stadium
    "NO": (29.951, -90.081, "dome"),           # Caesars Superdome
    "NYG": (40.813, -74.074, "outdoor"),       # MetLife Stadium
    "NYJ": (40.813, -74.074, "outdoor"),       # MetLife Stadium
    "PHI": (39.901, -75.168, "outdoor"),       # Lincoln Financial Field
    "PIT": (40.447, -80.016, "outdoor"),       # Acrisure Stadium
    "SF": (37.403, -121.970, "outdoor"),       # Levi's Stadium
    "SEA": (47.595, -122.332, "outdoor"),      # Lumen Field
    "TB": (27.976, -82.503, "outdoor"),        # Raymond James Stadium
    "TEN": (36.166, -86.771, "outdoor"),       # Nissan Stadium
    "WAS": (38.908, -76.864, "outdoor"),       # Northwest Stadium
}


def is_outdoor(team: str) -> bool:
    """True if the team's stadium exposes games to weather."""
    s = STADIUMS.get(team)
    return s is not None and s[2] == "outdoor"
