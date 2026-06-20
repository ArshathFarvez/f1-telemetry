"use strict";

const express  = require("express");
const { execFile } = require("child_process");
const path     = require("path");

const router = express.Router();

const PY = (script) => path.join(__dirname, "../../python", script);
const MB20 = { maxBuffer: 1024 * 1024 * 20 };

function runPy(scriptPath, args, res) {
  execFile("python", [scriptPath, ...args], MB20, (error, stdout, stderr) => {
    if (error) {
      console.error("PYTHON EXEC ERROR:", error.message);
      if (stderr) console.error("PYTHON STDERR:", stderr);
      return res.status(500).json({ success: false, error: "Python execution failed", details: error.message });
    }
    if (stderr) console.error("PYTHON STDERR:", stderr);
    try {
      res.json(JSON.parse(stdout));
    } catch {
      res.status(500).json({ success: false, error: "Invalid JSON from Python", raw: stdout.slice(0, 500) });
    }
  });
}

// ── GET /api/telemetry?driver&year&gp&session ─────────────────────────────
// Returns fastest lap telemetry (existing behaviour — kept for compatibility)
router.get("/", (req, res) => {
  const driver  = req.query.driver  || "1";
  const year    = req.query.year    || "2024";
  const gp      = req.query.gp      || "Monaco";
  const session = req.query.session || "Q";

  console.log(`[telemetry] driver=${driver} year=${year} gp=${gp} session=${session}`);

  execFile("python", [PY("telemetry.py"), driver, year, gp, session], MB20, (error, stdout, stderr) => {
    if (error) {
      console.error("PYTHON EXEC ERROR:", error.message);
      return res.status(500).json({ success: false, error: "Python execution failed", details: error.message });
    }
    if (stderr) console.error("PYTHON STDERR:", stderr);
    try {
      const telemetryData = JSON.parse(stdout);
      console.log(`Telemetry loaded: ${telemetryData.length} points`);
      res.json({ success: true, driver, year, gp, session, points: telemetryData.length, data: telemetryData });
    } catch {
      res.status(500).json({ success: false, error: "Invalid JSON returned from Python", raw: stdout.slice(0, 500) });
    }
  });
});

// ── GET /api/telemetry/laps?driver&year&gp&session ────────────────────────
// Returns the full lap list for a driver/session with times and sector splits
router.get("/laps", (req, res) => {
  const driver  = req.query.driver  || "1";
  const year    = req.query.year    || "2024";
  const gp      = req.query.gp      || "Monaco";
  const session = req.query.session || "Q";

  console.log(`[telemetry/laps] driver=${driver} year=${year} gp=${gp} session=${session}`);
  runPy(PY("laps.py"), [driver, year, gp, session], res);
});

// ── GET /api/telemetry/lap?driver&year&gp&session&lap ─────────────────────
// Returns telemetry + summary for a specific lap number (or "fastest" / "last")
router.get("/lap", (req, res) => {
  const driver  = req.query.driver  || "1";
  const year    = req.query.year    || "2024";
  const gp      = req.query.gp      || "Monaco";
  const session = req.query.session || "Q";
  const lap     = req.query.lap     || "fastest";

  console.log(`[telemetry/lap] driver=${driver} year=${year} gp=${gp} session=${session} lap=${lap}`);
  runPy(PY("telemetry_lap.py"), [driver, year, gp, session, lap], res);
});

module.exports = router;
