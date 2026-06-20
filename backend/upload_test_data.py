from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

data = {
    "season": 2026,
    "grand_prix": "Canada",
    "session": "Race",
    "driver_number": 3,
    "driver_code": "VER",
    "lap_number": 1
}

result = supabase.table("telemetry_sessions").insert(data).execute()

print("Upload Success")
print(result.data)