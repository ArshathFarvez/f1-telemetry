"""
Race strategy simulator (simple + explainable).

Session: 2024 Monaco Grand Prix — Race
Driver:  VER

Goals:
  - Load FastF1 race lap data (with cache enabled)
  - Estimate simple pace components:
      - base compound pace
      - tyre degradation (seconds per lap of tyre life)
      - fuel effect (seconds per lap of race progression)
  - Simulate and compare multiple pit strategies (>= one-stop + two-stop)
  - Predict:
      - total race time
      - average stint pace
      - tyre wear impact
  - Visualize:
      - race pace timeline
      - tyre degradation projection
      - strategy comparison
      - cumulative race time

This is not a full F1 strategy model (no traffic/SC/track position). It is meant to
be engineering-grade, readable, and useful for quick "what-if" comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# =========================
# Configuration
# =========================
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "R"  # Race
DRIVER = "VER"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"

# Red Bull themed colors
RB_BLUE = "#1E5BC6"
RB_YELLOW = "#FCD700"
RB_GREY = "#9AA0A6"
RB_WHITE = "#FFFFFF"


# =========================
# Data structures
# =========================
@dataclass(frozen=True)
class Strategy:
    name: str
    compounds: list[str]  # compound per stint, in order
    pit_laps: list[int]  # pit lap numbers (end of stint), increasing


@dataclass(frozen=True)
class SimulationResult:
    strategy: Strategy
    lap_table: pd.DataFrame  # per lap prediction
    total_time_s: float
    avg_stint_pace_s: float
    tyre_wear_impact_s: float


@dataclass(frozen=True)
class PaceModel:
    base_pace_by_compound: dict[str, float]  # seconds
    degradation_s_per_lap_by_compound: dict[str, float]  # seconds / tyre-life lap
    fuel_effect_s_per_lap: float  # seconds / race lap (positive => slower later)
    pit_loss_s: float


# =========================
# Utilities
# =========================
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


# =========================
# Data loading
# =========================
def extract_pit_laps(raw_laps: pd.DataFrame) -> list[int]:
    """Pit stop laps (best-effort) based on PitInTime/PitOutTime flags."""
    if "PitInTime" not in raw_laps.columns and "PitOutTime" not in raw_laps.columns:
        return []

    mask = False
    if "PitInTime" in raw_laps.columns:
        mask = mask | raw_laps["PitInTime"].notna()
    if "PitOutTime" in raw_laps.columns:
        mask = mask | raw_laps["PitOutTime"].notna()

    pit_laps = sorted(set(raw_laps.loc[mask, "LapNumber"].dropna().astype(int).tolist()))
    # Many feeds can flag formation/start artifacts as pit out on lap 1–2.
    # Ignore those so "pit stops" represent actual in-race stops.
    return [p for p in pit_laps if p >= 3]


def filter_valid_laps(laps: pd.DataFrame) -> pd.DataFrame:
    """Keep accurate laps and drop pit in/out laps for modelling."""
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()

    pit_cols = [c for c in ["PitInTime", "PitOutTime"] if c in laps.columns]
    if pit_cols:
        pit_mask = False
        for c in pit_cols:
            pit_mask = pit_mask | laps[c].notna()
        laps = laps.loc[~pit_mask]

    return laps


def build_lap_dataframe(laps: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "LapNumber": laps["LapNumber"].astype(int),
            "LapTimeSeconds": laps["LapTime"].map(td_to_seconds),
            "Stint": pd.to_numeric(laps.get("Stint", np.nan), errors="coerce"),
            "Compound": laps.get("Compound", None),
            "TyreLife": pd.to_numeric(laps.get("TyreLife", np.nan), errors="coerce"),
        }
    )
    df = df.dropna(subset=["LapNumber", "LapTimeSeconds"]).sort_values("LapNumber").reset_index(drop=True)
    return df


# =========================
# Degradation + fuel modeling
# =========================
def estimate_pit_loss_seconds(raw_laps: pd.DataFrame, clean_df: pd.DataFrame) -> float:
    """
    Estimate pit loss from this driver's own data:
      pit_loss ≈ median(pit lap time) - median(non-pit lap time)
    Fallback to a reasonable Monaco estimate if pit lap timing isn't available.
    """
    pit_laps = extract_pit_laps(raw_laps)
    if not pit_laps:
        return 20.0

    pit_times = raw_laps.loc[raw_laps["LapNumber"].isin(pit_laps), "LapTime"].map(td_to_seconds).dropna()
    base_times = clean_df["LapTimeSeconds"].dropna()
    if pit_times.empty or base_times.empty:
        return 20.0

    pit_loss = float(np.median(pit_times) - np.median(base_times))
    return float(np.clip(pit_loss, 12.0, 30.0))


def estimate_base_pace_by_compound(df: pd.DataFrame) -> dict[str, float]:
    """
    Base pace per compound:
      Use the median of the fastest 30% laps on that compound (reduces traffic/outliers).
    """
    base = {}
    for comp in sorted(df["Compound"].dropna().unique()):
        comp_df = df[df["Compound"] == comp].copy()
        if comp_df.empty:
            continue
        comp_df = comp_df.sort_values("LapTimeSeconds")
        n = max(int(round(len(comp_df) * 0.30)), 3)
        base[comp] = float(comp_df.head(n)["LapTimeSeconds"].median())
    return base


def estimate_degradation_by_compound(df: pd.DataFrame) -> dict[str, float]:
    """
    Degradation per compound:
      Fit a simple linear slope of lap time vs tyre life for each compound.
    """
    slopes = {}
    for comp in sorted(df["Compound"].dropna().unique()):
        comp_df = df[(df["Compound"] == comp) & df["TyreLife"].notna()].copy()
        if len(comp_df) < 8:
            continue
        x = comp_df["TyreLife"].to_numpy(dtype=float)
        y = comp_df["LapTimeSeconds"].to_numpy(dtype=float)
        a, _b = np.polyfit(x, y, deg=1)
        # Degradation should not be negative (tyres don't "wear into" speed here).
        # Clip to a reasonable positive band to avoid noisy fits dominating.
        slopes[comp] = float(np.clip(a, 0.0, 0.30))
    return slopes


def estimate_fuel_effect(df: pd.DataFrame) -> float:
    """
    Fuel effect estimate (simple):
      We approximate how lap times change over the race independent of tyre life
      by looking at lap time vs lap number on the longest stint.

    If we can't estimate reliably, fallback to a small negative value:
      negative means slightly faster later due to lower fuel.
    """
    if df["Stint"].dropna().empty:
        return -0.03

    # Longest stint has the most data for a trend.
    stint_counts = df.dropna(subset=["Stint"]).groupby("Stint")["LapNumber"].count().sort_values(ascending=False)
    longest_stint = int(stint_counts.index[0])
    s = df[df["Stint"] == longest_stint].copy()
    if len(s) < 10:
        return -0.03

    # Remove the first 2 laps of the stint (often outliers: warmup/traffic)
    s = s.sort_values("LapNumber").iloc[2:].copy()
    if len(s) < 8:
        return -0.03

    x = s["LapNumber"].to_numpy(dtype=float)
    y = s["LapTimeSeconds"].to_numpy(dtype=float)
    a, _b = np.polyfit(x, y, deg=1)
    # Clip to a reasonable band for interpretability.
    return float(np.clip(a, -0.15, 0.15))


def build_pace_model(raw_laps: pd.DataFrame, clean_df: pd.DataFrame) -> PaceModel:
    base = estimate_base_pace_by_compound(clean_df)
    deg = estimate_degradation_by_compound(clean_df)
    fuel = estimate_fuel_effect(clean_df)
    pit_loss = estimate_pit_loss_seconds(raw_laps, clean_df)

    # Ensure compounds found in base have a degradation entry (default small)
    for comp in base.keys():
        deg.setdefault(comp, 0.03)

    return PaceModel(
        base_pace_by_compound=base,
        degradation_s_per_lap_by_compound=deg,
        fuel_effect_s_per_lap=fuel,
        pit_loss_s=pit_loss,
    )


# =========================
# Strategy simulation
# =========================
def make_strategies(observed_compounds: list[str], race_laps: int) -> list[Strategy]:
    """
    Build at least one 1-stop and one 2-stop strategy.
    We try to keep the compounds realistic by using observed compounds for this driver.
    """
    # If only one compound observed, still create variants using it.
    if not observed_compounds:
        observed_compounds = ["HARD"]

    # Prefer common Monaco patterns: Medium->Hard (1 stop), Medium->Hard->Hard (2 stop)
    one_stop_compounds = []
    if "MEDIUM" in observed_compounds and "HARD" in observed_compounds:
        one_stop_compounds = ["MEDIUM", "HARD"]
    else:
        one_stop_compounds = [observed_compounds[0], observed_compounds[-1]]

    # Simple default windows (can be refined by model):
    one_stop_pit = int(round(race_laps * 0.65))

    # Two-stop (split race into 3 stints)
    two_stop_compounds = []
    if "MEDIUM" in observed_compounds and "HARD" in observed_compounds:
        two_stop_compounds = ["MEDIUM", "HARD", "HARD"]
    else:
        two_stop_compounds = [observed_compounds[0], observed_compounds[-1], observed_compounds[-1]]

    pit1 = int(round(race_laps * 0.40))
    pit2 = int(round(race_laps * 0.72))

    return [
        Strategy(name="One-stop", compounds=one_stop_compounds, pit_laps=[one_stop_pit]),
        Strategy(name="Two-stop", compounds=two_stop_compounds, pit_laps=[pit1, pit2]),
    ]


def simulate_strategy(strategy: Strategy, model: PaceModel, race_laps: int) -> SimulationResult:
    """
    Simulate a race by generating lap time predictions for each lap:
      lap_time = base(compound) + degradation(compound)*tyre_life + fuel_effect*lap_number
    Add pit loss on pit laps.
    """
    base = model.base_pace_by_compound
    deg = model.degradation_s_per_lap_by_compound

    # Build stint boundaries from pit laps
    pits = [p for p in strategy.pit_laps if 1 <= p < race_laps]
    pits = sorted(pits)
    boundaries = [0] + pits + [race_laps]

    rows = []
    total_time = 0.0
    tyre_wear_impact = 0.0
    stint_paces = []

    for stint_idx in range(len(boundaries) - 1):
        stint_start = boundaries[stint_idx] + 1
        stint_end = boundaries[stint_idx + 1]
        compound = strategy.compounds[min(stint_idx, len(strategy.compounds) - 1)]

        base_pace = base.get(compound, float(np.nan))
        if not np.isfinite(base_pace):
            # fallback: use overall median base pace if unknown
            base_pace = float(np.nanmedian(list(base.values()))) if base else 80.0

        d = deg.get(compound, 0.03)

        lap_times = []
        for lap in range(stint_start, stint_end + 1):
            tyre_life = lap - stint_start + 1
            fuel_term = model.fuel_effect_s_per_lap * lap
            wear_term = d * tyre_life
            pred = base_pace + fuel_term + wear_term

            # Apply pit loss at the end-of-stint pit lap (except final boundary)
            if lap in pits:
                pred += model.pit_loss_s

            rows.append(
                {
                    "Strategy": strategy.name,
                    "LapNumber": lap,
                    "Stint": stint_idx + 1,
                    "Compound": compound,
                    "TyreLife": tyre_life,
                    "PredLapTimeSeconds": pred,
                    "FuelTermSeconds": fuel_term,
                    "WearTermSeconds": wear_term,
                    "IsPitLap": lap in pits,
                }
            )
            total_time += pred
            tyre_wear_impact += wear_term
            lap_times.append(pred)

        stint_paces.append(float(np.mean(lap_times)))

    lap_table = pd.DataFrame(rows)
    avg_stint_pace = float(np.mean(stint_paces)) if stint_paces else float("nan")

    return SimulationResult(
        strategy=strategy,
        lap_table=lap_table,
        total_time_s=float(total_time),
        avg_stint_pace_s=float(avg_stint_pace),
        tyre_wear_impact_s=float(tyre_wear_impact),
    )


def estimate_pit_windows(model: PaceModel, strategy: Strategy, race_laps: int) -> list[tuple[int, int]]:
    """
    Simple pit window suggestion:
      center on strategy's pit lap, allow +/- 3 laps, and clamp to race bounds.
    """
    windows = []
    for p in strategy.pit_laps:
        windows.append((max(2, p - 3), min(race_laps - 1, p + 3)))
    return windows


# =========================
# Visualization
# =========================
def plot_race_pace_timeline(results: list[SimulationResult]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title(f"Race Pace Timeline (Simulated) — {DRIVER} ({GRAND_PRIX} {YEAR})")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Predicted lap time (s)")
    ax.grid(True, alpha=0.25)

    colors = [RB_BLUE, RB_YELLOW]
    for i, r in enumerate(results):
        df = r.lap_table
        ax.plot(df["LapNumber"], df["PredLapTimeSeconds"], linewidth=2, alpha=0.9, color=colors[i % len(colors)], label=r.strategy.name)

        # mark pit laps
        pit_laps = df.loc[df["IsPitLap"], "LapNumber"].tolist()
        for p in pit_laps:
            ax.axvline(p, color=RB_GREY, alpha=0.35, linewidth=1)

    ax.legend()
    plt.tight_layout()
    plt.show()


def plot_degradation_projection(results: list[SimulationResult]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title("Tyre Degradation Projection by Stint")
    ax.set_xlabel("Tyre life (laps)")
    ax.set_ylabel("Predicted lap time (s)")
    ax.grid(True, alpha=0.25)

    for r in results:
        df = r.lap_table
        for stint in sorted(df["Stint"].unique()):
            s = df[df["Stint"] == stint]
            ax.plot(
                s["TyreLife"],
                s["PredLapTimeSeconds"],
                linewidth=1.8,
                alpha=0.75,
                label=f"{r.strategy.name} - Stint {stint} ({s['Compound'].iloc[0]})",
            )

    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.show()


def plot_strategy_comparison(results: list[SimulationResult]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.set_title("Strategy Comparison (Total Race Time)")
    ax.set_ylabel("Total time (minutes)")
    ax.grid(True, axis="y", alpha=0.25)

    names = [r.strategy.name for r in results]
    totals_min = [r.total_time_s / 60.0 for r in results]
    colors = [RB_BLUE, RB_YELLOW][: len(results)]

    ax.bar(names, totals_min, color=colors, alpha=0.9, edgecolor="none")
    for n, t in zip(names, totals_min):
        ax.text(n, t, f"{t:.1f}", ha="center", va="bottom", color=RB_WHITE, fontsize=10)

    plt.tight_layout()
    plt.show()


def plot_cumulative_race_time(results: list[SimulationResult]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title("Cumulative Race Time (Simulated)")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Cumulative time (minutes)")
    ax.grid(True, alpha=0.25)

    colors = [RB_BLUE, RB_YELLOW]
    for i, r in enumerate(results):
        df = r.lap_table.copy()
        df["CumulativeMinutes"] = df["PredLapTimeSeconds"].cumsum() / 60.0
        ax.plot(df["LapNumber"], df["CumulativeMinutes"], linewidth=2.2, alpha=0.9, color=colors[i % len(colors)], label=r.strategy.name)

    ax.legend()
    plt.tight_layout()
    plt.show()


# =========================
# Printing / reporting
# =========================
def print_summary(model: PaceModel, results: list[SimulationResult], race_laps: int) -> None:
    fastest = min(results, key=lambda r: r.total_time_s)

    print("Pace model:")
    print(f"- Pit loss estimate: {model.pit_loss_s:.1f}s")
    print(f"- Fuel effect estimate: {model.fuel_effect_s_per_lap:+.3f}s/lap  (negative = faster later)")
    print("- Base pace by compound (s):")
    for k, v in model.base_pace_by_compound.items():
        print(f"  - {k}: {v:.3f}")
    print("- Degradation by compound (s/tyre-lap):")
    for k, v in model.degradation_s_per_lap_by_compound.items():
        print(f"  - {k}: {v:+.3f}")

    print("\nSimulation results:")
    for r in results:
        print(
            f"- {r.strategy.name}: total={r.total_time_s/60:.2f} min, "
            f"avg_stint_pace={r.avg_stint_pace_s:.3f}s, tyre_wear_impact={r.tyre_wear_impact_s:.1f}s"
        )

    print("\nRecommendation:")
    print(f"- Fastest simulated strategy: {fastest.strategy.name}")
    print(f"- Projected race finish time: {fastest.total_time_s/60:.2f} minutes")

    windows = estimate_pit_windows(model, fastest.strategy, race_laps)
    if windows:
        print("- Estimated optimal pit windows:")
        for i, (a, b) in enumerate(windows, start=1):
            print(f"  - Stop {i}: laps {a}–{b}")
    else:
        print("- Estimated optimal pit windows: N/A")

    # Compound effectiveness: choose compound with best consistency in the model (lowest degradation)
    if model.degradation_s_per_lap_by_compound:
        best_comp = min(model.degradation_s_per_lap_by_compound.items(), key=lambda kv: kv[1])[0]
        print(f"- Tyre compound effectiveness (lowest degradation): {best_comp}")


# =========================
# Main
# =========================
def main() -> None:
    enable_cache()
    session = load_session()

    raw_laps = session.laps.pick_drivers([DRIVER])
    race_laps = int(raw_laps["LapNumber"].max())

    pit_laps = extract_pit_laps(raw_laps)

    clean_laps = filter_valid_laps(raw_laps)
    clean_df = build_lap_dataframe(clean_laps)

    observed_compounds = sorted([c for c in clean_df["Compound"].dropna().unique()])
    model = build_pace_model(raw_laps, clean_df)

    strategies = make_strategies(observed_compounds, race_laps)
    results = [simulate_strategy(s, model, race_laps) for s in strategies]

    print(f"Driver: {DRIVER}")
    print(f"Race laps: {race_laps}")
    print(f"Observed pit stop laps (from data): {pit_laps if pit_laps else 'None detected'}\n")

    print_summary(model, results, race_laps)

    # Dashboard plots
    plot_race_pace_timeline(results)
    plot_degradation_projection(results)
    plot_strategy_comparison(results)
    plot_cumulative_race_time(results)


if __name__ == "__main__":
    main()

