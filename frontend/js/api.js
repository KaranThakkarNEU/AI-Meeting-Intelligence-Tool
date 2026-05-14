/**
 * api.js — thin client over the FastAPI backend.
 * Exposes a global `API` object: { BASE, WS_BASE, getJSON, openWebSocket, escapeHTML }.
 */
(function () {
  "use strict";

  // Resolve the API base URL:
  //   1. window.API_BASE — explicit override (e.g. for a separately-hosted frontend)
  //   2. Page loaded from the legacy two-server dev workflow (frontend on :3000)
  //      → talk to FastAPI on :8765
  //   3. Otherwise: same-origin. Works both for `uvicorn app.main:app` locally
  //      (which now serves the frontend itself) and for any deployed host.
  const isLegacyDevPort = location.port === "3000";
  const BASE = window.API_BASE
    || (isLegacyDevPort
        ? "http://127.0.0.1:8765"
        : `${location.protocol}//${location.host}`);
  // http -> ws, https -> wss (the replace handles both automatically).
  const WS_BASE = BASE.replace(/^http/, "ws");

  async function getJSON(path) {
    const r = await fetch(BASE + path);
    if (!r.ok) throw new Error(`GET ${path} → HTTP ${r.status}`);
    return r.json();
  }

  function openWebSocket(path) {
    return new WebSocket(WS_BASE + path);
  }

  function escapeHTML(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  window.API = { BASE, WS_BASE, getJSON, openWebSocket, escapeHTML };
})();
