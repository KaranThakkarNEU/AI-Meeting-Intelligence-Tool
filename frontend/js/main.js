/**
 * main.js — bootstrap. Wires the DOM after all scripts loaded.
 */
(function () {
  "use strict";
  const { getJSON, escapeHTML } = window.API;
  const $ = (id) => document.getElementById(id);

  document.addEventListener("DOMContentLoaded", async () => {
    // ---- DOM refs ----
    const el = {
      statusDot: $("status-dot"),
      statusText: $("status-text"),
      modelPill: $("model-pill"),
      modelName: $("model-name"),
      transcript: $("transcript"),
      formatHint: $("format-hint"),
      meetingDate: $("meeting-date"),
      aliases: $("aliases"),
      runBtn: $("run-btn"),
      clearBtn: $("clear-btn"),
      cancelBtn: $("cancel-btn"),
      cancelRow: $("cancel-row"),
      samplesList: $("samples-list"),
      pipelineBar: $("pipeline-bar"),
      results: $("results"),
      copyBtn: $("copy-json"),
      scrollDemoBtn: $("scroll-to-demo"),
    };

    let lastReport = null;

    // ---- Header status ----
    const setStatus = (state, text) => {
      el.statusDot.className = `status-dot ${state}`;
      el.statusText.textContent = text;
    };

    // ---- Initial health check ----
    try {
      const h = await getJSON("/health");
      if (el.modelName) el.modelName.textContent = h.model;
      setStatus(h.claude_reachable ? "connected" : "error",
                h.claude_reachable ? "ready" : "API unreachable");
    } catch {
      setStatus("error", "server offline");
      if (el.modelName) el.modelName.textContent = "—";
    }

    // ---- Sample list ----
    window.Samples.init({
      container: el.samplesList,
      onSelect: (sample) => {
        el.transcript.value = sample.transcript || "";
        if (sample.meeting_date) {
          const d = new Date(sample.meeting_date);
          const pad = (n) => String(n).padStart(2, "0");
          el.meetingDate.value = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        }
        // Scroll to top of demo so user sees the textarea fill in.
        document.getElementById("demo").scrollIntoView({ behavior: "smooth", block: "start" });
        el.transcript.focus();
      },
    });

    // ---- Pipeline runner ----
    window.PipelineRunner.init({
      pipelineBar: el.pipelineBar,
      results: el.results,
      onStateChange: ({ state, elapsedSec, message }) => {
        if (state === "running") {
          setStatus("running", "running…");
          el.runBtn.disabled = true;
          el.cancelRow.classList.remove("hidden");
          el.copyBtn.disabled = true;
        } else if (state === "complete") {
          setStatus("connected", `done in ${elapsedSec}s`);
          el.runBtn.disabled = false;
          el.cancelRow.classList.add("hidden");
          el.copyBtn.disabled = false;
        } else if (state === "error") {
          setStatus("error", message || "error");
          el.runBtn.disabled = false;
          el.cancelRow.classList.add("hidden");
        } else if (state === "closed") {
          el.runBtn.disabled = false;
          el.cancelRow.classList.add("hidden");
        }
      },
      onComplete: (report) => { lastReport = report; },
    });

    // ---- Build payload + run ----
    const runPipeline = () => {
      const transcript = el.transcript.value.trim();
      if (transcript.length < 10) {
        alert("Transcript is too short (need at least 10 characters).");
        return;
      }
      if (transcript.length > 50000) {
        alert("Transcript exceeds 50,000 character limit.");
        return;
      }
      let aliases = null;
      const aliasesText = el.aliases.value.trim();
      if (aliasesText) {
        try { aliases = JSON.parse(aliasesText); }
        catch (e) { alert(`Speaker aliases must be valid JSON. Example: {"JD": "John Doe"}`); return; }
      }
      const payload = {
        transcript,
        meeting_date: el.meetingDate.value ? new Date(el.meetingDate.value).toISOString() : null,
        speaker_aliases: aliases,
      };
      window.PipelineRunner.run(payload);
    };

    el.runBtn.addEventListener("click", runPipeline);
    el.cancelBtn.addEventListener("click", () => window.PipelineRunner.cancel());
    el.clearBtn.addEventListener("click", () => {
      el.transcript.value = "";
      el.meetingDate.value = "";
      window.Renderers.clear();
      el.results.innerHTML = `<div class="empty">Choose a sample on the left, or paste a transcript and hit <strong>Run pipeline</strong>.</div>`;
      lastReport = null;
      el.copyBtn.disabled = true;
    });
    el.copyBtn.addEventListener("click", async () => {
      if (!lastReport) return;
      await navigator.clipboard.writeText(JSON.stringify(lastReport, null, 2));
      el.copyBtn.classList.add("copied");
      el.copyBtn.textContent = "✓ Copied";
      setTimeout(() => {
        el.copyBtn.classList.remove("copied");
        el.copyBtn.textContent = "Copy full JSON";
      }, 1800);
    });

    // Cmd/Ctrl+Enter to run.
    el.transcript.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        runPipeline();
      }
    });

    // Scroll-to-demo CTA from hero.
    if (el.scrollDemoBtn) {
      el.scrollDemoBtn.addEventListener("click", () => {
        document.getElementById("demo").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }

    // ---- Quota modal ----
    const modalEl = document.getElementById("quota-modal");
    const modalCloseBtn = document.getElementById("quota-modal-close");
    const adminEmailEl = document.getElementById("admin-email-display");
    const emailLinkEl = document.getElementById("email-admin-link");
    function showQuotaModal(detail) {
      if (detail && detail.admin_email) {
        adminEmailEl.textContent = detail.admin_email;
        const subject = encodeURIComponent("AI Meeting Intelligence — Access Request");
        const body = encodeURIComponent("Hi, I'd like to request more demo runs on your AI Meeting Intelligence Tool. Thanks!");
        emailLinkEl.href = `mailto:${detail.admin_email}?subject=${subject}&body=${body}`;
      }
      modalEl.classList.remove("hidden");
      modalEl.setAttribute("aria-hidden", "false");
    }
    function hideQuotaModal() {
      modalEl.classList.add("hidden");
      modalEl.setAttribute("aria-hidden", "true");
    }
    modalCloseBtn.addEventListener("click", hideQuotaModal);
    modalEl.addEventListener("click", (e) => { if (e.target === modalEl) hideQuotaModal(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") hideQuotaModal(); });
    window.QuotaModal = { show: showQuotaModal, hide: hideQuotaModal };

    // ---- Scroll-driven reveal animation ----
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => entries.forEach((e) => { if (e.isIntersecting) e.target.classList.add("in"); }),
        { threshold: 0.15 }
      );
      document.querySelectorAll(".reveal").forEach((n) => observer.observe(n));
    } else {
      document.querySelectorAll(".reveal").forEach((n) => n.classList.add("in"));
    }
  });
})();
