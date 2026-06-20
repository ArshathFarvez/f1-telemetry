"use strict";

/**
 * Root entry point — delegates entirely to backend/server.js.
 *
 * This file exists so the project can be started from the repo root with:
 *   node server.js
 *   npm start
 *
 * All route definitions, middleware, and port binding live in backend/server.js.
 */

require("./backend/server");
