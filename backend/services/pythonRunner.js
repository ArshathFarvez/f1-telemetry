"use strict";

/**
 * pythonRunner.js
 *
 * Canonical service layer for executing Python analytics scripts.
 * Delegates to utils/spawnPython for the actual spawn implementation so
 * there is a single source of truth for process management.
 */

const { runPythonScript, scriptPath, DEFAULT_TIMEOUT_MS } = require("../utils/spawnPython");

module.exports = { runPythonScript, scriptPath, DEFAULT_TIMEOUT_MS };
