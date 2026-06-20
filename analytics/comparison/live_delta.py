"""
Live delta (cumulative lap delta) between two fastest laps.

Session: 2024 Monaco Grand Prix — Qualifying
Drivers: VER vs LEC

This script:
  - Loads the session with FastF1 (cache enabled)
  - Finds each driver's fastest lap
  - Extracts telemetry channels: Distance, Speed, Time
  - Builds a cumulative delta over distance:
        delta = time_VER(distance) - time_LEC(distance)
    (positive delta => VER behind; negative delta => VER ahead)
  - Produces a dataframe:
        distance, delta_time, leading_driver
  - Plots delta vs distance with dark styling and shaded gain/loss regions
  - Prints:
        - who leads at the finish line
        - largest gained section
        - largest lost section
  - Adds corner annotations (best-effort) by marking major speed minima
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

DRIVER_A = "VER"  # Red Bull
DRIVER_B = "LEC"  # Ferrari

COLORS = {
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
    """Convert a pandas/py timedelta to seconds (float)."""
    if pd.isna(td):
        return float("nan")
    return float(td.total_seconds())


def get_fastest_lap(session, driver: str) -> pd.Series:
    laps = session.laps.pick_drivers([driver])
    fastest = laps.pick_fastest()
    if fastest is None:
        raise RuntimeError(f"No fastest lap found for {driver}")
    return fastest


def telemetry_time_seconds(telemetry: pd.DataFrame) -> np.ndarray:
    """
    FastF1 telemetry includes a Time column (timedelta since lap start).
    Convert to seconds.
    """
    if "Time" not in telemetry.columns:
        raise KeyError("Telemetry is missing the 'Time' column.")
    return telemetry["Time"].map(td_to_seconds).to_numpy(dtype=float)


def build_delta_dataframe(
    tel_a: pd.DataFrame,
    tel_b: pd.DataFrame,
    driver_a: str,
    driver_b: str,
    n_points: int = 2500,
) -> pd.DataFrame:
    """
    Interpolate each lap's time vs distance onto a shared distance grid, then compute:
      delta_time = time_a - time_b
    """
    required = ["Distance", "Speed", "Time"]
    for r in required:
        if r not in tel_a.columns or r not in tel_b.columns:
            raise KeyError(f"Missing required telemetry column '{r}'.")

    dist_a = tel_a["Distance"].to_numpy(dtype=float)
    dist_b = tel_b["Distance"].to_numpy(dtype=float)

    # Use the overlap range so we don't extrapolate.
    d_max = float(min(np.nanmax(dist_a), np.nanmax(dist_b)))
    d_min = float(max(np.nanmin(dist_a), np.nanmin(dist_b)))
    if not np.isfinite(d_max) or d_max <= d_min:
        raise RuntimeError("Could not determine a valid shared distance range.")

    distance = np.linspace(d_min, d_max, n_points)

    time_a = telemetry_time_seconds(tel_a)
    time_b = telemetry_time_seconds(tel_b)

    # Ensure monotonically increasing distance for interpolation
    order_a = np.argsort(dist_a)
    order_b = np.argsort(dist_b)

    time_a_i = np.interp(distance, dist_a[order_a], time_a[order_a])
    time_b_i = np.interp(distance, dist_b[order_b], time_b[order_b])

    delta = time_a_i - time_b_i
    leader = np.where(delta < 0, driver_a, driver_b)  # negative => A ahead

    df = pd.DataFrame(
        {
            "Distance": distance,
            "DeltaTime": delta,
            "LeadingDriver": leader,
        }
    )
    return df


def find_gain_loss_sections(df: pd.DataFrame) -> dict:
    """
    Find the biggest per-segment gain/loss for DRIVER_A relative to DRIVER_B.

    We use the first difference of delta_time:
      delta = t_A - t_B
      if delta decreases over a segment => A gained time
      if delta increases over a segment => A lost time
    """
    dist = df["Distance"].to_numpy(dtype=float)
    delta = df["DeltaTime"].to_numpy(dtype=float)

    d_delta = np.diff(delta)
    d_dist = np.diff(dist)

    # Protect against any weird zero distances
    d_dist[d_dist == 0] = np.nan

    # Segment gain/loss in seconds (not per meter)
    gain_idx = int(np.nanargmin(d_delta))  # most negative change => biggest gain for A
    loss_idx = int(np.nanargmax(d_delta))  # most positive change => biggest loss for A

    def segment(i: int) -> tuple[float, float, float]:
        start = float(dist[i])
        end = float(dist[i + 1])
        change = float(d_delta[i])  # seconds
        return start, end, change

    gain_seg = segment(gain_idx)
    loss_seg = segment(loss_idx)

    return {"gain": gain_seg, "loss": loss_seg}


def annotate_corners(ax, reference_tel: pd.DataFrame, n_corners: int = 10, min_spacing_m: float = 200.0) -> None:
    """
    Best-effort corner annotations.

    Monaco has many slow corners. Without a corner map, we approximate by selecting
    major local minima in Speed along the lap and labeling them C1..Cn.
    """
    dist = reference_tel["Distance"].to_numpy(dtype=float)
    speed = reference_tel["Speed"].to_numpy(dtype=float)

    if len(dist) < 100:
        return

    # Candidate minima: sort by speed ascending (slowest points)
    candidates = np.argsort(speed)
    chosen = []

    for idx in candidates:
        d = dist[idx]
        if not np.isfinite(d):
            continue
        if all(abs(d - dist[j]) >= min_spacing_m for j in chosen):
            chosen.append(int(idx))
        if len(chosen) >= n_corners:
            break

    chosen = sorted(chosen, key=lambda i: dist[i])
    for i, idx in enumerate(chosen, start=1):
        ax.axvline(dist[idx], color="white", alpha=0.06, linewidth=1)
        ax.text(
            dist[idx],
            ax.get_ylim()[0] * 0.95,
            f"C{i}",
            rotation=90,
            va="bottom",
            ha="center",
            fontsize=8,
            color="white",
            alpha=0.6,
        )


def plot_delta(df: pd.DataFrame, tel_ref: pd.DataFrame) -> None:
    plt.style.use("dark_background")

    x = df["Distance"].to_numpy(dtype=float)
    y = df["DeltaTime"].to_numpy(dtype=float)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(f"Live Delta — {GRAND_PRIX} {YEAR} Qualifying (Fastest Laps)")
    ax.set_xlabel("Distance (m)")
    ax.set_ylabel(f"Delta time: {DRIVER_A} - {DRIVER_B} (s)")
    ax.grid(True, alpha=0.25)

    # Main delta line (use DRIVER_A color)
    ax.plot(x, y, color=COLORS[DRIVER_A], linewidth=2.0, label=f"Delta ({DRIVER_A}-{DRIVER_B})")

    # Zero line
    ax.axhline(0, color="white", linewidth=1.0, alpha=0.5)

    # Shaded regions:
    # Above 0 => A behind (B ahead) -> shade in Ferrari red
    # Below 0 => A ahead -> shade in Red Bull blue
    ax.fill_between(x, y, 0, where=(y >= 0), color=COLORS[DRIVER_B], alpha=0.15, interpolate=True, label=f"{DRIVER_B} ahead")
    ax.fill_between(x, y, 0, where=(y < 0), color=COLORS[DRIVER_A], alpha=0.15, interpolate=True, label=f"{DRIVER_A} ahead")

    annotate_corners(ax, tel_ref, n_corners=10, min_spacing_m=200.0)

    ax.legend()
    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    lap_a = get_fastest_lap(session, DRIVER_A)
    lap_b = get_fastest_lap(session, DRIVER_B)

    tel_a = lap_a.get_telemetry()[["Distance", "Speed", "Time"]].copy()
    tel_b = lap_b.get_telemetry()[["Distance", "Speed", "Time"]].copy()

    delta_df = build_delta_dataframe(tel_a, tel_b, DRIVER_A, DRIVER_B, n_points=2500)

    # Finish-line leader
    finish_delta = float(delta_df["DeltaTime"].iloc[-1])
    finish_leader = DRIVER_A if finish_delta < 0 else DRIVER_B

    sections = find_gain_loss_sections(delta_df)
    gain_start, gain_end, gain_change = sections["gain"]
    loss_start, loss_end, loss_change = sections["loss"]

    print("Finish line:")
    print(f"- Delta ({DRIVER_A}-{DRIVER_B}): {finish_delta:+.3f}s")
    print(f"- Leader at finish: {finish_leader}")

    # Interpret segment changes:
    # gain_change is negative => A gained. loss_change is positive => A lost.
    print("\nBiggest sections (per small distance segment):")
    print(f"- Largest gained section for {DRIVER_A}: {gain_start:.0f}m–{gain_end:.0f}m ({gain_change:+.3f}s)")
    print(f"- Largest lost section for {DRIVER_A}:  {loss_start:.0f}m–{loss_end:.0f}m ({loss_change:+.3f}s)")

    plot_delta(delta_df, tel_ref=tel_b)  # use LEC lap as reference for corner hints


if __name__ == "__main__":
    main()

