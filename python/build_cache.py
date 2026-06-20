"""
python/build_cache.py

Download and cache Max Verstappen telemetry for every available event
across 2018-2026 into the existing local telemetry-cache directory.

Driver number mapping:
  2018-2021  ->  33
  2022-2025  ->   1
  2026       ->   3

Sessions attempted per event (unavailable ones are silently skipped):
  FP1, FP2, FP3,
  Sprint Qualifying, Sprint Shootout, Sprint,
  Qualifying, Race

Usage:
    python python/build_cache.py                  # full 2018-2026 run
    python python/build_cache.py --year 2024      # single year
    python python/build_cache.py --dry-run        # print plan, no downloads

Estimated runtime : 8-16 hours (full run, network-dependent)
Estimated cache   : 10-20 GB
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import fastf1

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR    = PROJECT_ROOT / "telemetry-cache"

DRIVER_BY_YEAR = {
    2018: "33", 2019: "33", 2020: "33", 2021: "33",
    2022: "1",  2023: "1",  2024: "1",  2025: "1",
    2026: "3",
}

# Ordered list tried per event. FastF1 raises if a session doesn't exist for
# that weekend format (e.g. Sprint sessions on standard weekends) — skipped.
SESSIONS = [
    "FP1",
    "FP2",
    "FP3",
    "Sprint Qualifying",   # 2023+  sprint shootout branding
    "Sprint Shootout",     # alternate naming used by FastF1
    "Sprint",
    "Qualifying",
    "Race",
]

DELAY_BETWEEN_SESSIONS = 2   # seconds — avoids hammering the F1 timing API

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg, fh=None):
    line = f"[{_ts()}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + "\n")
        fh.flush()

# ---------------------------------------------------------------------------
# Per-session loader
# ---------------------------------------------------------------------------

def load_one(year, event_name, session_id, driver_number, dry_run, fh):
    """
    Attempt to load one session.
    Returns "ok", "skip", or "error".
    """
    label = f"{year}  {event_name:<40}  {session_id:<20}  driver={driver_number}"

    if dry_run:
        log(f"  DRY-RUN  {label}", fh)
        return "skip"

    try:
        session = fastf1.get_session(year, event_name, session_id)
        session.load(
            laps=True,
            telemetry=True,
            weather=True,
            messages=False,
        )

        if driver_number not in (session.drivers or []):
            log(f"  SKIP     {label}  (driver not in session)", fh)
            return "skip"

        log(f"  OK       {label}", fh)
        return "ok"

    except Exception as exc:
        # Covers: session not available, no data for this format, network errors.
        reason = str(exc).split("\n")[0][:100]
        log(f"  SKIP     {label}  ({reason})", fh)
        return "skip"

# ---------------------------------------------------------------------------
# Per-year runner
# ---------------------------------------------------------------------------

def process_year(year, dry_run, fh):
    counts = {"ok": 0, "skip": 0, "error": 0}
    driver_number = DRIVER_BY_YEAR.get(year, "1")

    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
    except Exception as exc:
        log(f"  ERROR fetching schedule for {year}: {exc}", fh)
        counts["error"] += 1
        return counts

    events = schedule["EventName"].tolist()
    log(f"\n{'='*60}", fh)
    log(f"  {year}  |  {len(events)} events  |  driver #{driver_number}", fh)
    log(f"{'='*60}", fh)

    for event_name in events:
        for session_id in SESSIONS:
            result = load_one(year, event_name, session_id, driver_number, dry_run, fh)
            counts[result if result in counts else "error"] += 1
            if not dry_run:
                time.sleep(DELAY_BETWEEN_SESSIONS)

    return counts

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build VER telemetry cache for 2018-2026"
    )
    parser.add_argument("--year", type=int, default=None,
                        help="Process a single year only")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be downloaded without fetching")
    args = parser.parse_args()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(CACHE_DIR))

    years = [args.year] if args.year else list(DRIVER_BY_YEAR.keys())
    mode  = "DRY-RUN" if args.dry_run else "LIVE"

    log_path = PROJECT_ROOT / "python" / "build_cache.log"
    t_start  = time.time()

    with open(log_path, "a", encoding="utf-8") as fh:
        log(f"\n{'#'*60}", fh)
        log(f"  build_cache.py  |  mode={mode}  |  years={years}", fh)
        log(f"  cache_dir={CACHE_DIR}", fh)
        log(f"{'#'*60}", fh)

        total = {"ok": 0, "skip": 0, "error": 0}

        for year in years:
            counts = process_year(year, args.dry_run, fh)
            for k in total:
                total[k] += counts[k]

        elapsed = time.time() - t_start
        log(f"\n{'#'*60}", fh)
        log(
            f"  Finished in {elapsed/60:.1f} min  |  "
            f"ok={total['ok']}  skipped={total['skip']}  errors={total['error']}",
            fh,
        )
        log(f"  Log written to: {log_path}", fh)
        log(f"{'#'*60}\n", fh)

    return 0


if __name__ == "__main__":
    sys.exit(main())
