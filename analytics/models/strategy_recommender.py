"""
Simple strategy recommender using a tyre degradation model (Linear Regression).

Session: 2024 Monaco Grand Prix — Race
Driver:  VER (Max Verstappen)

What this script does:
  - Loads race data via FastF1 (with local cache enabled)
  - Extracts lap times, stint/compound/tyre life, and pit stop laps
  - Trains a simple degradation model:
        LapTimeSeconds ~ TyreLife + Compound(one-hot)
  - Uses that model to:
        - project stint pace
        - estimate degradation slope (wear trend)
        - propose an "ideal" pit window and pit lap
        - recommend a next compound (from compounds actually used in the race)
  - Produces plots:
        - degradation prediction curve
        - projected race pace
        - pit strategy timeline
  - Prints an "AI recommendation" (rule + model based)

Notes:
  - This is intentionally beginner-readable and explainable; it is not a full
    race strategy optimizer (which would need traffic, SC/VSC, pit loss models,
    and competitor modelling).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fastf1
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


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
RB_GREY = "#9AA0A6"
RB_BG = "#0B0F1A"


@dataclass(frozen=True)
class Recommendation:
    pit_lap: int | None
    next_compound: str | None
    expected_stint_pace_seconds: float | None
    pit_window: tuple[int, int] | None
    notes: str


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
    """Best-effort: keep accurate laps and drop pit in/out laps for modelling."""
    if hasattr(laps, "pick_accurate"):
        laps = laps.pick_accurate()

    pit_cols = [c for c in ["PitInTime", "PitOutTime"] if c in laps.columns]
    if pit_cols:
        pit_mask = False
        for c in pit_cols:
            pit_mask = pit_mask | laps[c].notna()
        laps = laps.loc[~pit_mask]

    return laps


def extract_pit_laps(raw_laps: pd.DataFrame) -> list[int]:
    """Pit stop laps (best-effort) based on PitInTime/PitOutTime flags."""
    if "PitInTime" not in raw_laps.columns and "PitOutTime" not in raw_laps.columns:
        return []
    pit_mask = False
    if "PitInTime" in raw_laps.columns:
        pit_mask = pit_mask | raw_laps["PitInTime"].notna()
    if "PitOutTime" in raw_laps.columns:
        pit_mask = pit_mask | raw_laps["PitOutTime"].notna()
    pit_laps = raw_laps.loc[pit_mask, "LapNumber"].dropna().astype(int).tolist()
    return sorted(set(pit_laps))


def build_laps_df(laps: pd.DataFrame) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "LapNumber": laps["LapNumber"].astype(int),
            "LapTimeSeconds": laps["LapTime"].map(td_to_seconds),
            "Stint": pd.to_numeric(laps.get("Stint", np.nan), errors="coerce"),
            "Compound": laps.get("Compound", None),
            "TyreLife": pd.to_numeric(laps.get("TyreLife", np.nan), errors="coerce"),
        }
    )
    df = df.dropna(subset=["LapTimeSeconds", "LapNumber"])
    df = df.sort_values("LapNumber").reset_index(drop=True)
    return df


def build_stint_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.dropna(subset=["Stint"]).groupby(["Stint", "Compound"], dropna=False)
    summary = g.agg(
        StintLength=("LapNumber", "count"),
        AveragePace=("LapTimeSeconds", "mean"),
        FastestLap=("LapTimeSeconds", "min"),
        PaceStd=("LapTimeSeconds", "std"),
        LapStart=("LapNumber", "min"),
        LapEnd=("LapNumber", "max"),
        TyreLifeMax=("TyreLife", "max"),
    ).reset_index()
    return summary.sort_values("Stint").reset_index(drop=True)


def make_features(df: pd.DataFrame, compounds: list[str]) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Features:
      - TyreLife (numeric)
      - Compound one-hot (for observed compounds)
    """
    x_parts = [df["TyreLife"].ffill().fillna(0).to_numpy(dtype=float).reshape(-1, 1)]
    feature_names = ["TyreLife"]

    for c in compounds:
        x_parts.append((df["Compound"] == c).astype(int).to_numpy().reshape(-1, 1))
        feature_names.append(f"Compound_{c}")

    X = np.hstack(x_parts)
    y = df["LapTimeSeconds"].to_numpy(dtype=float)
    return X, y, feature_names


def train_degradation_model(df: pd.DataFrame) -> tuple[LinearRegression, list[str]]:
    compounds = sorted([c for c in df["Compound"].dropna().unique()])
    X, y, feature_names = make_features(df, compounds)
    model = LinearRegression()
    model.fit(X, y)
    return model, compounds


def predict_lap_time(model: LinearRegression, compounds: list[str], compound: str, tyre_life: np.ndarray) -> np.ndarray:
    tyre_life = np.asarray(tyre_life, dtype=float).reshape(-1, 1)
    one_hots = []
    for c in compounds:
        one_hots.append((np.full((len(tyre_life), 1), 1) if c == compound else np.zeros((len(tyre_life), 1))))
    X = np.hstack([tyre_life] + one_hots)
    return model.predict(X)


def estimate_pit_loss_seconds(raw_laps: pd.DataFrame, clean_df: pd.DataFrame) -> float:
    """
    Try to estimate pit loss from this driver's own data:
      pit_loss ≈ median(pit lap time) - median(non-pit lap time)
    If pit lap times aren't available, fallback to a conservative Monaco estimate.
    """
    pit_laps = extract_pit_laps(raw_laps)
    if not pit_laps:
        return 20.0

    pit_times = raw_laps.loc[raw_laps["LapNumber"].isin(pit_laps), "LapTime"].map(td_to_seconds).dropna()
    base_times = clean_df["LapTimeSeconds"].dropna()
    if pit_times.empty or base_times.empty:
        return 20.0

    pit_loss = float(np.median(pit_times) - np.median(base_times))
    # keep in a reasonable range
    return float(np.clip(pit_loss, 12.0, 30.0))


def pick_current_stint(df: pd.DataFrame) -> int | None:
    if df["Stint"].dropna().empty:
        return None
    return int(df["Stint"].dropna().iloc[-1])


def simulate_pit_window_and_next_compound(
    df: pd.DataFrame,
    raw_laps: pd.DataFrame,
    model: LinearRegression,
    compounds: list[str],
) -> Recommendation:
    """
    Heuristic recommendation:
      - Identify the last (current) stint and its compound.
      - Estimate degradation slope by predicting lap time at tyre life t and t+1.
      - Create a pit window in the last 25% of the stint (based on observed stint length).
      - Recommend pit lap where expected gain from fresh tyres exceeds a pit-loss threshold fraction.
      - Next compound: choose compound with best pace consistency historically + best predicted pace.
    """
    stint = pick_current_stint(df)
    if stint is None:
        return Recommendation(None, None, None, None, "No stint information available.")

    stint_df = df[df["Stint"] == stint].copy()
    if stint_df.empty:
        return Recommendation(None, None, None, None, "Could not locate laps for current stint.")

    compound_now = str(stint_df["Compound"].dropna().iloc[-1]) if not stint_df["Compound"].dropna().empty else None
    if compound_now is None:
        return Recommendation(None, None, None, None, "No compound info available for current stint.")

    pit_loss = estimate_pit_loss_seconds(raw_laps, df)

    # Pit window: last 25% of the stint, minimum 2 laps wide
    lap_start = int(stint_df["LapNumber"].min())
    lap_end = int(stint_df["LapNumber"].max())
    stint_len = int(len(stint_df))
    if stint_len < 6:
        return Recommendation(None, None, None, None, "Stint is too short for a meaningful pit window.")

    width = max(int(round(stint_len * 0.25)), 2)
    window_start = max(lap_end - width + 1, lap_start + 1)
    window_end = lap_end

    # Degradation estimate from model for this compound
    tyre_life_now = float(np.nanmax(stint_df["TyreLife"])) if stint_df["TyreLife"].notna().any() else float(stint_len)
    pred_now = float(predict_lap_time(model, compounds, compound_now, np.array([tyre_life_now]))[0])
    pred_next = float(predict_lap_time(model, compounds, compound_now, np.array([tyre_life_now + 1]))[0])
    degradation_s_per_lap = pred_next - pred_now

    # Next compound candidates = compounds observed for this driver
    used_compounds = sorted([c for c in df["Compound"].dropna().unique()])
    candidates = [c for c in used_compounds if c in compounds]
    if not candidates:
        candidates = compounds

    # Evaluate candidates at "fresh tyre" life and mid-stint life
    fresh_life = 1.0
    mid_life = 10.0
    candidate_scores = []
    for c in candidates:
        p_fresh = float(predict_lap_time(model, compounds, c, np.array([fresh_life]))[0])
        p_mid = float(predict_lap_time(model, compounds, c, np.array([mid_life]))[0])
        slope = (p_mid - p_fresh) / max(mid_life - fresh_life, 1.0)

        # Consistency from historical laps on that compound (lower std is better)
        comp_std = float(df.loc[df["Compound"] == c, "LapTimeSeconds"].std()) if (df["Compound"] == c).any() else float("nan")
        comp_std = comp_std if np.isfinite(comp_std) else 999.0

        # Lower is better: predicted pace + small penalty for wear slope + std
        score = p_mid + (slope * 5.0) + (comp_std * 0.25)
        candidate_scores.append((c, score, p_mid, comp_std, slope))

    candidate_scores.sort(key=lambda x: x[1])
    next_compound = candidate_scores[0][0]
    expected_pace = candidate_scores[0][2]

    # Choose a recommended pit lap within the window.
    # We pit earlier if degradation is steep; later if not.
    if degradation_s_per_lap > 0.10:
        recommended = window_start
        note = "High degradation detected; pit early in window."
    elif degradation_s_per_lap > 0.05:
        recommended = int(round((window_start + window_end) / 2))
        note = "Moderate degradation; pit mid-window."
    else:
        recommended = window_end
        note = "Low degradation; pit late in window."

    # Basic undercut check: if predicted lap time at end of window is much worse than fresh tyre,
    # it increases the attractiveness of pitting earlier.
    pred_end = float(predict_lap_time(model, compounds, compound_now, np.array([tyre_life_now + (window_end - window_start)]))[0])
    fresh_next = float(predict_lap_time(model, compounds, next_compound, np.array([fresh_life]))[0])
    undercut_potential = max(0.0, pred_end - fresh_next)

    note += f" Estimated pit loss ~{pit_loss:.1f}s, undercut potential ~{undercut_potential:.2f}s."

    return Recommendation(
        pit_lap=int(recommended),
        next_compound=str(next_compound),
        expected_stint_pace_seconds=float(expected_pace),
        pit_window=(int(window_start), int(window_end)),
        notes=note,
    )


def plot_degradation_curve(model: LinearRegression, compounds: list[str], used_compounds: list[str]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.set_title(f"Degradation Prediction Curve — {DRIVER} ({GRAND_PRIX} {YEAR} Race)")
    ax.set_xlabel("Tyre life (laps)")
    ax.set_ylabel("Predicted lap time (s)")
    ax.grid(True, alpha=0.25)

    tyre_life = np.arange(1, 31, 1)
    for c in used_compounds:
        y = predict_lap_time(model, compounds, c, tyre_life)
        ax.plot(tyre_life, y, linewidth=2, alpha=0.9, label=c, color=RB_BLUE if c == "HARD" else RB_YELLOW)

    ax.legend(title="Compound")
    plt.tight_layout()
    plt.show()


def plot_projected_race_pace(df: pd.DataFrame, model: LinearRegression, compounds: list[str]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.set_title(f"Projected vs Actual Race Pace — {DRIVER} ({GRAND_PRIX} {YEAR})")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap time (s)")
    ax.grid(True, alpha=0.25)

    ax.plot(df["LapNumber"], df["LapTimeSeconds"], color=RB_GREY, alpha=0.5, linewidth=1.5, label="Actual")

    # Project using model on existing laps (in-sample projection)
    pred = []
    for _, r in df.iterrows():
        comp = str(r["Compound"])
        life = float(r["TyreLife"]) if np.isfinite(r["TyreLife"]) else 0.0
        pred.append(float(predict_lap_time(model, compounds, comp, np.array([life]))[0]))

    ax.plot(df["LapNumber"], pred, color=RB_BLUE, alpha=0.9, linewidth=2, label="Model projection")
    ax.legend()
    plt.tight_layout()
    plt.show()


def plot_pit_strategy_timeline(stint_summary: pd.DataFrame, pit_laps: list[int], rec: Recommendation) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 3.5))
    ax.set_title(f"Pit Strategy Timeline — {DRIVER} ({GRAND_PRIX} {YEAR} Race)")
    ax.set_xlabel("Lap Number")
    ax.set_yticks([])
    ax.grid(True, axis="x", alpha=0.25)

    for _, s in stint_summary.iterrows():
        if pd.isna(s["Stint"]):
            continue
        y = 1
        ax.hlines(
            y=y,
            xmin=float(s["LapStart"]),
            xmax=float(s["LapEnd"]),
            color=RB_BLUE,
            linewidth=10,
            alpha=0.5,
        )
        ax.text(float(s["LapStart"]), 1.05, f"Stint {int(s['Stint'])} ({s['Compound']})", color="white", fontsize=9)

    for p in pit_laps:
        ax.axvline(p, color=RB_YELLOW, alpha=0.6, linewidth=2, label="Pit stop" if p == pit_laps[0] else None)

    if rec.pit_window is not None:
        ax.axvspan(rec.pit_window[0], rec.pit_window[1], color=RB_YELLOW, alpha=0.12, label="Recommended window")
    if rec.pit_lap is not None:
        ax.axvline(rec.pit_lap, color="white", alpha=0.9, linewidth=1.5, label="Recommended pit lap")

    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(loc="upper right")
    plt.tight_layout()
    plt.show()


def main() -> None:
    enable_cache()
    session = load_session()

    raw_laps = session.laps.pick_drivers([DRIVER])
    pit_laps = extract_pit_laps(raw_laps)

    laps = filter_laps(raw_laps)
    df = build_laps_df(laps)
    stint_summary = build_stint_summary(df)

    model, compounds = train_degradation_model(df.dropna(subset=["Compound"]))
    used_compounds = sorted([c for c in df["Compound"].dropna().unique() if c in compounds])

    rec = simulate_pit_window_and_next_compound(df, raw_laps, model, compounds)

    print("AI recommended strategy:")
    print(f"- Recommended pit lap: {rec.pit_lap if rec.pit_lap is not None else 'N/A'}")
    print(f"- Recommended next compound: {rec.next_compound or 'N/A'}")
    if rec.expected_stint_pace_seconds is not None:
        print(f"- Expected stint pace (model, mid-life): {rec.expected_stint_pace_seconds:.3f}s")
    else:
        print("- Expected stint pace: N/A")
    print(f"- Notes: {rec.notes}")

    # "Estimated fastest race strategy" (simple): pick the best stint by average pace
    best_stint = stint_summary.loc[stint_summary["AveragePace"].idxmin()]
    print("\nEstimated fastest race strategy (from observed stints):")
    print(
        f"- Best performing stint: Stint {int(best_stint['Stint'])} ({best_stint['Compound']}) "
        f"avg {best_stint['AveragePace']:.3f}s"
    )
    print(f"- Predicted optimal pit lap: {rec.pit_lap if rec.pit_lap is not None else 'N/A'}")

    # Plots
    plot_degradation_curve(model, compounds, used_compounds or compounds)
    plot_projected_race_pace(df, model, compounds)
    plot_pit_strategy_timeline(stint_summary, pit_laps, rec)


if __name__ == "__main__":
    main()

