"""Unit tests for pick display labels. Run: python3 test_picks.py

These pin down the labeling rules with hand-computed cases so a
team/number mixup (e.g. showing "NE -6.5" when the line is Bills -6.5
and the pick is New England) fails here instead of on the website.
"""
from weekly_picks import (
    BOOK_PARLAY_PAYS,
    build_parlay,
    fair_american,
    pick_spread_label,
    pick_total_label,
    validate_picks,
)

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

print(f"{passed} passed, {failed} failed")
raise SystemExit(1 if failed else 0)
