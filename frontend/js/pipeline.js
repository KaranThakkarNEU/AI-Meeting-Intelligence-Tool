/**
 * pipeline.js — WebSocket runner + per-stage timing.
 * Exposes a global `PipelineRunner`: { init, run, cancel }.
 */
(function () {
  "use strict";
  const { openWebSocket } = window.API;

  let elements = {};
  let onStateChange = null;
  let onComplete = null;
  let ws = null;
  let stageStarts = {};
  let runStartedAt = 0;

  function init(opts) {
    elements = {
      pipelineBar: opts.pipelineBar,
      results: opts.results,
    };
    onStateChange = opts.onStateChange || (() => {});
    onComplete = opts.onComplete || (() => {});
    window.Renderers.setContainer(elements.results);
  }

  function resetBar() {
    elements.pipelineBar.querySelectorAll(".stage-pill").forEach((p) => {
      p.className = "stage-pill";
      const t = p.querySelector(".timing");
      if (t) t.remove();
    });
    stageStarts = {};
  }
  function markStage(stage, status) {
    const pill = elements.pipelineBar.querySelector(`.stage-pill[data-stage="${stage}"]`);
    if (!pill) return;
    pill.className = `stage-pill ${status}`;
    if (status === "done" && stageStarts[stage]) {
      const t = ((performance.now() - stageStarts[stage]) / 1000).toFixed(1);
      const tEl = document.createElement("span");
      tEl.className = "timing";
      tEl.textContent = `${t}s`;
      pill.appendChild(tEl);
    }
  }
  function markAllActive() {
    elements.pipelineBar.querySelectorAll(".stage-pill").forEach((p) => {
      p.classList.add("active");
      stageStarts[p.dataset.stage] = performance.now();
    });
  }

  function run(payload) {
    if (ws) { try { ws.close(); } catch {} }
    window.Renderers.clear();
    resetBar();
    runStartedAt = performance.now();
    onStateChange({ state: "running" });
    markAllActive();

    ws = openWebSocket("/ws/analyze");
    ws.onopen = () => ws.send(JSON.stringify(payload));
    ws.onmessage = (msg) => {
      let ev;
      try { ev = JSON.parse(msg.data); } catch { return; }
      const { stage, status, data } = ev;
      if (status === "error") {
        markStage(stage, "error");
        window.Renderers.error(stage, (data && (data.detail || data.message)) || "Unknown error");
        return;
      }
      const renderer = window.Renderers[stage];
      if (renderer) renderer(data);

      if (stage === "done") {
        const totalSec = ((performance.now() - runStartedAt) / 1000).toFixed(2);
        window.Renderers.complete(data);
        onStateChange({ state: "complete", elapsedSec: totalSec });
        onComplete(data);
      } else {
        markStage(stage, "done");
      }
    };
    ws.onerror = () => onStateChange({ state: "error", message: "WebSocket error" });
    ws.onclose = () => {
      ws = null;
      onStateChange({ state: "closed" });
    };
  }

  function cancel() {
    if (ws) { try { ws.close(); } catch {} ws = null; }
    onStateChange({ state: "closed" });
  }

  window.PipelineRunner = { init, run, cancel };
})();
