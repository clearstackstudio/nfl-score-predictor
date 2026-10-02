"""Fetch historical hourly wind for all FBS stadiums (2022-2024).

One Open-Meteo archive call per stadium; output cached to
data/cfb/cfb_stadium_wind.parquet for the calibration analysis.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
STADIUMS = json.loads((REPO / "cfb" / "cfb_stadiums.json").read_text())


def fetch_stadium(school, lat, lon):
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}"
           "&start_date=2022-01-01&end_date=2024-12-31"
           "&hourly=wind_speed_10m&wind_speed_unit=mph&timezone=UTC")
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)
    times = pd.to_datetime(d["hourly"]["time"], utc=True)
    winds = d["hourly"]["wind_speed_10m"]
    return pd.DataFrame({"school": school, "time": times, "wind_mph": winds})


def main():
    out_path = REPO / "data" / "cfb" / "cfb_stadium_wind.parquet"
    if out_path.exists():
        print("cache exists, skipping")
        return
    frames = []
    for i, (school, s) in enumerate(STADIUMS.items()):
        if s["dome"]:
            continue
        try:
            frames.append(fetch_stadium(school, s["lat"], s["lon"]))
        except Exception as e:
            print(f"  {school}: {e}")
        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(STADIUMS)}")
        time.sleep(0.1)
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(out_path)
    print(f"{len(df):,} hourly rows -> {out_path}")


if __name__ == "__main__":
    main()
