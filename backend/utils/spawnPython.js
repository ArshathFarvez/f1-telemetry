"use strict";

const { spawn } = require("child_process");
const path = require("path");

const PROJECT_ROOT = path.resolve(__dirname, "../..");
const ANALYTICS_ROOT = path.join(PROJECT_ROOT, "analytics");

// Default timeout: 120 s — FastF1 session loads can be slow on first run.
const DEFAULT_TIMEOUT_MS = 120_000;

/**
 * Resolve the absolute path to a Python analytics script.
 * @param {string} relativePath  e.g. "comparison/driver_comparison.py"
 */
function scriptPath(relativePath) {
  return path.join(ANALYTICS_ROOT, relativePath);
}

/**
 * Spawn a Python script and collect its stdout as a string.
 *
 * The script is expected to print a single JSON object/array to stdout.
 * Anything on stderr is captured and surfaced in the rejection reason.
 *
 * @param {string}   scriptFile   Absolute path to the .py file.
 * @param {string[]} args         CLI arguments forwarded to the script.
 * @param {number}   timeoutMs    Kill timeout in milliseconds.
 * @returns {Promise<unknown>}    Parsed JSON value from stdout.
 */
function runPythonScript(scriptFile, args = [], timeoutMs = DEFAULT_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    const proc = spawn("python", [scriptFile, ...args], {
      cwd: PROJECT_ROOT,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    let stdout = "";
    let stderr = "";
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      proc.kill("SIGTERM");
      reject(new ScriptTimeoutError(scriptFile, timeoutMs));
    }, timeoutMs);

    proc.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
    proc.stderr.on("data", (chunk) => { stderr += chunk.toString(); });

    proc.on("close", (code) => {
      clearTimeout(timer);
      if (timedOut) return;

      if (code !== 0) {
        return reject(new ScriptExitError(scriptFile, code, stderr));
      }

      const raw = stdout.trim();
      if (!raw) {
        return reject(new ScriptOutputError(scriptFile, "Script produced no output on stdout."));
      }

      try {
        resolve(JSON.parse(raw));
      } catch {
        reject(new ScriptOutputError(scriptFile, `stdout is not valid JSON.\n${raw.slice(0, 500)}`));
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(new ScriptSpawnError(scriptFile, err));
    });
  });
}

// ---------------------------------------------------------------------------
// Typed error classes — lets controllers distinguish failure modes cleanly.
// ---------------------------------------------------------------------------

class ScriptTimeoutError extends Error {
  constructor(script, ms) {
    super(`Script timed out after ${ms}ms: ${path.basename(script)}`);
    this.name = "ScriptTimeoutError";
    this.statusCode = 504;
  }
}

class ScriptExitError extends Error {
  constructor(script, code, stderr) {
    super(`Script exited with code ${code}: ${path.basename(script)}`);
    this.name = "ScriptExitError";
    this.statusCode = 500;
    this.detail = stderr.slice(0, 1000);
  }
}

class ScriptOutputError extends Error {
  constructor(script, reason) {
    super(`Script output error (${path.basename(script)}): ${reason}`);
    this.name = "ScriptOutputError";
    this.statusCode = 502;
  }
}

class ScriptSpawnError extends Error {
  constructor(script, cause) {
    super(`Failed to spawn script ${path.basename(script)}: ${cause.message}`);
    this.name = "ScriptSpawnError";
    this.statusCode = 500;
    this.cause = cause;
  }
}

module.exports = { runPythonScript, scriptPath, DEFAULT_TIMEOUT_MS };
