// IT Helpdesk Copilot front end. All model and ticket text is inserted with textContent (no innerHTML).
"use strict";

const $ = (id) => document.getElementById(id);
const MODE_LABELS = {
  answer: "Grounded answer",
  clarify: "Needs more information",
  insufficient_sources: "No matching guide",
};

let samples = [];

async function loadSamples() {
  try {
    const res = await fetch("/api/samples");
    samples = await res.json();
  } catch (err) {
    samples = [];
  }
  const box = $("samples");
  samples.forEach((sample) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = sample.title;
    btn.addEventListener("click", () => {
      $("ticket").value = sample.ticket;
      $("ticket").focus();
    });
    box.appendChild(btn);
  });

  // Optional deep link for demos: /?sample=<id>&run=1
  const params = new URLSearchParams(window.location.search);
  const wanted = samples.find((s) => s.id === params.get("sample"));
  if (wanted) {
    $("ticket").value = wanted.ticket;
    if (params.get("run") === "1") submitTicket();
  }
}

function citationLink(citation, label) {
  const a = document.createElement("a");
  a.href = citation.url;
  a.target = "_blank";
  a.rel = "noopener";
  a.textContent = label;
  a.title = `${citation.guide} > ${citation.section}`;
  return a;
}

function render(data) {
  $("result").hidden = false;
  const mode = $("mode");
  mode.textContent = MODE_LABELS[data.mode] || data.mode;
  mode.className = `badge badge-${data.mode}`;
  $("summary").textContent = data.summary || "";

  $("question-box").hidden = !data.clarifying_question;
  $("question").textContent = data.clarifying_question || "";

  const esc = data.escalation || {};
  $("escalation-box").hidden = !esc.recommended;
  $("escalation").textContent = esc.reason || "";

  const byId = {};
  const sourceNumbers = {};
  (data.citations || []).forEach((c, i) => {
    byId[c.id] = c;
    sourceNumbers[c.id] = i + 1;
  });

  const steps = $("steps");
  steps.replaceChildren();
  (data.steps || []).forEach((step) => {
    const li = document.createElement("li");
    li.appendChild(document.createTextNode(step.text + " "));
    step.citations.forEach((id) => {
      if (!byId[id]) return;
      const sup = document.createElement("sup");
      sup.appendChild(citationLink(byId[id], `[${sourceNumbers[id]}]`));
      li.appendChild(sup);
    });
    steps.appendChild(li);
  });
  $("steps-box").hidden = !(data.steps || []).length;

  const sources = $("sources");
  sources.replaceChildren();
  (data.citations || []).forEach((c, i) => {
    const li = document.createElement("li");
    li.appendChild(document.createTextNode(`[${i + 1}] `));
    li.appendChild(citationLink(c, `${c.guide} > ${c.section}`));
    const meta = document.createElement("span");
    meta.className = "muted";
    meta.textContent = `  ${c.id} (score ${c.score.toFixed(3)})`;
    li.appendChild(meta);
    sources.appendChild(li);
  });
  $("sources-box").hidden = !(data.citations || []).length;

  $("draft-box").hidden = !data.draft_reply;
  $("draft").value = data.draft_reply || "";

  const r = data.retrieval || { hits: [] };
  const diag = data.diagnostics || {};
  $("retrieval-meta").textContent =
    `Gate: ${r.gate} | top score ${Number(r.top_score || 0).toFixed(3)} (minimum ${r.min_score}) | ` +
    `guide lead ${Number(r.doc_margin || 0).toFixed(3)} | shared words ${(r.shared_terms || []).length} | ` +
    `LLM called: ${diag.llm_called ? "yes" : "no"}${diag.model ? " (" + diag.model + ")" : ""} | ` +
    `time ${(diag.latency_ms / 1000 || 0).toFixed(1)} s` +
    (diag.dropped_steps ? ` | steps removed by checks: ${diag.dropped_steps}` +
      ` (${(diag.ungrounded_steps || []).length} not supported by any retrieved section)` : "") +
    (diag.reattributed_steps ? ` | citations re-attributed: ${diag.reattributed_steps}` : "");
  const hits = $("hits");
  hits.replaceChildren();
  (r.hits || []).forEach((h) => {
    const tr = document.createElement("tr");
    const td1 = document.createElement("td");
    td1.appendChild(citationLink(h, h.id));
    const td2 = document.createElement("td");
    td2.textContent = h.score.toFixed(3);
    const td3 = document.createElement("td");
    td3.textContent = h.used_as_context ? "yes" : "no";
    tr.append(td1, td2, td3);
    hits.appendChild(tr);
  });
}

async function submitTicket(event) {
  if (event) event.preventDefault();
  const ticket = $("ticket").value.trim();
  if (!ticket) return;
  $("submit").disabled = true;
  $("status").textContent = "Retrieving guides and generating locally on CPU (this can take 10-60 s)...";
  try {
    const res = await fetch("/api/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ticket }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    render(data);
    $("status").textContent = "Done.";
    document.body.dataset.state = "done";
  } catch (err) {
    $("status").textContent = `Error: ${err.message}`;
    document.body.dataset.state = "error";
  } finally {
    $("submit").disabled = false;
  }
}

$("ticket-form").addEventListener("submit", submitTicket);
$("copy").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("draft").value);
    $("copy").textContent = "Copied";
  } catch (err) {
    $("draft").select();
  }
  setTimeout(() => ($("copy").textContent = "Copy draft"), 1500);
});
loadSamples();
