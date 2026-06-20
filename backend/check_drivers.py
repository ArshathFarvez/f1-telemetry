import fastf1

fastf1.Cache.enable_cache("../telemetry-cache")

sessions = [
    (2018, "Monaco Grand Prix", "Qualifying"),
    (2020, "Monaco Grand Prix", "Qualifying"),
    (2022, "Monaco Grand Prix", "Qualifying"),
    (2024, "Monaco Grand Prix", "Qualifying"),
    (2026, "Monaco Grand Prix", "Qualifying"),
]

for year, gp, session_name in sessions:
    try:
        session = fastf1.get_session(year, gp, session_name)
        session.load()

        drivers = sorted(session.laps["Driver"].dropna().unique())

        print(f"\n{year}")
        print(drivers)

    except Exception as e:
        print(f"{year} -> {e}")