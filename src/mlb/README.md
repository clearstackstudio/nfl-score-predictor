# Honest Line MLB model

Team-level MLB prediction model + walk-forward backtest, built October 2026.
Same honesty rules as the NBA/NFL models: **the betting line is never a model
input** (only the benchmark), **prediction precedes update** (every game is
predicted from ratings built only on prior games), and the published numbers
are the real numbers -- including the verdict.

## Headline backtest results (2012-2021, 22,765 games)

- Straight-up: **55.3%** (home teams won 53.5%; model picks home 55.8% of the time)
- Brier: model **0.2456** vs closing line **0.2402** -- the line is sharper
- Flat $100 moneyline, bet only when |model_prob - implied_prob| >= 0.05:
  **5061-6308 (44.5%), -$24,959, -2.2% ROI** over 11,369 bets
- Totals: model RMSE 4.42 vs line 4.37; O/U at a 0.5-run threshold:
  6582-6472 (50.4%), -$47,939, -3.7% ROI
- **Verdict: competent forecaster, no betting edge.** Team strength alone does
  not beat the closing MLB line. (Full numbers: `backtest_results.json`.)

## How to run

```bash
cd ~/workspace/nfl-score-predictor
python3 src/mlb/backtest.py                      # full run, writes src/mlb/backtest_results.json
python3 src/mlb/backtest.py --seasons 2016 2021  # evaluate a slice
python3 src/mlb/backtest.py --out /tmp/mlb.json  # custom output path
```

Takes ~1-2 minutes: loads the data, fits the home edge, grid-tunes
(alpha, carryover) on 2012-2015 walk-forward RMSE, fits the winprob sigma on
the same split, then runs the full walk-forward twice (all seasons + the
2016-2021 post-tuning slice).

## Modules

- `data.py` -- pairs the two rows-per-game CSV into game records; derives
  home/away from the park (tenant mapping verified empirically); flags 30
  neutral-site games (Tokyo/London/Sydney/Mexico/Puerto Rico series, Field of
  Dreams, Fort Bragg, Omaha, Williamsport Classic, and six 2017
  hurricane-relocation games) where the home edge is zeroed. 2020's 60-game
  season flows through naturally.
- `ratings.py` -- `MLBRatings`: park-adjusted exponential runs ratings
  (offense/defense per team), expanding park factors with a 100-game shrinkage
  prior, expanding league scoring average, fitted home edge (0.130 runs),
  season rollover. Tuned: alpha=1/40, carryover=0.25 (flat RMSE surface;
  slow learning wins in baseball).
- `winprob.py` -- P(home win) = Normal CDF(predicted margin / sigma),
  sigma=4.135 fitted on tuning residuals. Calibration check: predicted 0.40
  -> actual 0.465; 0.50 -> 0.53; 0.60 -> 0.60; 0.73 -> 0.70. Slightly
  under-confident on underdogs, otherwise well-calibrated.
- `pitcher.py` -- DESIGN ONLY. The historical data has no pitcher column, so
  the backtest is team-level. Documents how live picks will adjust for
  probable pitchers from the free MLB Stats API, with a league-average
  fallback. Never called by the backtest.
- `backtest.py` -- walk-forward evaluation, metrics, JSON + printed report.

## Live-picks plan (to be built Feb/Mar 2027, ahead of the 2027 season)

1. Nightly cron (mirroring the NBA `nba-daily-picks` pattern): pull today's
   schedule + probable pitchers from the MLB Stats API, run the team model
   (ratings carried forward from the 2021 end-state or re-seeded), apply the
   `pitcher.py` adjustment, publish picks + win probabilities.
2. Validate the `STARTER_SHARE = 0.6` starting point on 2027 games before
   trusting it -- it is NOT a fitted constant.
3. Keep the team-level backtest as the baseline; the pitcher's job is to add
   whatever the market hasn't already priced (the closing line already knows
   the probable pitcher, so this is an uphill battle -- say so if it fails).

## Limitations (documented, not hidden)

- Team-level only: no pitcher, bullpen, lineup, or weather inputs.
  The closing line already prices the probable pitcher, which is the biggest
  single-game factor in MLB -- the main reason for "no betting edge."
- Park factors are simple runs-environment ratios (conflate park + DH/schedule
  mix); computed leakage-safe on prior games only.
- No margin-of-victory scaling in updates; no rest/travel adjustments
  (baseball's daily grind makes these second-order).
- 2020's 60-game season and the fanless stands are in the sample as-is.
