"""Backup-QB haircut implementation test — FROZEN 2026-10-29 (Bryant approved).

Spec: research/week6_diagnostic/HAIRCUT-PREREG-DRAFT.md (frozen 2026-10-29).
Frame/joins identical to run_backup_qb.py: walk-forward frame
(research/nfl_threshold/per_game.csv) joined to data/schedules_games.parquet,
regular-season games 2021-2025. Backup definition: starter differs from the
team's previous-game starter that season (openers excluded).
Intervention: predicted margin of a backup team reduced by exactly 1.0 pt
(home backup -> margin -1; away backup -> margin +1; both -> unchanged).
Totals untouched. Play selection re-run at |edge| >= 0.5 (tau = 0.5).
Primary: net winner-count change on affected plays (pushes = non-winners).
Adopt bar (frozen): pooled net winners >= +5 AND every season >= -2 AND
net >= 0 in >= 3 of 5 seasons AND all-plays winners do not decrease AND
leakage check (non-backup delta == 0 exactly).
No live-model change is made by this run.
"""
import pandas as pd
import numpy as np

ROOT = '/home/hatch/workspace/nfl-score-predictor'
TAU = 0.5
HAIRCUT = 1.0

# ---- Frame construction: copied verbatim from run_backup_qb.py ----
sched = pd.read_parquet(f'{ROOT}/data/schedules_games.parquet')
sched = sched[(sched.game_type == 'REG') & (sched.season.between(2021, 2025))]
sched = sched.sort_values(['season', 'gameday', 'game_id'])

rows = []
for _, g in sched.iterrows():
    rows.append(dict(season=g.season, date=g.gameday, team=g.home_team,
                     qb=g.home_qb_id, opp=g.away_team, home=True))
    rows.append(dict(season=g.season, date=g.gameday, team=g.away_team,
                     qb=g.away_qb_id, opp=g.home_team, home=False))
tg = pd.DataFrame(rows).sort_values(['season', 'team', 'date'])

tg['prev_qb'] = tg.groupby(['season', 'team'])['qb'].shift(1)
tg['is_backup'] = (tg.prev_qb.notna()) & (tg.qb != tg.prev_qb)
tg['qb_starts_prior'] = tg.groupby(['season', 'team', 'qb']).cumcount()
tg['team_games_prior'] = tg.groupby(['season', 'team']).cumcount()
tg['is_backup_sens'] = (tg.prev_qb.notna()) & (tg.qb != tg.prev_qb) & \
    (tg.qb_starts_prior <= 0.5 * tg.team_games_prior)

flags = tg.pivot_table(index=['season', 'date', 'team'], values=['is_backup', 'is_backup_sens'],
                       aggfunc='first').reset_index()

pg = pd.read_csv(f'{ROOT}/research/nfl_threshold/per_game.csv')
pg = pg[pg.season.between(2021, 2025) & (pg.week <= 18)].copy()
pg['date'] = pg['date'].astype(str)

lk = sched[['season', 'gameday', 'home_team', 'away_team']].rename(
    columns={'gameday': 'date', 'home_team': 'home', 'away_team': 'away'})
pg = pg.merge(lk, on=['season', 'home', 'away'], how='left', suffixes=('', '_sched'))
assert pg.date_sched.notna().all(), 'matchup not found in schedules'
pg['date'] = pg['date_sched']
pg = pg.drop(columns=['date_sched'])

m = pg.merge(flags.rename(columns={'team': 'home',
                                   'is_backup': 'home_backup',
                                   'is_backup_sens': 'home_backup_sens'}),
             on=['season', 'date', 'home'], how='left')
m = m.merge(flags.rename(columns={'team': 'away',
                                  'is_backup': 'away_backup',
                                  'is_backup_sens': 'away_backup_sens'}),
            on=['season', 'date', 'away'], how='left')
assert m.home_backup.notna().all() and m.away_backup.notna().all(), 'unmatched games'
print(f'frame games: {len(m)}  seasons: {sorted(m.season.unique())}')
# ---- End of verbatim frame construction ----

# ---- Intervention (frozen spec section 1) ----
m['adj'] = np.where(m.home_backup & ~m.away_backup, -HAIRCUT,
            np.where(m.away_backup & ~m.home_backup, +HAIRCUT, 0.0))
m['hc_margin'] = m.our_margin + m.adj
m['edge_base'] = m.our_margin - m.line_margin
m['edge_hc'] = m.hc_margin - m.line_margin
assert (m.edge_base - m.spread_edge).abs().max() < 1e-9, 'edge definition mismatch'

m['home_covers'] = m.actual_margin > m.line_margin
m['push'] = m.actual_margin == m.line_margin


def grade(df, edge_col):
    """Return per-game selection: pick_home (NaN if no play), win (NaN push/none)."""
    sel = df[edge_col].abs() >= TAU
    pick_home = np.where(sel, df[edge_col] > 0, np.nan)
    win = np.where(~sel | df.push, np.nan,
                   np.where((df[edge_col] > 0) == df.home_covers, 1.0, 0.0))
    return pick_home, win


m['pick_base'], m['win_base'] = grade(m, 'edge_base')
m['pick_hc'], m['win_hc'] = grade(m, 'edge_hc')

m['any_backup'] = m.home_backup | m.away_backup
m['both_backup'] = m.home_backup & m.away_backup
m['one_backup'] = m.any_backup & ~m.both_backup


def record(df, win_col, pick_col):
    plays = df[df[pick_col].notna()]
    w = int((plays[win_col] == 1).sum())
    l = int((plays[win_col] == 0).sum())
    p = int((plays[pick_col].notna() & plays.push).sum())
    return plays, w, l, p


def season_table(mask, label):
    print(f'\n=== {label} ===')
    print(f'{"season":<7}{"plays B->A":<13}{"W-L-P before":<15}{"W-L-P after":<15}{"net winners":<12}')
    pooled = {}
    for s in sorted(m.season.unique()):
        d = m[mask & (m.season == s)]
        _, wb, lb, pb = record(d, 'win_base', 'pick_base')
        _, wa, la, pa = record(d, 'win_hc', 'pick_hc')
        nb = int(d.pick_base.notna().sum()); na = int(d.pick_hc.notna().sum())
        print(f'{s:<7}{nb:>3} -> {na:<7}{wb}-{lb}-{pb:<9}{wa}-{la}-{pa:<9}{wa-wb:+d}')
        pooled[s] = wa - wb
    d = m[mask]
    _, wb, lb, pb = record(d, 'win_base', 'pick_base')
    _, wa, la, pa = record(d, 'win_hc', 'pick_hc')
    nb = int(d.pick_base.notna().sum()); na = int(d.pick_hc.notna().sum())
    print(f'{"POOLED":<7}{nb:>3} -> {na:<7}{wb}-{lb}-{pb:<9}{wa}-{la}-{pa:<9}{wa-wb:+d}')
    return pooled, (wb, wa)


# PRIMARY: affected plays = backup-involved excl. both-backup, play under either selection
aff_mask = m.one_backup & (m.pick_base.notna() | m.pick_hc.notna())
print(f'\ngames with >=1 backup team: {int(m.any_backup.sum())}; both-backup games: {int(m.both_backup.sum())}')
print(f'affected games (one backup, play under either selection): {int(aff_mask.sum())}')
pooled_aff, (aff_wb, aff_wa) = season_table(aff_mask, 'PRIMARY — affected plays (one-backup games)')

# Play movement within affected games
aff = m[aff_mask]
flipped = int(((aff.pick_base.notna()) & (aff.pick_hc.notna()) & (aff.pick_base != aff.pick_hc)).sum())
added = int((aff.pick_base.isna() & aff.pick_hc.notna()).sum())
dropped = int((aff.pick_base.notna() & aff.pick_hc.isna()).sum())
same = int(((aff.pick_base.notna()) & (aff.pick_hc.notna()) & (aff.pick_base == aff.pick_hc)).sum())
print(f'play movement (affected games): flipped {flipped}, added {added}, dropped {dropped}, unchanged {same}')

# Metric 2: ATS on backup-involved plays (incl. both-backup), backing vs fading
print('\n=== ATS on backup-involved plays (all, incl. both-backup) ===')
bk = m[m.any_backup]
for tag, wc, pc in (('before', 'win_base', 'pick_base'), ('after ', 'win_hc', 'pick_hc')):
    plays, w, l, p = record(bk, wc, pc)
    pct = 100 * w / (w + l) if (w + l) else float('nan')
    print(f'{tag}: {len(plays)} plays  {w}W-{l}L-{p}P  ({pct:.1f}%)')
    one = plays[plays.one_backup]
    backs = np.where(one.home_backup, one[pc] == 1, one[pc] == 0)
    for lab, sub in (('backing backup team', one[backs]), ('fading backup team', one[~backs])):
        w2 = int((sub[wc] == 1).sum()); l2 = int((sub[wc] == 0).sum()); p2 = int(sub.push.sum())
        pct2 = 100 * w2 / (w2 + l2) if (w2 + l2) else float('nan')
        print(f'    {lab}: {w2}W-{l2}L-{p2}P ({pct2:.1f}%)')

# Metric 3: residual gap after haircut (sanity check)
apps = []
for _, g in m.iterrows():
    for side, flag in (('home', g.home_backup), ('away', g.away_backup)):
        if flag:
            s = 1.0 if side == 'home' else -1.0
            apps.append(s * (g.hc_margin - g.line_margin))
gap_after = float(np.mean(apps))
print(f'\nresidual gap after haircut (sanity check): {gap_after:+.3f} over {len(apps)} appearances (expected ~+0.11)')

# Metric 4: all plays + leakage check
_, wb_all, lb_all, pb_all = record(m, 'win_base', 'pick_base')
_, wa_all, la_all, pa_all = record(m, 'win_hc', 'pick_hc')
nb_mask = ~m.any_backup
_, wb_nb, _, _ = record(m[nb_mask], 'win_base', 'pick_base')
_, wa_nb, _, _ = record(m[nb_mask], 'win_hc', 'pick_hc')
print(f'\nALL plays: before {wb_all}W-{lb_all}L-{pb_all}P | after {wa_all}W-{la_all}L-{pa_all}P | delta winners {wa_all-wb_all:+d}')
print(f'LEAKAGE CHECK: non-backup winners before {wb_nb}, after {wa_nb}, delta {wa_nb-wb_nb} (must be exactly 0)')

# Metric 5a (descriptive): sensitivity population — games with exactly one sens appearance
sens_mask = (m.home_backup_sens ^ m.away_backup_sens) & (m.pick_base.notna() | m.pick_hc.notna())
_, wb_s, lb_s, pb_s = record(m[sens_mask], 'win_base', 'pick_base')
_, wa_s, la_s, pa_s = record(m[sens_mask], 'win_hc', 'pick_hc')
print(f'\nDESCRIPTIVE sensitivity population (exactly one true-fill-in appearance, play either way): '
      f'{int(sens_mask.sum())} games; before {wb_s}W-{lb_s}L-{pb_s}P, after {wa_s}W-{la_s}L-{pa_s}P, net {wa_s-wb_s:+d}')

# Metric 5b (descriptive): both-backup games per season
print('\nDESCRIPTIVE both-backup games (margin unchanged by construction):')
for s in sorted(m.season.unique()):
    d = m[m.both_backup & (m.season == s)]
    _, wb2, lb2, pb2 = record(d, 'win_base', 'pick_base')
    _, wa2, la2, pa2 = record(d, 'win_hc', 'pick_hc')
    print(f'  {s}: {len(d)} games; before {wb2}W-{lb2}L-{pb2}P, after {wa2}W-{la2}L-{pa2}P')

# Adopt bar (frozen section 5)
net_pooled = aff_wa - aff_wb
worst_season = min(pooled_aff.values())
n_nonneg = sum(1 for v in pooled_aff.values() if v >= 0)
all_delta = wa_all - wb_all
leak_ok = (wa_nb - wb_nb) == 0
print('\n=== ADOPT BAR (frozen) ===')
print(f'1. pooled net winners on affected plays {net_pooled:+d} >= +5? {net_pooled >= 5}')
print(f'2. worst season net {worst_season:+d} >= -2? {worst_season >= -2}')
print(f'3. seasons with net >= 0: {n_nonneg}/5 >= 3? {n_nonneg >= 3}')
print(f'4. all-plays winners delta {all_delta:+d} >= 0? {all_delta >= 0} | leakage check passes? {leak_ok}')
clears = net_pooled >= 5 and worst_season >= -2 and n_nonneg >= 3 and all_delta >= 0 and leak_ok
print(f'VERDICT: {"CLEARS THE FROZEN BAR" if clears else "FAILS THE FROZEN BAR — KILL"}')
