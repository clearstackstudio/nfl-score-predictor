"""Adjusted-efficiency model for NCAAB: offense/defense per possession + tempo.

Approach (the NCAAB analogue of the NBA efficiency totals model, extended
to produce the margin as well):
  - Each team carries three exponentially-weighted moving averages:
      off  = points scored per possession (raw PPP)
      def  = points allowed per possession (raw PPP)
      tempo = possessions per game
  - League-average EMAs for PPP and tempo drift with the era.
  - "Adjusted" happens at prediction time (one-iteration SOS adjustment,
    same pattern as the NBA totals model):
      expected home PPP = lg + (home_off - lg) + (away_def - lg)
      expected away PPP = lg + (away_off - lg) + (home_def - lg)
      expected possessions = lg_t + (home_t - lg_t) + (away_t - lg_t)
    i.e. each team's raw efficiency is adjusted by the opponent's rating
    relative to the league average. The update step records raw PPP only.
  - Predicted margin = (home_ppp - away_ppp) * poss + home_edge
    (home_edge = 0 for neutral-site games).
  - Predicted total = (home_ppp + away_ppp) * poss.

November prior (transfer-portal era): rosters turn over heavily every
offseason, so early-season ratings are noisy. November updates use half
the per-game weight (NOV_ALPHA_FACTOR = 0.5), December 0.75, January on
full weight -- structural priors, not fitted values.

Honesty rules (same as the NBA model):
  - The betting line is NEVER a model input, anywhere. It is only the
    benchmark the backtest compares against.
  - Prediction precedes update: call ``predict`` BEFORE ``update`` for
    leakage-safe walk-forward evaluation.
  - Games are processed in chronological order.
"""
from __future__ import annotations


# Fitted defaults (walk-forward RMSE on the 2013-2019 tuning split;
# the 2020-2026 seasons were held out of tuning). The RMSE surface is flat
# near the minimum (12.015-12.071 across alpha 0.08-0.12 / carry 0.5-0.67),
# so these are plateau-center values, not sharp optima:
#   TEAM_ALPHA = 0.10, SEASON_CARRYOVER = 0.6, HOME_EDGE_PTS = 5.04
# (mean home margin on non-neutral tuning-split games). NOV/DEC_ALPHA_FACTOR
# are structural priors for early-season roster noise (transfer-portal
# era), not fitted values.
TEAM_ALPHA = 0.10
NOV_ALPHA_FACTOR = 0.5
DEC_ALPHA_FACTOR = 0.75
LEAGUE_ALPHA = 0.005
SEASON_CARRYOVER = 0.6
HOME_EDGE_PTS = 5.04


def month_alpha_factor(month: int) -> float:
    if month == 11:
        return NOV_ALPHA_FACTOR
    if month == 12:
        return DEC_ALPHA_FACTOR
    return 1.0


def sanitize_poss(poss: float | None, season: int) -> float | None:
    """Vet a box-score pace value before it touches the ratings.

    Returns None when the caller should fall back to the model's tempo
    estimate instead. Rejects:
      - missing/NaN/non-numeric values;
      - implausible values (<45 or >105 possessions; early CBBD seasons
        contain garbage like 7.0 for a 130-point game);
      - the entire 2013 season: CBBD's 2013 pace field is on an inflated
        scale (mean 75.7, implying 0.875 PPP vs ~1.05 in every other
        season -- true 2012-13 tempo was ~63).
    """
    if poss is None:
        return None
    try:
        p = float(poss)
    except (TypeError, ValueError):
        return None
    if p != p:  # NaN
        return None
    if season == 2013:
        return None
    if not (45.0 <= p <= 105.0):
        return None
    return p


class NCAABEfficiency:
    """Per-possession efficiency ratings -> margin and total.

    Call ``predict`` BEFORE ``update`` for leakage-safe walk-forward
    evaluation. Constructor params let the backtester experiment:
      team_alpha   - per-game EMA weight for team off/def/tempo (0.10)
      league_alpha - per-game EMA weight for league PPP/tempo (0.005)
      carryover    - fraction of team ratings kept at season rollover (0.6)
      home_edge    - home-court edge in points, 0 on neutral courts (5.04)
    """

    def __init__(self, team_alpha: float = TEAM_ALPHA,
                 league_alpha: float = LEAGUE_ALPHA,
                 carryover: float = SEASON_CARRYOVER,
                 home_edge: float = HOME_EDGE_PTS) -> None:
        self.off: dict[str, float] = {}
        self.deff: dict[str, float] = {}
        self.tempo: dict[str, float] = {}
        self.team_alpha = team_alpha
        self.league_alpha = league_alpha
        self.carryover = carryover
        self.home_edge = home_edge
        self.league_ppp = 1.00   # sensible prior; EMAs converge within weeks
        self.league_tempo = 68.0

    def _off(self, team: str) -> float:
        return self.off.setdefault(team, self.league_ppp)

    def _def(self, team: str) -> float:
        return self.deff.setdefault(team, self.league_ppp)

    def _tempo(self, team: str) -> float:
        return self.tempo.setdefault(team, self.league_tempo)

    def predict_poss(self, home: str, away: str) -> float:
        """Expected possessions from tempo ratings as they stand."""
        lgt = self.league_tempo
        return max(lgt + (self._tempo(home) - lgt)
                   + (self._tempo(away) - lgt), 50.0)

    def predict(self, home: str, away: str,
                neutral: bool = False) -> tuple[float, float]:
        """(predicted home margin, predicted total) from ratings as they
        stand. Positive margin = home favored. Call BEFORE update()."""
        lg = self.league_ppp
        h_ppp = lg + (self._off(home) - lg) + (self._def(away) - lg)
        a_ppp = lg + (self._off(away) - lg) + (self._def(home) - lg)
        poss = self.predict_poss(home, away)
        home_pts = h_ppp * poss
        away_pts = a_ppp * poss
        edge = 0.0 if neutral else self.home_edge
        return (home_pts - away_pts + edge, home_pts + away_pts)

    def update(self, home: str, away: str, home_score: float,
               away_score: float, poss: float, month: int) -> None:
        """Learn from a final score. Call AFTER predict(). ``month`` is the
        calendar month of the game (November updates are down-weighted)."""
        if not poss or poss <= 0:
            return
        a = self.team_alpha * month_alpha_factor(month)
        h_ppp = home_score / poss
        a_ppp = away_score / poss
        ho, hd, ht = self._off(home), self._def(home), self._tempo(home)
        ao, ad, at = self._off(away), self._def(away), self._tempo(away)
        self.off[home] = ho + a * (h_ppp - ho)
        self.deff[home] = hd + a * (a_ppp - hd)
        self.tempo[home] = ht + a * (poss - ht)
        self.off[away] = ao + a * (a_ppp - ao)
        self.deff[away] = ad + a * (h_ppp - ad)
        self.tempo[away] = at + a * (poss - at)
        la = self.league_alpha
        self.league_ppp += la * ((h_ppp + a_ppp) / 2.0 - self.league_ppp)
        self.league_tempo += la * (poss - self.league_tempo)

    def new_season(self) -> None:
        """Regress each team's ratings toward the league average at a
        season boundary. Fitted carryover 0.6: program/coach quality
        persists year-to-year more than raw roster turnover suggests."""
        c = self.carryover
        for team in list(self.off):
            self.off[team] = c * self.off[team] + (1.0 - c) * self.league_ppp
            self.deff[team] = c * self.deff[team] + (1.0 - c) * self.league_ppp
            self.tempo[team] = c * self.tempo[team] + (1.0 - c) * self.league_tempo
