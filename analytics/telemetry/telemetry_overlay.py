"""
Overlay fastest-lap telemetry for two drivers (VER vs LEC).

Session: 2024 Monaco Grand Prix — Qualifying
Plots:
  - Speed vs Distance
  - Throttle vs Distance
  - Brake vs Distance
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

DRIVERS = {
    # Red Bull blue / Ferrari red (approx. brand colors)
    "VER": {"label": "VER", "color": "#1E5BC6"},
    "LEC": {"label": "LEC", "color": "#E10600"},
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


def get_fastest_lap_telemetry(session, driver_abbr: str) -> tuple[pd.Series, pd.DataFrame]:
    """
    Return (fastest_lap_row, telemetry_df) for a driver.

    telemetry_df contains channels like Speed/Throttle/Brake/Distance.
    """
    driver_laps = session.laps.pick_drivers([driver_abbr])
    fastest_lap = driver_laps.pick_fastest()
    if fastest_lap is None:
        raise RuntimeError(f"Could not find a fastest lap for driver {driver_abbr}")

    # FastF1 telemetry aligned by distance for a single lap.
    telemetry = fastest_lap.get_telemetry()
    return fastest_lap, telemetry


def get_channel(telemetry: pd.DataFrame, channel: str) -> pd.Series:
    if channel not in telemetry.columns:
        raise KeyError(f"Missing telemetry channel '{channel}'. Available: {list(telemetry.columns)}")
    return telemetry[channel]


def format_speed_label() -> str:
    return "Speed (km/h)"


def get_top_speed_kmh(telemetry: pd.DataFrame) -> float:
    return float(get_channel(telemetry, "Speed").max())


def get_first_brake_distance(telemetry: pd.DataFrame, brake_threshold: float = 1.0) -> float | None:
    """
    "Braked later" is interpreted as the driver whose first meaningful braking
    (Brake > threshold) happened at the greatest distance along the lap.
    """
    brake = get_channel(telemetry, "Brake")
    distance = get_channel(telemetry, "Distance")

    mask = brake > brake_threshold
    if not mask.any():
        return None

    first_idx = mask.idxmax()  # first True in pandas
    return float(distance.loc[first_idx])


def plot_telemetry_overlay(speed, throttle, brake, distance, drivers_meta):
    plt.style.use("dark_background")

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"Fastest Lap Telemetry Overlay - {GRAND_PRIX} {YEAR} Qualifying", fontsize=14)

    # Speed
    axes[0].plot(distance["VER"], speed["VER"], color=drivers_meta["VER"]["color"], label="VER")
    axes[0].plot(distance["LEC"], speed["LEC"], color=drivers_meta["LEC"]["color"], label="LEC")
    axes[0].set_ylabel(format_speed_label())
    axes[0].set_title("Speed vs Distance")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    # Throttle
    axes[1].plot(distance["VER"], throttle["VER"], color=drivers_meta["VER"]["color"], label="VER")
    axes[1].plot(distance["LEC"], throttle["LEC"], color=drivers_meta["LEC"]["color"], label="LEC")
    axes[1].set_ylabel("Throttle (%)")
    axes[1].set_title("Throttle vs Distance")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend()

    # Brake
    axes[2].plot(distance["VER"], brake["VER"], color=drivers_meta["VER"]["color"], label="VER")
    axes[2].plot(distance["LEC"], brake["LEC"], color=drivers_meta["LEC"]["color"], label="LEC")
    axes[2].set_xlabel("Distance (m)")
    axes[2].set_ylabel("Brake (%)")
    axes[2].set_title("Brake vs Distance")
    axes[2].grid(True, alpha=0.25)
    axes[2].legend()

    plt.tight_layout()
    return fig


def main() -> None:
    enable_cache()
    session = load_session()

    fastest_laps = {}
    telemetries = {}
    for abbr in DRIVERS.keys():
        fastest_lap, telemetry = get_fastest_lap_telemetry(session, abbr)
        fastest_laps[abbr] = fastest_lap
        telemetries[abbr] = telemetry

    # Extract required channels
    channels = {"Speed": {}, "Throttle": {}, "Brake": {}, "Distance": {}}
    for abbr, telemetry in telemetries.items():
        channels["Speed"][abbr] = get_channel(telemetry, "Speed")
        channels["Throttle"][abbr] = get_channel(telemetry, "Throttle")
        channels["Brake"][abbr] = get_channel(telemetry, "Brake")
        channels["Distance"][abbr] = get_channel(telemetry, "Distance")

    # Build plots
    plot_telemetry_overlay(
        speed=channels["Speed"],
        throttle=channels["Throttle"],
        brake=channels["Brake"],
        distance=channels["Distance"],
        drivers_meta=DRIVERS,
    )
    plt.show()

    # Compute and print required comparisons
    top_speeds = {abbr: get_top_speed_kmh(telemetries[abbr]) for abbr in DRIVERS.keys()}
    faster_top_speed = max(top_speeds, key=top_speeds.get)

    first_brake_dist = {
        abbr: get_first_brake_distance(telemetries[abbr], brake_threshold=1.0) for abbr in DRIVERS.keys()
    }

    braked_later = None
    a = first_brake_dist.get("VER")
    b = first_brake_dist.get("LEC")
    if a is not None and b is not None:
        braked_later = "VER" if a > b else "LEC"
    elif a is not None:
        braked_later = "VER"
    elif b is not None:
        braked_later = "LEC"

    print("Comparison results:")
    print(f"- Higher top speed: {faster_top_speed} ({top_speeds[faster_top_speed]:.1f} km/h)")
    if braked_later is not None:
        print(
            f"- Braked later (first brake): {braked_later} "
            f"(VER={first_brake_dist['VER']:.1f}m, LEC={first_brake_dist['LEC']:.1f}m)"
        )
    else:
        print("- Braked later: N/A (could not detect meaningful braking on one/both laps)")


if __name__ == "__main__":
    main()

