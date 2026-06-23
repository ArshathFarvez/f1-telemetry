import fastf1
import json
import sys

# --------------------------------------------------
# INPUTS
# argv:
# [1] driver
# [2] year
# [3] grand prix
# [4] session
# --------------------------------------------------

driver_number = sys.argv[1] if len(sys.argv) > 1 else "1"
year = int(sys.argv[2]) if len(sys.argv) > 2 else 2024
gp = sys.argv[3] if len(sys.argv) > 3 else "Monaco"
session_type = sys.argv[4] if len(sys.argv) > 4 else "Q"

try:
    print(
        f"[telemetry.py] Loading session: {year} {gp} {session_type} Driver={driver_number}",
        file=sys.stderr
    )

    # --------------------------------------------------
    # LOAD SESSION
    # --------------------------------------------------

    session = fastf1.get_session(year, gp, session_type)
    session.load()

    print(
        f"[telemetry.py] Session loaded successfully",
        file=sys.stderr
    )

    # --------------------------------------------------
    # DEBUG AVAILABLE DRIVERS
    # --------------------------------------------------

    try:
        available_drivers = session.drivers
        print(
            f"[telemetry.py] Available drivers: {available_drivers}",
            file=sys.stderr
        )
    except Exception as e:
        print(
            f"[telemetry.py] Driver list error: {str(e)}",
            file=sys.stderr
        )

    # --------------------------------------------------
    # GET DRIVER LAPS
    # --------------------------------------------------

    driver_laps = session.laps.pick_drivers(driver_number)

    if driver_laps.empty:
        print(
            f"[telemetry.py] No laps found for driver {driver_number}",
            file=sys.stderr
        )

        print(json.dumps({
            "success": False,
            "error": f"No laps found for driver {driver_number}",
            "driver": driver_number,
            "year": year,
            "gp": gp,
            "session": session_type
        }))
        sys.exit(0)

    print(
        f"[telemetry.py] Found {len(driver_laps)} laps",
        file=sys.stderr
    )

    # --------------------------------------------------
    # FASTEST LAP
    # --------------------------------------------------

    fastest_lap = driver_laps.pick_fastest()

    if fastest_lap is None:
        print(
            f"[telemetry.py] No fastest lap found",
            file=sys.stderr
        )

        print(json.dumps({
            "success": False,
            "error": "No fastest lap found"
        }))
        sys.exit(0)

    # --------------------------------------------------
    # TELEMETRY
    # --------------------------------------------------

    telemetry = fastest_lap.get_car_data().add_distance()

    if telemetry.empty:
        print(
            f"[telemetry.py] Telemetry data is empty",
            file=sys.stderr
        )

        print(json.dumps({
            "success": False,
            "error": "Telemetry data empty"
        }))
        sys.exit(0)

    # --------------------------------------------------
    # CONVERT TO JSON
    # --------------------------------------------------

    data = []

    for _, row in telemetry.iterrows():

        try:
            data.append({
                "distance": round(float(row["Distance"]), 2),
                "speed": int(row["Speed"]),
                "throttle": int(row["Throttle"]),
                "brake": bool(row["Brake"]),
                "rpm": int(row["RPM"]),
                "gear": int(row["nGear"])
            })

        except Exception:
            continue

    print(
        f"[telemetry.py] Returning {len(data)} telemetry rows",
        file=sys.stderr
    )

    print(json.dumps(data))

except Exception as e:

    print(
        f"[telemetry.py] ERROR: {str(e)}",
        file=sys.stderr
    )

    print(json.dumps({
        "success": False,
        "error": str(e)
    }))