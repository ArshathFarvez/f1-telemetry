"""
scripts/build_cache.py

Download and cache Max Verstappen (VER) telemetry for every available
event across 2018–2026 into the local telemetry-cache directory.

Usage:
    python scripts/build_cache.py [--year YEAR] [--dry-run]

Options:
    --year YEAR   Only process a single year (e.g. --year 2024)
    --dry-run     Print what would be fetched without downloading anything

Run time estimate:  6–14 hours for a full 2018–2026 run (network dependent)
Cache size estimate: 8–15 GB
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import fastf1
from fastf1.exceptions import DataNotLoadedError

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR    = PROJECT_ROOT / "telemetry-cache"
LOG_FILE     = PROJECT_ROOT / "scripts" / "build_cache.log"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

YEARS = range(2018, 2027)

# Sessions to attempt per event. FastF1 will raise an error for sessions that
# don't exist (e.g. SQ/S only appear in sprint weekends) — those are skipped.
SESSION_IDENTIFIERS = ["FP1", "FP2", "FP3", "SQ", "S", "Q", "R"]

DRIVER = "VER"

# Seconds to wait between session loads to avoid hammering the API.
INTER_SESSION_DELAY = 2

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log(msg: str, file=None):
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    if file:
        file.write(line + "\n")
        file.flush()

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

def build_year(year: int, dry_run: bool, log_file) -> dict:
    """Process all events for a single year. Returns summary counts."""
    counts = {"ok": 0, "skipped": 0, "error": 0}

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as exc:
        log(f"  ERROR fetching schedule for {year}: {exc}", log_file)
        counts["error"] += 1
        return counts

    events = schedule["EventName"].tolist()
    log(f"\n=== {year} — {len(events)} events ===", log_file)

    for event_name in events:
        for session_id in SESSION_IDENTIFIERS:
            label = f"{year} | {event_name:<35} | {session_id}"

            if dry_run:
                log(f"  DRY-RUN  {label}", log_file)
                counts["skipped"] += 1
                continue

            try:
                try:
                    session = fastf1.get_session(year, event_name, session_id)
                except ValueError:
                    log(f"  SKIP     {label}  (session not available)", log_file)
                    counts["skipped"] += 1
                    continue

                # load() fetches and caches: laps, car_data, position, weather, etc.
                session.load(
                    laps=True,
                    telemetry=True,
                    weather=True,
                    messages=False,   # not needed for telemetry analysis
                )

                # Verify VER was actually in this session
                if DRIVER not in session.drivers:
                    log(f"  SKIP     {label}  (VER not in session)", log_file)
                    counts["skipped"] += 1
                    continue

                log(f"  OK       {label}", log_file)
                counts["ok"] += 1

            except DataNotLoadedError:
                log(f"  SKIP     {label}  (no data)", log_file)
                counts["skipped"] += 1

            except Exception as exc:
                # Broad catch: e.g. network errors or F1 API changes between seasons.
                short = str(exc).split("\n")[0][:120]
                log(f"  ERROR    {label}  — {short}", log_file)
                counts["error"] += 1

            finally:
                time.sleep(INTER_SESSION_DELAY)

    return counts


def main():
    parser = argparse.ArgumentParser(description="Build VER telemetry cache 2018–2026")
    parser.add_argument("--year", type=int, default=None,
                        help="Restrict to a single year")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be fetched without downloading")
    args = parser.parse_args()

    # Setup
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    years = [args.year] if args.year else list(YEARS)

    mode = "DRY-RUN" if args.dry_run else "LIVE"
    
    with open(LOG_FILE, "a", encoding="utf-8") as lf:
        log(f"\n{'='*60}", lf)
        log(f"build_cache.py  mode={mode}  driver={DRIVER}  years={years}", lf)
        log(f"cache_dir={CACHE_DIR}", lf)
        log(f"{'='*60}", lf)

        total   = {"ok": 0, "skipped": 0, "error": 0}
        t_start = time.time()

        for year in years:
            counts = build_year(year, args.dry_run, lf)
            for k in total:
                total[k] += counts[k]

        elapsed = time.time() - t_start
        log(f"\n{'='*60}", lf)
        log(f"Done in {elapsed/60:.1f} min  |  "
            f"ok={total['ok']}  skipped={total['skipped']}  errors={total['error']}", lf)
        log(f"{'='*60}\n", lf)

    return 0 if total["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
