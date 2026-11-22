// remgtd View: renders the server's state; never changes Reminders.

const ui = {
  data: null,
  guide: [],
  expanded: new Set(JSON.parse(localStorage.getItem("remgtd.guide.expanded") || "[]")),
  connected: false,
  tab: localStorage.getItem("remgtd.tab") || "system",
  sphere: localStorage.getItem("remgtd.sphere") || "all",
  problemsOnly: false,
};

const $ = (sel) => document.querySelector(sel);
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;

// --- data helpers ---------------------------------------------------------------

const item = (id) => ui.data.items[String(id)];
const items = (ids) => (ids || []).map(item).filter(Boolean);
const kindOf = (tag) => (ui.data.contexts.find((c) => c.tag.toLowerCase() === tag.toLowerCase()) || {}).kind;
const isAgenda = (tag) => (kindOf(tag) || "").toLowerCase() === ui.data.config.agendaKind.toLowerCase();
const findingsOf = (it) => it.findings.map((n) => ui.data.findings[n]);
const inSphere = (it) => ui.sphere === "all" || (ui.sphere === "work") === it.work;
const hasProblems = (it) => it.findings.length > 0 || items(it.children).some((c) => c.findings.length > 0);
const visible = (it) => inSphere(it) && (!ui.problemsOnly || hasProblems(it));

function actions() {
  const out = [];
  for (const loop of items(ui.data.lists.openLoops)) out.push(...items(loop.children));
  for (const na of items(ui.data.lists.nextActions)) out.push(na, ...items(na.children));
  return out;
}

// --- fragments ------------------------------------------------------------------

const badges = (it) =>
  findingsOf(it)
    .map((f) => `<span class="badge ${f.severity}" title="${esc(f.title + ": " + f.message)}">${f.rule}</span>`)
    .join("");

const chips = (tags) =>
  tags.map((t) => `<span class="chip ${isAgenda(t) ? "agenda" : ""}">#${esc(t)}</span>`).join("");

const workTag = (it) => (it.work && ui.sphere === "all" ? `<span class="tag-work">Work</span>` : "");

function row(it, { loopName = false, age = false } = {}) {
  const parent = it.parentId ? item(it.parentId) : null;
  const classes = ["row", it.isLead ? "lead" : "", it.contexts.length || it.role === "inbox" ? "" : "nocontext"];
  const sub = loopName && parent ? `<span class="sub">↳ ${esc(parent.title)}</span>` : "";
  const meta = [
    it.due ? `due ${esc(it.due)}` : "",
    age && it.ageDays != null ? `${it.ageDays} d` : "",
  ].filter(Boolean).join(" · ");
  return `<li class="${classes.join(" ")}" data-id="${it.id}">
    ${it.isLead || it.flagged ? `<span class="flag" title="${it.isLead ? "Lead Action" : "Flagged"}">⚑</span>` : ""}
    <span class="title">${esc(it.title)}${sub}</span>
    ${chips(it.contexts)} ${workTag(it)} ${meta ? `<span class="meta">${meta}</span>` : ""} ${badges(it)}
  </li>`;
}

const list = (rows, empty = "Nothing here.") =>
  rows.length ? `<ul class="plain">${rows.join("")}</ul>` : `<p class="empty">${esc(empty)}</p>`;

// --- tabs -----------------------------------------------------------------------

function loopsTab() {
  const loops = items(ui.data.lists.openLoops).filter(visible);
  const cards = loops.map((loop) => {
    const kids = items(loop.children).filter((c) => !ui.problemsOnly || c.findings.length || loop.findings.length);
    kids.sort((a, b) => (b.isLead - a.isLead) || (b.contexts.length > 0) - (a.contexts.length > 0));
    return `<div class="card">
      <div class="head" data-id="${loop.id}"><span class="title">${esc(loop.title)}</span>${workTag(loop)}${badges(loop)}</div>
      <ul>${kids.map((k) => row(k)).join("")}</ul>
    </div>`;
  });
  const singles = items(ui.data.lists.nextActions).filter(visible);
  return `<h2>Open Loops · ${loops.length}</h2>
    ${cards.join("") || `<p class="empty">No Open Loops${ui.sphere !== "all" ? " in this Sphere" : ""}.</p>`}
    <h2>Single Next Actions · ${singles.length}</h2>
    ${list(singles.map((it) => row(it)))}`;
}

function contextsTab() {
  const acts = actions().filter(visible);
  let html = "";
  for (const kind of ui.data.contextKinds) {
    const blocks = ui.data.contexts
      .filter((c) => c.kind === kind)
      .map((c) => ({ c, rows: acts.filter((a) => a.contexts.some((t) => t.toLowerCase() === c.tag.toLowerCase())) }))
      .filter((b) => b.rows.length);
    if (!blocks.length) continue;
    html += `<h2>${esc(kind)}</h2>`;
    for (const { c, rows } of blocks) {
      rows.sort((a, b) => b.isLead - a.isLead);
      html += `<h3>#${esc(c.tag)} <span class="meta">${rows.length}</span></h3>${list(rows.map((r) => row(r, { loopName: true })))}`;
    }
  }
  const none = acts.filter((a) => !a.contexts.length);
  if (none.length) html += `<h2>Without a Context</h2>${list(none.map((r) => row(r, { loopName: true })))}`;
  return html || `<p class="empty">No Next Actions${ui.sphere !== "all" ? " in this Sphere" : ""}.</p>`;
}

function waitingTab() {
  const rows = items(ui.data.lists.waitingFor).filter(visible);
  return `<h2>Waiting For · ${rows.length}</h2>${list(rows.map((r) => row(r, { age: true })), "Not waiting on anyone.")}`;
}

function reflectTab() {
  const byRule = (rule) =>
    ui.data.findings.filter((f) => f.rule === rule).flatMap((f) => f.itemIds).map(item).filter(Boolean).filter(inSphere);
  const stalled = byRule("R6");
  const oldWaiting = byRule("R12");
  const someday = items(ui.data.lists.someday).filter(visible);
  const sections = [...new Set(someday.map((s) => s.section || ""))].sort((a, b) => (a === "") - (b === "") || a.localeCompare(b));
  let html = "";
  if (stalled.length) html += `<h2>Stalled Open Loops</h2>${list(stalled.map((r) => row(r, { age: true })))}`;
  if (oldWaiting.length) html += `<h2>Waiting For, due for a follow-up</h2>${list(oldWaiting.map((r) => row(r, { age: true })))}`;
  html += `<h2>Autopilot</h2>${list(items(ui.data.lists.autopilot).filter(visible).map((r) => row(r)))}`;
  html += `<h2>Someday/Maybe · ${someday.length}</h2>`;
  for (const s of sections) {
    const rows = someday.filter((r) => (r.section || "") === s);
    html += (sections.length > 1 ? `<h3>${esc(s || "Unsorted")}</h3>` : "") + list(rows.map((r) => row(r)));
  }
  return html;
}

// --- System: the whole system on one screen -------------------------------------

function tile(title, tab, count, body, health = "") {
  return `<section class="tile">
    <header${tab ? ` data-goto="${tab}"` : ""}><span class="tile-title">${esc(title)}</span><span class="tile-count">${count}</span>${health}</header>
    ${body}
  </section>`;
}

function compact(rows, max = 8) {
  if (!rows.length) return `<p class="empty">Empty</p>`;
  const shown = rows.slice(0, max).map((it) => `<li data-id="${it.id}">${it.isLead || it.flagged ? "⚑ " : ""}${esc(it.title)} ${badges(it)}</li>`);
  const more = rows.length > max ? `<li class="more">+${rows.length - max} more</li>` : "";
  return `<ul class="compact">${shown.join("")}${more}</ul>`;
}

const ok = (good, text) => `<span class="health ${good ? "good" : "attention"}">${good ? "✓" : "!"} ${esc(text)}</span>`;

function systemTab() {
  const d = ui.data;
  const { violations, hints } = d.counts;
  const head = violations
    ? `<div class="verdict attention">${plural(violations, "Violation")} · ${plural(hints, "Hint")}: the system has drifted from the book.</div>`
    : `<div class="verdict good">By the book. ${hints ? `${plural(hints, "Hint")} to look at.` : "Nothing to look at."}</div>`;

  const inbox = items(d.lists.inbox);
  const oldest = d.steps.oldestInboxDays;
  const inboxTile = tile("In-box", "", inbox.length, compact(inbox),
    ok(!inbox.length || oldest <= d.config.thresholds.inboxDays, inbox.length ? `oldest ${oldest} d` : "empty"));

  const loops = items(d.lists.openLoops).filter(inSphere);
  const loopRows = loops.map((loop) => {
    const lead = items(loop.children).find((c) => c.isLead);
    return `<li data-id="${loop.id}"><span class="loop">${esc(loop.title)}</span> ${badges(loop)}
      ${lead ? `<span class="lead-line" data-id="${lead.id}">⚑ ${esc(lead.title)} ${chips(lead.contexts)}</span>` : `<span class="lead-line missing">no Lead Action</span>`}</li>`;
  });
  const loopsBad = loops.filter((l) => l.findings.some((n) => d.findings[n].severity === "violation")).length;
  const loopsTile = tile("Open Loops", "loops", loops.length,
    loops.length ? `<ul class="compact loops">${loopRows.join("")}</ul>` : `<p class="empty">None</p>`,
    ok(!loopsBad, loopsBad ? `${loopsBad} need attention` : "all have a Lead Action"));

  const acts = actions().filter(inSphere);
  let ctxBody = "";
  for (const kind of d.contextKinds) {
    const counts = d.contexts
      .filter((c) => c.kind === kind)
      .map((c) => [c.tag, acts.filter((a) => a.contexts.some((t) => t.toLowerCase() === c.tag.toLowerCase())).length])
      .filter(([, n]) => n);
    if (counts.length) ctxBody += `<div class="kind"><span class="kind-name">${esc(kind)}</span>${counts.map(([t, n]) => `<span class="chip">#${esc(t)} ${n}</span>`).join(" ")}</div>`;
  }
  const noCtx = acts.filter((a) => !a.contexts.length).length;
  const nextTile = tile("Next Actions", "contexts", acts.filter((a) => a.contexts.length).length,
    (ctxBody || `<p class="empty">None</p>`) + `<p class="meta">${items(d.lists.nextActions).filter(inSphere).length} single, the rest inside Open Loops</p>`,
    ok(!noCtx, noCtx ? `${noCtx} without a Context` : "all have a Context"));

  const waiting = items(d.lists.waitingFor).filter(inSphere);
  const waitingTile = tile("Waiting For", "waiting", waiting.length, compact(waiting),
    ok(!d.steps.oldWaiting, d.steps.oldWaiting ? `${d.steps.oldWaiting} to follow up` : "current"));

  const someday = items(d.lists.someday).filter(inSphere);
  const bySection = {};
  for (const s of someday) bySection[s.section || "Unsorted"] = (bySection[s.section || "Unsorted"] || 0) + 1;
  const somedayTile = tile("Someday/Maybe", "reflect", someday.length,
    `<div class="kind">${Object.entries(bySection).map(([s, n]) => `<span class="chip">${esc(s)} ${n}</span>`).join(" ")}</div>`);

  const autopilot = items(d.lists.autopilot).filter(inSphere);
  const autoTile = tile("Autopilot", "reflect", autopilot.length, compact(autopilot));

  return `${head}<div class="tiles">${inboxTile}${loopsTile}${nextTile}${waitingTile}${somedayTile}${autoTile}</div>`;
}

// --- Step Guide -------------------------------------------------------------------

const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<code>$1</code>");

function stepStatus(id) {
  const s = ui.data.steps;
  const leads = s.leadActions.filter((l) => ui.sphere === "all" || (ui.sphere === "work") === l.work).length;
  switch (id) {
    case "capture": {
      const c = s.checklist;
      const sweep = c ? ` · ${esc(c.name)} ${c.done}/${c.total}` : "";
      return [true, `In-box ${s.inbox}${sweep}`];
    }
    case "clarify":
      return s.inbox ? [s.oldestInboxDays <= ui.data.config.thresholds.inboxDays, `${s.inbox} to clarify · oldest ${s.oldestInboxDays} d`] : [true, "In-box empty"];
    case "organize":
      return s.violations ? [false, `${plural(s.violations, "Violation")} · mostly ${s.topViolation.rule}`] : [true, "No Violations"];
    case "reflect": {
      const parts = [];
      if (s.stalled) parts.push(`${s.stalled} stalled`);
      if (s.oldWaiting) parts.push(`${s.oldWaiting} to follow up`);
      const link = ui.data.config.weeklyReviewUrl ? ` · <a href="${esc(ui.data.config.weeklyReviewUrl)}" target="_blank" rel="noopener">weekly review ↗</a>` : "";
      return [!parts.length, (parts.join(" · ") || "Current") + link, true];
    }
    case "engage":
      return [true, `${plural(leads, "Lead Action")}`];
    default:
      return [true, ""];
  }
}

function bulletList(entries) {
  return `<ul>${entries.map((e) => `<li class="d${e.depth}">${inline(e.text)}</li>`).join("")}</ul>`;
}

function renderGuide() {
  const el = $("#guide");
  if (!ui.guide.length || !ui.data || !ui.data.steps) return;
  el.innerHTML = ui.guide
    .map((card) => {
      const [good, text, raw] = stepStatus(card.id);
      const open = ui.expanded.has(card.id);
      return `<article class="step ${open ? "open" : ""}">
        <header data-step="${card.id}">
          <span class="step-name">${card.n}. ${esc(card.name)}</span>
          <span class="step-status ${good ? "good" : "attention"}">${raw ? text : esc(text)}</span>
        </header>
        ${open ? `<div class="step-body">
          <p>${inline(card.purpose)}</p>
          <p class="from-to"><span>From</span> ${inline(card.start)}<br><span>To</span> ${inline(card.end)}</p>
          ${card.questions.length ? `<h4>Key questions${card.questionsNote ? ` <em>${esc(card.questionsNote)}</em>` : ""}</h4>${bulletList(card.questions)}` : ""}
          ${card.advice.length ? `<h4>Advice</h4>${bulletList(card.advice)}` : ""}
        </div>` : ""}
      </article>`;
    })
    .join("");
}

const TABS = { system: systemTab, loops: loopsTab, contexts: contextsTab, waiting: waitingTab, reflect: reflectTab };

// --- chrome -----------------------------------------------------------------------

function renderChrome() {
  document.querySelectorAll("[data-sphere]").forEach((b) => b.classList.toggle("on", b.dataset.sphere === ui.sphere));
  document.querySelectorAll("[data-tab]").forEach((b) => b.classList.toggle("on", b.dataset.tab === ui.tab));
  const status = $("#status");
  status.className = "status " + (ui.connected ? (ui.data && ui.data.ok === false ? "stale" : "live") : "");

  const banner = $("#banner");
  let msg = "";
  if (!ui.connected) msg = "Not connected. Run <code>remgtd open</code> to start the server.";
  else if (ui.data && ui.data.ok === false) msg = `Can't read Reminders: ${esc(ui.data.error)}${ui.data.items && Object.keys(ui.data.items).length ? " (showing the last known data)" : ""}`;
  else if (ui.data && ui.data.groupFound === false) msg = `List group “${esc(ui.data.config.group)}” not found in Reminders. Set <code>group</code> in the config.`;
  banner.innerHTML = msg;
  banner.hidden = !msg;

  if (!ui.data || !ui.data.counts) return;
  const { violations, hints } = ui.data.counts;
  const p = $("#problems");
  p.innerHTML = `<span class="${violations ? "v" : "zero"}">${plural(violations, "Violation")}</span> · <span class="${hints ? "h" : "zero"}">${plural(hints, "Hint")}</span>`;
  p.classList.toggle("on", ui.problemsOnly);
}

function render() {
  renderChrome();
  if (!ui.data || !ui.data.lists || !ui.data.lists.openLoops) return;
  if (!TABS[ui.tab]) ui.tab = "system";
  renderGuide();
  const y = window.scrollY;
  let html = "";
  if (ui.problemsOnly) {
    const general = ui.data.findings.filter((f) => !f.itemIds.length);
    if (general.length) {
      html += `<h2>System</h2><ul class="findings">${general
        .map((f) => `<li><span class="badge ${f.severity}">${f.rule}</span> ${esc(f.message)}</li>`)
        .join("")}</ul>`;
    }
  }
  html += TABS[ui.tab]();
  $("#main").innerHTML = html;
  window.scrollTo(0, y);
}

// --- events -----------------------------------------------------------------------

document.addEventListener("click", async (e) => {
  const sphere = e.target.closest("[data-sphere]");
  if (sphere) {
    ui.sphere = sphere.dataset.sphere;
    localStorage.setItem("remgtd.sphere", ui.sphere);
    return render();
  }
  const tab = e.target.closest("[data-tab]");
  if (tab) {
    ui.tab = tab.dataset.tab;
    localStorage.setItem("remgtd.tab", ui.tab);
    return render();
  }
  if (e.target.closest("a")) return;
  const step = e.target.closest("[data-step]");
  if (step) {
    const id = step.dataset.step;
    ui.expanded.has(id) ? ui.expanded.delete(id) : ui.expanded.add(id);
    localStorage.setItem("remgtd.guide.expanded", JSON.stringify([...ui.expanded]));
    return renderGuide();
  }
  const goto = e.target.closest("[data-goto]");
  if (goto && !e.target.closest("[data-id]")) {
    ui.tab = goto.dataset.goto;
    localStorage.setItem("remgtd.tab", ui.tab);
    window.scrollTo(0, 0);
    return render();
  }
  if (e.target.closest("#problems")) {
    ui.problemsOnly = !ui.problemsOnly;
    return render();
  }
  const target = e.target.closest("[data-id]");
  if (target) {
    await fetch(`/open/${target.dataset.id}`, { method: "POST", headers: { "X-Remgtd": "1" } }).catch(() => {});
  }
});

function connect() {
  const source = new EventSource("/events");
  source.addEventListener("state", (e) => {
    ui.data = JSON.parse(e.data);
    ui.connected = true;
    render();
  });
  source.onopen = () => {
    ui.connected = true;
    renderChrome();
  };
  source.onerror = () => {
    ui.connected = false;
    renderChrome();
  };
}

render();
connect();
fetch("/guide.json")
  .then((r) => r.json())
  .then((cards) => {
    ui.guide = cards;
    renderGuide();
  })
  .catch(() => {});
