"""
Find the fastest qualifying lap for each driver using FastF1.

Example session: 2024 Monaco Grand Prix — Qualifying
"""

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


def load_session():
    """Enable cache, load the session, and return the session object."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    print("Loading session (this may take a moment on first run)...")
    session = fastf1.get_session(YEAR, GRAND_PRIX, SESSION_TYPE)
    session.load()
    print("Session loaded successfully.\n")
    return session


def build_fastest_laps_dataframe(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Build a DataFrame with the fastest lap for each driver.
    Output columns: Driver, LapTime, Team
    """
    results = []

    drivers = sorted([d for d in laps["Driver"].dropna().unique()])
    for driver in drivers:
        # pick_driver() is deprecated; pick_drivers() supports a list of drivers.
        driver_laps = laps.pick_drivers([driver])
        fastest = driver_laps.pick_fastest()
        if fastest is None:
            continue

        results.append(
            {
                "Driver": fastest["Driver"],
                "LapTime": fastest["LapTime"],
                "Team": fastest.get("Team", None),
            }
        )

    df = pd.DataFrame(results)
    df = df.dropna(subset=["LapTime"]).sort_values("LapTime", ascending=True).reset_index(
        drop=True
    )
    return df


def format_lap_time(lap_time) -> str:
    """Format a pandas Timedelta as m:ss.mmm (common motorsport format)."""
    if pd.isna(lap_time):
        return ""

    total_ms = int(lap_time.total_seconds() * 1000)
    minutes, ms_remaining = divmod(total_ms, 60_000)
    seconds, milliseconds = divmod(ms_remaining, 1000)
    return f"{minutes}:{seconds:02d}.{milliseconds:03d}"


def main():
    session = load_session()

    laps = session.laps
    fastest_by_driver = build_fastest_laps_dataframe(laps)

    top_10 = fastest_by_driver.head(10).copy()
    top_10["LapTime"] = top_10["LapTime"].map(format_lap_time)

    print("Top 10 fastest drivers (Qualifying):")
    print(top_10[["Driver", "LapTime", "Team"]].to_string(index=False))


if __name__ == "__main__":
    main()

