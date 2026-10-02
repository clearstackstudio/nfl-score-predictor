"""Unit tests for pick display labels. Run: python3 test_picks.py

These pin down the labeling rules with hand-computed cases so a
team/number mixup (e.g. showing "NE -6.5" when the line is Bills -6.5
and the pick is New England) fails here instead of on the website.
"""
from weekly_picks import (
    BOOK_PARLAY_PAYS,
    TOTAL_CIRCUIT,
    build_parlay,
    fair_american,
    pick_spread_label,
    pick_total_label,
    validate_picks,
)
from weather import indoor_total_adjustment, wind_total_adjustment
from epa_ratings import adjusted_ratings

passed = failed = 0

def check(name, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")

# --- spread labels: picked team's perspective, home-margin convention ---
# The original bug: line Bills -6.5 (home_margin +6.5), pick NE (away) showed "NE -6.5".
check("underdog away pick", pick_spread_label("away", 6.5, "BUF", "NE"), "NE +6.5")
check("favorite home pick", pick_spread_label("home", 6.5, "BUF", "NE"), "BUF -6.5")
# Away favored: line PIT -3.5 at Cleveland => home_margin -3.5.
check("underdog home pick", pick_spread_label("home", -3.5, "CLE", "PIT"), "CLE +3.5")
check("favorite away pick", pick_spread_label("away", -3.5, "CLE", "PIT"), "PIT -3.5")
check("pick'em", pick_spread_label("home", 0.0, "KC", "LV"), "Pick'em")
check("no pick -> no label", pick_spread_label(None, 6.5, "BUF", "NE"), None)
check("half point", pick_spread_label("away", 10.5, "MIN", "MIA"), "MIA +10.5")

# --- total labels ---
check("over", pick_total_label("over", 48.5), "Over 48.5")
check("under", pick_total_label("under", 38.0), "Under 38")
check("no total pick", pick_total_label(None, 48.5), None)

# --- fair odds ---
check("fair 68.7%", fair_american(0.687), "-219")
check("fair 25%", fair_american(0.25), "+300")
check("fair 50%", fair_american(0.5), "+100")

# --- end-to-end validation on synthetic weeks ---
def mk(away, home, line_spread, line_total, our_spread, our_total):
    se = round(our_spread - line_spread, 1)
    te = round(our_total - line_total, 1)
    ps = ("home" if se > 0 else "away") if abs(se) >= 0.5 else None
    pt = ("over" if te > 0 else "under") if abs(te) >= 1.0 else None
    return {
        "away_abbr": away, "home_abbr": home,
        "line_spread": line_spread, "line_total": line_total,
        "spread_edge": se, "total_edge": te,
        "pick_spread": ps, "pick_total": pt,
        "pick_spread_label": pick_spread_label(ps, line_spread, home, away),
        "pick_total_label": pick_total_label(pt, line_total),
        "spread_labels": {
            "home": pick_spread_label("home", line_spread, home, away),
            "away": pick_spread_label("away", line_spread, home, away),
        },
        "cover_prob": 0.65 if ps else None, "ou_prob": 0.7 if pt else None,
    }

week = [
    mk("NE", "BUF", 6.5, 48.5, 1.2, 54.7),    # NE +6.5, Over 48.5
    mk("PIT", "CLE", -2.5, 38.5, -2.4, 27.4),  # no spread play, Under 38.5
    mk("NYJ", "CHI", 3.5, 43.5, 20.9, 53.0),   # CHI -3.5, Over 43.5
]
parlay = build_parlay(week)
try:
    validate_picks(week, parlay)
    passed += 1
except AssertionError as e:
    failed += 1
    print(f"FAIL validate good week: {e}")

# Label must name the picked team: corrupt one and confirm validation catches it.
bad = [dict(p) for p in week]
bad[0]["pick_spread_label"] = "BUF -6.5"  # the original bug, recreated
try:
    validate_picks(bad, build_parlay(bad))
    failed += 1
    print("FAIL validator did not catch wrong-team label")
except AssertionError:
    passed += 1

# Wrong side for the edge direction must also fail.
bad2 = [dict(p) for p in week]
bad2[0]["pick_spread"] = "home"
try:
    validate_picks(bad2, build_parlay(bad2))
    failed += 1
    print("FAIL validator did not catch wrong-side pick")
except AssertionError:
    passed += 1

# --- circuit breaker: extreme total disagreement -> skipped with a note ---
cb = mk("KC", "LV", -3.0, 45.0, -3.0, 45.0 + TOTAL_CIRCUIT + 1.5)
cb["pick_total"] = None
cb["pick_total_note"] = "No play — our number is too far from the market to trust."
cb["pick_total_label"] = None
cb["ou_prob"] = None
try:
    validate_picks([cb], build_parlay([cb]))
    passed += 1
except AssertionError as e:
    failed += 1
    print(f"FAIL validator rejected circuit-breaker skip: {e}")

# Same extreme edge but no note -> must fail (a missing pick needs a reason).
cb2 = dict(cb)
cb2["pick_total_note"] = None
try:
    validate_picks([cb2], build_parlay([cb2]))
    failed += 1
    print("FAIL validator allowed missing total pick without note")
except AssertionError:
    passed += 1

# --- recency weighting: same games, different order -> different rating ---
import pandas as pd

def rating_frame(aaa_off):
    rows = []
    gid = 0
    for i, epa in enumerate(aaa_off):
        gid += 1
        rows.append({"season": 2026, "week": i + 1, "game_id": gid, "team": "AAA",
                     "off_epa_play": epa, "def_epa_play": 0.0, "off_plays": 60 + i,
                     "opp": "BBB"})
        rows.append({"season": 2026, "week": i + 1, "game_id": gid, "team": "BBB",
                     "off_epa_play": 0.0, "def_epa_play": 0.0, "off_plays": 63,
                     "opp": "AAA"})
    return pd.DataFrame(rows)

off_up, _, pace_up = adjusted_ratings(rating_frame([-0.2, -0.2, -0.2, 0.4]), 8, 2026, {})
off_down, _, pace_down = adjusted_ratings(rating_frame([0.4, -0.2, -0.2, -0.2]), 8, 2026, {})
# Identical game sets, only order differs: flat means would rate them equal.
check("recency favors the hot finish", off_up["AAA"] > off_down["AAA"], True)

# Pace is recency-weighted: plays rise 60->63, so the weighted pace must sit
# above the flat mean (61.5) and below the most recent game (63).
check("pace recency-weighted", 61.5 < pace_up["AAA"] < 63.0, True)
check("pace BBB flat", abs(pace_up["BBB"] - 63.0) < 1e-9, True)

# --- QB adjustments ---
from epa_ratings import qb_adjustments

def qb_frames():
    tg_rows, qb_rows = [], []
    gid = 0
    for wk in (1, 2):
        gid += 1
        for team, opp in (("AAA", "BBB"), ("BBB", "AAA")):
            tg_rows.append({"season": 2026, "week": wk, "game_id": gid,
                            "team": team, "off_epa_play": 0.0,
                            "def_epa_play": 0.0, "off_plays": 60, "opp": opp})
        # QB1 throws all of AAA's passes, badly; QB2 stars elsewhere
        for _ in range(30):
            qb_rows.append({"game_id": gid, "week": wk, "season": 2026,
                            "posteam": "AAA", "passer_id": "QB1", "epa": -0.2})
            qb_rows.append({"game_id": gid, "week": wk, "season": 2026,
                            "posteam": "BBB", "passer_id": "QB2", "epa": 0.2})
    return pd.DataFrame(tg_rows), pd.DataFrame(qb_rows)

_tg, _qp = qb_frames()
# Backup QB2 (great) replaces QB1 (bad) for AAA -> positive bump.
adj = qb_adjustments(_qp, _tg, len(_tg), 2026, [("BBB", "AAA", "QB2", "QB2")])
check("qb change bumps offense", adj["AAA"] > 0.01, True)
check("qb unchanged team ~0", abs(adj["BBB"]) < 1e-9, True)
# Same starter as the window -> exactly 0.
adj2 = qb_adjustments(_qp, _tg, len(_tg), 2026, [("BBB", "AAA", "QB2", "QB1")])
check("qb same starter -> 0", adj2["AAA"] == 0.0, True)
# Unknown starter -> 0.
adj3 = qb_adjustments(_qp, _tg, len(_tg), 2026, [("BBB", "AAA", None, "QB2")])
check("qb unknown home -> 0", adj3["BBB"] == 0.0, True)

# --- wind adjustment: hinge at 10 mph, -1 pt/mph, cap -8, outdoor only ---
check("wind calm -> 0", wind_total_adjustment(5.0, "BUF"), 0.0)
check("wind 10 -> 0", wind_total_adjustment(10.0, "BUF"), 0.0)
check("wind 13 -> -3", wind_total_adjustment(13.0, "BUF"), -3.0)
check("wind 18 -> -8 cap", wind_total_adjustment(18.0, "BUF"), -8.0)
check("wind 25 -> -8 cap", wind_total_adjustment(25.0, "BUF"), -8.0)
check("wind dome -> 0", wind_total_adjustment(25.0, "DET"), 0.0)
check("wind retractable -> 0", wind_total_adjustment(25.0, "DAL"), 0.0)
check("wind unknown -> 0", wind_total_adjustment(None, "BUF"), 0.0)

# --- indoor adjustment: +3.0 for dome/retractable, 0 for outdoor/unknown ---
check("indoor dome -> +3", indoor_total_adjustment("DET"), 3.0)
check("indoor retractable -> +3", indoor_total_adjustment("DAL"), 3.0)
check("indoor outdoor -> 0", indoor_total_adjustment("BUF"), 0.0)
check("indoor unknown -> 0", indoor_total_adjustment("XXX"), 0.0)

print(f"{passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
