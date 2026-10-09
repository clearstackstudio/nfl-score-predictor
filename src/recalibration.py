"""Empirical probability recalibration for spread/total models.

The spread/total models publish P(cover) = Phi(|model - line| / sd): how far
our number sits from the market line, in units of typical game noise. The
2026-10-09 calibration check proved this systematically overconfident -- a
published 77% hits ~45% -- because (model - line) is mostly our error, not
signal, when the model is no better than the closing line.

These curves map raw published probability -> empirical hit rate, via
piecewise-linear interpolation on the walk-forward backtest bins. Anchored at
(0.50, 0.50): a zero edge is a coin flip by symmetry. Flat beyond the last
bin: we have no data distinguishing an 80% raw prob from a 95% one.

Fitted 2026-10-09 from the modern-era backtests (the regime the live models
operate in). Source: goals/nfl-score-prediction-website/files/calibration-check.md.
Refit when the monthly model health check shows drift. MLB moneyline probs
are well-calibrated and intentionally excluded.
"""

from __future__ import annotations

# (raw_prob, empirical_rate) points per (sport, market).
# x = bin mean predicted prob from the calibration report; y = actual rate.
_CURVES: dict[tuple[str, str], list[tuple[float, float]]] = {
    ("nfl", "ats"): [
        (0.50, 0.50),
        (0.532, 0.434),
        (0.575, 0.491),
        (0.623, 0.495),
        (0.674, 0.504),
        (0.775, 0.449),
    ],
    ("nfl", "totals"): [
        (0.50, 0.50),
        (0.538, 0.510),
        (0.574, 0.510),
        (0.623, 0.533),
        (0.663, 0.481),
    ],
    ("nba", "ats"): [
        (0.50, 0.50),
        (0.533, 0.510),
        (0.573, 0.499),
        (0.622, 0.500),
        (0.672, 0.524),
        (0.743, 0.513),
    ],
    ("nba", "totals"): [
        (0.50, 0.50),
        (0.535, 0.502),
        (0.573, 0.491),
        (0.622, 0.475),
        (0.663, 0.502),
    ],
    ("cfb", "ats"): [
        (0.50, 0.50),
        (0.531, 0.499),
        (0.574, 0.506),
        (0.624, 0.514),
        (0.675, 0.469),
        (0.780, 0.497),
    ],
    ("cfb", "totals"): [
        (0.50, 0.50),
        (0.536, 0.493),
        (0.574, 0.508),
        (0.624, 0.519),
        (0.662, 0.527),
    ],
}

# Bumped whenever the curves are refit. The parlay lock only preserves
# parlays built under the current calibration, so a refit rebuilds the
# week's parlay once instead of displaying stale probabilities.
CALIBRATION_VERSION = "empirical-2026-10-09"


def recalibrate(prob: float, sport: str, market: str) -> float:
    """Map a raw Phi(|edge|/sd) probability to its empirical hit rate.

    Piecewise-linear on the fitted bins; flat beyond the last bin (no data
    up there). Floored at 0.50 -- we never publish a sub-50% probability for
    a side we're picking -- and clamped to [0.50, 0.99].
    """
    pts = _CURVES[(sport, market)]
    if prob <= pts[0][0]:
        cal = pts[0][1]
    elif prob >= pts[-1][0]:
        cal = pts[-1][1]
    else:
        cal = pts[-1][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= prob <= x1:
                t = (prob - x0) / (x1 - x0)
                cal = y0 + t * (y1 - y0)
                break
    return min(0.99, max(0.50, cal))
