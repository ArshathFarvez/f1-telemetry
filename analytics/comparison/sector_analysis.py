"""
Sector performance comparison for multiple drivers (fastest qualifying laps).

Session: 2024 Monaco Grand Prix — Qualifying
Drivers: VER, LEC, NOR, PIA

Outputs:
  - DataFrame with Sector1/2/3 and LapTime (seconds)
  - Dark-themed bar chart comparing sector times
  - Printed winners:
      - fastest sector 1/2/3 driver
      - overall fastest lap
      - "most gained" per sector (largest gap to the slowest in that sector)
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

DRIVERS = ["VER", "LEC", "NOR", "PIA"]

COLORS = {
    "VER": "#1E5BC6",  # Red Bull blue
    "LEC": "#E10600",  # Ferrari red
    "NOR": "#FF8700",  # McLaren orange
    "PIA": "#FF8700",  # McLaren orange
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


def td_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return float(td.total_seconds())


def get_fastest_lap_row(session, driver: str) -> pd.Series:
    laps = session.laps.pick_drivers([driver])
    fastest = laps.pick_fastest()
    if fastest is None:
        raise RuntimeError(f"No fastest lap found for driver {driver}")
    return fastest


def build_dataframe(session) -> pd.DataFrame:
    rows = []
    for d in DRIVERS:
        lap = get_fastest_lap_row(session, d)
        rows.append(
            {
                "Driver": d,
                "Sector1Seconds": td_to_seconds(lap.get("Sector1Time", None)),
                "Sector2Seconds": td_to_seconds(lap.get("Sector2Time", None)),
                "Sector3Seconds": td_to_seconds(lap.get("Sector3Time", None)),
                "LapTimeSeconds": td_to_seconds(lap.get("LapTime", None)),
            }
        )

    df = pd.DataFrame(rows)
    df = df.dropna(subset=["LapTimeSeconds"]).sort_values("LapTimeSeconds").reset_index(drop=True)
    return df


def winner_for_column(df: pd.DataFrame, column: str) -> str | None:
    valid = df.dropna(subset=[column])
    if valid.empty:
        return None
    idx = valid[column].idxmin()
    return str(df.loc[idx, "Driver"])


def most_gained_driver(df: pd.DataFrame, column: str) -> tuple[str | None, float | None]:
    """
    "Gains the most" for a sector is treated as the driver who is fastest in that
    sector and has the largest advantage vs the slowest driver in that sector.
    """
    valid = df.dropna(subset=[column])
    if valid.empty:
        return None, None

    best_idx = valid[column].idxmin()
    best_driver = str(df.loc[best_idx, "Driver"])
    best_time = float(df.loc[best_idx, column])
    worst_time = float(valid[column].max())
    return best_driver, float(worst_time - best_time)


def plot_sector_bars(df: pd.DataFrame) -> None:
    plt.style.use("dark_background")

    sector_cols = ["Sector1Seconds", "Sector2Seconds", "Sector3Seconds"]
    sector_names = ["Sector 1", "Sector 2", "Sector 3"]

    # Keep bars in the requested driver order (not sorted by lap time)
    df_plot = df.set_index("Driver").reindex(DRIVERS).reset_index()

    x = range(len(sector_cols))
    width = 0.18

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(f"Sector Performance Comparison — {GRAND_PRIX} {YEAR} Qualifying (Fastest Laps)")
    ax.set_xlabel("Sector")
    ax.set_ylabel("Time (seconds)")
    ax.grid(True, axis="y", alpha=0.25)

    offsets = {
        "VER": -1.5 * width,
        "LEC": -0.5 * width,
        "NOR": 0.5 * width,
        "PIA": 1.5 * width,
    }

    for driver in DRIVERS:
        times = [df_plot.loc[df_plot["Driver"] == driver, c].values[0] for c in sector_cols]
        ax.bar(
            [i + offsets[driver] for i in x],
            times,
            width=width,
            label=driver,
            color=COLORS.get(driver, "#AAAAAA"),
            alpha=0.95,
        )

    ax.set_xticks(list(x))
    ax.set_xticklabels(sector_names)
    ax.legend(title="Driver")

    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    df = build_dataframe(session)

    print("Fastest-lap sector comparison (seconds):")
    print(df.to_string(index=False))

    s1 = winner_for_column(df, "Sector1Seconds")
    s2 = winner_for_column(df, "Sector2Seconds")
    s3 = winner_for_column(df, "Sector3Seconds")
    overall = winner_for_column(df, "LapTimeSeconds")

    print("\nWinners:")
    print(f"- Fastest Sector 1: {s1 or 'N/A'}")
    print(f"- Fastest Sector 2: {s2 or 'N/A'}")
    print(f"- Fastest Sector 3: {s3 or 'N/A'}")
    print(f"- Overall fastest lap: {overall or 'N/A'}")

    mg1_driver, mg1_delta = most_gained_driver(df, "Sector1Seconds")
    mg2_driver, mg2_delta = most_gained_driver(df, "Sector2Seconds")
    mg3_driver, mg3_delta = most_gained_driver(df, "Sector3Seconds")

    print("\nMost gained (largest advantage vs slowest in sector):")
    if mg1_driver is not None:
        print(f"- Sector 1: {mg1_driver} by {mg1_delta:.3f}s")
    else:
        print("- Sector 1: N/A")

    if mg2_driver is not None:
        print(f"- Sector 2: {mg2_driver} by {mg2_delta:.3f}s")
    else:
        print("- Sector 2: N/A")

    if mg3_driver is not None:
        print(f"- Sector 3: {mg3_driver} by {mg3_delta:.3f}s")
    else:
        print("- Sector 3: N/A")

    plot_sector_bars(df)


if __name__ == "__main__":
    main()

