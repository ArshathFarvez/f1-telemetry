"""
Load a FastF1 session for the F1 Pitwall analytics pipeline.

Example session: 2024 Monaco Grand Prix — Qualifying
"""

from pathlib import Path

import fastf1

# Paths (project root is two levels above this file)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "telemetry-cache"

# Session settings
YEAR = 2024
GRAND_PRIX = "Monaco"
SESSION_TYPE = "Q"  # Qualifying


def load_session():
    """Enable cache, load the session, and return the session object."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    print("Loading session (this may take a moment on first run)...")
    session = fastf1.get_session(YEAR, GRAND_PRIX, SESSION_TYPE)
    session.load()
    return session


def print_session_summary(session):
    """Print basic information about the loaded session."""
    event_name = session.event["EventName"]
    session_name = session.name
    driver_numbers = session.drivers

    print("\nSession loaded successfully.")
    print(f"Event:   {event_name}")
    print(f"Session: {session_name}")
    print(f"Number of drivers: {len(driver_numbers)}")

    print("\nDrivers:")
    for number in driver_numbers:
        driver = session.get_driver(number)
        abbreviation = driver["Abbreviation"]
        full_name = driver["FullName"]
        print(f"  {number} - {abbreviation} ({full_name})")


def main():
    session = load_session()
    print_session_summary(session)


if __name__ == "__main__":
    main()
