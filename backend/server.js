"use strict";

const express = require("express");
const cors = require("cors");

const telemetryRoutes = require("./routes/telemetryRoutes");
const analyticsRoutes = require("./routes/analyticsRoutes");

const app = express();

// ─────────────────────────────────────────────────────────────────────────────
// Middleware
// ─────────────────────────────────────────────────────────────────────────────
app.use(cors());
app.use(express.json());

// ─────────────────────────────────────────────────────────────────────────────
// Diagnostic: log every incoming request
// ─────────────────────────────────────────────────────────────────────────────
app.use((req, _res, next) => {
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
  next();
});

// ─────────────────────────────────────────────────────────────────────────────
// Health check
// ─────────────────────────────────────────────────────────────────────────────
app.get("/", (_req, res) => {
  res.json({
    status: "ok",
    service: "F1 Telemetry Server 🚀",
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Smoke-test endpoints
// ─────────────────────────────────────────────────────────────────────────────
app.get("/test", (_req, res) => {
  console.log("TEST HIT");

  res.json({
    ok: true,
  });
});

app.get("/api/analytics/test", (_req, res) => {
  console.log("ANALYTICS TEST HIT");

  res.json({
    analytics: true,
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Telemetry routes
// Final endpoint:
// GET /api/telemetry
// ─────────────────────────────────────────────────────────────────────────────
app.use("/api/telemetry", telemetryRoutes);

// ─────────────────────────────────────────────────────────────────────────────
// Analytics routes
// Final endpoints:
// GET /api/analytics/compare
// GET /api/analytics/tyres
// GET /api/analytics/strategy
// GET /api/analytics/track-evolution
// ─────────────────────────────────────────────────────────────────────────────
app.use("/api/analytics", analyticsRoutes);

// ─────────────────────────────────────────────────────────────────────────────
// 404 handler — ALWAYS JSON
// ─────────────────────────────────────────────────────────────────────────────
app.use((req, res) => {
  res.status(404).json({
    error: "NotFound",
    message: `Route not found: ${req.method} ${req.url}`,
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Global error handler
// ─────────────────────────────────────────────────────────────────────────────
// eslint-disable-next-line no-unused-vars
app.use((err, _req, res, _next) => {
  console.error("[server] Unhandled error:", err);

  res.status(err.statusCode || 500).json({
    error: err.name || "InternalServerError",
    message: err.message || "An unexpected error occurred",
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// Safe route printer (Express v4 + v5 compatible)
// ─────────────────────────────────────────────────────────────────────────────
function printRoutes() {
  console.log("\nRegistered routes:");

  const routes = [
    "GET  /",
    "GET  /test",
    "GET  /api/analytics/test",
    "GET  /api/telemetry",
    "GET  /api/telemetry/laps",
    "GET  /api/telemetry/lap",
    "GET  /api/analytics/compare",
    "GET  /api/analytics/tyres",
    "GET  /api/analytics/strategy",
    "GET  /api/analytics/track-evolution",
  ];

  routes.forEach((route) => {
    console.log(`  ${route}`);
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Start server
// ─────────────────────────────────────────────────────────────────────────────
const PORT = 5000;

app.listen(PORT, () => {
  console.log(`\nServer running on port ${PORT} 🚀`);

  printRoutes();

  console.log("\nSmoke-test endpoints:");
  console.log("  http://localhost:5000/test");
  console.log("  http://localhost:5000/api/analytics/test");

  console.log("\nAPI endpoints:");
  console.log("  http://localhost:5000/api/telemetry");
  console.log("  http://localhost:5000/api/analytics/compare");
  console.log("  http://localhost:5000/api/analytics/tyres");
  console.log("  http://localhost:5000/api/analytics/strategy");
  console.log("  http://localhost:5000/api/analytics/track-evolution");
});