import os
import fastf1
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

fastf1.Cache.enable_cache("../telemetry-cache")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Monaco 2026 Qualifying
session = fastf1.get_session(2026, "Monaco Grand Prix", "Q")
session.load()

# Verstappen laps
laps = session.laps.pick_drivers("VER")

# Choose fastest lap
lap = laps.pick_fastest()

telemetry = lap.get_car_data().add_distance()

# session row id from telemetry_sessions table
SESSION_ID = 2

rows = []

for _, row in telemetry.iterrows():

    rows.append({
        "session_id": SESSION_ID,
        "distance": float(row["Distance"]),
        "speed": float(row["Speed"]),
        "throttle": float(row["Throttle"]),
        "brake": bool(row["Brake"]),
        "gear": int(row["nGear"]),
        "rpm": int(row["RPM"]),
        "drs": int(row["DRS"])
    })

# Upload in chunks
CHUNK_SIZE = 500

for i in range(0, len(rows), CHUNK_SIZE):
    supabase.table("telemetry_points").insert(
        rows[i:i + CHUNK_SIZE]
    ).execute()

print(f"Uploaded {len(rows)} telemetry points")