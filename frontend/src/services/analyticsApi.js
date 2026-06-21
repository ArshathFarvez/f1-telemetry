const API_URL = (
  import.meta.env.VITE_API_URL || "http://localhost:5000"
).replace(/\/+$/, "");

const BASE = `${API_URL}/api/analytics`;
const TELEMETRY_BASE = `${API_URL}/api/telemetry`;

const CLIENT_TIMEOUT_MS = 150000;

// ======================================================
// SHARED FETCH
// ======================================================

async function apiFetch(url, options = {}) {
  const controller = new AbortController();

  const timer = setTimeout(() => {
    controller.abort();
  }, CLIENT_TIMEOUT_MS);

  console.log(`[analyticsApi] GET ${url}`);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    const contentType =
      response.headers.get("content-type") || "";

    if (!contentType.includes("application/json")) {
      const text = await response.text();

      console.error("NON JSON RESPONSE:", text);

      throw new Error(
        `Expected JSON but received ${contentType}`
      );
    }

    const json = await response.json();

    if (!response.ok) {
      throw new Error(
        json.message || `HTTP ${response.status}`
      );
    }

    console.log(`[analyticsApi] SUCCESS ${url}`);

    return json;
  } catch (err) {
    if (err.name === "AbortError") {
      throw new Error(
        `Request timeout after ${
          CLIENT_TIMEOUT_MS / 1000
        }s`
      );
    }

    console.error(`[analyticsApi] ERROR`, err);

    throw err;
  } finally {
    clearTimeout(timer);
  }
}

// ======================================================
// QUERY STRING
// ======================================================

function qs(params = {}) {
  const filtered = Object.entries(params).filter(
    ([, value]) =>
      value !== undefined &&
      value !== null
  );

  if (!filtered.length) {
    return "";
  }

  return (
    "?" +
    filtered
      .map(
        ([key, value]) =>
          `${encodeURIComponent(
            key
          )}=${encodeURIComponent(value)}`
      )
      .join("&")
  );
}

// ======================================================
// TELEMETRY LAPS — list of all laps for a driver/session
// ======================================================

export async function fetchLaps({
  driver,
  year,
  gp,
  session,
} = {}) {
  const query = qs({
    driver,
    year,
    gp,
    session,
  });

  return apiFetch(
    `${TELEMETRY_BASE}/laps${query}`
  );
}

// ======================================================
// TELEMETRY LAP — full telemetry + summary for one lap
// lap: "fastest" | "last" | number
// ======================================================

export async function fetchLapTelemetry({
  driver,
  year,
  gp,
  session,
  lap,
} = {}) {
  const query = qs({
    driver,
    year,
    gp,
    session,
    lap,
  });

  return apiFetch(
    `${TELEMETRY_BASE}/lap${query}`
  );
}

// ======================================================
// SCHEDULE
// ======================================================

export async function fetchSchedule({
  year,
} = {}) {
  const query = qs({ year });

  return apiFetch(
    `${BASE}/schedule${query}`
  );
}

// ======================================================
// COMPARISON
// ======================================================

export async function fetchComparison({
  year,
  gp,
  session,
  drivers,
} = {}) {
  const query = qs({
    year,
    gp,
    session,
    drivers: drivers?.join(","),
  });

  return apiFetch(
    `${BASE}/compare${query}`
  );
}

// ======================================================
// TYRES
// ======================================================

export async function fetchTyres({
  year,
  gp,
  session,
  driver,
} = {}) {
  const query = qs({
    year,
    gp,
    session,
    driver,
  });

  return apiFetch(
    `${BASE}/tyres${query}`
  );
}

// ======================================================
// STRATEGY
// ======================================================

export async function fetchStrategy({
  year,
  gp,
  session,
  driver,
} = {}) {
  const query = qs({
    year,
    gp,
    session,
    driver,
  });

  return apiFetch(
    `${BASE}/strategy${query}`
  );
}

// ======================================================
// TRACK EVOLUTION
// ======================================================

export async function fetchTrackEvolution({
  year,
  gp,
  session,
} = {}) {
  const query = qs({
    year,
    gp,
    session,
  });

  return apiFetch(
    `${BASE}/track-evolution${query}`
  );
}
