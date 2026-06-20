import fastf1
import os

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

fastf1.Cache.enable_cache("../telemetry-cache")

session = fastf1.get_session(
    2026,
    "Monaco Grand Prix",
    "Qualifying"
)

session.load()

laps = session.laps.pick_drivers("VER")

fastest_lap = laps.pick_fastest()

telemetry = fastest_lap.get_car_data().add_distance()

session_row = {
    "season": 2026,
    "grand_prix": "Monaco Grand Prix",
    "session": "Qualifying",
    "driver_number": 3,
    "driver_code": "VER",
    "lap_number": int(fastest_lap["LapNumber"])
}

session_result = (
    supabase
    .table("telemetry_sessions")
    .insert(session_row)
    .execute()
)

session_id = session_result.data[0]["id"]

rows = []

for _, row in telemetry.iterrows():

    rows.append({
        "session_id": session_id,
        "distance": float(row["Distance"]),
        "speed": float(row["Speed"]),
        "throttle": float(row["Throttle"]),
        "brake": bool(row["Brake"]),
        "gear": int(row["nGear"]),
        "rpm": int(row["RPM"]),
        "drs": int(row["DRS"]),
    })

supabase.table("telemetry_points").insert(rows).execute()

print(f"Uploaded {len(rows)} telemetry points")