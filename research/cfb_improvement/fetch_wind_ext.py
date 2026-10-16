"""Extend ERA5 hourly wind coverage to 2014-2025 for H-T2 (CFB wind study).

Same method as cfb/fetch_cfb_wind.py (Open-Meteo archive, wind_speed_10m,
mph, UTC) but the full backtest window. One call per outdoor school;
per-school parquet parts are checkpointed under parts/ so a failure can
resume. Output: wind_2014_2025.parquet in this directory (research-local;
the repo's data/cfb/cfb_stadium_wind.parquet is untouched).
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STADIUMS = json.loads((REPO / "cfb" / "cfb_stadiums.json").read_text())
PARTS = HERE / "parts"
PARTS.mkdir(exist_ok=True)


def fetch_stadium(school, lat, lon):
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}"
           "&start_date=2014-01-01&end_date=2025-12-31"
           "&hourly=wind_speed_10m&wind_speed_unit=mph&timezone=UTC")
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=180) as r:
                d = json.load(r)
            times = pd.to_datetime(d["hourly"]["time"], utc=True)
            winds = d["hourly"]["wind_speed_10m"]
            return pd.DataFrame({"school": school, "time": times,
                                 "wind_mph": winds})
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{school}: {last}")


def main():
    schools = [(s, v) for s, v in STADIUMS.items() if not v["dome"]]
    print(f"{len(schools)} outdoor schools", flush=True)
    failed = []
    for i, (school, s) in enumerate(schools):
        part = PARTS / f"{school.replace('/', '_')}.parquet"
        if part.exists():
            continue
        try:
            df = fetch_stadium(school, s["lat"], s["lon"])
            df.to_parquet(part, index=False)
        except Exception as e:  # noqa: BLE001
            failed.append(school)
            print(f"  FAILED {school}: {e}", flush=True)
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(schools)}", flush=True)
        time.sleep(0.15)
    frames = [pd.read_parquet(p) for p in sorted(PARTS.glob("*.parquet"))]
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(HERE / "wind_2014_2025.parquet", index=False)
    print(f"{len(out):,} hourly rows, {out['school'].nunique()} schools "
          f"-> wind_2014_2025.parquet")
    if failed:
        print("FAILED SCHOOLS:", failed)
        sys.exit(1)


if __name__ == "__main__":
    main()
