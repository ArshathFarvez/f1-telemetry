import fastf1
import json
import sys

# -----------------------------
# INPUTS — all from Node.js args
# argv: driver year gp session
# -----------------------------
driver_number = sys.argv[1] if len(sys.argv) > 1 else "1"
year          = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
gp            = sys.argv[3]      if len(sys.argv) > 3 else "Monaco"
session_type  = sys.argv[4]      if len(sys.argv) > 4 else "Q"

# -----------------------------
# LOAD SESSION
# -----------------------------
session = fastf1.get_session(year, gp, session_type)
session.load()

# -----------------------------
# GET DRIVER LAP
# -----------------------------
driver_laps = session.laps.pick_drivers(driver_number)

fastest_lap = driver_laps.pick_fastest()

telemetry = fastest_lap.get_car_data().add_distance()

# -----------------------------
# CONVERT TO JSON
# -----------------------------
data = []

for _, row in telemetry.iterrows():
    data.append({
        "distance": round(float(row["Distance"]), 2),
        "speed": int(row["Speed"]),
        "throttle": int(row["Throttle"]),
        "brake": bool(row["Brake"]),
        "rpm": int(row["RPM"]),
        "gear": int(row["nGear"])
    })

# -----------------------------
# OUTPUT JSON
# -----------------------------
print(json.dumps(data))