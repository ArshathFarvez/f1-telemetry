"""
API entry point for driver comparison.
Imports the existing driver_comparison module, runs the analysis,
and emits a single JSON object to stdout for the Node.js controller.

Usage:
    python analytics/comparison/compare_api.py [--drivers VER LEC] [--year 2024] [--gp Monaco]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow sibling imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fastf1
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"


def td_to_seconds(td) -> float | None:
    if pd.isna(td):
        return None
    return round(float(td.total_seconds()), 3)


def format_td(td) -> str | None:
    if pd.isna(td):
        return None
    total_ms = int(td.total_seconds() * 1000)
    minutes, ms_rem = divmod(total_ms, 60_000)
    seconds, ms = divmod(ms_rem, 1000)
    return f"{minutes}:{seconds:02d}.{ms:03d}"


def run(year: int, gp: str, drivers: list[str], session_type: str = "Q") -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    session = fastf1.get_session(year, gp, session_type)
    session.load(telemetry=False, weather=False, messages=False)

    results = []
    for driver in drivers:
        laps = session.laps.pick_drivers([driver])
        fastest = laps.pick_fastest()
        if fastest is None:
            continue

        top_speed = None
        try:
            car_data = fastest.get_car_data()
            if car_data is not None and "Speed" in car_data.columns:
                top_speed = round(float(car_data["Speed"].max()), 1)
        except Exception:
            pass

        results.append({
            "driver":      str(fastest["Driver"]),
            "team":        str(fastest.get("Team", "")) or None,
            "lapTime":     format_td(fastest["LapTime"]),
            "lapTimeS":    td_to_seconds(fastest["LapTime"]),
            "sector1":     format_td(fastest.get("Sector1Time")),
            "sector1S":    td_to_seconds(fastest.get("Sector1Time")),
            "sector2":     format_td(fastest.get("Sector2Time")),
            "sector2S":    td_to_seconds(fastest.get("Sector2Time")),
            "sector3":     format_td(fastest.get("Sector3Time")),
            "sector3S":    td_to_seconds(fastest.get("Sector3Time")),
            "topSpeed":    top_speed,
        })

    results.sort(key=lambda r: r["lapTimeS"] or float("inf"))

    winner = results[0]["driver"] if results else None
    sector_winners = {}
    for s in ("sector1S", "sector2S", "sector3S"):
        valid = [r for r in results if r[s] is not None]
        if valid:
            sector_winners[s.replace("S", "")] = min(valid, key=lambda r: r[s])["driver"]

    return {
        "session":       {"year": year, "grandPrix": gp, "type": session_type},
        "drivers":       results,
        "overallWinner": winner,
        "sectorWinners": sector_winners,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--drivers", nargs="+", default=["VER", "LEC"])
    parser.add_argument("--year",    type=int,   default=2024)
    parser.add_argument("--gp",      type=str,   default="Monaco")
    parser.add_argument("--session", type=str,   default="Q")
    args = parser.parse_args()

    result = run(args.year, args.gp, args.drivers, args.session)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
