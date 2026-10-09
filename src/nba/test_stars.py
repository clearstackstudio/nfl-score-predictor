"""Unit tests for the NBA star-out adjustment. Run: python3 test_stars.py

Pins down the fitted 1.5-pt constant, the loader's warn-and-skip behavior,
and the exact wiring order used in daily_picks.py (rest, then stars).
"""
import datetime
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stars import (STAR_OUT_PTS, apply_star_adjustment, is_star,
                   load_stars_out)

passed = failed = 0


def check(name, got, want):
    global passed, failed
    if got == want:
        passed += 1
    else:
        failed += 1
        print(f"FAIL {name}: got {got!r}, want {want!r}")


# --- fitted constant ---
check("constant is 1.5", STAR_OUT_PTS, 1.5)

# --- apply_star_adjustment: home-margin convention ---
check("home star out", apply_star_adjustment(5.0, 1, 0), 3.5)
check("away star out", apply_star_adjustment(5.0, 0, 1), 6.5)
check("two home stars", apply_star_adjustment(5.0, 2, 0), 2.0)
check("one each cancels", apply_star_adjustment(5.0, 1, 1), 5.0)
check("none out unchanged", apply_star_adjustment(-3.25, 0, 0), -3.25)
check("custom pts", apply_star_adjustment(0.0, 1, 0, pts_per_star=2.0), -2.0)

# --- is_star: ex-ante 2026 All-Star selections ---
check("lebron is a star", is_star("LeBron James"), True)
check("jokic diacritic-tolerant", is_star("Nikola Jokic"), True)
check("sengun diacritic form", is_star("Alperen Şengün"), True)
check("curry selected-not-played counts", is_star("Stephen Curry"), True)
check("leonard commissioners pick counts", is_star("Kawhi Leonard"), True)
check("ingram replacement counts", is_star("Brandon Ingram"), True)
check("role player not a star", is_star("Dorian Finney-Smith"), False)
check("empty string not a star", is_star(""), False)


def write_tmp(doc):
    p = Path(tempfile.mkdtemp()) / "star_out.json"
    p.write_text(json.dumps(doc))
    return p


D = datetime.date(2026, 10, 21)

# --- loader: happy path ---
p = write_tmp({"season": 2027, "date": "2026-10-21",
               "stars_out": {"Los Angeles Lakers": ["LeBron James"],
                             "Boston Celtics": ["Jayson Tatum"]}})
got = load_stars_out(2027, D, p)
check("valid team+star kept",
      got, {"Los Angeles Lakers": ["LeBron James"]})

# --- loader: team variants normalize, unknown teams warn-and-skip ---
p = write_tmp({"season": 2027, "date": "2026-10-21",
               "stars_out": {"LA Clippers": ["Kawhi Leonard"],
                             "Springfield Atoms": ["LeBron James"]}})
got = load_stars_out(2027, D, p)
check("team variant normalized, unknown team skipped",
      got, {"Los Angeles Clippers": ["Kawhi Leonard"]})

# --- loader: stale / missing / malformed ---
p = write_tmp({"season": 2027, "date": "2026-10-20", "stars_out":
               {"Los Angeles Lakers": ["LeBron James"]}})
check("stale date ignored", load_stars_out(2027, D, p), {})
p = write_tmp({"season": 2026, "date": "2026-10-21", "stars_out":
               {"Los Angeles Lakers": ["LeBron James"]}})
check("stale season ignored", load_stars_out(2027, D, p), {})
check("missing file -> {}",
      load_stars_out(2027, D, Path(tempfile.mkdtemp()) / "nope.json"), {})
p = write_tmp({"season": 2027, "date": "2026-10-21", "stars_out": {}})
check("empty stars_out -> {}", load_stars_out(2027, D, p), {})
bad = Path(tempfile.mkdtemp()) / "bad.json"
bad.write_text("{not json")
check("malformed json -> {}", load_stars_out(2027, D, bad), {})

# --- loader: multiple stars, suffix tolerance ---
p = write_tmp({"season": 2027, "date": "2026-10-21",
               "stars_out": {"Dallas Mavericks": ["Luka Doncic", "Kyrie Irving"]}})
got = load_stars_out(2027, D, p)
check("two out incl. non-star filtered",
      got, {"Dallas Mavericks": ["Luka Doncic"]})

# --- integration: exact wiring order from daily_picks.py (rest, then stars)
# on synthetic values: rest-adjusted margin 4.0, home star out -> 2.5
from features import apply_rest_adjustment
m = apply_rest_adjustment(3.0, 2, 0)          # +0.58*2 = 4.16
m = apply_star_adjustment(m, 1, 0)            # -1.5
check("rest-then-star wiring", round(m, 2), 2.66)

print(f"{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
