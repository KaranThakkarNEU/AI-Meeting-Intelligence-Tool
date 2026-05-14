/**
 * renderers.js — one render function per pipeline stage.
 * Exposes a global `Renderers` object with a render function per stage event.
 */
(function () {
  "use strict";
  const { escapeHTML } = window.API;

  let resultsEl = null;
  let sortKey = "priority";
  let sortAsc = false;

  function setContainer(el) { resultsEl = el; }
  function clear() {
    if (resultsEl) resultsEl.innerHTML = "";
    sortKey = "priority"; sortAsc = false;
  }

  function makeCard(stage, title, bodyHTML, meta = "") {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="head">
        <h4><span class="stage-badge ${stage}"></span>${escapeHTML(title)}</h4>
        <div class="meta">${escapeHTML(meta)}</div>
      </div>
      ${bodyHTML}
    `;
    resultsEl.appendChild(card);
    requestAnimationFrame(() => card.classList.add("visible"));
    card.scrollIntoView({ behavior: "smooth", block: "nearest" });
    return card;
  }

  function preprocessing(data) {
    const speakers = data.speakers || [];
    const body = `
      <div class="meta-grid">
        <div class="stat"><div class="label">Utterances</div><div class="val">${data.utterance_count}</div></div>
        <div class="stat"><div class="label">Speakers</div><div class="val">${speakers.length}</div></div>
      </div>
      <div class="speakers" style="margin-top:10px;">
        ${speakers.map((s) => `<span class="tag">${escapeHTML(s)}</span>`).join("")}
      </div>`;
    return makeCard("preprocessing", "Preprocessing", body, `${data.utterance_count} utterances`);
  }

  function actionItems(data) {
    const items = data.items || [];
    if (!items.length) {
      return makeCard("action_items", "Action Items",
        `<div class="empty">No action items extracted.</div>`, "0 items");
    }
    const prio = { high: 3, medium: 2, low: 1 };
    const sorted = [...items].sort((a, b) => {
      let av, bv;
      if (sortKey === "priority") { av = prio[a.priority]; bv = prio[b.priority]; }
      else if (sortKey === "confidence") { av = a.confidence; bv = b.confidence; }
      else if (sortKey === "assignee") { av = (a.assignee || "").toLowerCase(); bv = (b.assignee || "").toLowerCase(); }
      else if (sortKey === "due_date") { av = a.due_date || ""; bv = b.due_date || ""; }
      else { av = a.description; bv = b.description; }
      if (av < bv) return sortAsc ? -1 : 1;
      if (av > bv) return sortAsc ? 1 : -1;
      return 0;
    });
    const arrow = (k) => sortKey === k ? (sortAsc ? "▲" : "▼") : "";
    const body = `
      <table>
        <thead><tr>
          <th data-sort="priority">Priority <span class="sort-arrow">${arrow("priority")}</span></th>
          <th data-sort="description">Description <span class="sort-arrow">${arrow("description")}</span></th>
          <th data-sort="assignee">Assignee <span class="sort-arrow">${arrow("assignee")}</span></th>
          <th data-sort="due_date">Due <span class="sort-arrow">${arrow("due_date")}</span></th>
          <th data-sort="confidence">Conf. <span class="sort-arrow">${arrow("confidence")}</span></th>
        </tr></thead>
        <tbody>
          ${sorted.map((it) => `
            <tr>
              <td><span class="priority ${it.priority}">${it.priority}</span></td>
              <td>${escapeHTML(it.description)}
                <span class="quote">"${escapeHTML(it.source_quote)}"</span>
              </td>
              <td>${escapeHTML(it.assignee || "—")}</td>
              <td>${escapeHTML(it.due_date || "—")}</td>
              <td class="conf">${(it.confidence * 100).toFixed(0)}%</td>
            </tr>`).join("")}
        </tbody>
      </table>`;
    const card = makeCard("action_items", "Action Items", body, `${items.length} items`);
    card.querySelectorAll("th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const k = th.dataset.sort;
        if (sortKey === k) sortAsc = !sortAsc;
        else { sortKey = k; sortAsc = false; }
        card.remove();
        actionItems(data);
      });
    });
    return card;
  }

  function decisions(data) {
    const items = data.items || [];
    if (!items.length) {
      return makeCard("decisions", "Decisions",
        `<div class="empty">No decisions captured.</div>`, "0 items");
    }
    const body = items.map((d) => `
      <div class="list-item decision">
        <div class="title">${escapeHTML(d.decision)}</div>
        <div class="row-tags">
          ${d.made_by ? `<span class="tag">by ${escapeHTML(d.made_by)}</span>` : ""}
          ${d.is_tentative ? `<span class="tag warn">tentative</span>` : `<span class="tag good">firm</span>`}
          ${d.dissent ? `<span class="tag bad">dissent</span>` : ""}
        </div>
        ${d.context ? `<div class="body">${escapeHTML(d.context)}</div>` : ""}
        <div class="quote">"${escapeHTML(d.source_quote)}"</div>
      </div>`).join("");
    return makeCard("decisions", "Decisions", body, `${items.length} items`);
  }

  function topics(data) {
    const items = data.items || [];
    const body = items.map((t) => `
      <div class="list-item topic">
        <div class="title">${escapeHTML(t.title)}</div>
        <div class="body">${escapeHTML(t.summary)}</div>
        <div class="range">utterances [${t.start_utterance_index}–${t.end_utterance_index}] · ${
          (t.speakers || []).map((s) => escapeHTML(s)).join(", ")
        }</div>
      </div>`).join("");
    return makeCard("topics", "Topics", body, `${items.length} segments`);
  }

  function sentiment(data) {
    const toneClass = { positive: "good", neutral: "", negative: "bad", mixed: "warn" }[data.overall_tone] || "";
    const ps = data.per_speaker || [];
    const body = `
      <div class="sentiment-row">
        <span class="tag ${toneClass}">tone: ${escapeHTML(data.overall_tone)}</span>
        <span class="tag">energy: ${escapeHTML(data.energy)}</span>
        ${data.conflict_detected ? `<span class="tag bad">⚠ conflict detected</span>` : `<span class="tag good">no conflict</span>`}
      </div>
      <div class="sentiment-grid">
        ${ps.map((s) => `
          <div class="sentiment-tile">
            <div class="name">${escapeHTML(s.speaker)}</div>
            <div class="sub">sentiment: ${escapeHTML(s.sentiment)} · engagement: ${escapeHTML(s.engagement)}</div>
          </div>`).join("")}
      </div>`;
    return makeCard("sentiment", "Sentiment", body, `${ps.length} speakers`);
  }

  function summary(data) {
    const body = `
      <div class="summary-text">${escapeHTML(data.executive_summary)}</div>
      <div class="meta-grid" style="margin-top:10px;">
        ${data.duration_minutes != null
          ? `<div class="stat"><div class="label">Est. duration</div><div class="val">${data.duration_minutes} min</div></div>` : ""}
        <div class="stat"><div class="label">Participants</div><div class="val">${data.participant_count}</div></div>
      </div>
      <h5 style="margin:14px 0 4px;font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;">Key takeaways</h5>
      <ul class="takeaways">
        ${(data.key_takeaways || []).map((k) => `<li>${escapeHTML(k)}</li>`).join("")}
      </ul>`;
    return makeCard("summary", `Summary — ${data.title}`, body);
  }

  function validation(data) {
    const rate = data.hallucination_rate;
    const cls = rate <= 0.03 ? "good" : rate <= 0.10 ? "warn" : "bad";
    const body = `
      <div class="sentiment-row">
        <span class="tag ${cls}" style="font-size:13px; padding:5px 12px;">
          hallucination rate: ${(rate * 100).toFixed(1)}%
        </span>
        <span class="tag">${data.flagged_fields}/${data.total_fields_checked} fields flagged</span>
      </div>
      ${(data.warnings || []).length ? `
        <details style="margin-top:10px;">
          <summary>${data.warnings.length} warning${data.warnings.length === 1 ? "" : "s"} ▾</summary>
          <div class="warn-list">
            ${data.warnings.map((w) => `
              <div class="warn-row">
                <code>${escapeHTML(w.stage)}.${escapeHTML(w.field)}</code><br>${escapeHTML(w.message)}
              </div>`).join("")}
          </div>
        </details>`
      : `<div class="hint" style="margin-top:8px;">✓ No semantic issues found.</div>`}`;
    return makeCard("validation", "Validation", body);
  }

  function complete(report) {
    const body = `
      <div class="meta-grid">
        <div class="stat"><div class="label">Latency</div><div class="val">${report.pipeline_latency_seconds.toFixed(2)}s</div></div>
        <div class="stat"><div class="label">Total tokens</div><div class="val">${report.total_tokens_used.toLocaleString()}</div></div>
        <div class="stat"><div class="label">Model</div><div class="val" style="font-size:12px;">${escapeHTML(report.model_used)}</div></div>
        <div class="stat"><div class="label">Stage errors</div><div class="val">${(report.stage_errors || []).length}</div></div>
      </div>`;
    return makeCard("preprocessing", "Pipeline Complete", body, "✓ done");
  }

  function error(stage, msg) {
    return makeCard(stage || "preprocessing", `Error in ${stage}`,
      `<div class="empty" style="color:#fca5a5;">${escapeHTML(msg)}</div>`);
  }

  window.Renderers = {
    setContainer, clear,
    preprocessing, action_items: actionItems, decisions, topics,
    sentiment, summary, validation, complete, error,
  };
})();
