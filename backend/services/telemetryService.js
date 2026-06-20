"use strict";

const axios = require("axios");

const OPENF1_CAR_DATA_URL = "https://api.openf1.org/v1/car_data";

async function fetchTelemetry(driverNumber, sessionKey) {
  const driver  = parseInt(driverNumber, 10) || 1;
  const session = parseInt(sessionKey,   10);

  if (!session) throw new Error("sessionKey is required");

  console.log(`[telemetryService] fetching driver=${driver} session=${session}`);

  const response = await axios.get(OPENF1_CAR_DATA_URL, {
    params: { driver_number: driver, session_key: session },
    timeout: 30_000,
  });

  const raw = Array.isArray(response.data) ? response.data : [];
  console.log(`[telemetryService] raw rows received: ${raw.length}`);

  const normalized = normalizeTelemetry(raw);
  console.log(`[telemetryService] normalized rows returned: ${normalized.length}`);

  return normalized;
}

function normalizeTelemetry(data) {
  return data
    .map((row) => ({
      time:     row.date  ?? null,   // ISO timestamp — used as chart x-axis key
      speed:    row.speed    ?? 0,
      throttle: row.throttle ?? 0,
      brake:    row.brake    ?? 0,
      gear:     row.n_gear   ?? row.gear ?? 0,
      rpm:      row.rpm      ?? 0,
      drs:      row.drs      ?? 0,
    }))
    // Drop rows where the car is completely stationary (all zeros = pit/garage)
    .filter((row) => row.speed > 0 || row.rpm > 0 || row.throttle > 0)
    .slice(0, 1000);
}

module.exports = { fetchTelemetry, normalizeTelemetry };
