"""Team strength from runs scored/allowed, park-adjusted.

Model: each team has an offensive rating (expected runs scored per game in a
neutral park vs an average defense) and a defensive rating (expected runs
allowed per game in a neutral park vs an average offense). Both are
exponential moving averages of park-adjusted, home-edge-adjusted game
observations.

Honesty rules (same as the NBA/NFL models):
  - The betting line is NEVER an input, anywhere in this module.
  - Call ``predict`` BEFORE ``update``: predictions use only games already
    played. The backtest relies on this ordering.
  - Park factors, the league scoring average, and the home edge are all
    computed from PRIOR games only (expanding windows with shrinkage
    priors), never from the full sample.

Park factors: simple ratio of (runs per game at this park) to (league runs
per game), computed on games before the current date, shrunk toward 1.0
with a 100-game prior. Choice documented: an expanding window rather than a
3-year rolling one, because parks change rarely and rolling windows add
noise; the shrinkage prior keeps new/relocated parks (Globe Life Field,
Suntrust Park, the Jays' 2021 temp homes) stable. Limitation: the simple
ratio conflates park effects with the DH/schedule mix at that park -- it
measures the park's *runs environment*, which is what prediction needs.

Recency: plain exponential update with learning rate ``alpha`` (tuned on
the 2012-2015 walk-forward split; see ``tune_params``). No margin-of-victory
scaling: MLB scores are low-variance enough that the exponential weight
does the work, and blowouts in baseball are less systematically
informative than in basketball.

Season rollover: ratings regress toward the league average with
``carryover`` (tuned; NBA precedent uses 0.5).

Home edge: fitted, not assumed -- mean home margin on non-neutral games
(see ``fit_home_edge``). It is split evenly between runs scored and
allowed, and zeroed for neutral-site games.
"""
from __future__ import annotations

import math

import pandas as pd

LEAGUE_AVG_PRIOR_RUNS = 4.4   # runs/team-game prior for the league average
LEAGUE_AVG_PRIOR_WT = 1000.0  # ...with this many team-games of weight
PARK_PRIOR_GAMES = 100.0      # shrinkage games toward 1.0 for park factors

TUNE_SEASONS = (2012, 2013, 2014, 2015)  # tuning split; 2016+ untouched by tuning
ALPHA_GRID = (1 / 15, 1 / 20, 1 / 30, 1 / 40)
CARRYOVER_GRID = (0.25, 0.5, 2 / 3, 0.75)


class MLBRatings:
    """Park-adjusted exponential runs ratings.

    Call ``predict`` BEFORE ``update`` for leakage-safe walk-forward use.
    """

    def __init__(self, alpha: float = 1 / 30, carryover: float = 0.5,
                 home_edge: float = 0.2) -> None:
        self.alpha = alpha
        self.carryover = carryover
        self.home_edge = home_edge
        self.off: dict[str, float] = {}
        self.deff: dict[str, float] = {}
        # Expanding accumulators (prior games only -- updated after predict).
        self.lg_runs = 0.0
        self.lg_games = 0
        self.park_runs: dict[str, float] = {}
        self.park_games: dict[str, int] = {}

    # -- internal state -------------------------------------------------
    def _league_avg(self) -> float:
        """Runs per team-game, expanding, with a 4.4-run prior."""
        return ((self.lg_runs + LEAGUE_AVG_PRIOR_RUNS * LEAGUE_AVG_PRIOR_WT)
                / (2 * self.lg_games + LEAGUE_AVG_PRIOR_WT))

    def _park_factor(self, park: str) -> float:
        """Runs environment at ``park`` vs league average, prior games only."""
        lg_per_game = self.lg_runs / self.lg_games if self.lg_games else LEAGUE_AVG_PRIOR_RUNS * 2
        pr = self.park_runs.get(park, 0.0)
        pg = self.park_games.get(park, 0)
        park_per_game = (pr + PARK_PRIOR_GAMES * lg_per_game) / (pg + PARK_PRIOR_GAMES)
        return park_per_game / lg_per_game

    def _off(self, team: str) -> float:
        return self.off.setdefault(team, self._league_avg())

    def _def(self, team: str) -> float:
        return self.deff.setdefault(team, self._league_avg())

    # -- public API ------------------------------------------------------
    def predict(self, home: str, away: str, park: str,
                neutral: bool = False) -> tuple[float, float]:
        """Predicted (home_runs, away_runs) from ratings as they stand.

        Call BEFORE update().
        """
        pf = self._park_factor(park)
        lavg = self._league_avg()
        edge = 0.0 if neutral else self.home_edge
        exp_h = pf * (self._off(home) + self._def(away) - lavg) + edge / 2
        exp_a = pf * (self._off(away) + self._def(home) - lavg) - edge / 2
        return exp_h, exp_a

    def update(self, home: str, away: str, home_runs: float,
               away_runs: float, park: str, neutral: bool = False) -> None:
        """Learn from a final score. Call AFTER predict()."""
        pf = self._park_factor(park)
        lavg = self._league_avg()
        edge = 0.0 if neutral else self.home_edge
        # Strip park + home edge: neutral-site-equivalent scoring observations.
        adj_h = home_runs / pf - edge / 2
        adj_a = away_runs / pf + edge / 2
        # Each observation implies an offensive and a defensive rating:
        #   adj_h ~= off_h + def_a - lavg   ->  implied off_h = adj_h - def_a + lavg
        #   adj_h ~= off_h + def_a - lavg   ->  implied def_a = adj_h - off_h + lavg
        # (and symmetrically for the away side).
        oh, da = self._off(home), self._def(away)
        oa, dh = self._off(away), self._def(home)
        a = self.alpha
        self.off[home] = oh + a * ((adj_h - da + lavg) - oh)
        self.deff[away] = da + a * ((adj_h - oh + lavg) - da)
        self.off[away] = oa + a * ((adj_a - dh + lavg) - oa)
        self.deff[home] = dh + a * ((adj_a - oa + lavg) - dh)
        # Advance the expanding accumulators AFTER the prediction used them.
        self.lg_runs += home_runs + away_runs
        self.lg_games += 1
        self.park_runs[park] = self.park_runs.get(park, 0.0) + home_runs + away_runs
        self.park_games[park] = self.park_games.get(park, 0) + 1

    def new_season(self) -> None:
        """Regress every rating toward the league average at a season boundary."""
        lavg = self._league_avg()
        c = self.carryover
        for team in self.off:
            self.off[team] = c * self.off[team] + (1 - c) * lavg
        for team in self.deff:
            self.deff[team] = c * self.deff[team] + (1 - c) * lavg


def fit_home_edge(games: pd.DataFrame) -> float:
    """Mean home margin in runs on non-neutral games. Fitted, not assumed."""
    g = games[~games["neutral"]]
    return float((g["home_runs"] - g["away_runs"]).mean())


def walk_forward(games: pd.DataFrame, alpha: float, carryover: float,
                 home_edge: float, hook=None) -> None:
    """Run the predict/update loop; call ``hook(row, pred_h, pred_a)`` before
    each update. Shared by tuning and the backtest so both use identical
    leakage-safe ordering."""
    r = MLBRatings(alpha=alpha, carryover=carryover, home_edge=home_edge)
    last_season = None
    for row in games.itertuples():
        season = int(row.season)
        if last_season is not None and season != last_season:
            r.new_season()
        last_season = season
        pred_h, pred_a = r.predict(row.home, row.away, row.park, bool(row.neutral))
        if hook is not None:
            hook(row, pred_h, pred_a)
        r.update(row.home, row.away, float(row.home_runs), float(row.away_runs),
                 row.park, bool(row.neutral))


def _tuning_rmse(games: pd.DataFrame, alpha: float, carryover: float,
                 home_edge: float) -> float:
    se, n = 0.0, 0

    def hook(row, pred_h, pred_a):
        nonlocal se, n
        se += (pred_h - pred_a - (row.home_runs - row.away_runs)) ** 2
        n += 1

    walk_forward(games, alpha, carryover, home_edge, hook)
    return math.sqrt(se / n) if n else float("nan")


def tune_params(games: pd.DataFrame, home_edge: float,
                tune_seasons: tuple[int, ...] = TUNE_SEASONS,
                alphas: tuple[float, ...] = ALPHA_GRID,
                carryovers: tuple[float, ...] = CARRYOVER_GRID,
                ) -> tuple[float, float, float]:
    """Grid-search (alpha, carryover) on walk-forward margin RMSE over the
    tuning seasons only. Returns (best_alpha, best_carryover, best_rmse)."""
    tune = games[games["season"].isin(tune_seasons)].copy()
    best, best_rmse = (alphas[0], carryovers[0]), float("inf")
    results = []
    for a in alphas:
        for c in carryovers:
            rmse = _tuning_rmse(tune, a, c, home_edge)
            results.append((rmse, a, c))
            if rmse < best_rmse:
                best, best_rmse = (a, c), rmse
    results.sort()
    print("tuning grid (rmse, alpha, carryover):")
    for rmse, a, c in results:
        print(f"  rmse={rmse:.4f}  alpha=1/{1/a:.0f}  carryover={c:.3f}")
    return best[0], best[1], best_rmse


def fit_sigma(games: pd.DataFrame, alpha: float, carryover: float,
              home_edge: float,
              tune_seasons: tuple[int, ...] = TUNE_SEASONS) -> float:
    """Std dev of (actual - predicted) margin residuals on the tuning split.
    This is the sigma used by winprob.margin_to_prob -- fitted, not assumed."""
    tune = games[games["season"].isin(tune_seasons)].copy()
    resid = []

    def hook(row, pred_h, pred_a):
        resid.append((row.home_runs - row.away_runs) - (pred_h - pred_a))

    walk_forward(tune, alpha, carryover, home_edge, hook)
    mean = sum(resid) / len(resid)
    var = sum((x - mean) ** 2 for x in resid) / len(resid)
    return math.sqrt(var)
