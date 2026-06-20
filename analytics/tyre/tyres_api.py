"""
API entry point for tyre degradation analysis.
Reuses the filtering and dataframe logic from tyre_degradation.py,
emits a single JSON object to stdout.

Usage:
    python analytics/tyre/tyres_api.py [--driver VER] [--year 2024] [--gp Monaco]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fastf1
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"


def td_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return round(float(td.total_seconds()), 3)


def filter_laps(laps: pd.DataFrame) -> pd.DataFrame:
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()
    pit_cols = [c for c in ["PitInTime", "PitOutTime"] if c in laps.columns]
    if pit_cols:
        mask = False
        for c in pit_cols:
            mask = mask | laps[c].notna()
        laps = laps.loc[~mask]
    if "TrackStatus" in laps.columns:
        laps = laps.loc[~laps["TrackStatus"].astype(str).str.contains(r"4|6", regex=True)]
    return laps


def run(year: int, gp: str, driver: str, session_type: str = "R") -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    raw = session.laps.pick_drivers([driver])
    clean = filter_laps(raw)

    df = pd.DataFrame({
        "lapNumber":     clean["LapNumber"].astype(int),
        "lapTimeS":      clean["LapTime"].map(td_to_seconds),
        "compound":      clean.get("Compound", pd.Series([None] * len(clean))),
        "tyreLife":      clean.get("TyreLife",  pd.Series([None] * len(clean))),
        "stint":         clean.get("Stint",     pd.Series([None] * len(clean))),
    }).dropna(subset=["lapTimeS"]).reset_index(drop=True)

    laps_list = df.where(pd.notnull(df), None).to_dict(orient="records")

    # Stint summary
    stint_summary = []
    if "stint" in df.columns and df["stint"].notna().any():
        for (stint, compound), grp in df.dropna(subset=["stint"]).groupby(["stint", "compound"], dropna=False):
            times = grp["lapTimeS"].dropna()
            if times.empty:
                continue
            stint_summary.append({
                "stint":        int(stint),
                "compound":     str(compound) if compound else None,
                "laps":         int(len(grp)),
                "avgPaceS":     round(float(times.mean()), 3),
                "fastestLapS":  round(float(times.min()), 3),
                "stdDevS":      round(float(times.std()), 3) if len(times) > 1 else 0.0,
            })

    # Compound summary
    compound_summary = []
    for compound, grp in df.dropna(subset=["compound"]).groupby("compound"):
        times = grp["lapTimeS"].dropna()
        compound_summary.append({
            "compound":    str(compound),
            "laps":        int(len(grp)),
            "avgPaceS":    round(float(times.mean()), 3),
            "fastestLapS": round(float(times.min()), 3),
            "stdDevS":     round(float(times.std()), 3) if len(times) > 1 else 0.0,
        })

    fastest_row = df.loc[df["lapTimeS"].idxmin()] if not df.empty else None
    most_used = df["compound"].value_counts(dropna=True)

    return {
        "session":       {"year": year, "grandPrix": gp, "type": session_type},
        "driver":        driver,
        "totalLaps":     int(len(df)),
        "fastestLap":    {
            "lapNumber": int(fastest_row["lapNumber"]) if fastest_row is not None else None,
            "lapTimeS":  round(float(fastest_row["lapTimeS"]), 3) if fastest_row is not None else None,
            "compound":  str(fastest_row["compound"]) if fastest_row is not None else None,
        },
        "mostUsedCompound": str(most_used.index[0]) if not most_used.empty else None,
        "stintSummary":     stint_summary,
        "compoundSummary":  compound_summary,
        "laps":             laps_list,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", type=str, default="VER")
    parser.add_argument("--year",   type=int, default=2024)
    parser.add_argument("--gp",     type=str, default="Monaco")
    parser.add_argument("--session", type=str, default="R")
    args = parser.parse_args()

    result = run(args.year, args.gp, args.driver, args.session)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
