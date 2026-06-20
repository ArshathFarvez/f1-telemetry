import fastf1

print("Loading Monaco 2024 Qualifying session...")

session = fastf1.get_session(2024, "Monaco", "Q")
session.load()

print("\nDrivers & Teams:\n")

print(
    session.results[
        ["Abbreviation", "FullName", "TeamName"]
    ]
)