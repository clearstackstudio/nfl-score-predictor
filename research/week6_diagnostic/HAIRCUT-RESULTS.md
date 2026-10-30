# Backup-QB Haircut Implementation Test — RESULTS (run 2026-10-29)

Pre-registration: `HAIRCUT-PREREG-DRAFT.md` — FROZEN 2026-10-29 at
Bryant's approval ("Freeze it as written and run the test"). Runner:
`run_haircut.py`, frame and joins identical to the diagnostic
(`run_backup_qb.py`). **No model or code change was made, and none is
authorized by this result. The verdict returns to Bryant.**

Question: does shaving a backup team's predicted margin by the measured
overshoot (a single pre-committed 1.0-pt haircut, spread-only, additive
with the unchanged QB adjustment, play selection re-run at τ = 0.5)
win more picks than it loses?

## Verdict: FAILS THE FROZEN BAR — KILL

| Adopt-bar condition (frozen §5) | Bar | Result |
|---|---|---|
| 1. Pooled net winners on affected plays | ≥ +5 | **−2** ✗ |
| 2. No season materially worse | every season ≥ −2 | worst season **−4** (2022) ✗ |
| 3. Consistency | net ≥ 0 in ≥ 3 of 5 seasons | **4 of 5** ✓ |
| 4. No cost elsewhere | all-plays Δ winners ≥ 0 | **−2** ✗ |
| Leakage check (frozen §4) | non-backup Δ exactly 0 | **0** ✓ (run valid) |

Three of four conditions fail. Per the frozen terms, the backup-QB
haircut question **closes permanently**: no re-run at 0.5 or 1.5 pts
under any re-labeling. The diagnostic's finding stands as a known,
accepted limitation — the model's margins in backup weeks run ~1 pt
optimistic vs the market, and we publish anyway.

## Primary metric — winner count on affected plays

Affected plays = plays in one-backup games (both-backup games excluded
per §1 — the haircut cannot change their margin) under either selection.
Pushes count as non-winners.

| Season | Plays before → after | W–L–P before | W–L–P after | Net winners |
|---|---|---|---|---|
| 2021 | 44 → 44 | 22-22-0 | 22-22-0 | **+0** |
| 2022 | 53 → 48 | 26-25-2 | 22-24-2 | **−4** |
| 2023 | 43 → 42 | 10-31-2 | 11-29-2 | **+1** |
| 2024 | 40 → 39 | 17-21-2 | 18-19-2 | **+1** |
| 2025 | 47 → 47 | 23-23-1 | 23-23-1 | **+0** |
| **Pooled** | **227 → 220** | **98-122-7** | **96-117-7** | **−2** |

Play movement across the 233 affected games: **0 flipped, 13 dropped,
6 added, 214 unchanged.** The 1.0-pt shift never once crossed the line
far enough to flip a pick's side — every change was a marginal play
falling off (or onto) the τ = 0.5 board, and the dropped plays happened
to carry more winners (the pooled record improves slightly in win% —
96-117 vs 98-122 — while *losing* two winners in absolute count, which
is exactly the distinction Bryant's winner-count objective exists to
catch).

## Secondary and checks

- **ATS on all backup-involved plays** (incl. both-backup): before
  110-134-7 (45.1%) → after 108-129-7 (45.6%). Backing the backup team:
  46.1% → 47.0%. Fading: 42.4% → 42.9%. Rates tick up; winner counts
  fall. The bar was on counts, as frozen.
- **Residual gap after the haircut (sanity check):** +0.306 pooled over
  289 appearances. The draft expected ~+0.11; the exact figure is
  explained by construction — 233 of 289 appearances sit in one-backup
  games and shift by the full point, while the 56 appearances in
  both-backup games do not move (their margins are unchanged by
  construction): +1.11 − 233/289 ≈ +0.30. The haircut was applied as
  specified.
- **All plays, 2021–2025:** 571 winners before → 569 after (Δ −2, all of
  it from affected plays, as required).
- **Leakage check:** winners on non-backup-involved plays 461 → 461,
  Δ exactly 0. The run is a valid implementation of the frozen spec.
- **Descriptive — sensitivity population** (exactly one true-fill-in
  appearance, 191 games with a play either way): 84 winners before →
  80 after, net **−4**. The haircut loses in genuine spot-start games
  too, so the failure is not an artifact of the definition's permanent-
  starter changes.
- **Descriptive — both-backup games:** identical before/after in every
  season (25 plays, 12 winners), as constructed.

## Honest caveats

- The measured +1.11-pt overshoot is real (frozen diagnostic, 5 of 5
  seasons), but it lives in the *middle* of the margin distribution:
  correcting it moves predicted margins without flipping any pick in
  five seasons of data. What it changes is which marginal plays clear
  τ = 0.5, and that churn was a small net negative here. A margin bias
  does not automatically convert into pick wins — this is the same
  lesson as the killed publish-threshold test (τ = 0.5 stands).
- 2022 drives the failure (−4 of the −2 net is more than the total; the
  other four seasons sum to +2). With ~45 affected plays per season,
  single-season swings of this size are well within noise — which is
  precisely why the frozen bar demanded a pooled gain and a
  worst-season floor, and why the verdict follows the bar rather than a
  post-hoc story about 2022.
- Nothing here re-opens the diagnostic: its question (does the rating
  overshoot?) was answered yes; this test's question (does the obvious
  correction win more picks?) is answered no. Both results stand.

## What happens next (not automatic)

Nothing. The model is unchanged, the question is closed, and the
finding joins threshold and momentum in the killed pile. Any future
backup-QB idea would be a new hypothesis needing its own
pre-registration and Bryant's approval — and it would have to explain
why it is not a second bite at this data.
