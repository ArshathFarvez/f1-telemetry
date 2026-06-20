"""
API entry point for strategy simulation.
Reuses pace modelling and simulation logic from race_simulator.py,
emits a single JSON object to stdout.

Usage:
    python analytics/strategy/strategy_api.py [--driver VER] [--year 2024] [--gp Monaco]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fastf1
import numpy as np
import pandas as pd

# Import shared logic from the existing module
from race_simulator import (
    filter_valid_laps,
    build_lap_dataframe,
    build_pace_model,
    make_strategies,
    simulate_strategy,
    estimate_pit_windows,
    extract_pit_laps,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"


def _clean(value):
    """Recursively replace NaN/Inf with None for JSON serialisation."""
    if isinstance(value, float):
        return None if (math.isnan(value) or math.isinf(value)) else value
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


def run(year: int, gp: str, driver: str, session_type: str = "R") -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    raw_laps = session.laps.pick_drivers([driver])
    race_laps = int(raw_laps["LapNumber"].max())
    observed_pit_laps = extract_pit_laps(raw_laps)

    clean_laps = filter_valid_laps(raw_laps)
    clean_df = build_lap_dataframe(clean_laps)

    observed_compounds = sorted(clean_df["Compound"].dropna().unique().tolist())
    model = build_pace_model(raw_laps, clean_df)
    strategies = make_strategies(observed_compounds, race_laps)
    results = [simulate_strategy(s, model, race_laps) for s in strategies]

    best = min(results, key=lambda r: r.total_time_s)

    strategies_out = []
    for r in results:
        pit_windows = estimate_pit_windows(model, r.strategy, race_laps)
        # Lap table: keep only a summary (every 5th lap) to keep payload lean
        lap_table = r.lap_table[["LapNumber", "Stint", "Compound", "TyreLife",
                                  "PredLapTimeSeconds", "IsPitLap"]].copy()
        lap_table = lap_table[lap_table["LapNumber"] % 5 == 0].copy()

        strategies_out.append({
            "name":             r.strategy.name,
            "compounds":        r.strategy.compounds,
            "pitLaps":          r.strategy.pit_laps,
            "totalTimeS":       round(r.total_time_s, 3),
            "totalTimeMin":     round(r.total_time_s / 60, 2),
            "avgStintPaceS":    round(r.avg_stint_pace_s, 3),
            "tyreWearImpactS":  round(r.tyre_wear_impact_s, 3),
            "pitWindows":       [{"start": a, "end": b} for a, b in pit_windows],
            "lapTableSample":   lap_table.where(pd.notnull(lap_table), None).to_dict(orient="records"),
        })

    pace_model_out = {
        "pitLossS":              round(model.pit_loss_s, 3),
        "fuelEffectSPerLap":     round(model.fuel_effect_s_per_lap, 4),
        "basePaceByCompound":    {k: round(v, 3) for k, v in model.base_pace_by_compound.items()},
        "degradationByCompound": {k: round(v, 4) for k, v in model.degradation_s_per_lap_by_compound.items()},
    }

    best_compound = (
        min(model.degradation_s_per_lap_by_compound.items(), key=lambda kv: kv[1])[0]
        if model.degradation_s_per_lap_by_compound else None
    )

    return _clean({
        "session":              {"year": year, "grandPrix": gp, "type": session_type},
        "driver":               driver,
        "raceLaps":             race_laps,
        "observedPitLaps":      observed_pit_laps,
        "observedCompounds":    observed_compounds,
        "paceModel":            pace_model_out,
        "strategies":           strategies_out,
        "recommendation": {
            "fastestStrategy":       best.strategy.name,
            "projectedFinishTimeMin": round(best.total_time_s / 60, 2),
            "bestCompound":          best_compound,
        },
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--driver", type=str, default="VER")
    parser.add_argument("--year",   type=int, default=2024)
    parser.add_argument("--gp",     type=str, default="Monaco")
    parser.add_argument("--session", type=str, default="R")
    args = parser.parse_args()

    result = run(args.year, args.gp, args.driver, args.session)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
