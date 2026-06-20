"""
Compare two drivers' fastest qualifying laps using FastF1.

Session: 2024 Monaco Grand Prix — Qualifying
Drivers compared: VER vs LEC
"""

from __future__ import annotations

from pathlib import Path

import fastf1
import pandas as pd


# Paths (project root is two levels above this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"

# Session settings
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "Q"  # Qualifying

# Drivers to compare (FastF1 driver abbreviations)
DRIVERS = ["VER", "LEC"]


def format_timedelta(td) -> str:
    """Format a pandas Timedelta as m:ss.mmm (motorsport-friendly)."""
    if pd.isna(td):
        return ""

    total_ms = int(td.total_seconds() * 1000)
    minutes, ms_remaining = divmod(total_ms, 60_000)
    seconds, milliseconds = divmod(ms_remaining, 1000)
    return f"{minutes}:{seconds:02d}.{milliseconds:03d}"


def enable_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_session():
    print("Loading session (this may take a moment on first run)...")
    session = fastf1.get_session(YEAR, GRAND_PRIX, SESSION_TYPE)
    session.load()
    print("Session loaded successfully.\n")
    return session


def get_fastest_lap_metrics(session, driver: str) -> dict:
    """
    Return a dict of metrics for a driver's fastest lap:
      - lap time
      - sector 1/2/3 time
      - top speed (km/h) during that lap
      - team
    """
    laps = session.laps.pick_drivers([driver])
    fastest = laps.pick_fastest()
    if fastest is None:
        raise RuntimeError(f"No fastest lap found for driver {driver}")

    top_speed = None
    try:
        car_data = fastest.get_car_data()
        if car_data is not None and "Speed" in car_data.columns:
            top_speed = float(car_data["Speed"].max())
    except Exception:
        # If car data isn't available, keep top_speed as None.
        top_speed = None

    return {
        "Driver": fastest["Driver"],
        "Team": fastest.get("Team", None),
        "LapTime": fastest["LapTime"],
        "Sector1Time": fastest.get("Sector1Time", None),
        "Sector2Time": fastest.get("Sector2Time", None),
        "Sector3Time": fastest.get("Sector3Time", None),
        "TopSpeed": top_speed,
    }


def pick_winner(df: pd.DataFrame, column: str) -> str | None:
    """Return the driver with the minimum (fastest) timedelta in column."""
    valid = df.dropna(subset=[column])
    if valid.empty:
        return None
    idx = valid[column].idxmin()
    return str(df.loc[idx, "Driver"])


def main() -> None:
    enable_cache()
    session = load_session()

    rows = [get_fastest_lap_metrics(session, d) for d in DRIVERS]
    df = pd.DataFrame(rows)

    df = df.sort_values("LapTime", ascending=True).reset_index(drop=True)

    # Pretty-print copy (keep raw timedeltas for winner logic)
    display_df = df.copy()
    display_df["LapTime"] = display_df["LapTime"].map(format_timedelta)
    display_df["Sector1Time"] = display_df["Sector1Time"].map(format_timedelta)
    display_df["Sector2Time"] = display_df["Sector2Time"].map(format_timedelta)
    display_df["Sector3Time"] = display_df["Sector3Time"].map(format_timedelta)
    display_df["TopSpeed"] = display_df["TopSpeed"].map(
        lambda v: "" if pd.isna(v) or v is None else f"{v:.1f}"
    )

    print("Fastest lap comparison (Qualifying):")
    print(display_df[["Driver", "Team", "LapTime", "Sector1Time", "Sector2Time", "Sector3Time", "TopSpeed"]].to_string(index=False))

    # Overall winner (fastest lap)
    overall_winner = pick_winner(df, "LapTime")
    if overall_winner is not None:
        print(f"\nFaster overall (fastest lap): {overall_winner}")

    # Sector winners
    s1_winner = pick_winner(df, "Sector1Time")
    s2_winner = pick_winner(df, "Sector2Time")
    s3_winner = pick_winner(df, "Sector3Time")

    print("\nSector winners:")
    print(f"  Sector 1: {s1_winner or 'N/A'}")
    print(f"  Sector 2: {s2_winner or 'N/A'}")
    print(f"  Sector 3: {s3_winner or 'N/A'}")


if __name__ == "__main__":
    main()

