"use strict";

const path = require("path");
const { runPythonScript, scriptPath } = require("../services/pythonRunner");

// ---------------------------------------------------------------------------
// Shared helpers
// ---------------------------------------------------------------------------

/**
 * Parse and validate the common year / grandPrix query params.
 * Returns { year, gp } or throws a 400-level Error.
 */
function parseSessionParams(query) {
  const year    = query.year ? parseInt(query.year, 10) : null;
  const gp      = (query.gp || query.grandPrix || "").trim();

  if (!year || Number.isNaN(year) || year < 2018 || year > new Date().getFullYear() + 1) {
    const err = new Error(`Missing or invalid year: "${query.year}". Must be 2018–present.`);
    err.statusCode = 400;
    throw err;
  }
  const session = (query.session || "").trim().toUpperCase() || null;


  if (!gp) {
    const err = new Error("Missing required query param: gp");
    err.statusCode = 400;
    throw err;
  }
  return { year, gp, session };
}

/**
 * Centralised error responder — surfaces statusCode from typed script errors.
 */
function handleError(res, err, context) {
  const status = err.statusCode || 500;
  console.error(`[analytics/${context}]`, err.message, err.detail || "");
  res.status(status).json({
    error:   err.name || "AnalyticsError",
    message: err.message,
    ...(err.detail ? { detail: err.detail } : {}),
  });
}

// ---------------------------------------------------------------------------
// GET /api/analytics/compare
// Query params: year, gp, drivers (comma-separated, e.g. "VER,LEC")
// ---------------------------------------------------------------------------
async function getComparison(req, res) {
  try {
    const { year, gp, session } = parseSessionParams(req.query);

    const rawDrivers = req.query.drivers || "VER,LEC";
    const drivers = rawDrivers
      .split(",")
      .map((d) => d.trim().toUpperCase())
      .filter(Boolean)
      .slice(0, 6);

    console.log(`[GET /api/analytics/compare] year=${year} gp=${gp} session=${session} drivers=${drivers.join(",")}`);
    const script = scriptPath("comparison/compare_api.py");
    const args   = ["--year", String(year), "--gp", gp, "--drivers", ...drivers];
    if (session) args.push("--session", session);

    const data = await runPythonScript(script, args);
    res.json(data);
  } catch (err) {
    handleError(res, err, "compare");
  }
}

// ---------------------------------------------------------------------------
// GET /api/analytics/tyres
// Query params: year, gp, driver
// ---------------------------------------------------------------------------
async function getTyreAnalysis(req, res) {
  try {
    const { year, gp, session } = parseSessionParams(req.query);
    const driver = (req.query.driver || "").trim().toUpperCase();
    if (!driver) {
      return res.status(400).json({ error: "BadRequest", message: "Missing required query param: driver" });
    }

    console.log(`[GET /api/analytics/tyres] year=${year} gp=${gp} session=${session} driver=${driver}`);
    const script = scriptPath("tyre/tyres_api.py");
    const args   = ["--year", String(year), "--gp", gp, "--driver", driver];
    if (session) args.push("--session", session);

    const data = await runPythonScript(script, args);
    res.json(data);
  } catch (err) {
    handleError(res, err, "tyres");
  }
}

// ---------------------------------------------------------------------------
// GET /api/analytics/strategy
// Query params: year, gp, driver
// ---------------------------------------------------------------------------
async function getStrategy(req, res) {
  try {
    const { year, gp, session } = parseSessionParams(req.query);
    const driver = (req.query.driver || "").trim().toUpperCase();
    if (!driver) {
      return res.status(400).json({ error: "BadRequest", message: "Missing required query param: driver" });
    }

    console.log(`[GET /api/analytics/strategy] year=${year} gp=${gp} session=${session} driver=${driver}`);
    const script = scriptPath("strategy/strategy_api.py");
    const args   = ["--year", String(year), "--gp", gp, "--driver", driver];
    if (session) args.push("--session", session);

    const data = await runPythonScript(script, args);
    res.json(data);
  } catch (err) {
    handleError(res, err, "strategy");
  }
}

// ---------------------------------------------------------------------------
// GET /api/analytics/track-evolution
// Query params: year, gp
// ---------------------------------------------------------------------------
async function getTrackEvolution(req, res) {
  try {
    const { year, gp, session } = parseSessionParams(req.query);

    console.log(`[GET /api/analytics/track-evolution] year=${year} gp=${gp} session=${session}`);
    const script = scriptPath("track_evolution/evolution_api.py");
    const args   = ["--year", String(year), "--gp", gp];
    if (session) args.push("--session", session);

    const data = await runPythonScript(script, args);
    res.json(data);
  } catch (err) {
    handleError(res, err, "track-evolution");
  }
}

// ---------------------------------------------------------------------------
// GET /api/analytics/schedule
// Query params: year
// ---------------------------------------------------------------------------
async function getSchedule(req, res) {
  try {
    const year = req.query.year ? parseInt(req.query.year, 10) : null;
    if (!year || Number.isNaN(year) || year < 2018 || year > new Date().getFullYear() + 1) {
      return res.status(400).json({ error: "BadRequest", message: `Invalid year: "${req.query.year}"` });
    }
    console.log(`[GET /api/analytics/schedule] year=${year}`);
    const script = scriptPath("schedule_api.py");
    const data   = await runPythonScript(script, [String(year)]);
    res.json(data);
  } catch (err) {
    handleError(res, err, "schedule");
  }
}

module.exports = { getComparison, getTyreAnalysis, getStrategy, getTrackEvolution, getSchedule };
