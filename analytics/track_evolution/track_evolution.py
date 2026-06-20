"""
Track evolution analysis: how lap times improve over a qualifying session.

Session: 2024 Monaco Grand Prix — Qualifying

What this script does:
  - Loads the session with FastF1 (with local cache enabled)
  - Collects every valid lap from all drivers
  - Converts lap times into seconds
  - Plots lap time vs session elapsed time (scatter)
  - Highlights the fastest lap of the session
  - Prints:
      - fastest driver
      - fastest lap time
      - average lap improvement over the session (early vs late)
"""

from __future__ import annotations

from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import pandas as pd


# ===== Configuration =====
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "Q"  # Qualifying

# Cache under project root: telemetry-cache/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"


def enable_cache() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_session():
    print("Loading session (this may take a moment on first run)...")
    session = fastf1.get_session(YEAR, GRAND_PRIX, SESSION_TYPE)
    session.load()
    print("Session loaded successfully.\n")
    return session


def timedelta_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return float(td.total_seconds())


def build_laps_dataframe(session) -> pd.DataFrame:
    """
    Build a dataframe with:
      - Driver
      - LapTimeSeconds
      - SessionTimeSeconds (elapsed)
    """
    laps = session.laps

    # "Valid laps" (best available filter in FastF1)
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()

    # Choose a session-time reference. LapStartTime is usually best for evolution.
    time_col = "LapStartTime" if "LapStartTime" in laps.columns else "Time"
    if time_col not in laps.columns:
        raise RuntimeError("Could not find a session time column (LapStartTime/Time) in laps.")

    df = pd.DataFrame(
        {
            "Driver": laps["Driver"],
            "LapTimeSeconds": laps["LapTime"].map(timedelta_to_seconds),
            "SessionTimeSeconds": laps[time_col].map(timedelta_to_seconds),
        }
    )

    df = df.dropna(subset=["Driver", "LapTimeSeconds", "SessionTimeSeconds"]).reset_index(drop=True)
    return df


def compute_average_improvement(df: pd.DataFrame) -> float:
    """
    A simple, readable metric:
      average improvement = mean(lap time in earliest 25% of session)
                            minus mean(lap time in latest 25% of session)

    Positive number => laps got faster over time.
    """
    df_sorted = df.sort_values("SessionTimeSeconds").reset_index(drop=True)
    n = len(df_sorted)
    if n < 8:
        return float("nan")

    q = max(int(n * 0.25), 1)
    early_mean = df_sorted.head(q)["LapTimeSeconds"].mean()
    late_mean = df_sorted.tail(q)["LapTimeSeconds"].mean()
    return float(early_mean - late_mean)


def plot_track_evolution(df: pd.DataFrame, fastest_row: pd.Series) -> None:
    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(f"Track Evolution — {GRAND_PRIX} {YEAR} Qualifying")
    ax.set_xlabel("Session Time Elapsed (minutes)")
    ax.set_ylabel("Lap Time (seconds)")
    ax.grid(True, alpha=0.25)

    x_minutes = df["SessionTimeSeconds"] / 60.0
    y = df["LapTimeSeconds"]

    ax.scatter(
        x_minutes,
        y,
        s=18,
        alpha=0.25,
        color="#9AA0A6",
        edgecolors="none",
        label="Valid laps",
    )

    # Highlight fastest lap
    fx = float(fastest_row["SessionTimeSeconds"]) / 60.0
    fy = float(fastest_row["LapTimeSeconds"])
    ax.scatter(
        [fx],
        [fy],
        s=80,
        color="#FFD100",
        edgecolors="#000000",
        linewidths=0.5,
        label=f"Fastest lap ({fastest_row['Driver']})",
        zorder=5,
    )
    ax.legend()

    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    df = build_laps_dataframe(session)
    if df.empty:
        raise RuntimeError("No valid laps found to analyze.")

    fastest_idx = df["LapTimeSeconds"].idxmin()
    fastest = df.loc[fastest_idx]

    avg_improvement = compute_average_improvement(df)

    print("Fastest lap:")
    print(f"- Driver: {fastest['Driver']}")
    print(f"- Lap time: {fastest['LapTimeSeconds']:.3f}s")

    if pd.isna(avg_improvement):
        print("- Average lap improvement over session: N/A (not enough laps)")
    else:
        print(f"- Average lap improvement over session (early vs late): {avg_improvement:.3f}s")

    plot_track_evolution(df, fastest)


if __name__ == "__main__":
    main()

