import fastf1
import json
import sys

year = int(sys.argv[1]) if len(sys.argv) > 1 else 2024

schedule = fastf1.get_event_schedule(year, include_testing=False)

gps = schedule["EventName"].tolist()

print(json.dumps(gps))
