/**
 * samples.js — loads sample transcripts from /samples and wires click-to-load.
 * Exposes a global `Samples` object: { init, loadSampleById }.
 */
(function () {
  "use strict";
  const { getJSON, escapeHTML } = window.API;

  let containerEl = null;
  let onSelect = null;
  let lastSelectedCard = null;

  async function init({ container, onSelect: handler }) {
    containerEl = container;
    onSelect = handler;
    containerEl.innerHTML = `<div class="empty">Loading samples…</div>`;
    try {
      const data = await getJSON("/samples");
      render(data.items || []);
    } catch (e) {
      containerEl.innerHTML = `<div class="empty">Could not load samples.<br>Is the backend running on :8765?</div>`;
    }
  }

  function render(items) {
    if (!items.length) {
      containerEl.innerHTML = `<div class="empty">No samples found.</div>`;
      return;
    }
    containerEl.innerHTML = items.map((it) => `
      <div class="sample-card" data-id="${escapeHTML(it.id)}">
        <div class="sample-head">
          <span class="sample-id">${escapeHTML(it.id)}</span>
          <span class="sample-cat">${escapeHTML(String(it.category).replace(/_/g, " "))}</span>
        </div>
        <div class="sample-preview">${escapeHTML(it.preview)}</div>
        <div class="sample-meta">${it.line_count} lines · ${it.char_count} chars</div>
      </div>
    `).join("");
    containerEl.querySelectorAll(".sample-card").forEach((card) => {
      card.addEventListener("click", () => loadSampleById(card.dataset.id, card));
    });
  }

  async function loadSampleById(id, cardEl) {
    try {
      const data = await getJSON(`/samples/${id}`);
      if (cardEl) {
        if (lastSelectedCard) lastSelectedCard.classList.remove("active");
        cardEl.classList.add("active");
        lastSelectedCard = cardEl;
      }
      if (typeof onSelect === "function") onSelect(data);
    } catch (e) {
      console.error(e);
      alert(`Could not load sample ${id}: ${e.message}`);
    }
  }

  window.Samples = { init, loadSampleById };
})();
