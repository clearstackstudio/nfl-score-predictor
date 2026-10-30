"""Backup-QB pre-registered test — FROZEN 2026-10-29 (Bryant approved).

Spec: research/week6_diagnostic/FOLLOWUP-SCOPE-2026-10-26.md (Candidate 2).
Population: regular-season games 2021-2025 in the walk-forward frame
(research/nfl_threshold/per_game.csv joined to data/schedules_games.parquet).
Backup definition (mechanical, leakage-safe): a team's starting QB differs
from that team's starting QB in its previous regular-season game that
season; a team's first game of a season is excluded (cannot be a backup
game). Sensitivity: starter started <= half of the team's prior games that
season.
Primary metric: mean model residual (our_margin - actual_margin) and mean
market residual (line_margin - actual_margin), signed from the backup
team's perspective; gap = model resid - market resid per appearance.
Adopt bar (frozen): same direction in >=3 of the seasons AND pooled gap
> 1.0 pt. Secondary: model ATS record on plays (|spread_edge| >= 0.5)
involving a backup team, backing vs fading.
Week 6 2026 excluded (frame predates it).
"""
import pandas as pd
import numpy as np

ROOT = '/home/hatch/workspace/nfl-score-predictor'

sched = pd.read_parquet(f'{ROOT}/data/schedules_games.parquet')
sched = sched[(sched.game_type == 'REG') & (sched.season.between(2021, 2025))]
sched = sched.sort_values(['season', 'gameday', 'game_id'])

# Build per-team-game starter records
rows = []
for _, g in sched.iterrows():
    rows.append(dict(season=g.season, date=g.gameday, team=g.home_team,
                     qb=g.home_qb_id, opp=g.away_team, home=True))
    rows.append(dict(season=g.season, date=g.gameday, team=g.away_team,
                     qb=g.away_qb_id, opp=g.home_team, home=False))
tg = pd.DataFrame(rows).sort_values(['season', 'team', 'date'])

tg['prev_qb'] = tg.groupby(['season', 'team'])['qb'].shift(1)
tg['is_backup'] = (tg.prev_qb.notna()) & (tg.qb != tg.prev_qb)
# sensitivity: starts by this QB in team's prior games this season
tg['qb_starts_prior'] = tg.groupby(['season', 'team', 'qb']).cumcount()
tg['team_games_prior'] = tg.groupby(['season', 'team']).cumcount()
tg['is_backup_sens'] = (tg.prev_qb.notna()) & (tg.qb != tg.prev_qb) & \
    (tg.qb_starts_prior <= 0.5 * tg.team_games_prior)

flags = tg.pivot_table(index=['season', 'date', 'team'], values=['is_backup', 'is_backup_sens'],
                       aggfunc='first').reset_index()

pg = pd.read_csv(f'{ROOT}/research/nfl_threshold/per_game.csv')
# Frozen population is REGULAR-SEASON games: the frame file also carries
# playoff rows (weeks 19-22); those are excluded here, as specified.
pg = pg[pg.season.between(2021, 2025) & (pg.week <= 18)].copy()
pg['date'] = pg['date'].astype(str)

# Join via a schedules game lookup on the unique (season, home, away)
# matchup: for 3 Saturday games the frame's recorded date is one day off
# from schedules' gameday, so date alone cannot be the join key.
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

m['model_resid'] = m.our_margin - m.actual_margin      # home perspective
m['market_resid'] = m.line_margin - m.actual_margin    # home perspective


def appearances(df, col_h, col_a):
    """One row per backup appearance, residuals from the backup team's view."""
    out = []
    for _, g in df.iterrows():
        for side, flag in (('home', g[col_h]), ('away', g[col_a])):
            if flag:
                s = 1.0 if side == 'home' else -1.0
                out.append(dict(season=g.season,
                                model_resid=s * g.model_resid,
                                market_resid=s * g.market_resid,
                                gap=s * (g.our_margin - g.line_margin),
                                edge=g.spread_edge, actual=g.actual_margin,
                                line=g.line_margin, side=side))
    return pd.DataFrame(out)


def report(label, col_h, col_a):
    ap = appearances(m, col_h, col_a)
    print(f'\n=== {label}: {len(ap)} backup appearances ===')
    pooled_gap = ap.gap.mean()
    print(f'pooled: model resid {ap.model_resid.mean():+.3f} | market resid '
          f'{ap.market_resid.mean():+.3f} | GAP {pooled_gap:+.3f} (n={len(ap)})')
    seasons = {}
    for s, sub in ap.groupby('season'):
        seasons[s] = (sub.gap.mean(), len(sub), sub.model_resid.mean(), sub.market_resid.mean())
        print(f'  {s}: gap {sub.gap.mean():+.3f} (n={len(sub)})  model '
              f'{sub.model_resid.mean():+.3f}  market {sub.market_resid.mean():+.3f}')
    same_dir = sum(1 for v in seasons.values() if v[0] > 0)
    print(f'  seasons with positive gap: {same_dir}/{len(seasons)}')
    return ap, pooled_gap, same_dir, seasons


ap, pooled_gap, same_dir, seasons = report('PRIMARY definition', 'home_backup', 'away_backup')
ap_s, pooled_gap_s, same_dir_s, seasons_s = report('SENSITIVITY definition', 'home_backup_sens', 'away_backup_sens')

# Non-backup baseline (descriptive, per frozen spec: "vs non-backup games")
nb = m[(~m.home_backup) & (~m.away_backup)]
print(f'\nnon-backup games: {len(nb)}  model resid (home view) {nb.model_resid.mean():+.3f}  '
      f'market resid {nb.market_resid.mean():+.3f}  raw gap {(nb.our_margin - nb.line_margin).mean():+.3f}')
both = m[m.home_backup & m.away_backup]
print(f'games with backup QB on BOTH teams: {len(both)}')
bk_any = m[m.home_backup | m.away_backup]
print(f'games with >=1 backup team: {len(bk_any)} of {len(m)} ({100*len(bk_any)/len(m):.1f}%)')

# Secondary: ATS on plays involving a backup team, backing vs fading
plays = m[(m.spread_edge.abs() >= 0.5) & (m.home_backup | m.away_backup)].copy()
plays['pick_home'] = plays.spread_edge > 0
plays['home_covers'] = plays.actual_margin > plays.line_margin
plays['push'] = plays.actual_margin == plays.line_margin
plays['win'] = np.where(plays.push, np.nan,
                        np.where(plays.pick_home == plays.home_covers, 1.0, 0.0))
# does the pick back the backup team?
plays['backs_backup'] = np.where(plays.home_backup & ~plays.away_backup, plays.pick_home,
                        np.where(plays.away_backup & ~plays.home_backup, ~plays.pick_home, np.nan))
print(f'\nplays involving a backup team (|edge|>=0.5): {len(plays)}')
for label2, sub in (('backing the backup team', plays[plays.backs_backup == True]),
                    ('fading the backup team', plays[plays.backs_backup == False])):
    w = (sub.win == 1).sum(); l = (sub.win == 0).sum(); p = sub.push.sum()
    pct = 100 * w / (w + l) if (w + l) else float('nan')
    print(f'  {label2}: {int(w)}W-{int(l)}L-{int(p)}P  ({pct:.1f}%)')
allp = plays.dropna(subset=['win'])
print(f'  all backup-involved plays: {int((allp.win==1).sum())}W-{int((allp.win==0).sum())}L '
      f'across {plays.season.nunique()} seasons; per season: '
      f'{plays.groupby("season").size().to_dict()}')

print(f'\nADOPT BAR CHECK (primary): pooled gap {pooled_gap:+.3f} > 1.0? {pooled_gap > 1.0} | '
      f'same-direction seasons {same_dir}/5 >= 3? {same_dir >= 3}')
print(f'VERDICT: {"CLEARS BAR" if (pooled_gap > 1.0 and same_dir >= 3) else "KILL — bar not met"}')
