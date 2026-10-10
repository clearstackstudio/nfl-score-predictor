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

# Platt scaling, fitted 2026-10-10: logistic regression of actual home win
# on logit(raw p_home) over the 2012-2021 walk-forward.
# Validated: +0.00128 Brier on untouched 2022-2026 (paired z=+3.93),
# closing ~24% of the model-vs-line Brier gap. Corrects the model's tail
# overconfidence -- raw p_home underestimates home underdogs by 4-8pp in
# the bottom deciles (confirmed 2012-15, 2016-21, AND 2022-26).
# See the model pattern study (2026-10-10).
PLATT_INTERCEPT = 0.110
PLATT_SLOPE = 0.711


def margin_to_prob(margin: float, sigma: float = SIGMA,
                   apply_platt: bool = True) -> float:
    """P(home wins) for a predicted home margin in runs. No ties in MLB.

    Platt recalibration is applied by default (validated 2026-10-10);
    pass apply_platt=False for the raw normal-CDF value (e.g. to log
    pre/post-correction values for the 2027 validation).
    """
    p = 0.5 * (1.0 + math.erf(margin / (sigma * math.sqrt(2.0))))
    return platt_scale(p) if apply_platt else p


def platt_scale(p_home: float) -> float:
    """Apply Platt (logistic) recalibration to a raw home win probability.

    Monotone in p_home, so pick sides are preserved except near 0.5 --
    the decision boundary moves to ~0.473 raw (the +0.110 intercept shifts
    everything slightly toward home, correcting the underdog underestimation).
    """
    p = min(max(p_home, 1e-9), 1.0 - 1e-9)
    logit = math.log(p / (1.0 - p))
    return 1.0 / (1.0 + math.exp(-(PLATT_INTERCEPT + PLATT_SLOPE * logit)))
