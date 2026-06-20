import os
import fastf1
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

fastf1.Cache.enable_cache("../telemetry-cache")

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

YEAR = 2026
GP = "Monaco Grand Prix"
SESSION = "Q"

session = fastf1.get_session(YEAR, GP, SESSION)
session.load()

verstappen = session.laps.pick_drivers("VER")

driver_number = 3

for _, lap in verstappen.iterrows():

    row = {
        "season": YEAR,
        "grand_prix": GP,
        "session": "Qualifying",
        "driver_number": driver_number,
        "driver_code": "VER",
        "lap_number": int(lap["LapNumber"])
    }

    supabase.table("telemetry_sessions").insert(row).execute()

print(f"Uploaded {len(verstappen)} laps")