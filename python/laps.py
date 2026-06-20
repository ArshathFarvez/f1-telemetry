import fastf1
import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR    = PROJECT_ROOT / "telemetry-cache"

driver_number = sys.argv[1] if len(sys.argv) > 1 else "1"
year          = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
gp            = sys.argv[3]      if len(sys.argv) > 3 else "Monaco"
session_type  = sys.argv[4]      if len(sys.argv) > 4 else "Q"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

session = fastf1.get_session(year, gp, session_type)
session.load(telemetry=False, weather=False, messages=False)

driver_laps = session.laps.pick_drivers(driver_number)

def td_s(td):
    try:
        val = round(float(td.total_seconds()), 3)
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    except Exception:
        return None

def fmt_lap(td):
    try:
        total_ms = int(td.total_seconds() * 1000)
        m, rest  = divmod(total_ms, 60_000)
        s, ms    = divmod(rest, 1000)
        return f"{m}:{s:02d}.{ms:03d}"
    except Exception:
        return None

laps_out = []
fastest  = driver_laps.pick_fastest()
fastest_num = int(fastest["LapNumber"]) if fastest is not None else None

for _, row in driver_laps.iterrows():
    lap_num = int(row["LapNumber"])
    lt_s    = td_s(row.get("LapTime"))
    laps_out.append({
        "lapNumber":    lap_num,
        "lapTime":      fmt_lap(row.get("LapTime")),
        "lapTimeS":     lt_s,
        "sector1S":     td_s(row.get("Sector1Time")),
        "sector2S":     td_s(row.get("Sector2Time")),
        "sector3S":     td_s(row.get("Sector3Time")),
        "compound":     str(row["Compound"]) if "Compound" in row.index and row["Compound"] else None,
        "isFastest":    lap_num == fastest_num,
    })

laps_out.sort(key=lambda r: r["lapNumber"])

print(json.dumps({
    "driver":     driver_number,
    "year":       year,
    "grandPrix":  gp,
    "session":    session_type,
    "fastestLap": fastest_num,
    "laps":       laps_out,
}))
