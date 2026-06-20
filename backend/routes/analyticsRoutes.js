"use strict";

const { Router } = require("express");
const {
  getComparison,
  getTyreAnalysis,
  getStrategy,
  getTrackEvolution,
  getSchedule,
} = require("../controllers/analyticsController");

const router = Router();

/**
 * GET /api/analytics/schedule?year=2024
 * Returns ordered list of Grand Prix names for the given season.
 */
router.get("/schedule", getSchedule);

/**
 * GET /api/analytics/compare
 * Compare fastest qualifying laps for two or more drivers.
 *
 * Query params:
 *   year     {number}  Season year          (default: 2024)
 *   gp       {string}  Grand Prix name      (default: "Monaco")
 *   drivers  {string}  Comma-separated list (default: "VER,LEC")
 *
 * Example: /api/analytics/compare?year=2024&gp=Monaco&drivers=VER,LEC,NOR
 */
router.get("/compare", getComparison);

/**
 * GET /api/analytics/tyres
 * Tyre degradation analysis for a single driver's race.
 *
 * Query params:
 *   year    {number}  Season year     (default: 2024)
 *   gp      {string}  Grand Prix name (default: "Monaco")
 *   driver  {string}  Driver code     (default: "VER")
 *
 * Example: /api/analytics/tyres?year=2024&gp=Monaco&driver=VER
 */
router.get("/tyres", getTyreAnalysis);

/**
 * GET /api/analytics/strategy
 * Race strategy simulation for a single driver.
 *
 * Query params:
 *   year    {number}  Season year     (default: 2024)
 *   gp      {string}  Grand Prix name (default: "Monaco")
 *   driver  {string}  Driver code     (default: "VER")
 *
 * Example: /api/analytics/strategy?year=2024&gp=Monaco&driver=VER
 */
router.get("/strategy", getStrategy);

/**
 * GET /api/analytics/track-evolution
 * Track grip evolution and weather correlation for a qualifying session.
 *
 * Query params:
 *   year  {number}  Season year     (default: 2024)
 *   gp    {string}  Grand Prix name (default: "Monaco")
 *
 * Example: /api/analytics/track-evolution?year=2024&gp=Monaco
 */
router.get("/track-evolution", getTrackEvolution);

module.exports = router;
