from pathlib import Path

cache = Path("../telemetry-cache")

sessions = 0

for file in cache.rglob("car_data.ff1pkl"):
    sessions += 1

print(f"Cached sessions found: {sessions}")