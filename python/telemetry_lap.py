import fastf1
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR    = PROJECT_ROOT / "telemetry-cache"

driver_number = sys.argv[1] if len(sys.argv) > 1 else "1"
year          = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
gp            = sys.argv[3]      if len(sys.argv) > 3 else "Monaco"
session_type  = sys.argv[4]      if len(sys.argv) > 4 else "Q"
lap_arg       = sys.argv[5]      if len(sys.argv) > 5 else "fastest"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))

session = fastf1.get_session(year, gp, session_type)
session.load()

driver_laps = session.laps.pick_drivers(driver_number)

def td_s(td):
    try:
        return round(float(td.total_seconds()), 3)
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

# Resolve which lap to use
if lap_arg == "fastest":
    lap = driver_laps.pick_fastest()
elif lap_arg == "last":
    lap = driver_laps.iloc[-1] if len(driver_laps) > 0 else driver_laps.pick_fastest()
else:
    lap_num = int(lap_arg)
    matching = driver_laps[driver_laps["LapNumber"] == lap_num]
    lap = matching.iloc[0] if len(matching) > 0 else driver_laps.pick_fastest()

# Telemetry
telemetry = lap.get_car_data().add_distance()

data = []
for _, row in telemetry.iterrows():
    data.append({
        "distance": round(float(row["Distance"]), 2),
        "speed":    int(row["Speed"]),
        "throttle": int(row["Throttle"]),
        "brake":    bool(row["Brake"]),
        "rpm":      int(row["RPM"]),
        "gear":     int(row["nGear"]),
    })

# Summary
top_speed   = max((r["speed"] for r in data), default=0)
avg_speed   = round(sum(r["speed"] for r in data) / len(data), 1) if data else 0
lap_num_out = int(lap["LapNumber"])

print(json.dumps({
    "driver":    driver_number,
    "lapNumber": lap_num_out,
    "lapTime":   fmt_lap(lap.get("LapTime")),
    "lapTimeS":  td_s(lap.get("LapTime")),
    "sector1S":  td_s(lap.get("Sector1Time")),
    "sector2S":  td_s(lap.get("Sector2Time")),
    "sector3S":  td_s(lap.get("Sector3Time")),
    "topSpeed":  top_speed,
    "avgSpeed":  avg_speed,
    "compound":  str(lap["Compound"]) if "Compound" in lap.index and lap["Compound"] else None,
    "points":    len(data),
    "data":      data,
}))
