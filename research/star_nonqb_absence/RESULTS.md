# Results: star non-QB absence bias study (NFL)

Date: 2026-10-10/11. Pre-registration: `~/workspace/goals/ultimate-multi-sport-prediction-model/files/star-nonqb-absence-preregistration.md` (written before any game data was touched). Research only — no model changes.

## Verdict

**NULL** (per pre-registered decision rule). The primary test did not clear the
|1.0|-point bar. **Do not add a non-QB injury feature.** File with the other
killed ideas.

## Primary result (high-quality sources: PFR direct + nflverse snaps)

- n=1,064 star-absence team-games (1980–2001 via PFR gamelogs, 2013–2024 via
  nflverse snap counts)
- mean residual = **−0.201** pts, 95% CI [−1.032, +0.631], **p = 0.64**
- |−0.201| < 1.0 and p > 0.05 → null by the pre-registered rule, not close.

Position splits (high-quality sources, star-level rows):
- skill (RB/WR/TE): n=339, −0.571, CI [−2.014, +0.872], p=0.44
- OL (T/G/C): n=243, −1.272, CI [−3.023, +0.479], p=0.15
- defense: n=658, +0.054, CI [−1.015, +1.123], p=0.92
- All null; directions inconsistent.

Other pre-registered secondaries (high-quality sources):
- early (streak ≤ 4): −0.057, p=0.91; late (streak ≥ 5): −0.591, p=0.44
- leave-one-season-out primary means: [−0.489, +0.023] — stable, all near zero
- excluding strike seasons (1982/1987): −0.205, p=0.63
- dose-response 2+ stars out: −2.73 (n=81, p=0.11) — descriptive only, null

Sanity checks: baseline residual +0.0000 over 21,722 team-games; residual SD
13.64 (published ~13.7); fidelity gate passed (RMSE 13.67, ATS 52.1% reproduced
from residuals.csv before any join).

## Data-source heterogeneity (must-read caveat)

A third source — Wayback Machine snapshots of PFR gamelogs for 2002–2012
(n=420 team-games, used because PFR rate-blocked direct scraping) — shows a
sharply different result: **mean −2.662, p=0.0001**, significant across all
position groups (skill −3.99, OL −3.71, defense −1.74) and all absence lengths.

This contradicts the two independent high-quality sources (PFR direct +0.129,
p=0.83; nflverse snaps −0.524, p=0.38). The pattern — uniform negative shift
across positions, extreme season-to-season variation (2003: −6.0, 2010: +4.6),
no dose-response gradient — is consistent with a systematic data artifact
rather than a football effect, but the specific mechanism was not identified
despite investigation (absence records spot-check correct against known
injuries; week/team mappings verified; not outlier-driven — trimmed mean
−2.61).

Because the anomaly is unexplained, the 2002–2012 Wayback data is **excluded
from the trusted conclusion**. The verdict above rests on the 1,064 high-quality
observations. Resolving the Wayback discrepancy (or replacing 2002–2012 with a
validated source) is prerequisite to any revisit.

For the record, the all-sources primary (n=1,484, including Wayback) is
−0.897, 95% CI [−1.609, −0.185], p=0.0136 — statistically significant but
below the pre-registered |1.0|-point bar, hence null by rule. It is reported
here for completeness but is not the trusted estimate given the heterogeneity.

## Deviations from pre-registration (documented before analysis)

1. **Set-difference absence detection.** PFR gamelogs only mark DNP weeks
   explicitly from ~2000 onward; earlier seasons omit missed games. Uniform
   rule: missed weeks = team's regular-season game weeks within the player's
   tenure, minus weeks he played. DNP-mark agreement check (seasons ≥ 2000):
   100% (18/18).
2. **Multi-source assembly.** PFR direct scraping was rate-blocked (HTTP 403)
   after 1980–2001; 2013–2024 uses nflverse snap counts (validated join on
   pfr_player_id); 2002–2012 uses Wayback Machine snapshots (see heterogeneity
   caveat above). Pre-reg updated to document this before analysis.
3. **2002–2012 effectively excluded from conclusion** (see above). 50
   Wayback players (2009–2012 seasons) remain unscraped due to archive.org
   rate-limiting (HTTP 429); they are missing at random and would not change
   the high-quality-source verdict.

## Files

- Scripts: `research/star_nonqb_absence/` — `01_scrape_allpro.py`,
  `02_scrape_gamelogs.py` (PFR direct), `02b_snaps.py` (nflverse),
  `02c_wayback.py` (Wayback), `03_build_absences.py`, `04_analyze.py`
- Data: `allpro_stars.csv` (1,026 star-seasons), `star_gameweeks.csv` (PFR),
  `star_gameweeks_snaps.csv` (nflverse), `star_gameweeks_wb.csv` (Wayback),
  `absences_teamgame.csv`, `absences_starlevel.csv`, `join_audit.txt`
- Pre-registration:
  `~/workspace/goals/ultimate-multi-sport-prediction-model/files/star-nonqb-absence-preregistration.md`
