"""Download FBS team logos from CFBD /teams into site/public/logos/cfb/.

Slug function must stay identical to the one in
site/app/lib/cfb-team-logo.tsx: lowercase, strip non-alphanumeric.
Run: .venv-cfb/bin/python cfb/fetch_cfb_logos.py
"""
from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "site" / "public" / "logos" / "cfb"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from fetch_cfb import get_client
    import cfbd
    from cfbd.api import teams_api

    OUT.mkdir(parents=True, exist_ok=True)
    client = get_client()
    teams = teams_api.TeamsApi(client).get_fbs_teams(year=2026)
    print(f"{len(teams)} FBS teams")

    seen: dict[str, str] = {}
    ok = fail = skipped = 0
    for t in teams:
        d = t.to_dict()
        school = d.get("school") or ""
        s = slug(school)
        if not s:
            print(f"  SKIP (empty slug): {school!r}")
            skipped += 1
            continue
        if s in seen:
            print(f"  COLLISION: {school!r} -> {s} (already {seen[s]!r})")
            fail += 1
            continue
        seen[s] = school
        dest = OUT / f"{s}.png"
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        logos = d.get("logos") or []
        # Prefer the 256px light logo (index 2 in CFBD's list).
        url = next((u for u in logos if "/256/" in u and "dark" not in u),
                   logos[0] if logos else None)
        if not url:
            print(f"  NO LOGO URL: {school}")
            fail += 1
            continue
        try:
            # curl handles the CDN's connection resets far better than
            # urllib here; retry through them with backoff.
            import subprocess
            import time
            r = subprocess.run(
                ["curl", "-sS", "--retry", "5", "--retry-all-errors",
                 "--retry-delay", "2", "--max-time", "60",
                 "-A", "honest-line/1.0", "-o", str(dest), url],
                capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip()[-200:])
            if dest.stat().st_size < 500:
                dest.unlink(missing_ok=True)
                raise ValueError(f"suspiciously small ({dest.stat().st_size} bytes)")
            ok += 1
            time.sleep(0.4)
        except Exception as e:
            print(f"  FAIL {school}: {e}")
            fail += 1
    print(f"downloaded={ok} already_had={skipped} failed={fail}")


if __name__ == "__main__":
    main()
