import fastf1
import os

from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# FastF1 Cache
fastf1.Cache.enable_cache("../telemetry-cache")

sessions = [
    (2026, "Monaco Grand Prix", "Qualifying"),
    (2026, "Monaco Grand Prix", "Race"),
    (2026, "Canada", "Qualifying"),
    (2026, "Canada", "Race"),
]

for season, gp, session_name in sessions:

    try:
        print(f"\n{'=' * 60}")
        print(f"Loading {season} | {gp} | {session_name}")
        print(f"{'=' * 60}")

        session = fastf1.get_session(
            season,
            gp,
            session_name
        )

        session.load()

        laps = session.laps.pick_drivers("VER")

        print(f"VER laps found: {len(laps)}")

        if len(laps) == 0:
            print("No laps found. Skipping.")
            continue

        fastest_lap = laps.pick_fastest()

        if fastest_lap is None:
            print("No fastest lap found. Skipping.")
            continue

        lap_number = int(fastest_lap["LapNumber"])

        print(f"Fastest lap number: {lap_number}")

        telemetry = fastest_lap.get_car_data().add_distance()

        if telemetry.empty:
            print("No telemetry data found. Skipping.")
            continue

        print(f"Telemetry points: {len(telemetry)}")

        # Create session record
        session_row = {
            "season": season,
            "grand_prix": gp,
            "session": session_name,
            "driver_number": 3,
            "driver_code": "VER",
            "lap_number": lap_number
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
                "x": None,
                "y": None,
                "lap_time": None,
                "sector": None
            })

        supabase.table("telemetry_points").insert(rows).execute()

        print(f"✅ Uploaded {len(rows)} telemetry points")

    except Exception as e:
        print(f"❌ Error processing {season} {gp} {session_name}")
        print(e)
        continue

print("\n🚀 Upload process completed.")