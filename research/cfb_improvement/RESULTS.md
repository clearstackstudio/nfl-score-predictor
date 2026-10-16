# CFB improvement diagnostic — RESULTS

**Date:** 2026-10-12/13 · **Pre-registration:**
`goals/ultimate-multi-sport-prediction-model/hidden_files/cfb-improvement-preregistration.md`
(written before any test was run; this report follows it hypothesis by
hypothesis). **Measurement only — no live code, picks, or data were changed.**

## Headline

Of nine hypotheses, **one clears the adoption bar clearly** (H-T3, totals
shrinkage), **one clears it marginally** (H-T2, a CFB-calibrated wind hinge),
**one is untestable** with the data on hand (H-S2, FCS opponents), and the
rest fail. The parlay cannot be rescued by any leg policy — every policy
loses double digits, and the honest fix is a publishing decision, not a
model change.

The baseline itself is the sobering context: on the honest walk-forward
frame the published pick rules grade **49.2% ATS** (z vs the 52.4% breakeven
= −5.8) and **50.6% OU** (z vs breakeven ≈ −3.2) over 2014–2025. There is no
spread threshold, week, or conference slice that turns this into a winning
pick set. What *can* be improved is forecast accuracy: shrinkage makes the
model's totals meaningfully closer to reality (total RMSE 18.73 → 17.73),
even though totals picks remain a coin flip against the line.

## Method and frames

- **Frame A (replication):** the published harness's own ordering
  (season, week, date). It reproduces the published backtest
  (`data/cfb/cfb_backtest.json`) **exactly** on all 8,945 games,
  2014–2025: SU 69.82%, margin RMSE 17.82 vs line 15.63, ATS
  4157-4185-153 (49.8%), total RMSE 18.71 vs line 16.34, OU
  4111-4002-89 (50.7%). The capture code is a faithful copy of the live
  ratings pipeline.
- **Frame B (test frame):** identical ratings math, but games and
  team-games are ordered strictly chronologically (season, date, game_id).
  The published harness sorts by week number, and CFBD postseason week
  numbers restart at 1 — bowl games were being predicted with ratings
  contaminated by same-season games played *after* them (and early-season
  games with stale cutoffs). All hypothesis tests run on frame B
  (8,947 games; +2 vs frame A from cutoff remapping at season boundaries,
  immaterial). Frame B baseline: SU 69.7%, margin RMSE 17.82 vs line 15.64,
  **ATS 4102-4233-154 = 49.2%**, total RMSE 18.73 vs line 16.35, **OU
  4083-3987-90 = 50.6%**. Note the published record flatters ATS by
  ~0.6pp because of the ordering artifact.
- **Frame B8:** frame B with MIN_GAMES raised 4 → 8 (H-S3 variant).
- All fits in H-T1/H-T2/H-T3/H-T4 are walk-forward (fit on prior seasons
  only). 2026 is reported separately at the end and was never tuned on.
- Adoption bar (pre-registered): a change must improve its metric in a
  **majority of backtest seasons AND overall**, by a margin that survives
  the sample size. One-season wins are noise.

Per-season baseline (frame B, published thresholds ATS ≥0.5, OU ≥1.0):

| Season | Games | ATS | ATS% | OU | OU% | Margin RMSE (line) | Total RMSE (line) |
|---|---|---|---|---|---|---|---|
| 2014 | 666 | 328-294-11 | 52.7% | 314-283-8 | 52.6% | 18.40 (15.74) | 19.69 (16.81) |
| 2015 | 757 | 350-352-8 | 49.9% | 342-352-4 | 49.3% | 17.62 (15.88) | 19.42 (16.89) |
| 2016 | 747 | 325-368-14 | 46.9% | 375-297-4 | 55.8% | 18.91 (16.60) | 18.22 (16.97) |
| 2017 | 770 | 353-354-18 | 49.9% | 337-352-11 | 48.9% | 17.92 (15.64) | 19.73 (17.18) |
| 2018 | 769 | 342-373-13 | 47.8% | 375-323-2 | 53.7% | 17.83 (15.98) | 18.62 (16.56) |
| 2019 | 773 | 360-357-10 | 50.2% | 345-349-10 | 49.7% | 17.40 (15.47) | 18.13 (16.12) |
| 2020 | 534 | 237-266-9 | 47.1% | 258-231-4 | 52.8% | 18.23 (16.02) | 18.74 (17.04) |
| 2021 | 767 | 360-364-10 | 49.7% | 320-359-7 | 47.1% | 17.59 (15.60) | 18.45 (15.98) |
| 2022 | 774 | 349-364-13 | 48.9% | 321-367-12 | 46.7% | 17.78 (15.25) | 18.65 (15.35) |
| 2023 | 790 | 364-369-15 | 49.7% | 360-350-9 | 50.7% | 17.11 (15.21) | 18.13 (15.80) |
| 2024 | 794 | 359-391-16 | 47.9% | 360-368-14 | 49.5% | 17.89 (15.41) | 18.62 (16.24) |
| 2025 | 806 | 375-381-17 | 49.6% | 376-356-5 | 51.4% | 17.38 (15.00) | 18.45 (15.53) |

---

## Spreads

### H-S1 — edge threshold: **KILLED**

No threshold comes close. Every cumulative threshold from |edge| ≥ 0.5 to
≥ 10 grades 48.2–49.4% ATS, all significantly below the 52.4% breakeven
(z vs breakeven −3.1 to −5.8):

| Threshold | n decided | ATS% | z vs 50% | z vs breakeven |
|---|---|---|---|---|
| ≥0.5 (published) | 8,335 | 49.2% | −1.43 | −5.79 |
| ≥2 | 6,951 | 49.4% | −0.97 | −4.95 |
| ≥3 | 6,076 | 48.9% | −1.72 | −5.44 |
| ≥5 | 4,486 | 48.5% | −2.00 | −5.19 |
| ≥7 | 3,197 | 48.2% | −2.03 | −4.73 |
| ≥10 | 1,786 | 48.7% | −1.09 | −3.10 |

Edge size carries no information about covering: buckets are flat
(0.5–1: 49.9%; 1–2: 47.3%; 2–3: 53.0%; 3–4: 49.5%; 5–7: 49.3%; 7–10:
47.6%; 10+: 48.7%), and the largest edges do slightly *worse*. The single
good-looking bucket (2–3 pts, 53.0%, n=875, z=+1.79 vs 50%) is not
significant against breakeven and does not repeat per-season (at threshold
≥3, only 2014 and 2023 exceed 52% — full per-season table in
`out_main.txt`). Publishing fewer, "stronger" spread picks does not help.

### H-S2 — FCS opponents: **UNTESTABLE with data on hand**

Zero of the 8,947 backtest games — and zero of all 9,363 lined games in the
repo's dataset (2014–2026) — involve a non-FBS team. The historical data
simply contains no FBS-vs-FCS games to grade, and the CFBD quota is
exhausted until ~Nov 1, so the missing history cannot be built now.

This matters because the hypothesis is live-relevant: the *live* pick
generator does publish FBS-vs-FCS games (2026 Week 6 included Sacramento
State and North Dakota State). Those picks sit entirely outside everything
the backtest has ever validated. Flagged for Bryant: either exclude
FCS-opponent games from live picks on principle (unvalidated), or build
the FBS-vs-FCS history once the CFBD quota resets and test then. This
study takes no position — there is no evidence either way.

### H-S3 — early-season weeks / stronger shrinkage: **KILLED**

The premise fails: early games are not worse. ATS by games-played-prior
(minimum of the two teams): 0–1 games: 49.6% (n=1,594); 2–3: 49.8%
(n=1,479); 4–5: 49.4% (n=1,446); 6+: 48.7% (n=3,816) — late-season games
are if anything the worst. By week band it is flat: wk1-2 48.5%, wk3-4
50.0%, wk5-8 49.9%, wk9-12 48.7%, wk13+ 49.1%, postseason 48.2%.

The stronger-shrinkage variant (frame B8, MIN_GAMES 4 → 8) changes
nothing: overall ATS 49.3% vs 49.2%; on early games (≤3 played) 49.8% vs
49.7%; per-season it is better in 1 season, worse in 0, the same in 11 —
a +0.1pp wiggle that does not approach the adoption bar and leaves every
number ~3pp under breakeven.

### H-S4 — conference vs non-conference: **KILLED**

Conference games: 49.7% (2870-2909-113, n=5,779 decided). Non-conference:
48.2% (1232-1324-41, n=2,556). The 1.5pp gap is not significant
(two-proportion z = +1.23), conference ATS per-season oscillates around
50% (46.4%–52.3%), and neither slice clears breakeven. Nothing to publish
or exclude on this dimension.

---

## Totals

Baseline (frame B): published rule (|edge| ≥ 1.0) OU 50.6%
(4083-3987-90); live rule (with the ≤8.5 circuit) 50.4% (2513-2469-62).
Over picks 49.8%, under picks 51.7%. By edge bucket: [1, 2.5) 49.7%;
[2.5, 5) 52.9%; [5, 8.5) 48.7%; [8.5, ∞) 50.8%. The [2.5, 5) pocket is
examined under H-P1(c) below — it does **not** validate (52.9% overall but
≥52.4% in only 5 of 12 seasons; z vs breakeven = +0.42).

### H-T1 — pace term: **KILLED**

The current formula already uses team pace (average of the two teams'
trailing plays/game, from `cfb_ratings.predict`), so the question was
whether a better plays specification helps. It does not, by any
specification tried:

| Variant | Total RMSE | OU% |
|---|---|---|
| Current (mean of team paces) | 18.73 | 50.6% |
| Constant 72 plays | 18.91 | 50.7% |
| Pace shrunk 50% toward 72 | 18.82 | 50.7% |
| Geometric-mean pace | 18.73 | 50.6% |
| Harmonic-mean pace | 18.72 | 50.6% |
| Min pace (slow team dictates) | 18.56 | 50.7% |

Walk-forward pace coefficient (P′ = 72 + b·(P−72), b fit on prior
seasons): b* = 1.25 (grid edge) chosen in 10 of 11 seasons, RMSE improved
in 10 seasons — but by 0.01–0.10 pts per season (~0.04 on average), and
OU% is unmoved. Min-pace's −0.17 is an in-sample number with no
walk-forward support. Against H-T3's ~1.0-pt improvement, pace
re-specification is a rounding error. The plays assumption is not the
drag.

### H-T2 — CFB-calibrated wind hinge: **SUPPORTED, MARGINAL** (candidate, second tier)

Wind data: ERA5 hourly at the home stadium, kickoff hour (fetched for this
study, 2014–2025, 134 outdoor schools). Coverage on frame B: 8,030 outdoor
games (713 neutral-site and 189 dome games excluded by construction; 15
games had no stadium match). Wind ≥15 mph: 366 games.

The physical pocket is real. Model total bias (our_total − actual) by
kickoff wind, outdoor games: 0–5 mph: +0.37 (n=2,706); 5–10: +1.40
(n=3,590); 10–15: +1.23 (n=1,378); **15–20: +4.55** (n=303); 20+: +1.63
(n=49). At ≥15 mph overall the bias is +4.34 — the model over-predicts
totals in real wind.

The 2022–2024 cross-check on frame B reproduces the original H2 kill:
the verbatim NFL hinge (10, 1.0, cap 8) flips the high-wind bias from
+3.66 to −3.08 and drops high-wind OU from 55.6% to 50.0%. The NFL slope
is roughly twice what college needs; the fix is the cap.

Walk-forward CFB fit (hinge grid fit on prior seasons only, evaluated
2016–2025) chose **(threshold 12, slope 1.0, cap 4)** every year:

- Outdoor total RMSE improved in **9 of 10** evaluation seasons
  (per-season gains 0.02–0.06); pooled WF outdoor RMSE **18.57 → 18.53
  (−0.04)**.
- Pooled WF outdoor OU: 50.7% → **50.9%** (1923-1872-51 → 1939-1870-48) —
  no degradation. Per-season OU is mixed (better in 6 of 10).
- In-sample best parameters (10, 0.75, 4) would take the ≥15 mph bias
  from +4.34 to +0.36 and high-wind OU from 48.2% to 52.3% (n=366) —
  descriptive only; the walk-forward parameters above are the honest
  shipping candidate.

Verdict against the bar: it improves its metric (outdoor total RMSE) in a
majority of seasons (9/10; sign-test p ≈ 0.02) and overall, without
degrading OU% — it clears the bar's letter. But the effect size is
negligible in practical terms (−0.04 RMSE, ~0.2%, on outdoor games only;
the subset where the hinge binds at all is a few hundred games). Listed
as a candidate because the mechanism is physical and the direction is
consistent, with the size stated plainly so the decision is informed.

### H-T3 — shrinkage of predicted totals: **SUPPORTED** (the study's one clear finding)

Shrink the PPA-sum component of the predicted total toward the historical
mean total: `total' = epa_const + s·(our_total − epa_const)`, s < 1.
(Margins are untouched — the spread uses the PPA *difference*; this
changes totals only.)

Fixed-factor results (full sample, descriptive):

| s | Total RMSE | OU (W-L-P) | OU% |
|---|---|---|---|
| 1.00 (current) | 18.73 | 4083-3987-90 | 50.6% |
| 0.95 | 18.52 | 4081-3954-90 | 50.8% |
| 0.90 | 18.33 | 4071-3930-89 | 50.9% |
| 0.85 | 18.15 | 4048-3913-88 | 50.8% |
| 0.80 | 17.99 | 4014-3898-88 | 50.7% |
| 0.70 | 17.73 | 3997-3860-89 | 50.9% |

Walk-forward (s chosen each season on prior seasons only): the procedure
picked **s* = 0.7 in all 11 evaluation seasons**, and shrunk totals beat
raw totals on RMSE in **11 of 11 seasons**, by 0.59–1.21 pts per season
(e.g. 2025: 18.45 → 17.25; 2021: 18.45 → 17.24; 2019: 18.13 → 17.17).
OU% improved in 7 of 11 seasons. This clears the adoption bar outright:
majority of seasons (unanimous), overall gain ~1.0 pt of RMSE (−5.3%),
closing roughly 40% of the model's gap to the closing line (18.73 vs line
16.34 → 17.73 vs 16.34).

What it does and does not do — stated plainly:

- It makes the published *numbers* more accurate. It does **not** make
  totals picks profitable: at s = 0.7 under the live rule, OU is 50.5%
  (2906-2850-67) vs 50.4% raw — still under breakeven.
- It changes pick volume: compressing edges means fewer circuit-breaker
  exclusions and more games clearing the ≥1.0 threshold — live-rule pick
  count rises from 5,044 to 5,823 (+15%) at the same win rate.
- **Grid-boundary caveat:** 0.7 was the smallest factor tested and the
  improvement is still increasing there. The true optimum may be lower.
  Adopting 0.7 as tested is justified by the pre-registration; if Bryant
  wants the optimum, the natural follow-up is a pre-registered extension
  of the grid (s ∈ [0.4, 0.7]) before or alongside adoption. Tuning
  further inside this study would break its own rules.
- The mechanism is the mirror image of the live 2026 symptom: the
  model's totals are most wrong exactly where they deviate most from the
  mean (the 2026 |edge| ≥ 5 collapse, 20-29). Shrinking deviations is
  the standard fix, and here it validates across 11 straight seasons.

### H-T4 — constant bias correction: **KILLED**

The bias is real but not stable, and stability is the whole hypothesis.
Model bias by season (our_total − actual): 2014 +0.16, 2015 +0.22, 2016
−0.75, 2017 +1.56, 2018 +0.31, 2019 +1.15, 2020 −0.75, 2021 +1.18, 2022
+2.67, 2023 +2.29, 2024 +2.09, 2025 +3.59 (line bias for comparison:
−0.43 overall, no trend). Positive in 10 of 12 seasons, overall +1.23 —
but the early-period mean is ≈ +0.35 (2014–2021) vs ≈ +2.66 in
2022–2025: the bias is *growing*, not constant.

The walk-forward expanding correction (subtract the mean bias of all
prior seasons) therefore chases a moving target: it improved total RMSE
in 8 of 11 seasons but by ≤0.17 pts (typically ≤0.08 — an order of
magnitude below H-T3), the fitted correction never exceeds +0.99 while
the actual bias reaches +3.59, and OU% gains are inconsistent (2025 OU
got worse, 51.4% → 50.6%). Same kill pattern as NFL H3: the quantity you
would correct with is not stable enough to correct with.

*Observation (not a candidate — outside the pre-registered hypotheses):*
the bias growth coincides with the recent era and with the design of
`epa_const`, an expanding all-history mean of actual totals that
necessarily lags a rising scoring environment. A windowed or
recency-weighted epa_const is the natural follow-up study if Bryant
wants to pursue the bias itself. Note H-T3's shrinkage partially absorbs
this bias mechanically (deviations shrink, the mean anchor is the same
epa_const), which is one more reason it works.

---

## Parlay — H-P1: **all policies KILLED; publishing fix recommended**

Simulation over frame B, 2014–2025, faithful to the live builder
(leg pool: spread picks |edge| ≥ 0.5, total picks 1.0 ≤ |edge| ≤ 8.5;
probabilities recalibrated exactly as live; top-3 legs per week; book
payouts +260/+600 with standard push rules). 185 weekly parlays.

Leg pool quality is the root problem: 13,533 legs, of which spread legs
win **48.3%** and total legs **49.8%**. A 3-leg parlay at +600 needs legs
of ≈52.4% each to break even. Worse, the recalibrated probabilities carry
almost no information: leg win rate by stated-probability band is 50.1%
(0.50–0.51), 49.5% (0.51–0.52), **48.3%** (0.52–0.53) — the "best" legs
win *least* often. Top-3-by-probability selection is effectively random
selection from a sub-50% pool, and because total legs carry higher
recalibrated probabilities, 180 of the 185 parlays were all-totals —
the same pathology as live 2026 Week 6.

| Policy | Parlays | Outright hits | Book ROI/unit | Fair-odds ROI/unit |
|---|---|---|---|---|
| (a) Current (top-3, any market) | 185 | 11.4% | **−0.128** (−23.6 total) | −0.140 |
| (b) Spread legs only | 185 | 10.3% | **−0.262** (−48.4 total) | −0.217 |
| (d) Current pool + EV gate | 174 | 11.5% | **−0.133** (−23.2 total) | −0.148 |

- (b) is worse than (a) because spread legs are the weakest pool (48.3%).
- (d)'s EV gate barely binds (174 of 185 weeks still bet) and cannot
  help: with probabilities this uninformative, gating on them selects
  nothing real.
- (a) per-season ROI swings wildly (+1.06 in 2020, −1.00 in 2021) and is
  negative in 7 of 12 seasons — no consistency to salvage.
- **(c) Legs only from validated slices: void.** No slice validated in
  this study. The least-bad pool — totals legs with edge in [2.5, 5) —
  wins 52.9% as picks but reaches ≥52.4% in only 5 of 12 seasons
  (z vs breakeven +0.42), so it does not meet the bar for "validated."
  For completeness, an explicitly *exploratory, post-hoc* simulation
  drawing top-3 legs from that bucket returns +0.084 ROI/unit (181
  parlays, 14.9% hits) — but the bucket was selected *because* it was
  the best of the buckets examined, the underlying slice fails its own
  validation, and treating this number as a finding would be exactly
  the selection error the pre-registration exists to prevent. It is
  reported so the record is complete, and it is **not** a candidate.

Verdict: no leg policy fixes the parlay, because the legs themselves are
sub-breakeven and their ranking signal is noise. Under the
pre-registration's fallback ("the fix is publishing policy"), the
candidate change is to **stop publishing the weekly CFB parlay** until
some leg pool demonstrably validates. (Live 2026 is 0-2 — consistent,
though far too small to be evidence on its own.)

---

## 2026 live check (reported separately, never tuned on)

Harness slice of the live season to date (frame B, n=276 lined games):
ATS 47.5% (122-135-5), OU 57.6% (148-109-0 — no pushes recorded in the
partial data), model total bias +2.46 vs line −0.73. This is **not** the
published live record — the published picks through Week 6 (n=111
graded) graded ATS 56-46-2 and OU 32-46; the two samples cover different
weeks and pick sets. The +2.46 harness bias is directionally consistent
with the H-T4 finding that the model's hot bias is largest in the most
recent seasons, and with the live symptom that triggered this study
(over picks 14-25 in weeks 5–6).

---

## Candidate changes for approval

Only the following cleared the pre-registered adoption bar. Nothing here
has been implemented; each requires Bryant's approval.

1. **Totals shrinkage, s = 0.7** (H-T3) — change the CFB totals formula
   to `epa_const + 0.7 × (ppa_sum × exp_plays)`. Walk-forward: total RMSE
   improved in 11/11 seasons, pooled gain ≈ 1.0 pt (18.73 → 17.73);
   OU% unchanged (~50.5% under the live rule); published totals pick
   volume rises ~15% because fewer games trip the circuit breaker.
   Caveat: 0.7 is the tested grid's edge — a pre-registered follow-up on
   s ∈ [0.4, 0.7] may find a better value; 0.7 is what this study
   validates. Spreads and margins are unaffected.
2. **CFB wind hinge (threshold 12 mph, slope 1.0, cap 4), outdoor games
   only** (H-T2) — walk-forward choice in all 10 evaluation years;
   outdoor total RMSE improved in 9/10 seasons, pooled −0.04; OU%
   unchanged; removes most of a real +4.3-pt model bias in ≥15 mph
   games. Marginal effect size; adopt or skip on cost/benefit — it is
   listed because it clears the bar, not because it is large.
3. **Stop publishing the weekly CFB parlay** (H-P1, publishing change,
   not a model change) — every leg policy loses 13–26% ROI over 185
   simulated weeks; no leg pool validates to restrict it to. Revisit if
   a future study validates a leg slice.

**Explicitly NOT candidates** (tested, failed the bar): any spread edge
threshold (H-S1); stronger early-season shrinkage MIN_GAMES 8 (H-S3);
conference-only publishing (H-S4); pace re-specification (H-T1); a
constant totals-bias correction (H-T4); spread-only or EV-gated parlay
legs (H-P1 b/d); the totals [2.5, 5) slice as a pick or parlay pool
(fails season-majority and significance). **Untested, not rejected:**
FCS-opponent games (H-S2 — no data exists; a live-publishing decision
about unvalidated games is Bryant's to make on principle, and the test
can be run once the CFBD quota resets and the history is built).

## Artifacts

All in `research/cfb_improvement/` (uncommitted, per instructions):
`capture.py` (frames; mode A replicates the published backtest exactly),
`frame_A.parquet` / `frame_B.parquet` / `frame_B8.parquet`,
`game_meta.parquet`, `wind_2014_2025.parquet` (ERA5, 14.1M hourly rows,
134 schools; per-school checkpoints in `parts/`),
`analyze_main.py` / `analyze_wind.py` / `analyze_parlay.py` with full
output in `out_main.txt` / `out_wind.txt` / `out_parlay.txt`,
`capture_B.log` / `capture_B8.log`. Wind fetch: `fetch_wind_ext.py`.
Metadata builder: `build_meta.py`.
