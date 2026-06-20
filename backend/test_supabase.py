from supabase import create_client
from dotenv import load_dotenv
import os

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(url, key)

result = supabase.table("telemetry_sessions").select("*").execute()

print("✅ Connected Successfully")
print(result.data)