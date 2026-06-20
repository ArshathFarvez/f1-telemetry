"""
Tyre degradation analysis (lap-time falloff) using FastF1.

Session: 2024 Monaco Grand Prix — Race
Driver:  VER (Max Verstappen)

Outputs:
  - Cleaned lap-by-lap dataframe:
      LapNumber, LapTimeSeconds, Compound, TyreLife
  - Dark-themed degradation plot (lap time vs lap number), colored by compound
  - Summary stats:
      average stint pace, fastest race lap, most-used compound
"""

from __future__ import annotations

from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import pandas as pd


# ===== Configuration =====
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "R"  # Race
DRIVER = "VER"

COMPOUND_COLORS = {
    "SOFT": "#E10600",  # red
    "MEDIUM": "#FFD100",  # yellow
    "HARD": "#FFFFFF",  # white
}

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


def lap_time_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return float(td.total_seconds())


def filter_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Remove:
      - invalid laps (FastF1's pick_accurate)
      - pit laps (laps with pit in/out times)
      - safety car / VSC affected laps if possible (best-effort)
    """
    # Invalid laps (track limits, incomplete timing, etc.)
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()

    # Pit laps: remove laps where driver enters/exits pit during that lap
    pit_cols = [c for c in ["PitInTime", "PitOutTime"] if c in laps.columns]
    if pit_cols:
        pit_mask = False
        for c in pit_cols:
            pit_mask = pit_mask | laps[c].notna()
        laps = laps.loc[~pit_mask]

    # Safety car affected (best-effort)
    # FastF1 sometimes provides `TrackStatus` per lap. Status codes vary by feed.
    # Commonly: '4' = Safety Car, '6' = Virtual Safety Car.
    if "TrackStatus" in laps.columns:
        status = laps["TrackStatus"].astype(str)
        # Avoid capture groups to keep pandas from warning.
        sc_mask = status.str.contains(r"4|6", regex=True)
        laps = laps.loc[~sc_mask]

    return laps


def build_dataframe(laps: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "LapNumber": laps["LapNumber"].astype(int),
            "LapTimeSeconds": laps["LapTime"].map(lap_time_to_seconds),
            "Compound": laps.get("Compound", pd.Series([None] * len(laps))),
            "TyreLife": laps.get("TyreLife", pd.Series([None] * len(laps))),
            "Stint": laps.get("Stint", pd.Series([None] * len(laps))),
        }
    )
    df = df.dropna(subset=["LapTimeSeconds"]).reset_index(drop=True)
    return df


def print_summary(df: pd.DataFrame) -> None:
    # Average stint pace
    if "Stint" in df.columns and df["Stint"].notna().any():
        stint_pace = (
            df.groupby(["Stint", "Compound"], dropna=False)["LapTimeSeconds"]
            .mean()
            .reset_index()
            .sort_values(["Stint"])
        )
        print("Average stint pace (seconds):")
        print(stint_pace.to_string(index=False))
        print()
    else:
        print(f"Average pace (seconds): {df['LapTimeSeconds'].mean():.3f}\n")

    # Fastest race lap
    fastest_row = df.loc[df["LapTimeSeconds"].idxmin()]
    print(
        "Fastest race lap:",
        f"Lap {int(fastest_row['LapNumber'])} in {fastest_row['LapTimeSeconds']:.3f}s",
        f"({fastest_row['Compound']})",
    )

    # Most used compound
    compound_counts = df["Compound"].value_counts(dropna=True)
    most_used = compound_counts.index[0] if not compound_counts.empty else None
    if most_used is not None:
        print(f"Tyre compound used most: {most_used} ({int(compound_counts.iloc[0])} laps)")
    else:
        print("Tyre compound used most: N/A")


def plot_degradation(df: pd.DataFrame) -> None:
    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(f"{DRIVER} Tyre Degradation — {GRAND_PRIX} {YEAR} Race")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (s)")
    ax.grid(True, alpha=0.25)

    # Plot each compound in its color for a clear overlay
    compounds = [c for c in df["Compound"].dropna().unique()]
    compounds_sorted = sorted(compounds, key=lambda c: ["SOFT", "MEDIUM", "HARD"].index(c) if c in ["SOFT", "MEDIUM", "HARD"] else 99)

    for compound in compounds_sorted:
        subset = df[df["Compound"] == compound]
        color = COMPOUND_COLORS.get(compound, "#AAAAAA")
        ax.scatter(
            subset["LapNumber"],
            subset["LapTimeSeconds"],
            s=22,
            alpha=0.9,
            label=compound,
            color=color,
            edgecolors="none",
        )

    # Light trend line (overall) to visualize falloff direction
    if len(df) >= 5:
        trend = df.sort_values("LapNumber")
        ax.plot(trend["LapNumber"], trend["LapTimeSeconds"], color="#CCCCCC", alpha=0.25, linewidth=1)

    ax.legend(title="Compound")
    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    laps_all = session.laps.pick_drivers([DRIVER])
    laps_clean = filter_laps(laps_all)
    df = build_dataframe(laps_clean)

    print(f"Driver: {DRIVER}")
    print(f"Total laps (raw): {len(laps_all)}")
    print(f"Total laps (cleaned): {len(df)}\n")

    print_summary(df)
    plot_degradation(df)


if __name__ == "__main__":
    main()

