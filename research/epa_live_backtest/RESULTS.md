# Live EPA model — walk-forward backtest of the EXACT live model

**Date:** 2026-10-12 · **Approved by:** Bryant (measurement only; no live code/data changed)
**Pre-registration:** `goals/ultimate-multi-sport-prediction-model/hidden_files/epa-live-backtest-preregistration.md` (written before any run)
**Interpreter:** `.venv-cfb/bin/python` (Python 3.12.3, pandas 3.0.6, pyarrow 25.0.1) — system `python3` here has no pyarrow and cannot read the parquet inputs.
**Artifacts:** `run_epa_live_backtest.py` (runner), `config_a.json`, `metrics.json`, `per_game.csv` (1,107 rows), `wind_cache.json` (ERA5 cache). No git commit/push.

## Verdict (up front)

**The upgraded live model is NOT better than the pre-upgrade numbers the site cites — on spread forecasting it measures the same to slightly worse, and the totals improvement comes from the live publication rules (wind hinge + circuit breaker), not from the upgraded ratings.**

- **Margin RMSE:** ours **14.44** vs closing line **12.73** — pre-upgrade cited 14.21 vs 12.73. Slightly worse point estimate (+0.23); the line's number is identical across both runs, so the comparison is apples-to-apples. Within noise, but there is no improvement to claim.
- **ATS (|edge| ≥ 1.5):** **47.5%** (399-441-26, 866 picks) vs pre-upgrade cited 48.2%. −0.7pp on n=840 decided (SE ≈ 1.7pp; z vs 50% = −1.45). The same, slightly worse point estimate; still below the 52.4% breakeven.
- **Totals, exact live rules (Config B):** total RMSE **15.00** (line 13.08) and OU **53.3%** (201-176-6, 383 picks) — vs 49.3% for the same predictions under the repo-harness rules (Config A). The gain is produced by the circuit breaker removing a 47.7% slice and, secondarily, the wind hinge — **not** by the ratings upgrade. Heavy caveat: the hinge and circuit were calibrated on these same 2021–2024 seasons, so 53.3% is an in-sample-flattered upper bound (z vs 50% = +1.29, not significant). As a pure forecaster the model still loses to the market on totals by ~1.9 RMSE.

## Method

- **Config A "repo harness":** `src/epa_ratings.run_backtest()` imported and called exactly as-is. Walk-forward 2021–2024 (PBP_YEARS), predict-then-learn, closing lines as benchmark only. ATS ≥ 1.5, OU ≥ 3.0, no wind, no circuit.
- **Config B "exact live totals":** the identical walk-forward re-run with the same imported functions (`adjusted_ratings`, `qb_adjustments`, `closing_home_spread`), emitting per-game rows; then the live totals rules applied post-hoc: ERA5 historical wind → `weather.wind_total_adjustment` (the live function, live team keys) → OU grading at |edge| ≥ 3.0 with `TOTAL_CIRCUIT = 7.0` excluding picks beyond it. Indoor adjustment is 0.0 (killed 2026-10-10) — a no-op, not re-added. ATS/SU/margin are A's by construction.
- **Internal validity check (pre-committed): PASSED, bit-identical.** Config B's pre-wind aggregates reproduce Config A's result dict with **0.0 difference on every metric** (games, SU%, both margin RMSEs, ATS w-l-p, both total RMSEs, OU w-l-p). The replication is exact, so every A↔B difference below is attributable to the wind hinge and circuit alone.
- **Wind:** Open-Meteo ERA5 archive API, hourly `wind_speed_10m` (mph, America/New_York), stadium coordinates from `src/stadiums.py`, hour containing kickoff (nflverse `gameday`+`gametime`). **Coverage 766/766 outdoor games (100%)** — the covered-subset fallback was not needed. 240 games received a nonzero adjustment; 73 games changed pick status/side vs raw edges.
- **Game-set accounting:** spreadspoke holds 1,139 games for 2021–2024. 17 are dropped by `run_backtest`'s name mapping — every one involves the **2021 Washington Football Team** (the only unmapped name; renamed franchises map by full name and the 2021 name isn't in `ABBR_TO_FULL`). 15 more are skipped cold-start (2021 Week 1: no prior PBP exists). **1,107 graded.** The Oct 9 diagnostic's 1,107-game frame is the same set.

## Config A — repo harness (the model, no live totals rules)

Overall: n=1,107 · SU 62.6% · margin RMSE 14.444 vs line 12.726 · total RMSE 15.169 vs line 13.077

| Season | n | SU% | Margin RMSE (ours / line) | ATS w-l-p | ATS% (picks) | Total RMSE (ours / line) | OU w-l-p | OU% (picks) |
|---|---|---|---|---|---|---|---|---|
| 2021 | 253 | 57.3 | 16.518 / 13.480 | 88-115-3 | 43.35 (206) | 15.905 / 13.409 | 88-80-3 | 52.38 (171) |
| 2022 | 284 | 63.4 | 12.772 / 11.457 | 96-111-5 | 46.38 (212) | 14.952 / 13.226 | 98-97-2 | 50.26 (197) |
| 2023 | 285 | 61.4 | 14.658 / 13.260 | 106-105-10 | 50.24 (221) | 15.780 / 13.123 | 94-124-3 | 43.12 (221) |
| 2024 | 285 | 67.7 | 13.811 / 12.692 | 109-110-8 | 49.77 (227) | 14.051 / 12.573 | 96-85-5 | 53.04 (186) |
| **All** | **1,107** | **62.6** | **14.444 / 12.726** | **399-441-26** | **47.50 (866)** | **15.169 / 13.077** | **376-386-13** | **49.34 (775)** |

Notes: 2021 is the model's worst season by far (margin RMSE 16.52) — it is the first PBP season, with no prior-season ratings to blend and 15 cold-start skips; treat it as a burn-in artifact when comparing across eras. ATS improves monotonically-ish after 2021 (46.4 → 50.2 → 49.8) but never clears breakeven. Directional totals split: overs 47.1% (231-259-10), unders 53.3% (145-127-3).

## Config B — exact live totals (wind hinge + 7.0 circuit)

ATS/SU/margin identical to Config A by construction. Totals only:

| Season | Total RMSE (adj ours / line) | OU w-l-p | OU% (picks) | Circuit-excluded |
|---|---|---|---|---|
| 2021 | 15.705 / 13.409 | 51-41-1 | 55.43 (93) | 80 |
| 2022 | 14.770 / 13.226 | 56-43-1 | 56.57 (100) | 94 |
| 2023 | 15.490 / 13.123 | 47-52-1 | 47.47 (100) | 114 |
| 2024 | 14.046 / 12.573 | 47-40-3 | 54.02 (90) | 100 |
| **All** | **14.997 / 13.077** | **201-176-6** | **53.32 (383)** | **388** |

Attribution (overall): post-wind but **without** the circuit, OU is 384-377-10 = **50.46%** (771 picks) and total RMSE 14.997 — so the wind hinge alone moves OU 49.34 → 50.46% and total RMSE 15.169 → 14.997. The **circuit breaker does the rest**: it excludes 388 would-be picks that went **183-201-4 (47.7%)**, leaving the 53.32% subset. Directional split under live rules: overs 50.2% (106-105-3), unders **57.2%** (95-71-3).

## Comparisons

**Vs the pre-upgrade numbers the site cites** (margin RMSE 14.21 vs line 12.73; ATS 48.2%, 2021–2024): the current code produces 14.44 and 47.5%. The closing-line benchmark is unchanged (12.726 vs cited 12.73), so the small regressions are in our model, not the benchmark or the window. They are within sampling noise of each other — the fair statement is **the upgrades (recency weighting, QB adjustment) bought no measurable spread improvement on 2021–2024**, not that they hurt. (Caveat: the pre-upgrade run's exact graded game set isn't recorded; if it graded a slightly different set than this harness's 1,107, part of the 0.23 / 0.7pp deltas could be game-set, not model.)

**Vs the Oct 9 totals-diagnostic replication: REPRODUCED EXACTLY, no drift.** The diagnostic reported model total RMSE ≈ 15.17–15.19 vs line 13.08 and OU 49.3% on 762 decided picks; Config A returns total RMSE 15.169 vs 13.077 and OU 376-386-13 (762 decided, 49.34%). Even the directional splits match theirs (overs 47.1%, unders 53.3%). H1's config-(a) "live" OU (50.3%, 784 picks) is *not* contradicted either — that config still included the indoor +3.0 adjustment that was killed on 2026-10-10, a different rule set from today's Config B.

**Vs the closing line:** the line beats the model on both RMSEs in every season, margins and totals, under both configs. That has been true in every measurement this project has taken and remains true.

## Findings (code/brief mismatches — documented, NOT patched)

1. **`src/stadiums.py` has no "LA" key — Rams home games silently get no weather adjustments, live or in this backtest.** The table lists SoFi Stadium as outdoor under `LAC`/`LAR`, but the EPA pipeline's team key is `LA`, so `is_outdoor("LA")` is False and `wind_total_adjustment(wind, "LA")` returns 0.0 no matter the wind (the live forecast fetcher skips them the same way). Hindcast impact over 2021–2024: 36 Rams home games, 9 with ERA5 kickoff wind > 10 mph at SoFi coordinates (max would-be hinge −8.0, the 2023-11-19 SEA game at 22.9 mph). Quantified effect on results: applying the hinge to those games hypothetically moves their OU subset from 8-7 to 8-6 with one extra circuit exclusion — **< 0.3pp on Config B's headline OU%**, i.e. the finding matters for correctness of the live product, not for this study's verdict. Flagged for a separate fix decision; nothing changed here.
2. **The 2021 Washington games are invisible to the backtest** (17 games dropped by the full-name mapping, above). This is inherited `run_backtest` behavior, identical in the Oct 9 replication, and one reason the graded set is 1,107 rather than 1,139.

## Caveats

- **Config B's OU% is calibrated in-sample.** Both the wind hinge (fit 2026-10-01) and the 7.0 circuit were calibrated on walk-forward 2021–2024 — the same window measured here. 53.3% should be read as "the live rules, on the data they were tuned on": an upper bound. The honest out-of-sample expectation is lower; the live 2025–2026 graded record is the real test and is still thin.
- **Significance:** B's OU z = +1.29 vs 50% (not significant); A's ATS z = −1.45 vs 50% (not significant). No result in this study clears a significance bar; all verdict language above is point-estimate language with sample sizes shown, per the pre-registration.
- **Wind inputs follow the live convention** — home-stadium coordinates even for the 23 neutral-site games in the graded set (Super Bowls, international games), because that is what `src/weather.py` does. Physically approximate for those games; immaterial to the totals (most are dome/foreign venues where the hinge is small or zero via the home team's climate — and it is the live behavior being measured).
- **ERA5 is reanalysis, not the live forecast.** Live picks use forecast wind at kickoff; this backtest uses observed ERA5 wind, per H1's method. Forecast error would add noise live (documented in `weather.py` itself), so B's wind benefit is also slightly optimistic vs live conditions.
- Nothing in `src/`, `site/`, or live data was modified. Uncommitted, per instructions.
