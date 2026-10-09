"""Home win probability from a predicted run differential.

    P(home win) = Phi(margin / sigma),  Phi = standard normal CDF.

Why the normal CDF: game-level MLB run differentials are approximately
normal (mean ~+0.2 for the home side, sd ~2.9 in this data). The ratings
model produces a location estimate (predicted margin); dividing by the
residual sd and passing through the normal CDF is the textbook conversion.
A Pythagorean-style ratio (RS^2/(RS^2+RA^2)) answers a different question
-- season-long win% from season-long run totals -- and misbehaves for
single-game differentials near zero; the normal CDF needs only one fitted
parameter, sigma.

SIGMA is fitted, not assumed: it is the std dev of (actual - predicted)
margin residuals from the walk-forward TUNING split (2012-2015) using the
tuned ratings params. Refit it if the ratings model changes; the value and
its provenance are printed by backtest.py and recorded in
backtest_results.json.
"""
from __future__ import annotations

import math

# Fitted 2026-10-08: residual sd on the 2012-2015 tuning walk-forward
# (alpha=1/40, carryover=0.25, home_edge=0.130). See backtest_results.json.
SIGMA = 4.135


def margin_to_prob(margin: float, sigma: float = SIGMA) -> float:
    """P(home wins) for a predicted home margin in runs. No ties in MLB."""
    return 0.5 * (1.0 + math.erf(margin / (sigma * math.sqrt(2.0))))
