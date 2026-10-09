"""Probable-pitcher adjustment -- DESIGN ONLY. Not used in the backtest.

The historical odds file has NO pitcher column, so the backtest in
``backtest.py`` is deliberately team-level: it measures what team strength
alone can do against the closing line. This module designs how the LIVE
picks script (to be built Feb/Mar 2027, ahead of the 2027 season) will fold
probable-pitcher information into the team-level prediction.

Data source (free, no key): the MLB Stats API.
    https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=YYYY-MM-DD&hydrate=probablePitcher
Each game node carries ``teams.home.probablePitcher`` /
``teams.away.probablePitcher`` with the pitcher's ``id`` and name. The same
API gives season/career stats per pitcher
(``/api/v1/people/{id}?hydrate=stats(group=pitching,type=season)``).

Adjustment design (all quantities in runs per game):
  1. For each probable starter, compute ``ra9_vs_avg`` = (league-average
     runs allowed per 9) - (pitcher's runs allowed per 9), using trailing
     365-day FIP (preferred; defense-independent) or ERA, regressed toward
     the mean by workload: ``adj * IP / (IP + 50)``. Positive = better than
     an average starter.
  2. Blend into the team-level predicted home margin::

         adj_margin = team_margin + STARTER_SHARE * (home_ra9_vs_avg - away_ra9_vs_avg)

     ``STARTER_SHARE`` ~= 0.6 is a STARTING POINT, not a fitted constant:
     starters face roughly 55-65% of batters in the modern game (~5-6 IP).
     Validate/refit on 2027 games before trusting it; bullpen quality is
     already partly in the team ratings.
  3. Totals get the symmetric treatment: better-than-average starters on
     both sides lower the predicted total::

         adj_total = team_total - STARTER_SHARE * (home_ra9_vs_avg + away_ra9_vs_avg)

Fallback (documented, mandatory): when the probable pitcher is TBD, missing,
or the API is unreachable, use ``LEAGUE_AVERAGE_PITCHER_ADJ = 0.0`` -- i.e.
no adjustment -- and flag the pick as lower-confidence. A pick must NEVER
be blocked on pitcher data.

What is NOT in the backtest: none of this. ``fetch_probables`` below is a
documented stub raising ``NotImplementedError``; the live-picks script will
implement it. No network calls happen during backtesting.
"""
from __future__ import annotations

LEAGUE_AVERAGE_PITCHER_ADJ = 0.0  # fallback: no adjustment when pitcher unknown
STARTER_SHARE = 0.6  # starting point only -- validate on 2027 data, not a fitted constant

SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1&date={date}&hydrate=probablePitcher"
)


def fetch_probables(date: str) -> dict:
    """Map gamePk -> {"home": pitcher_id|None, "away": pitcher_id|None}.

    STUB -- live-picks script implements this against SCHEDULE_URL.
    Raises NotImplementedError so it can never silently run in a backtest.
    """
    raise NotImplementedError(
        "live-only: implement against MLB Stats API schedule endpoint; "
        "never call from backtest.py"
    )


def regress_pitcher_adj(raw_ra9_vs_avg: float, innings_pitched: float,
                        prior_ip: float = 50.0) -> float:
    """Regress a pitcher's runs-saved-per-9 toward league average by workload."""
    return raw_ra9_vs_avg * innings_pitched / (innings_pitched + prior_ip)


def apply_pitcher_adjustment(team_margin: float, team_total: float,
                             home_adj: float | None,
                             away_adj: float | None) -> tuple[float, float]:
    """Blend probable-starter adjustments into a team-level prediction.

    ``home_adj``/``away_adj`` are regressed ra9-vs-average (positive = good);
    ``None`` falls back to the league-average pitcher (no adjustment).
    Pure function -- no I/O, safe to unit test.
    """
    h = LEAGUE_AVERAGE_PITCHER_ADJ if home_adj is None else home_adj
    a = LEAGUE_AVERAGE_PITCHER_ADJ if away_adj is None else away_adj
    adj_margin = team_margin + STARTER_SHARE * (h - a)
    adj_total = team_total - STARTER_SHARE * (h + a)
    return adj_margin, adj_total
