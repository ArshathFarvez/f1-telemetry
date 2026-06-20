"""
Weather vs performance analysis for qualifying.

Session: 2024 Monaco Grand Prix — Qualifying

This script:
  - Uses FastF1, pandas, numpy, matplotlib
  - Enables FastF1 cache under telemetry-cache/
  - Extracts weather fields:
      AirTemp, TrackTemp, Humidity, WindSpeed, Rainfall
  - Extracts lap fields:
      lap times, session timestamps
  - Correlates lap performance vs track temperature and other weather changes
  - Visualizes:
      TrackTemp over time, AirTemp over time, Humidity over time,
      LapTime vs TrackTemp
  - Prints:
      hottest/coolest track temperature
      fastest lap weather conditions
      estimated best grip window (track temp range with best median lap time)
"""

from __future__ import annotations

from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ===== Configuration =====
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "Q"  # Qualifying

# Cache under project root: telemetry-cache/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"

# Red Bull themed colors
RB_BLUE = "#1E5BC6"
RB_YELLOW = "#FCD700"
RB_GREY = "#9AA0A6"


def enable_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def td_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return float(td.total_seconds())


def load_session():
    print("Loading session (this may take a moment on first run)...")
    session = fastf1.get_session(YEAR, GRAND_PRIX, SESSION_TYPE)
    session.load()
    print("Session loaded successfully.\n")
    return session


def build_weather_df(session) -> pd.DataFrame:
    weather = session.weather_data.copy()
    if "Time" not in weather.columns:
        raise RuntimeError("Weather data is missing 'Time'.")

    weather["SessionTimeSeconds"] = weather["Time"].map(td_to_seconds)

    cols = ["AirTemp", "TrackTemp", "Humidity", "WindSpeed", "Rainfall"]
    for c in cols:
        if c not in weather.columns:
            weather[c] = np.nan

    weather = weather[["SessionTimeSeconds"] + cols]
    weather = weather.dropna(subset=["SessionTimeSeconds"]).sort_values("SessionTimeSeconds").reset_index(drop=True)
    return weather


def build_laps_df(session) -> pd.DataFrame:
    laps = session.laps
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()

    time_col = "LapStartTime" if "LapStartTime" in laps.columns else "Time"
    if time_col not in laps.columns:
        raise RuntimeError("Could not find lap time column (LapStartTime/Time).")

    df = pd.DataFrame(
        {
            "Driver": laps["Driver"],
            "LapTimeSeconds": laps["LapTime"].map(td_to_seconds),
            "SessionTimeSeconds": laps[time_col].map(td_to_seconds),
        }
    )
    df = df.dropna(subset=["Driver", "LapTimeSeconds", "SessionTimeSeconds"])
    df = df.sort_values("SessionTimeSeconds").reset_index(drop=True)
    return df


def join_weather_to_laps(laps_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach nearest weather sample to each lap (by session time).
    """
    w = weather_df.sort_values("SessionTimeSeconds").reset_index(drop=True)
    l = laps_df.sort_values("SessionTimeSeconds").reset_index(drop=True)

    joined = pd.merge_asof(
        l,
        w,
        on="SessionTimeSeconds",
        direction="nearest",
        tolerance=90.0,  # seconds
    )
    return joined


def correlation_report(df: pd.DataFrame, x_col: str, y_col: str) -> float | None:
    valid = df[[x_col, y_col]].dropna()
    if len(valid) < 5:
        return None
    x = valid[x_col].to_numpy(dtype=float)
    y = valid[y_col].to_numpy(dtype=float)
    if np.nanstd(x) == 0 or np.nanstd(y) == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def estimate_best_grip_window(df: pd.DataFrame, bins: int = 8) -> tuple[float, float, float] | None:
    """
    Estimate best grip window as the track temperature bin with lowest median lap time.
    Returns (temp_low, temp_high, median_lap_time).
    """
    valid = df[["TrackTemp", "LapTimeSeconds"]].dropna()
    if len(valid) < 20:
        return None

    temps = valid["TrackTemp"].to_numpy(dtype=float)
    t_min, t_max = float(np.nanmin(temps)), float(np.nanmax(temps))
    if not np.isfinite(t_min) or not np.isfinite(t_max) or t_max <= t_min:
        return None

    edges = np.linspace(t_min, t_max, bins + 1)
    valid = valid.copy()
    valid["TempBin"] = pd.cut(valid["TrackTemp"], bins=edges, include_lowest=True)

    medians = valid.groupby("TempBin", observed=True)["LapTimeSeconds"].median().dropna()
    if medians.empty:
        return None

    best_bin = medians.idxmin()
    # best_bin is an Interval
    return float(best_bin.left), float(best_bin.right), float(medians.loc[best_bin])


def plot_weather_and_performance(weather_df: pd.DataFrame, laps_weather_df: pd.DataFrame) -> None:
    plt.style.use("dark_background")

    t_w = weather_df["SessionTimeSeconds"] / 60.0
    t_l = laps_weather_df["SessionTimeSeconds"] / 60.0

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))
    fig.suptitle(f"Weather & Track Evolution — {GRAND_PRIX} {YEAR} Qualifying", fontsize=14)

    # TrackTemp over session
    ax = axes[0, 0]
    ax.plot(t_w, weather_df["TrackTemp"], color=RB_YELLOW, linewidth=2, label="TrackTemp")
    ax.set_title("Track Temperature over Session")
    ax.set_xlabel("Session time (min)")
    ax.set_ylabel("TrackTemp (°C)")
    ax.grid(True, alpha=0.25)
    ax.legend()

    # AirTemp over session
    ax = axes[0, 1]
    ax.plot(t_w, weather_df["AirTemp"], color=RB_BLUE, linewidth=2, label="AirTemp")
    ax.set_title("Air Temperature over Session")
    ax.set_xlabel("Session time (min)")
    ax.set_ylabel("AirTemp (°C)")
    ax.grid(True, alpha=0.25)
    ax.legend()

    # Lap time vs TrackTemp
    ax = axes[1, 0]
    ax.scatter(
        laps_weather_df["TrackTemp"],
        laps_weather_df["LapTimeSeconds"],
        s=18,
        alpha=0.25,
        color=RB_GREY,
        edgecolors="none",
        label="Valid laps",
    )
    ax.set_title("Lap Time vs Track Temperature")
    ax.set_xlabel("TrackTemp (°C)")
    ax.set_ylabel("Lap time (s)")
    ax.grid(True, alpha=0.25)
    ax.legend()

    # Humidity trend
    ax = axes[1, 1]
    ax.plot(t_w, weather_df["Humidity"], color=RB_GREY, linewidth=2, label="Humidity")
    ax.set_title("Humidity over Session")
    ax.set_xlabel("Session time (min)")
    ax.set_ylabel("Humidity (%)")
    ax.grid(True, alpha=0.25)
    ax.legend()

    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    weather_df = build_weather_df(session)
    laps_df = build_laps_df(session)
    laps_weather = join_weather_to_laps(laps_df, weather_df)

    hottest = float(weather_df["TrackTemp"].max())
    coolest = float(weather_df["TrackTemp"].min())

    fastest_idx = laps_weather["LapTimeSeconds"].idxmin()
    fastest = laps_weather.loc[fastest_idx]

    corr_tracktemp = correlation_report(laps_weather, "TrackTemp", "LapTimeSeconds")
    corr_airtemp = correlation_report(laps_weather, "AirTemp", "LapTimeSeconds")
    corr_humidity = correlation_report(laps_weather, "Humidity", "LapTimeSeconds")

    print("Track temperature extremes:")
    print(f"- Hottest TrackTemp: {hottest:.1f} °C")
    print(f"- Coolest TrackTemp: {coolest:.1f} °C")

    print("\nFastest lap weather conditions (nearest sample):")
    print(f"- Driver: {fastest['Driver']}")
    print(f"- LapTime: {fastest['LapTimeSeconds']:.3f}s")
    print(f"- TrackTemp: {fastest['TrackTemp']:.1f} °C")
    print(f"- AirTemp: {fastest['AirTemp']:.1f} °C")
    print(f"- Humidity: {fastest['Humidity']:.1f} %")
    print(f"- WindSpeed: {fastest['WindSpeed']:.1f} m/s")
    print(f"- Rainfall: {fastest['Rainfall']:.1f}")

    print("\nCorrelations (lap time vs weather):")
    def fmt(c):  # small helper
        return "N/A" if c is None else f"{c:+.3f}"

    print(f"- LapTime vs TrackTemp: {fmt(corr_tracktemp)}")
    print(f"- LapTime vs AirTemp:   {fmt(corr_airtemp)}")
    print(f"- LapTime vs Humidity:  {fmt(corr_humidity)}")

    grip = estimate_best_grip_window(laps_weather, bins=8)
    if grip is None:
        print("\nEstimated best grip window: N/A (not enough data)")
    else:
        t_lo, t_hi, median_time = grip
        print("\nEstimated best grip window (by TrackTemp bin with best median lap):")
        print(f"- TrackTemp: {t_lo:.1f}–{t_hi:.1f} °C")
        print(f"- Median lap time in window: {median_time:.3f}s")

    plot_weather_and_performance(weather_df, laps_weather)


if __name__ == "__main__":
    main()

