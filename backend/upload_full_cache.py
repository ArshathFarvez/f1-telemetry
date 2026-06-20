from pathlib import Path
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

TARGET_DRIVERS = {
    "VER",
    "RIC",
    "ALB",
    "PER",
    "LAW"
}

cache_root = Path("../telemetry-cache")

uploaded_sessions = 0
uploaded_points = 0


def parse_session_name(folder_name):

    if "Practice_1" in folder_name:
        return "FP1"

    if "Practice_2" in folder_name:
        return "FP2"

    if "Practice_3" in folder_name:
        return "FP3"

    if "Qualifying" in folder_name and "Sprint" not in folder_name:
        return "Q"

    if "Sprint_Qualifying" in folder_name:
        return "SQ"

    if "Sprint_Shootout" in folder_name:
        return "SQ"

    if "Sprint" in folder_name:
        return "S"

    if "Race" in folder_name:
        return "R"

    return None


for car_file in cache_root.rglob("car_data.ff1pkl"):

    try:

        session_folder = car_file.parent
        session_folder_name = session_folder.name

        race_folder = session_folder.parent
        race_folder_name = race_folder.name

        year_folder = race_folder.parent

        year = int(year_folder.name)

        session_code = parse_session_name(
            session_folder_name
        )

        if session_code is None:
            print(
                f"Skipping unknown session: "
                f"{session_folder_name}"
            )
            continue

        parts = race_folder_name.split("_")

        grand_prix = " ".join(parts[1:])

        print(
            f"\nLoading "
            f"{year} | "
            f"{grand_prix} | "
            f"{session_code}"
        )

        session = fastf1.get_session(
            year,
            grand_prix,
            session_code
        )

        session.load()

        available_drivers = set(
            session.laps["Driver"]
            .dropna()
            .unique()
        )

        drivers_to_upload = [
            d for d in TARGET_DRIVERS
            if d in available_drivers
        ]

        for driver in drivers_to_upload:

            laps = session.laps.pick_drivers(driver)

            if len(laps) == 0:
                continue

            fastest_lap = laps.pick_fastest()

            if fastest_lap is None:
                continue

            telemetry = (
                fastest_lap
                .get_car_data()
                .add_distance()
            )

            session_row = {
                "season": year,
                "grand_prix": grand_prix,
                "session": session_code,
                "driver_number": int(
                    fastest_lap["DriverNumber"]
                ),
                "driver_code": driver,
                "lap_number": int(
                    fastest_lap["LapNumber"]
                )
            }

            result = (
                supabase
                .table("telemetry_sessions")
                .insert(session_row)
                .execute()
            )

            session_id = result.data[0]["id"]

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
                    "drs": int(row["DRS"])
                })

            for i in range(0, len(rows), 500):

                batch = rows[i:i + 500]

                (
                    supabase
                    .table("telemetry_points")
                    .insert(batch)
                    .execute()
                )

            uploaded_sessions += 1
            uploaded_points += len(rows)

            print(
                f"✓ {driver} | "
                f"{len(rows)} points"
            )

    except Exception as e:

        print(
            f"Skipped: {car_file}"
        )

        print(e)

print("\n========================")
print(f"Sessions Uploaded: {uploaded_sessions}")
print(f"Points Uploaded: {uploaded_points}")
print("========================")