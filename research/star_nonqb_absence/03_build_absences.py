"""Step 3: build star-absence team-games via set-difference and join to residuals.

METHODOLOGY (revised from pre-reg draft — see deviation note in RESULTS.md):
PFR gamelogs only mark DNP weeks explicitly (partial_table rows) from ~2000
onward; earlier seasons simply omit missed games. The uniform approach:

  missed_weeks(player, season, team) =
      team's regular-season game weeks within the player's tenure
      MINUS weeks the player played for that team

Tenure per (player, season, team):
  - single-team season: weeks [1, season_max_week] (season_max_week from the
    backtest: 17 for 1980-2020 incl. strike years' renumbering, 18 for 2021+).
    Limitation (documented): a star signed mid-season counts pre-signing weeks
    as absences; vanishingly rare for All-Pros, accepted.
  - multi-team season (trade): [first_known_week, last_known_week] for that team.

Streaks: per (player, season, team), walk the team's game weeks in order;
streak = current run of consecutive missed team-games (bye weeks have no rows
and never break a streak).

Inputs:
  star_gameweeks.csv                     (from 02)
  ../new_coach_bias/residuals.csv        (fidelity-verified 2026-10-10)

Outputs:
  absences_teamgame.csv  - one row per (game, shorthanded team): PRIMARY unit
  absences_starlevel.csv - one row per (game, missing star): position splits
  join_audit.txt         - join validation metrics (pre-registered checks)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
GAMEWEEKS = OUT / "star_gameweeks.csv"          # PFR gamelogs (02)
GAMEWEEKS_SNAPS = OUT / "star_gameweeks_snaps.csv"  # nflverse snaps 2013+ (02b)
GAMEWEEKS_WB = OUT / "star_gameweeks_wb.csv"    # wayback 2002-2012 (02c)
RESID = OUT.parent / "new_coach_bias" / "residuals.csv"
TEAMGAME = OUT / "absences_teamgame.csv"
STARLEVEL = OUT / "absences_starlevel.csv"
AUDIT = OUT / "join_audit.txt"


def full_name(abbr: str, season: int) -> str | None:
    a = abbr.strip().upper()
    if a == "BAL":
        return "Baltimore Colts" if season <= 1983 else "Baltimore Ravens" if season >= 1996 else None
    if a in ("IND", "CLT"):
        return "Indianapolis Colts"
    if a == "ARI":
        return "Arizona Cardinals" if season >= 1994 else ("Phoenix Cardinals" if season >= 1988 else "St. Louis Cardinals")
    if a in ("CRD", "PHX"):
        return "St. Louis Cardinals" if season <= 1987 else "Phoenix Cardinals"
    if a == "STL":
        if season <= 1987:
            return "St. Louis Cardinals"
        return "St. Louis Rams" if 1995 <= season <= 2015 else None
    if a in ("LAC", "SD", "SDG"):
        return "San Diego Chargers" if season <= 2016 else "Los Angeles Chargers"
    if a in ("LAR", "RAM", "LA"):
        return "Los Angeles Rams" if season <= 1994 or season >= 2016 else "St. Louis Rams"
    if a in ("LV", "LVR", "OAK", "RAI"):
        if season <= 1981:
            return "Oakland Raiders"
        if season <= 1994:
            return "Los Angeles Raiders"
        if season <= 2019:
            return "Oakland Raiders"
        return "Las Vegas Raiders"
    if a == "HOU":
        # PFR gamelogs use HOU for the Oilers through 1996
        return "Houston Oilers" if season <= 1996 else "Houston Texans"
    if a in ("TEN", "OTI"):
        if season <= 1996:
            return "Houston Oilers"
        if season <= 1998:
            return "Tennessee Oilers"
        return "Tennessee Titans"
    if a == "HTX":
        return "Houston Texans"
    if a in ("WSH", "WAS"):
        if season <= 2019:
            return "Washington Redskins"
        if season <= 2021:
            return "Washington Football Team"
        return "Washington Commanders"
    static = {
        "ATL": "Atlanta Falcons", "BUF": "Buffalo Bills", "CAR": "Carolina Panthers",
        "CHI": "Chicago Bears", "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns",
        "DAL": "Dallas Cowboys", "DEN": "Denver Broncos", "DET": "Detroit Lions",
        "GB": "Green Bay Packers", "GNB": "Green Bay Packers",
        "JAX": "Jacksonville Jaguars", "KC": "Kansas City Chiefs", "KAN": "Kansas City Chiefs",
        "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
        "NE": "New England Patriots", "NWE": "New England Patriots",
        "NO": "New Orleans Saints", "NOR": "New Orleans Saints",
        "NYG": "New York Giants", "NYJ": "New York Jets",
        "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
        "SEA": "Seattle Seahawks", "SF": "San Francisco 49ers", "SFO": "San Francisco 49ers",
        "TB": "Tampa Bay Buccaneers", "TAM": "Tampa Bay Buccaneers",
    }
    return static.get(a)


def main() -> None:
    gw = pd.read_csv(GAMEWEEKS)
    print(f"PFR gameweek rows: {len(gw):,}")
    if GAMEWEEKS_SNAPS.exists():
        sn = pd.read_csv(GAMEWEEKS_SNAPS)
        print(f"snap gameweek rows: {len(sn):,}")
        # snaps cover 2013+; PFR covers earlier. Drop any PFR rows in snap years
        # to avoid double-counting (PFR scrape is incomplete there anyway).
        gw = gw[~gw["game_season"].isin(range(2013, 2025))].copy()
        gw["source"] = "pfr"
        sn["source"] = "snaps"
        gw = pd.concat([gw, sn], ignore_index=True)
    else:
        gw["source"] = "pfr"
    if GAMEWEEKS_WB.exists():
        wb = pd.read_csv(GAMEWEEKS_WB)
        print(f"wayback gameweek rows: {len(wb):,}")
        wb["source"] = "wayback"
        # wayback covers 2002-2012; drop any PFR rows there to avoid doubles
        gw = gw[~gw["game_season"].isin(range(2002, 2013))].copy()
        gw = pd.concat([gw, wb], ignore_index=True)
    print(f"combined gameweek rows: {len(gw):,}")
    gw["team_full"] = gw.apply(lambda r: full_name(str(r["team_abbr"]), int(r["game_season"])), axis=1)
    unmatched = gw[gw["team_full"].isna()]
    print(f"unmatched abbr rows: {len(unmatched)} ({len(unmatched)/max(len(gw),1):.2%})")
    if len(unmatched):
        print(unmatched[["game_season", "team_abbr", "player"]].drop_duplicates().to_string())
    gw = gw[gw["team_full"].notna()].copy()

    # ---- backtest team schedules ----
    res = pd.read_csv(RESID)
    res["week_num"] = pd.to_numeric(res["week"], errors="coerce")
    res = res[res["week_num"].notna()].copy()  # regular season only
    res["week_num"] = res["week_num"].astype(int)
    # team -> sorted game weeks, per season
    home_w = res.groupby(["season", "team_home"])["week_num"].apply(lambda s: sorted(set(s)))
    away_w = res.groupby(["season", "team_away"])["week_num"].apply(lambda s: sorted(set(s)))
    team_weeks: dict[tuple[int, str], list[int]] = {}
    for (season, team), weeks in home_w.items():
        team_weeks.setdefault((int(season), team), set()).update(weeks)
    for (season, team), weeks in away_w.items():
        team_weeks.setdefault((int(season), team), set()).update(weeks)
    team_weeks = {k: sorted(v) for k, v in team_weeks.items()}
    season_max_week = res.groupby("season")["week_num"].max().astype(int).to_dict()

    game_lookup: dict[tuple[int, str, int], pd.Series] = {}
    for r in res.itertuples():
        game_lookup[(int(r.season), r.team_home, int(r.week_num))] = r
        game_lookup[(int(r.season), r.team_away, int(r.week_num))] = r

    # ---- set-difference absences ----
    star_rows: list[dict] = []
    join_miss = 0
    n_tenures = 0
    for (slug, season), grp in gw.groupby(["player_slug", "game_season"]):
        season = int(season)
        teams = sorted(grp["team_full"].unique())
        multi = len(teams) > 1
        for team in teams:
            tgrp = grp[grp["team_full"] == team]
            played = set(tgrp[tgrp["played"] == 1]["week_num"].astype(int))
            known = sorted(set(tgrp["week_num"].astype(int)))
            if multi:
                tenure_lo, tenure_hi = min(known), max(known)
            else:
                tenure_lo, tenure_hi = 1, int(season_max_week.get(season, 18))
            n_tenures += 1
            sched = [w for w in team_weeks.get((season, team), []) if tenure_lo <= w <= tenure_hi]
            if not sched:
                continue
            # streaks: walk team game weeks in order
            streak = 0
            for w in sched:
                if w in played:
                    streak = 0
                else:
                    streak += 1
                    key = (season, team, w)
                    g = game_lookup.get(key)
                    if g is None:
                        join_miss += 1
                        continue
                    side = "home" if g.team_home == team else "away"
                    resid = float(g.actual_margin) - float(g.our_margin)
                    if side == "away":
                        resid = -resid
                    # one representative row per (player, team) for meta
                    meta = tgrp.iloc[0]
                    star_rows.append(
                        {
                            "season": season,
                            "week": w,
                            "team": team,
                            "side": side,
                            "player": meta["player"],
                            "player_slug": slug,
                            "pos": meta["pos"],
                            "pos_group": meta["pos_group"],
                            "streak": streak,
                            "resid": resid,
                            "ats_pick": g.ats_pick,
                            "source": meta["source"],
                        }
                    )
    star = pd.DataFrame(star_rows)
    print(f"tenures: {n_tenures:,}; star-level absence rows: {len(star):,}; "
          f"game-join misses: {join_miss}")

    # ---- method agreement check (PFR seasons >= 2000, where DNP rows are marked) ----
    marked = set(
        gw[(gw["source"] == "pfr") & (gw["played"] == 0) & (gw["game_season"] >= 2000)]
        .apply(lambda r: (int(r["game_season"]), r["team_full"], int(r["week_num"])), axis=1)
    )
    setdiff = set(
        star[(star["source"] == "pfr") & (star["season"] >= 2000)].apply(
            lambda r: (r["season"], r["team"], r["week"]), axis=1)
    )
    if marked:
        agree = len(marked & setdiff) / len(marked)
        print(f"DNP-mark agreement (season>=2000): {len(marked & setdiff)}/{len(marked)} = {agree:.3f}")
    else:
        agree = float("nan")
        print("DNP-mark agreement: no marked rows (unexpected)")

    # ---- team-game level (PRIMARY unit) ----
    res_gid = {}
    for r in res.itertuples():
        gid = f"{int(r.season)}_{int(r.week_num)}_{r.team_home}_vs_{r.team_away}"
        res_gid[(int(r.season), r.team_home, int(r.week_num))] = gid
        res_gid[(int(r.season), r.team_away, int(r.week_num))] = gid
    star["gid"] = star.apply(lambda r: res_gid.get((r["season"], r["team"], r["week"])), axis=1)
    teams_per_game = star.groupby("gid")["team"].nunique()
    both = set(teams_per_game[teams_per_game > 1].index)
    print(f"games with both teams shorthanded: {len(both)} (excluded from primary)")
    prim_star = star[~star["gid"].isin(both)].copy()
    tg = prim_star.groupby(["season", "week", "team", "gid"], as_index=False).agg(
        n_stars_out=("player", "nunique"),
        min_streak=("streak", "min"),
        resid=("resid", "first"),
        pos_groups=("pos_group", lambda s: "|".join(sorted(set(s)))),
        players=("player", lambda s: "|".join(sorted(set(s)))),
    )
    tg["early"] = (tg["min_streak"] <= 4).astype(int)

    tg.to_csv(TEAMGAME, index=False)
    star.to_csv(STARLEVEL, index=False)

    audit = [
        f"gameweek rows scraped: {len(gw)}",
        f"unmatched abbr rows: {len(unmatched)}",
        f"tenures processed: {n_tenures}",
        f"star-level absence rows: {len(star)}",
        f"game-join misses: {join_miss}",
        f"DNP-mark agreement (season>=2000): {agree:.3f}" if marked else "DNP-mark agreement: n/a",
        f"both-teams-shorthanded games (excluded from primary): {len(both)}",
        f"PRIMARY team-game observations: {len(tg)}",
        f"star-seasons with >=1 absence: {star[['player_slug','season']].drop_duplicates().shape[0]}",
    ]
    AUDIT.write_text("\n".join(audit) + "\n")
    print("\n".join(audit))
    print(f"wrote {TEAMGAME}, {STARLEVEL}, {AUDIT}")


if __name__ == "__main__":
    main()
