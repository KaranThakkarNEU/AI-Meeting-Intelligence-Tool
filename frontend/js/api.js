/**
 * api.js — thin client over the FastAPI backend.
 * Exposes a global `API` object: { BASE, WS_BASE, getJSON, openWebSocket, escapeHTML }.
 */
(function () {
  "use strict";

  const BASE = window.API_BASE || "http://127.0.0.1:8765";
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
