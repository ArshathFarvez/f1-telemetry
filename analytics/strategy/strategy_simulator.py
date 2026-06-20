"""
Strategy simulator (simple + explainable) using FastF1 race data.

Session: 2024 Monaco Grand Prix — Race
Driver:  VER (Max Verstappen)

This script:
  1) Loads race laps for VER (with cache enabled).
  2) Cleans laps (best-effort valid laps + removes pit in/out laps).
  3) Builds a per-stint strategy dataframe:
       - stint number
       - tyre compound
       - stint length
       - average pace (s)
       - fastest lap in stint (s)
  4) Simulates (heuristic but useful):
       - ideal pit stop windows
       - undercut potential
       - tyre degradation per stint
  5) Plots:
       - stint pace comparison
       - tyre degradation by stint
       - pit window visualization
  6) Prints:
       - best performing stint
       - estimated optimal pit lap
       - compound with best pace consistency
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# ===== Configuration =====
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "R"  # Race
DRIVER = "VER"

# Cache under project root: telemetry-cache/
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"

# Red Bull themed colors
RB_BLUE = "#1E5BC6"
RB_YELLOW = "#FCD700"
RB_DARK = "#0B0F1A"


@dataclass(frozen=True)
class PitWindow:
    stint: int
    compound: str
    start_lap: int
    end_lap: int
    recommended_lap: int
    degradation_s_per_lap: float
    estimated_undercut_s: float


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


def filter_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Best-effort cleaning: accurate laps and remove pit in/out laps."""
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()

    pit_cols = [c for c in ["PitInTime", "PitOutTime"] if c in laps.columns]
    if pit_cols:
        pit_mask = False
        for c in pit_cols:
            pit_mask = pit_mask | laps[c].notna()
        laps = laps.loc[~pit_mask]

    return laps


def build_laps_dataframe(laps: pd.DataFrame) -> pd.DataFrame:
    """Return a compact lap table for analysis."""
    df = pd.DataFrame(
        {
            "LapNumber": laps["LapNumber"].astype(int),
            "LapTimeSeconds": laps["LapTime"].map(td_to_seconds),
            "Stint": laps.get("Stint", pd.Series([np.nan] * len(laps))),
            "Compound": laps.get("Compound", pd.Series([None] * len(laps))),
            "TyreLife": laps.get("TyreLife", pd.Series([np.nan] * len(laps))),
        }
    )
    df = df.dropna(subset=["LapTimeSeconds", "LapNumber"]).reset_index(drop=True)
    df["Stint"] = pd.to_numeric(df["Stint"], errors="coerce")
    df["TyreLife"] = pd.to_numeric(df["TyreLife"], errors="coerce")
    return df


def build_strategy_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Build stint summary dataframe per requirements."""
    g = df.dropna(subset=["Stint"]).groupby(["Stint", "Compound"], dropna=False)
    summary = g.agg(
        StintLength=("LapNumber", "count"),
        AveragePace=("LapTimeSeconds", "mean"),
        FastestLapInStint=("LapTimeSeconds", "min"),
        LapStart=("LapNumber", "min"),
        LapEnd=("LapNumber", "max"),
        PaceStd=("LapTimeSeconds", "std"),
    ).reset_index()

    summary = summary.sort_values("Stint").reset_index(drop=True)
    return summary


def estimate_degradation_slope(stint_df: pd.DataFrame) -> float:
    """
    Estimate degradation as seconds per lap using a simple linear fit:
      LapTimeSeconds = a * TyreLife + b

    If TyreLife isn't available, fallback to LapNumber within the stint.
    """
    x = stint_df["TyreLife"]
    if x.notna().sum() >= 5:
        x_vals = x.to_numpy(dtype=float)
        y_vals = stint_df["LapTimeSeconds"].to_numpy(dtype=float)
    else:
        x_vals = stint_df["LapNumber"].to_numpy(dtype=float)
        y_vals = stint_df["LapTimeSeconds"].to_numpy(dtype=float)

    if len(x_vals) < 5:
        return float("nan")

    a, _b = np.polyfit(x_vals, y_vals, deg=1)
    return float(a)


def simulate_pit_windows(df: pd.DataFrame, stint_summary: pd.DataFrame) -> list[PitWindow]:
    """
    Heuristic pit window logic:
      - Window: last ~25% of the stint (but at least 2 laps wide)
      - Recommended lap: where degradation crosses a small threshold, otherwise mid-window
      - Undercut potential: how much slower the lap is expected to be by end of window vs start
        using estimated degradation slope * window width.
    """
    windows: list[PitWindow] = []

    for _i, row in stint_summary.iterrows():
        stint = int(row["Stint"]) if not pd.isna(row["Stint"]) else None
        if stint is None:
            continue

        lap_start = int(row["LapStart"])
        lap_end = int(row["LapEnd"])
        compound = str(row["Compound"])

        stint_len = int(row["StintLength"])
        if stint_len < 6:
            continue

        window_width = max(int(round(stint_len * 0.25)), 2)
        start_lap = max(lap_end - window_width + 1, lap_start + 1)
        end_lap = lap_end

        stint_df = df[df["Stint"] == stint].sort_values("LapNumber")
        slope = estimate_degradation_slope(stint_df)

        # Pick a recommended lap:
        # If slope is meaningful, lean toward earlier pit within the window for higher degradation.
        if not np.isnan(slope):
            # Threshold: if degradation > 0.08s/lap, pit earlier in window.
            if slope > 0.08:
                recommended = start_lap
            elif slope > 0.04:
                recommended = int(round((start_lap + end_lap) / 2))
            else:
                recommended = end_lap
        else:
            recommended = int(round((start_lap + end_lap) / 2))

        estimated_undercut = float("nan")
        if not np.isnan(slope):
            estimated_undercut = max(0.0, slope * (end_lap - start_lap))

        windows.append(
            PitWindow(
                stint=stint,
                compound=compound,
                start_lap=start_lap,
                end_lap=end_lap,
                recommended_lap=recommended,
                degradation_s_per_lap=float(slope) if not np.isnan(slope) else float("nan"),
                estimated_undercut_s=float(estimated_undercut),
            )
        )

    return windows


def plot_stint_pace(stint_summary: pd.DataFrame) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(f"{DRIVER} — Stint Pace Comparison ({GRAND_PRIX} {YEAR} Race)")
    ax.set_xlabel("Stint")
    ax.set_ylabel("Average pace (s)")
    ax.grid(True, axis="y", alpha=0.25)

    x = stint_summary["Stint"].astype(int)
    y = stint_summary["AveragePace"]
    ax.bar(x, y, color=RB_BLUE, alpha=0.9, edgecolor="none")

    # annotate compounds
    for xi, yi, comp in zip(x, y, stint_summary["Compound"]):
        ax.text(xi, yi, f" {comp}", va="bottom", ha="left", fontsize=9, color=RB_YELLOW)

    plt.tight_layout()
    plt.show()


def plot_degradation_by_stint(df: pd.DataFrame, stint_summary: pd.DataFrame) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.set_title(f"{DRIVER} — Tyre Degradation by Stint ({GRAND_PRIX} {YEAR} Race)")
    ax.set_xlabel("Tyre Life (laps)  (fallback: Lap Number)")
    ax.set_ylabel("Lap time (s)")
    ax.grid(True, alpha=0.25)

    for _i, s in stint_summary.iterrows():
        if pd.isna(s["Stint"]):
            continue
        stint_no = int(s["Stint"])
        stint_df = df[df["Stint"] == stint_no].sort_values("LapNumber")
        if len(stint_df) < 4:
            continue

        x = stint_df["TyreLife"]
        if x.notna().sum() >= 4:
            x_vals = x
            x_label = "TyreLife"
        else:
            x_vals = stint_df["LapNumber"]
            x_label = "LapNumber"

        ax.plot(
            x_vals,
            stint_df["LapTimeSeconds"],
            marker="o",
            markersize=3,
            linewidth=1.5,
            alpha=0.85,
            label=f"Stint {stint_no} ({s['Compound']})",
        )
        ax.set_xlabel("Tyre Life (laps)  (fallback: Lap Number)" if x_label == "TyreLife" else "Lap Number")

    ax.legend(fontsize=9)
    plt.tight_layout()
    plt.show()


def plot_pit_windows(windows: list[PitWindow]) -> None:
    if not windows:
        return

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.set_title(f"{DRIVER} — Ideal Pit Windows (heuristic)")
    ax.set_xlabel("Lap Number")
    ax.set_yticks([w.stint for w in windows])
    ax.set_ylabel("Stint")
    ax.grid(True, axis="x", alpha=0.25)

    for w in windows:
        ax.hlines(
            y=w.stint,
            xmin=w.start_lap,
            xmax=w.end_lap,
            color=RB_BLUE,
            linewidth=10,
            alpha=0.6,
        )
        ax.vlines(
            x=w.recommended_lap,
            ymin=w.stint - 0.25,
            ymax=w.stint + 0.25,
            color=RB_YELLOW,
            linewidth=2,
        )
        ax.text(
            w.end_lap + 0.2,
            w.stint,
            f"{w.compound}",
            va="center",
            fontsize=9,
            color="white",
            alpha=0.9,
        )

    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    laps = session.laps.pick_drivers([DRIVER])
    laps = filter_laps(laps)
    df = build_laps_dataframe(laps)

    if df.empty:
        raise RuntimeError("No laps found after filtering.")

    stint_summary = build_strategy_dataframe(df)
    windows = simulate_pit_windows(df, stint_summary)

    print("Strategy dataframe (per stint):")
    print(
        stint_summary[
            ["Stint", "Compound", "StintLength", "AveragePace", "FastestLapInStint"]
        ].to_string(index=False)
    )

    # Best performing stint = lowest average pace
    best_stint_row = stint_summary.loc[stint_summary["AveragePace"].idxmin()]
    print("\nSummary:")
    print(
        f"- Best performing stint: Stint {int(best_stint_row['Stint'])} "
        f"({best_stint_row['Compound']}) at {best_stint_row['AveragePace']:.3f}s avg"
    )

    # Estimated optimal pit lap: pick the recommended lap from the first window with largest undercut
    optimal_pit_lap = None
    if windows:
        # Prefer windows with meaningful degradation; then the one with max estimated undercut
        ranked = sorted(
            windows,
            key=lambda w: (0 if np.isnan(w.degradation_s_per_lap) else 1, w.estimated_undercut_s),
            reverse=True,
        )
        optimal = ranked[0]
        optimal_pit_lap = optimal.recommended_lap
        print(f"- Estimated optimal pit lap (heuristic): Lap {optimal_pit_lap}")
    else:
        print("- Estimated optimal pit lap (heuristic): N/A")

    # Best pace consistency compound: lowest std dev of lap times for that compound
    compound_consistency = (
        df.groupby("Compound")["LapTimeSeconds"].std().dropna().sort_values()
    )
    if not compound_consistency.empty:
        best_compound = compound_consistency.index[0]
        print(
            f"- Tyre compound with best pace consistency: {best_compound} "
            f"(std={compound_consistency.iloc[0]:.3f}s)"
        )
    else:
        print("- Tyre compound with best pace consistency: N/A")

    # Plots
    plot_stint_pace(stint_summary)
    plot_degradation_by_stint(df, stint_summary)
    plot_pit_windows(windows)


if __name__ == "__main__":
    main()

