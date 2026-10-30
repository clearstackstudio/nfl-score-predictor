# Backup-QB Team-Rating Test — RESULTS (run 2026-10-29)

Pre-registration: `FOLLOWUP-SCOPE-2026-10-26.md`, Candidate 2 — FROZEN
2026-10-29 at Bryant's approval ("Run the backup-QB test, drop the rest
candidate"). Runner: `run_backup_qb.py`. **No model or code change was made.
The verdict returns to Bryant; any change needs its own pre-registered
implementation test + his approval.**

Question: when a team starts a backup QB, does the model's remaining team
rating systematically overshoot the market?

## Verdict: CLEARS THE FROZEN ADOPT BAR

| Adopt-bar condition (frozen) | Result |
|---|---|
| Same direction in ≥ 3 of 5 seasons | **5 of 5 seasons, all positive** |
| Pooled model-vs-market residual gap > 1.0 pt | **+1.11 pts** (n = 289 backup appearances) |

The effect is real by the pre-registered standard: in backup-QB games the
model prices the backup team **~1.1 points higher than the market does**,
every season 2021–2025, and the outcome check agrees on the direction — the
model's margins overshoot actual results for backup teams by **+1.91 pts**
on average, while the market overshoots the same teams by only **+0.80**.
The model's excess optimism beyond the market's is the gap: +1.11.

## Primary numbers (frozen definition)

Backup = starter differs from the team's previous-game starter that season
(season openers excluded). Population: 1,327 regular-season games 2021–2025
in the walk-forward frame; 261 games (19.7%) involved at least one backup
team; 289 backup appearances (28 games had backups on both sides).

| Season | Appearances | Model resid | Market resid | Gap |
|---|---|---|---|---|
| 2021 | 58 | +1.39 | +0.51 | **+0.88** |
| 2022 | 63 | +1.86 | +0.10 | **+1.76** |
| 2023 | 61 | +2.68 | +1.15 | **+1.53** |
| 2024 | 52 | +3.28 | +3.01 | **+0.27** |
| 2025 | 55 | +0.39 | −0.56 | **+0.95** |
| **Pooled** | **289** | **+1.91** | **+0.80** | **+1.11** |

Residuals are signed from the backup team's perspective (positive = the
margin estimate was too kind to the backup team vs the actual result).
Baseline for scale: in non-backup games the model's raw disagreement with
the market is only +0.17 pts, so the +1.11 is specific to backup weeks, not
a general model tilt.

**Sensitivity cut** (starter had started ≤ half of the team's prior games
that season — i.e., true fill-ins, not new permanent starters): 225
appearances, pooled gap **+1.56**, also positive in **5 of 5** seasons. The
effect is *stronger* for genuine spot-starters, which fits the mechanism.

## Secondary: what it costs in winners (Bryant's framing)

Plays (|edge| ≥ 0.5) involving a backup team, 2021–2025: **252 plays
(~50 per season, ~2.8 per week) — record 110 W – 134 L – 7 P (45.1%)**.

- Backing the backup team: 59–69–6 (46.1%)
- Fading the backup team: 39–53–1 (42.4%)

Backup-QB games are where a disproportionate share of our losing plays
live: 134 losers vs 110 winners over five seasons, against a model that is
near break-even overall. Both directions lose — our margins in these games
are simply less reliable, and the rating overshoot is one measured piece of
why. What a fix is worth in winners cannot be read off this test; that is
exactly what the follow-up implementation test would measure (e.g., an
extra haircut on a backup team's rating and a recount of flipped/losing
plays). Nothing is claimed beyond the frozen metrics.

## Honest caveats

- Per-season appearance counts (~52–63) against a residual SD of ~13–14 pts
  make any single season noisy (per-season gap SE ≈ 1.9 pts). The frozen bar
  was point-estimate based and it cleared on the pooled figure plus 5/5 sign
  consistency — reported as frozen, not re-litigated after the fact.
- 2024 is the soft season (+0.27): the market overshot backup teams almost
  as much as we did (+3.01), so the *relative* gap is small even though our
  absolute overshoot was the largest of any season (+3.28).
- The gap statistic itself is model-minus-market (outcome-independent);
  the outcome dependence enters through the residual levels, which point
  the same way.
- Week 6 2026 (BAL @ CLE, the hypothesis-generating game) is excluded, as
  frozen — the frame predates it.

## Rest candidate — CLOSED

Candidate 1 (model record vs teams on ≥13 rest days) was **DROPPED by
Bryant's decision 2026-10-29** and formally closed: it duplicates the
2026-10-02 rest/travel test on the same walk-forward frame, which found no
systematic effect and took rest/travel off the board. Nothing was run.

## What happens next (not automatic)

Nothing changes in the model. If Bryant wants to pursue it, the next step
is a *separate* pre-registered implementation test — e.g., shaving the
backup team's rating by the measured overshoot when the QB adjustment is
at/near its cap — with its own adopt bar on winner counts. That decision is
his, separately, as with every prior test.
