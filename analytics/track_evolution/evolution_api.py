"""
API entry point for track evolution analysis.
Combines track_evolution.py and weather_analysis.py logic,
emits a single JSON object to stdout.

Usage:
    python analytics/track_evolution/evolution_api.py [--year 2024] [--gp Monaco]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fastf1
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"


def _clean(value):
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def td_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return float(td.total_seconds())


def build_laps_df(session) -> pd.DataFrame:
    laps = session.laps
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()
    time_col = "LapStartTime" if "LapStartTime" in laps.columns else "Time"
    df = pd.DataFrame({
        "driver":         laps["Driver"],
        "lapTimeS":       laps["LapTime"].map(td_to_seconds),
        "sessionTimeS":   laps[time_col].map(td_to_seconds),
    }).dropna().reset_index(drop=True)
    return df


def build_weather_df(session) -> pd.DataFrame:
    w = session.weather_data.copy()
    if "Time" not in w.columns:
        return pd.DataFrame()
    w["sessionTimeS"] = w["Time"].map(td_to_seconds)
    for col in ["AirTemp", "TrackTemp", "Humidity", "WindSpeed", "Rainfall"]:
        if col not in w.columns:
            w[col] = np.nan
    return w[["sessionTimeS", "AirTemp", "TrackTemp", "Humidity", "WindSpeed", "Rainfall"]].dropna(subset=["sessionTimeS"])


def compute_improvement(df: pd.DataFrame) -> float | None:
    df_s = df.sort_values("sessionTimeS").reset_index(drop=True)
    n = len(df_s)
    if n < 8:
        return None
    q = max(int(n * 0.25), 1)
    return round(float(df_s.head(q)["lapTimeS"].mean() - df_s.tail(q)["lapTimeS"].mean()), 3)


def estimate_best_grip_window(df: pd.DataFrame, bins: int = 8) -> dict | None:
    valid = df[["TrackTemp", "lapTimeS"]].dropna()
    if len(valid) < 20:
        return None
    temps = valid["TrackTemp"].to_numpy(dtype=float)
    edges = np.linspace(float(np.nanmin(temps)), float(np.nanmax(temps)), bins + 1)
    valid = valid.copy()
    valid["bin"] = pd.cut(valid["TrackTemp"], bins=edges, include_lowest=True)
    medians = valid.groupby("bin", observed=True)["lapTimeS"].median().dropna()
    if medians.empty:
        return None
    best = medians.idxmin()
    return {"trackTempLow": round(float(best.left), 1), "trackTempHigh": round(float(best.right), 1),
            "medianLapTimeS": round(float(medians[best]), 3)}


def run(year: int, gp: str, session_type: str = "Q") -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, messages=False)

    laps_df = build_laps_df(session)
    weather_df = build_weather_df(session)

    # Fastest lap
    fastest_idx = laps_df["lapTimeS"].idxmin()
    fastest = laps_df.loc[fastest_idx]

    avg_improvement = compute_improvement(laps_df)

    # Lap evolution sample: bucket into 30 time bins, take median lap time per bin
    evolution = []
    if not laps_df.empty:
        laps_df["timeBin"] = pd.cut(laps_df["sessionTimeS"], bins=30)
        for interval, grp in laps_df.groupby("timeBin", observed=True):
            times = grp["lapTimeS"].dropna()
            if times.empty:
                continue
            evolution.append({
                "sessionTimeMin": round(float(interval.mid) / 60, 2),
                "medianLapTimeS": round(float(times.median()), 3),
                "fastestLapTimeS": round(float(times.min()), 3),
                "lapCount": int(len(times)),
            })

    # Weather summary
    weather_summary = {}
    weather_samples = []
    if not weather_df.empty:
        weather_summary = {
            "airTempMin":    round(float(weather_df["AirTemp"].min()), 1),
            "airTempMax":    round(float(weather_df["AirTemp"].max()), 1),
            "trackTempMin":  round(float(weather_df["TrackTemp"].min()), 1),
            "trackTempMax":  round(float(weather_df["TrackTemp"].max()), 1),
            "humidityMean":  round(float(weather_df["Humidity"].mean()), 1),
            "windSpeedMean": round(float(weather_df["WindSpeed"].mean()), 1),
            "rainfall":      bool(weather_df["Rainfall"].fillna(0).astype(bool).any()),
        }
        # Downsample weather to ~40 points for the chart
        step = max(1, len(weather_df) // 40)
        sample = weather_df.iloc[::step].copy()
        weather_samples = sample.assign(
            sessionTimeMin=lambda d: (d["sessionTimeS"] / 60).round(2)
        )[["sessionTimeMin", "AirTemp", "TrackTemp", "Humidity", "WindSpeed"]].where(
            pd.notnull(sample), None
        ).to_dict(orient="records")

    # Fastest lap weather conditions (nearest sample)
    fastest_weather = {}
    if not weather_df.empty:
        idx = (weather_df["sessionTimeS"] - float(fastest["sessionTimeS"])).abs().idxmin()
        row = weather_df.loc[idx]
        fastest_weather = {
            "airTemp":    round(float(row["AirTemp"]), 1)    if pd.notna(row["AirTemp"])    else None,
            "trackTemp":  round(float(row["TrackTemp"]), 1)  if pd.notna(row["TrackTemp"])  else None,
            "humidity":   round(float(row["Humidity"]), 1)   if pd.notna(row["Humidity"])   else None,
            "windSpeed":  round(float(row["WindSpeed"]), 1)  if pd.notna(row["WindSpeed"])  else None,
        }

    # Join weather to laps for grip window
    laps_with_weather = laps_df.copy()
    if not weather_df.empty:
        laps_with_weather = pd.merge_asof(
            laps_df.sort_values("sessionTimeS"),
            weather_df.sort_values("sessionTimeS"),
            on="sessionTimeS", direction="nearest", tolerance=90.0,
        )

    grip_window = estimate_best_grip_window(laps_with_weather)

    return _clean({
        "session":          {"year": year, "grandPrix": gp, "type": session_type},
        "totalValidLaps":   int(len(laps_df)),
        "fastestLap": {
            "driver":       str(fastest["driver"]),
            "lapTimeS":     round(float(fastest["lapTimeS"]), 3),
            "sessionTimeMin": round(float(fastest["sessionTimeS"]) / 60, 2),
            "weather":      fastest_weather,
        },
        "avgImprovementS":  avg_improvement,
        "evolution":        evolution,
        "weatherSummary":   weather_summary,
        "weatherSamples":   weather_samples,
        "bestGripWindow":   grip_window,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--gp",   type=str, default="Monaco")
    parser.add_argument("--session", type=str, default="Q")
    args = parser.parse_args()

    result = run(args.year, args.gp, args.session)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
