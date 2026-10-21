"""NHL v1 model: xG ratings -> expected goals -> win/totals probabilities.

Frozen spec (scope doc, 2026-10-20 — do not tune against validation):
- Ratings from MoneyPuck expected goals (xGF/xGA per game, all situations):
  recency-weighted trailing window, exponential decay, 20-game half-life;
  single-step opponent adjustment (same discipline as the football models);
  prior-season ratings carried over at 0.5 and blended in over the first
  ~10 effective games of a season.
- Expected goals (lambda) are additive in xG space, anchored on the
  league's actual goals/game, plus a home-ice constant fitted on the
  discovery seasons only.
- Win probability from a Poisson goal matrix; games level after
  regulation resolve via OT (winner weighted by lambda share; OT
  decides 66% of tied games, measured on the discovery seasons from
  MoneyPuck ice time) and shootout (50/50).
- Rest term (v1.1, adopted 2026-10-20 per the pre-registered add-on
  test in research/nhl_rest/): expected goals shift by REST_BETA per
  rest-day of differential between the teams.
"""
import numpy as np
import pandas as pd

HALF_LIFE = 20.0                      # games
DECAY = 0.5 ** (1.0 / HALF_LIFE)
CARRYOVER = 0.5                       # prior-season rating retention
PRIOR_BLEND_GAMES = 10.0              # effective games to full weight
OT_DECISIVE = 0.66                    # share of tied games decided in OT
                                      # (measured on discovery seasons
                                      # 2019-2022 from MoneyPuck ice time:
                                      # games past regulation ending
                                      # before the 3900s shootout mark)
MAX_GOALS = 12                        # Poisson truncation
REST_BETA = 0.05                      # goals per rest-day of differential
                                      # (rest term adopted 2026-10-20 per
                                      # the pre-registered test in
                                      # research/nhl_rest/RESULTS.md:
                                      # validation Brier 0.2394 vs v1
                                      # 0.2401, bootstrap CI excludes 0)


def ratings_snapshot(history: pd.DataFrame, prior: dict) -> dict | None:
    """Opponent-adjusted xG ratings from games strictly before 'now'.

    history: team-game rows (team, opp, xgf, xga, gf). prior maps team ->
    (off_raw, def_raw) from last season's end, already carryover-scaled
    deviations applied by the caller. Returns dict with lg_goals (actual
    league goals/team-game), lg_x (league xG/team-game), off/def adjusted
    ratings per team (deviations from league xG), or None if too thin.
    """
    if history.empty:
        return None
    raw_off, raw_def, opps, opp_w = {}, {}, {}, {}
    for team, g in history.groupby("team"):
        g = g.iloc[::-1]                     # most recent first
        n = len(g)
        w = DECAY ** np.arange(n)
        raw_off[team] = float(np.average(g["xgf"], weights=w))
        raw_def[team] = float(np.average(g["xga"], weights=w))
        opps[team] = list(g["opp"])
        opp_w[team] = list(w)
        n_eff = w.sum() ** 2 / (w ** 2).sum()
        if n_eff < PRIOR_BLEND_GAMES and team in prior:
            b = n_eff / PRIOR_BLEND_GAMES
            raw_off[team] = b * raw_off[team] + (1 - b) * prior[team][0]
            raw_def[team] = b * raw_def[team] + (1 - b) * prior[team][1]
    if len(raw_off) < 8:
        return None
    lg_x = float(np.mean(list(raw_off.values())))
    lg_goals = float(history["gf"].mean())
    off, deff = {}, {}
    for t in raw_off:
        pw_d = [(raw_def[o] - lg_x, wt) for o, wt in zip(opps[t], opp_w[t])
                if o in raw_def]
        pw_o = [(raw_off[o] - lg_x, wt) for o, wt in zip(opps[t], opp_w[t])
                if o in raw_off]
        adj_d = (sum(v * wt for v, wt in pw_d) / sum(wt for _, wt in pw_d)
                 if pw_d else 0.0)
        adj_o = (sum(v * wt for v, wt in pw_o) / sum(wt for _, wt in pw_o)
                 if pw_o else 0.0)
        off[t] = (raw_off[t] - lg_x) - adj_d
        deff[t] = (raw_def[t] - lg_x) - adj_o
    return {"off": off, "def": deff, "raw_off": raw_off, "raw_def": raw_def,
            "lg_x": lg_x, "lg_goals": lg_goals}


def expected_goals(snap: dict, home: str, away: str, home_ice: float,
                   rest_d: int = 0):
    """(lambda_home, lambda_away) or None if a team is unrated.

    rest_d is the rest differential (home rest days - away rest days,
    capped to [-3, +3]; see rest_days_map). The rest term shifts
    lam_h by +REST_BETA * rest_d and lam_a by -REST_BETA * rest_d
    after the usual [0.5, 6.5] clip, with a 0.5 floor after the
    adjustment — exactly the term frozen in
    research/nhl_rest/PREREGISTRATION.md. rest_d=0 reproduces v1.
    """
    if home not in snap["off"] or away not in snap["off"]:
        return None
    base = snap["lg_goals"]
    lam_h = base + snap["off"][home] + snap["def"][away] + home_ice
    lam_a = base + snap["off"][away] + snap["def"][home]
    lam_h = float(np.clip(lam_h, 0.5, 6.5))
    lam_a = float(np.clip(lam_a, 0.5, 6.5))
    if rest_d:
        lam_h = max(lam_h + REST_BETA * rest_d, 0.5)
        lam_a = max(lam_a - REST_BETA * rest_d, 0.5)
    return lam_h, lam_a


def rest_days_map(tg: pd.DataFrame) -> dict:
    """game_id -> capped rest differential d in [-3, +3] (home - away).

    rest_days(team) = calendar days since that team's previous
    regular-season game within the same season; a team's first game
    of a season counts as 3. Derived from each team's previous game
    date only, so it is walk-forward safe (no future information).
    tg is the team-games table built by data_prep.py (regular
    season only, one row per team-game).
    """
    t = tg[["game_id", "team", "season", "date", "home"]].copy()
    t = t.sort_values(["team", "season", "date"])
    prev = t.groupby(["team", "season"])["date"].shift(1)
    t["rest"] = (t["date"] - prev).dt.days.fillna(3).astype(int)
    home = t[t["home"] == 1].set_index("game_id")["rest"]
    away = t[t["home"] == 0].set_index("game_id")["rest"]
    d = (home - away).dropna().clip(-3, 3)
    return {int(gid): int(v) for gid, v in d.items()}


def _pois(k: int, lam: float) -> float:
    from scipy.stats import poisson
    return float(poisson.pmf(k, lam))


def win_prob(lam_h: float, lam_a: float) -> float:
    """P(home wins the game), including OT/shootout resolution."""
    ph = np.array([_pois(i, lam_h) for i in range(MAX_GOALS + 1)])
    pa = np.array([_pois(j, lam_a) for j in range(MAX_GOALS + 1)])
    m = np.outer(ph, pa)
    m /= m.sum()
    p_reg_home = float(np.tril(m, -1).sum())       # home goals > away goals
    p_tie = float(np.trace(m))
    share = lam_h / (lam_h + lam_a)
    p_home_ot = OT_DECISIVE * share + (1 - OT_DECISIVE) * 0.5
    return p_reg_home + p_tie * p_home_ot


def total_probs(lam_h: float, lam_a: float) -> dict[int, float]:
    """P(total goals = k) for k up to 2*MAX_GOALS, from the same matrix."""
    ph = np.array([_pois(i, lam_h) for i in range(MAX_GOALS + 1)])
    pa = np.array([_pois(j, lam_a) for j in range(MAX_GOALS + 1)])
    m = np.outer(ph, pa)
    m /= m.sum()
    out: dict[int, float] = {}
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            out[i + j] = out.get(i + j, 0.0) + float(m[i, j])
    return out
