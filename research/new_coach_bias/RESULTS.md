# Results: new-head-coach bias study (NFL)

Date: 2026-10-10. Pre-registration: `~/workspace/goals/ultimate-multi-sport-prediction-model/files/new-coach-bias-preregistration.md` (written before any game data was touched). Research only — no model changes.

## Pipeline fidelity (pre-registered gate): PASS
Re-ran the published walk-forward (`src/backtest.py`, 1980–2024) verbatim:
- Our RMSE 13.67, line RMSE 13.32, ATS 3738–3436–201 = 52.1% — all match published figures exactly.
- 11,352 games; analysis sample = 10,861 regular-season games (playoff weeks excluded from analysis; playoffs still evolve ratings in the walk-forward, as the published pipeline does).

## Coach list validation
- 32/32 franchises scraped from PFR (an initial scrape missed the Saints' `nor` id — caught by the unmatched-key check, fixed, re-ran).
- 265 new-coach team-seasons 1980–2024 (expected ~250–350 ✓).
- Join coverage: 0% unmatched team-games.
- 10/10 random spot-checks agree with Wikipedia (incl. retread calls: Dennis Green ARI 2004, Dan Henning SD 1989).
- Baseline mean residual over all team-games: exactly +0.0000 (|.|<0.15 ✓); SD 13.64 (≈13.7 ✓).

## Tests (two-sided t-test vs 0; residual = actual − predicted from the new-coach team's perspective; negative = model OVERRATES new-coach teams)

| Test | n | Mean bias | 95% CI | p | Bar (|1.0|, p<.05) |
|---|---|---|---|---|---|
| PRIMARY: all new-coach games | 3,407 | −0.884 | [−1.333, −0.435] | 0.0001 | under (magnitude) |
| Secondary: weeks 1–4 | 818 | −1.496 | [−2.467, −0.526] | 0.0026 | **clears** |
| Secondary: weeks 5+ | 2,589 | −0.691 | [−1.196, −0.185] | 0.0074 | under |
| Secondary: first-time HC | 2,236 | −1.131 | [−1.684, −0.577] | 0.0001 | **clears** |
| Secondary: retread HC | 1,171 | −0.413 | [−1.181, +0.355] | 0.2918 | null |

## Robustness
- Leave-one-season-out primary means: [−0.986, −0.772] — no single season drives it.
- Excluding strike seasons (1982/1987): primary −0.805 (p=0.0005); weeks 1–4 −1.433 (clears); first-time −1.092 (clears); retread −0.256 (null).
- Excluding expansion teams (1995 CAR/JAX, 1999 CLE, 2002 HOU): primary −0.827 (p=0.0003).
- Residual distribution well-behaved (skew −0.00, kurtosis 0.33).

## Descriptive extras
- Mid-season firing ("turmoil") seasons: −3.91 pts (n=1,188 team-games, p<0.0001). Excluded from primary per pre-reg; not a predictive feature (firing known only ex post).
- Expansion teams: −4.70 pts (n=50, p=0.019) — expected, tiny sample.
- ATS impact: model picks involving new-coach teams went 52.5% (n=3,407) vs 52.1% baseline — the margin bias does not materially hurt the published ATS record.

## Verdict: NULL (per pre-registered decision rule)
The primary test did not clear the |1.0|-point bar (−0.884). **Do not add a coaching feature.**

## Honest interpretation
The effect is almost certainly real (p=0.0001, stable across sensitivity cuts) but small: the model overrates new-coach teams by ~0.9 points. It concentrates where theory predicts — first-time head coaches (−1.13) and early-season games (−1.50), while retreads are null (−0.41). Plausible mechanism: teams that fire coaches are dysfunctional beyond what their record shows, and first-time coaches don't fix it immediately; Elo's slow adjustment compounds it early. But real ≠ worth modeling: at <1 point it fails the practical-significance bar we set, and the ATS record is unaffected. File with the other nulls. If a future study revisits this, the first-time-HC × weeks-1–4 cell is where the signal lives.

## Deviations from pre-registration (documented)
1. Initial scrape missed the Saints (`nor` franchise id); caught by the unmatched-key sanity check, fixed before analysis.
2. Multi-coach seasons kept in the sample as `is_new_coach=0` rather than dropped — required for an unbiased baseline; primary test definition unchanged.
3. Strike-season exclusion added as a post-hoc sensitivity check (labeled as such); primary result reported with strike seasons included per pre-reg.
4. Scripts: `research/new_coach_bias/01_scrape_coaches.py`, `02_build_new_coach_list.py`, `03_run_residuals.py`, `04_analyze.py`. Data: `coaches_raw.csv`, `new_coach_seasons.csv`, `residuals.csv`. No `src/` or production files touched.
