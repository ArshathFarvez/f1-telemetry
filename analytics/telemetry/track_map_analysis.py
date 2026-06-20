"""
Track map analysis from telemetry coordinates.

Session: 2024 Monaco Grand Prix — Qualifying
Drivers: VER vs LEC

What this script does:
  - Loads the session with FastF1 (cache enabled)
  - Finds fastest lap for each driver
  - Aligns position data (X/Y) with car telemetry (Speed/Throttle/Brake) by time
  - Plots a Monaco "track map" (racing line) for both drivers
      - speed intensity color mapping
      - braking zone highlights
      - corner exit highlights (best-effort)
      - top speed highlights
  - Prints:
      - highest speed section
      - strongest braking zone
      - driver with smoother throttle application
"""

from __future__ import annotations

from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, Normalize


# ===== Configuration =====
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "Q"  # Qualifying

DRIVERS = ["VER", "LEC"]

DRIVER_COLORS = {
    "VER": "#1E5BC6",  # Red Bull blue
    "LEC": "#E10600",  # Ferrari red
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


def td_to_seconds(td) -> float:
    if pd.isna(td):
        return float("nan")
    return float(td.total_seconds())


def get_fastest_lap(session, driver: str) -> pd.Series:
    laps = session.laps.pick_drivers([driver])
    fastest = laps.pick_fastest()
    if fastest is None:
        raise RuntimeError(f"No fastest lap found for driver {driver}")
    return fastest


def align_position_and_car_data(lap: pd.Series) -> pd.DataFrame:
    """
    Build a single dataframe with:
      TimeSeconds, X, Y, Speed, Throttle, Brake
    using a nearest-time merge of position + car data.
    """
    pos = lap.get_pos_data()
    car = lap.get_car_data()

    # Standardize time to seconds for stable alignment.
    pos_df = pos[["Time", "X", "Y"]].copy()
    car_df = car[["Time", "Speed", "Throttle", "Brake"]].copy()
    pos_df["TimeSeconds"] = pos_df["Time"].map(td_to_seconds)
    car_df["TimeSeconds"] = car_df["Time"].map(td_to_seconds)

    pos_df = pos_df.dropna(subset=["TimeSeconds", "X", "Y"]).sort_values("TimeSeconds")
    car_df = car_df.dropna(subset=["TimeSeconds", "Speed"]).sort_values("TimeSeconds")

    # Merge asof aligns each position sample to the nearest car sample.
    merged = pd.merge_asof(
        pos_df,
        car_df[["TimeSeconds", "Speed", "Throttle", "Brake"]],
        on="TimeSeconds",
        direction="nearest",
        tolerance=0.05,  # 50ms tolerance is typically safe for FastF1 sampled data
    )

    merged = merged.dropna(subset=["Speed", "Throttle", "Brake"]).reset_index(drop=True)
    return merged


def make_driver_colormap(driver_color: str) -> LinearSegmentedColormap:
    """
    A simple two-tone colormap: dark -> driver_color.
    This keeps "team identity" while still encoding speed intensity.
    """
    return LinearSegmentedColormap.from_list("driver_cmap", ["#0A0A0A", driver_color])


def colored_line(ax, x: np.ndarray, y: np.ndarray, values: np.ndarray, color: str, label: str):
    """
    Plot a polyline where segment colors are driven by 'values' (speed),
    using a driver-themed colormap.
    """
    points = np.array([x, y]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    norm = Normalize(vmin=np.nanmin(values), vmax=np.nanmax(values))
    lc = LineCollection(
        segments,
        cmap=make_driver_colormap(color),
        norm=norm,
        linewidth=2.0,
        alpha=0.95,
    )
    lc.set_array(values[:-1])
    ax.add_collection(lc)
    ax.plot([], [], color=color, linewidth=2, label=label)  # legend handle
    return lc


def find_top_speed_point(df: pd.DataFrame) -> tuple[float, float, float]:
    i = int(df["Speed"].idxmax())
    return float(df.loc[i, "X"]), float(df.loc[i, "Y"]), float(df.loc[i, "Speed"])


def find_strongest_braking(df: pd.DataFrame) -> tuple[float, float, float]:
    """
    Strongest braking zone approximated by maximum deceleration:
      decel = -dV/dt  (km/h per second)
    """
    t = df["TimeSeconds"].to_numpy(dtype=float)
    v = df["Speed"].to_numpy(dtype=float)
    dt = np.diff(t)
    dv = np.diff(v)

    dt[dt <= 0] = np.nan
    decel = -(dv / dt)  # positive means slowing down

    idx = int(np.nanargmax(decel))
    # idx is between points idx and idx+1; use idx+1 for location
    x = float(df.loc[idx + 1, "X"])
    y = float(df.loc[idx + 1, "Y"])
    return x, y, float(decel[idx])


def throttle_smoothness(df: pd.DataFrame) -> float:
    """
    Lower means smoother.
    Use mean absolute derivative of throttle w.r.t. time.
    """
    t = df["TimeSeconds"].to_numpy(dtype=float)
    thr = df["Throttle"].to_numpy(dtype=float)
    dt = np.diff(t)
    dthr = np.diff(thr)
    dt[dt <= 0] = np.nan
    rate = np.abs(dthr / dt)
    return float(np.nanmean(rate))


def detect_corner_exits(df: pd.DataFrame, max_points: int = 8) -> pd.DataFrame:
    """
    Best-effort corner exit detection:
      - look for moments where Brake drops and Throttle ramps up shortly after.
    Returns a dataframe of selected points.
    """
    brake = df["Brake"].to_numpy(dtype=float)
    throttle = df["Throttle"].to_numpy(dtype=float)

    # "exit" = brake low and throttle high
    exit_mask = (brake < 5) & (throttle > 80)
    candidates = np.where(exit_mask)[0]
    if len(candidates) == 0:
        return df.iloc[0:0]

    # Take a spaced-out subset for readability
    chosen = [candidates[0]]
    for idx in candidates[1:]:
        if idx - chosen[-1] > 100:  # spacing in samples
            chosen.append(idx)
        if len(chosen) >= max_points:
            break

    return df.iloc[chosen][["X", "Y", "Speed"]]


def plot_track_map(data_by_driver: dict[str, pd.DataFrame]) -> None:
    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_title(f"Monaco Track Map — {YEAR} Qualifying (Fastest Laps)")

    line_collections = []

    # Plot both racing lines with speed intensity
    for driver, df in data_by_driver.items():
        x = df["X"].to_numpy(dtype=float)
        y = df["Y"].to_numpy(dtype=float)
        speed = df["Speed"].to_numpy(dtype=float)

        lc = colored_line(
            ax,
            x=x,
            y=y,
            values=speed,
            color=DRIVER_COLORS[driver],
            label=driver,
        )
        line_collections.append((driver, lc))

        # Braking zones (highlight where brake is high)
        brake_mask = df["Brake"] > 40
        ax.scatter(
            df.loc[brake_mask, "X"],
            df.loc[brake_mask, "Y"],
            s=6,
            color="#FFD100",
            alpha=0.22,
            linewidths=0,
            label=None,
        )

        # Corner exits (best-effort)
        exits = detect_corner_exits(df, max_points=8)
        if not exits.empty:
            ax.scatter(
                exits["X"],
                exits["Y"],
                s=25,
                color="#00E5FF",
                alpha=0.55,
                edgecolors="none",
                label=None,
            )

        # Top speed area (top 1% speeds)
        q = df["Speed"].quantile(0.99)
        top_mask = df["Speed"] >= q
        ax.scatter(
            df.loc[top_mask, "X"],
            df.loc[top_mask, "Y"],
            s=12,
            color="white",
            alpha=0.25,
            edgecolors="none",
            label=None,
        )

    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend(title="Driver")

    # Add one shared colorbar (speed) using the first collection
    if line_collections:
        _driver, lc0 = line_collections[0]
        cbar = fig.colorbar(lc0, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label("Speed intensity (km/h)")

    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    data_by_driver: dict[str, pd.DataFrame] = {}
    for d in DRIVERS:
        lap = get_fastest_lap(session, d)
        df = align_position_and_car_data(lap)
        data_by_driver[d] = df

    # ===== Print required metrics =====
    top_speed_info = {d: find_top_speed_point(df) for d, df in data_by_driver.items()}
    top_speed_driver = max(top_speed_info.keys(), key=lambda d: top_speed_info[d][2])
    x, y, v = top_speed_info[top_speed_driver]

    braking_info = {d: find_strongest_braking(df) for d, df in data_by_driver.items()}
    braking_driver = max(braking_info.keys(), key=lambda d: braking_info[d][2])
    bx, by, decel = braking_info[braking_driver]

    smoothness = {d: throttle_smoothness(df) for d, df in data_by_driver.items()}
    smoothest_driver = min(smoothness.keys(), key=lambda d: smoothness[d])

    print("Track map highlights:")
    print(
        f"- Highest speed section: {top_speed_driver} at {v:.1f} km/h "
        f"(X={x:.1f}, Y={y:.1f})"
    )
    print(
        f"- Strongest braking zone: {braking_driver} at {decel:.1f} (km/h)/s "
        f"(X={bx:.1f}, Y={by:.1f})"
    )
    print(
        f"- Smoother throttle application: {smoothest_driver} "
        f"(mean |dThrottle/dt| = {smoothness[smoothest_driver]:.1f} %/s)"
    )

    # ===== Plot =====
    plot_track_map(data_by_driver)


if __name__ == "__main__":
    main()

