// app.js — routing, state, inputs, undo/redo and rendering.

import { MODULES, defaults } from "./modules.js";
import { NOTES, ABOUT } from "./content.js";
import { History } from "./history.js";
import { esc, fmt } from "./viz.js";

const $ = (s, el = document) => el.querySelector(s);
const REPO = "https://github.com/Haneet10/Mech-Lab";
const byId = Object.fromEntries(MODULES.map((m) => [m.id, m]));
const motionOK = !matchMedia("(prefers-reduced-motion: reduce)").matches;

// ------------------------------------------------------------------ state

const state = {
  route: "beams",
  inputs: Object.fromEntries(MODULES.map((m) => [m.id, defaults(m)])),
};
const snapshot = () => JSON.stringify(state);
const history = new History();
let catalog = null;
let lastResult = null;

// ------------------------------------------------------------------ python engine

const engine = (() => {
  const params = new URLSearchParams(location.search);
  const local = params.get("pyodide");
  const url = new URL("js/worker.js", location.href);
  if (local) url.searchParams.set("pyodide", new URL(local, location.href).href);
  const worker = new Worker(url);
  const pending = new Map();
  let seq = 0;
  let readyResolve;
  const ready = new Promise((r) => (readyResolve = r));
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === "stage") setStatus("loading", m.text);
    else if (m.type === "ready") { readyResolve(m.info); }
    else if (m.type === "fatal") setStatus("error", "Python failed to load", m.error);
    else if (m.type === "result") { pending.get(m.id)?.(m); pending.delete(m.id); }
  };
  return {
    ready,
    call(name, args) {
      const id = ++seq;
      worker.postMessage({ id, name, args });
      return new Promise((res) => pending.set(id, res));
    },
  };
})();

// ------------------------------------------------------------------ shell

function buildRail() {
  const nav = $("#rail-list");
  nav.innerHTML = MODULES.map((m) =>
    `<a class="rail-item" href="#${m.id}" data-route="${m.id}">` +
    `<span class="rail-num">${m.num}</span><span class="rail-name">${esc(m.title)}</span>` +
    `<kbd class="rail-key">${Number(m.num)}</kbd></a>`).join("");
}

function setActiveRail() {
  document.querySelectorAll("[data-route]").forEach((a) => {
    const on = a.dataset.route === state.route;
    a.classList.toggle("active", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });
  const active = $(`.rail-item[data-route="${state.route}"]`);
  if (active && matchMedia("(max-width: 900px)").matches) active.scrollIntoView({ block: "nearest", inline: "center", behavior: motionOK ? "smooth" : "auto" });
}

function setStatus(kind, text, detail = "") {
  const el = $("#status");
  el.dataset.kind = kind;
  $("#status-text").textContent = text;
  el.title = detail || text;
}

// ------------------------------------------------------------------ routing

function render({ animate = true } = {}) {
  setActiveRail();
  const main = $("#main");
  if (animate && motionOK) { main.classList.remove("enter"); void main.offsetWidth; main.classList.add("enter"); }
  if (state.route === "about") { renderAbout(); document.title = "About · Mech Lab"; return; }
  const mod = byId[state.route];
  document.title = `${mod.title} · Mech Lab Playground`;
  const n = NOTES[mod.id] || {};
  main.innerHTML = `
    <header class="mod-head">
      <div class="mod-kicker"><span class="mod-num">${mod.num}</span><span class="sep">/</span>
        <a class="mod-src" href="${REPO}/blob/main/mech_toolkit/${mod.py}.py" target="_blank" rel="noopener">mech_toolkit.${mod.py}</a></div>
      <h1 class="mod-title">${esc(mod.title)}</h1>
      <p class="mod-lede">${esc(mod.tagline)}</p>
      <div class="mod-actions">
        <button class="btn ghost" id="reset" type="button">Reset</button>
        <button class="btn ghost" id="share" type="button">Copy link</button>
      </div>
    </header>

    <section class="work">
      <form class="inputs" id="inputs" autocomplete="off" aria-label="${esc(mod.title)} inputs"></form>
      <figure class="viz" aria-live="polite"><div id="viz" class="viz-body"><div class="viz-wait"><span class="spinner"></span>Waiting for Python</div></div></figure>
    </section>

    <section class="results" id="results" aria-live="polite"></section>
    <p class="reading" id="reading"></p>

    <section class="notes">
      <div class="note"><h2>Purpose</h2><p>${n.purpose ?? ""}</p></div>
      <div class="note"><h2>Approach</h2><ol>${(n.approach ?? []).map((a) => `<li>${a}</li>`).join("")}</ol></div>
      <div class="note"><h2>Reading the result</h2><p>${n.result ?? ""}</p>${n.source ? `<p class="source">${esc(n.source)}</p>` : ""}</div>
    </section>

    <section class="code">
      <header><span>Python · reproduce this result</span><button class="btn ghost small" id="copy-code" type="button">Copy</button></header>
      <pre><code id="code"></code></pre>
    </section>`;
  buildForm(mod);
  $("#reset").onclick = () => change(() => { state.inputs[mod.id] = defaults(mod); }, `Reset ${mod.title}`, null, true);
  $("#share").onclick = () => copy(location.href, "Link copied");
  $("#copy-code").onclick = () => copy($("#code").textContent, "Python copied");
  skeletonResults(mod);
  compute();
}

function renderAbout() {
  const a = ABOUT;
  const m = engineInfo;
  $("#main").innerHTML = `
    <header class="mod-head about-head">
      <div class="mod-kicker"><span class="mod-num">00</span><span class="sep">/</span><span>About</span></div>
      <h1 class="mod-title">${esc(a.title)}</h1>
      <p class="mod-lede wide">${a.lede}</p>
    </header>
    <section class="stats">
      <div><span class="k">Modules</span><span class="v">${MODULES.length}</span></div>
      <div><span class="k">Automated tests</span><span class="v">${m?.tests ?? "—"}</span></div>
      <div><span class="k">Python in browser</span><span class="v">${m?.python ?? "…"}</span></div>
      <div><span class="k">Server calls</span><span class="v">0</span></div>
    </section>
    ${a.sections.map((s) => `
      <section class="about-sec">
        <h2>${esc(s.heading)}</h2>
        ${s.body ? `<p>${s.body}</p>` : ""}
        ${s.items ? `<dl>${s.items.map(([k, v]) => `<div><dt>${esc(k)}</dt><dd>${v}</dd></div>`).join("")}</dl>` : ""}
      </section>`).join("")}
    <section class="about-sec"><h2>Links</h2><ul class="links">${a.links.map(([t, u]) => `<li><a href="${u}" target="_blank" rel="noopener">${esc(t)} <span aria-hidden="true">↗</span></a></li>`).join("")}</ul></section>`;
}

// ------------------------------------------------------------------ form

const labelOf = (f, i) => (typeof f.label === "function" ? f.label(i) : f.label);
const optionsOf = (f, i) => {
  if (f.options === "materials") return (catalog?.materials ?? [{ id: i[f.key], name: "Loading materials…" }]).map((m) => [m.id, m.name]);
  if (typeof f.options === "function") return f.options(i, catalog);
  return f.options;
};

// sliders: log mapping for wide positive ranges, linear otherwise
const useLog = (f) => f.min > 0 && f.max / f.min >= 50;
const toSlider = (f, v) => {
  const t = useLog(f) ? Math.log(v / f.min) / Math.log(f.max / f.min) : (v - f.min) / (f.max - f.min);
  return Math.round(Math.min(1, Math.max(0, t)) * 1000);
};
const fromSlider = (f, s) => {
  const t = s / 1000;
  const raw = useLog(f) ? f.min * Math.pow(f.max / f.min, t) : f.min + t * (f.max - f.min);
  const step = useLog(f) ? niceStep(raw, f.step) : f.step;
  return Number((Math.round(raw / step) * step).toFixed(6));
};
const niceStep = (v, base) => Math.max(base, 10 ** Math.floor(Math.log10(Math.abs(v) || 1)) / 10);

function buildForm(mod) {
  const form = $("#inputs");
  const i = state.inputs[mod.id];
  form.innerHTML = mod.fields.map((f) => fieldHTML(f, i)).join("");
  form.onsubmit = (e) => e.preventDefault();
  for (const f of mod.fields) wireField(mod, f);
  syncForm(mod);
}

function fieldHTML(f, i) {
  const id = `f-${f.key}`;
  const hint = f.hint ? `<p class="hint">${esc(f.hint)}</p>` : "";
  if (f.type === "number") {
    const slider = f.slider === false ? "" : `<input class="slider" type="range" min="0" max="1000" step="1" aria-label="${esc(labelOf(f, i))} slider" tabindex="-1">`;
    return `<div class="field num" data-key="${f.key}"><label for="${id}">${esc(labelOf(f, i))}</label>` +
      `<div class="numbox"><input id="${id}" type="number" inputmode="decimal" step="any" min="${f.min}" max="${f.max}" spellcheck="false"><span class="unit">${esc(f.unit ?? "")}</span></div>${slider}${hint}</div>`;
  }
  if (f.type === "seg") {
    return `<div class="field seg-field" data-key="${f.key}"><span class="label" id="${id}-l">${esc(labelOf(f, i))}</span>` +
      `<div class="seg" role="radiogroup" aria-labelledby="${id}-l">${f.options.map(([v, l]) => `<button type="button" role="radio" data-v="${esc(v)}">${esc(l)}</button>`).join("")}</div>${hint}</div>`;
  }
  if (f.type === "select") {
    return `<div class="field sel" data-key="${f.key}"><label for="${id}">${esc(labelOf(f, i))}</label><div class="selbox"><select id="${id}"></select><span class="chev" aria-hidden="true"></span></div>${hint}</div>`;
  }
  if (f.type === "stages") {
    return `<div class="field stages" data-key="${f.key}"><span class="label">${esc(labelOf(f, i))}</span><div class="stage-list"></div>` +
      `<button type="button" class="btn ghost small add-stage">+ Add stage</button><p class="hint">teeth on the driving gear → teeth on the driven gear</p></div>`;
  }
  return "";
}

function wireField(mod, f) {
  const box = $(`.field[data-key="${f.key}"]`);
  const inp = () => state.inputs[mod.id];
  if (f.type === "number") {
    const num = $("input[type=number]", box), sl = $(".slider", box);
    num.addEventListener("input", () => {
      const v = parseFloat(num.value);
      box.classList.toggle("invalid", !Number.isFinite(v));
      if (!Number.isFinite(v) || v === inp()[f.key]) return;
      box.classList.toggle("warn", v < f.min || v > f.max);
      setValue(mod, f, v, { fromNumber: true });
    });
    num.addEventListener("blur", () => { history.seal(); if (!Number.isFinite(parseFloat(num.value))) num.value = inp()[f.key]; box.classList.remove("invalid"); });
    num.addEventListener("keydown", (e) => {
      if (e.key !== "ArrowUp" && e.key !== "ArrowDown") return;
      e.preventDefault();
      const step = (e.shiftKey ? 10 : 1) * f.step;
      const v = Number((inp()[f.key] + (e.key === "ArrowUp" ? step : -step)).toFixed(6));
      setValue(mod, f, Math.min(f.max, Math.max(f.min, v)));
    });
    sl?.addEventListener("input", () => setValue(mod, f, fromSlider(f, +sl.value)));
    sl?.addEventListener("change", () => history.seal());
  } else if (f.type === "seg") {
    box.addEventListener("click", (e) => {
      const b = e.target.closest("button[data-v]");
      if (b && b.dataset.v !== inp()[f.key]) setValue(mod, f, b.dataset.v);
    });
    box.addEventListener("keydown", (e) => {
      if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
      const opts = f.options.map((o) => o[0]);
      const k = opts.indexOf(inp()[f.key]) + (e.key === "ArrowRight" ? 1 : -1);
      const v = opts[(k + opts.length) % opts.length];
      setValue(mod, f, v);
      $(`button[data-v="${CSS.escape(v)}"]`, box).focus();
      e.preventDefault();
    });
  } else if (f.type === "select") {
    $("select", box).addEventListener("change", (e) => setValue(mod, f, e.target.value));
  } else if (f.type === "stages") {
    box.addEventListener("input", (e) => {
      const t = e.target;
      if (!t.matches("input")) return;
      const v = parseInt(t.value, 10);
      if (!Number.isFinite(v) || v < 6 || v > 400) { t.parentElement.classList.add("invalid"); return; }
      t.parentElement.classList.remove("invalid");
      const k = +t.dataset.stage, side = +t.dataset.side;
      const next = structuredClone(inp().stages);
      if (next[k][side] === v) return;
      const before = next[k][side];
      next[k][side] = v;
      change(() => { inp().stages = next; }, `Stage ${k + 1} ${side ? "driven" : "driver"} ${before}T → ${v}T`, `stage-${k}-${side}`, false);
    });
    box.addEventListener("focusout", () => history.seal());
    box.addEventListener("click", (e) => {
      const rm = e.target.closest("[data-remove]");
      if (rm) {
        const k = +rm.dataset.remove;
        change(() => { inp().stages = inp().stages.filter((_, j) => j !== k); }, `Removed stage ${k + 1}`);
      }
      if (e.target.closest(".add-stage")) {
        const last = inp().stages[inp().stages.length - 1];
        change(() => { inp().stages = [...inp().stages, [last ? last[0] : 18, last ? last[1] : 54]]; }, `Added stage ${inp().stages.length + 1}`);
      }
    });
  }
}

function setValue(mod, f, v, { fromNumber = false } = {}) {
  const i = state.inputs[mod.id];
  const before = i[f.key];
  const label = labelOf(f, i);
  const show = (x) => {
    if (f.type === "number") return `${fmt(x, 6)}${f.unit ? " " + f.unit : ""}`;
    const o = optionsOf(f, i)?.find((p) => p[0] === x);
    return o ? o[1] : x;
  };
  const text = f.type === "number" ? `${label} ${show(before)} → ${show(v)}` : `${label}: ${show(v)}`;
  change(() => { i[f.key] = v; f.onChange?.(i); }, text, f.type === "number" ? `${mod.id}.${f.key}` : null, false, { skipNumber: fromNumber ? f.key : null });
}

/** Apply a mutation with an undo step, then refresh. */
function change(mutate, label, key = null, rebuild = false, opts = {}) {
  history.record(snapshot(), label, key);
  mutate();
  afterChange(rebuild, opts);
}

function afterChange(rebuild, opts = {}) {
  updateUndoButtons();
  writeHash();
  if (state.route === "about") return;
  const mod = byId[state.route];
  if (rebuild) buildForm(mod); else syncForm(mod, opts);
  compute();
}

function syncForm(mod, { skipNumber = null } = {}) {
  const i = state.inputs[mod.id];
  for (const f of mod.fields) {
    const box = $(`.field[data-key="${f.key}"]`);
    if (!box) continue;
    box.hidden = f.when ? !f.when(i) : false;
    const lab = $("label, .label", box);
    if (lab && typeof f.label === "function") lab.textContent = labelOf(f, i);
    if (f.type === "number") {
      const num = $("input[type=number]", box), sl = $(".slider", box);
      if (f.key !== skipNumber) { num.value = i[f.key]; box.classList.remove("invalid", "warn"); }
      if (sl) { sl.value = toSlider(f, i[f.key]); sl.style.setProperty("--p", `${sl.value / 10}%`); }
    } else if (f.type === "seg") {
      box.querySelectorAll("button[data-v]").forEach((b) => {
        const on = b.dataset.v === i[f.key];
        b.setAttribute("aria-checked", on);
        b.tabIndex = on ? 0 : -1;
      });
    } else if (f.type === "select") {
      const sel = $("select", box);
      const opts = optionsOf(f, i) ?? [];
      const html = opts.map(([v, l]) => `<option value="${esc(v)}">${esc(l)}</option>`).join("");
      if (sel.dataset.html !== html) { sel.innerHTML = html; sel.dataset.html = html; }
      sel.value = i[f.key];
      sel.disabled = f.options === "materials" && !catalog;
    } else if (f.type === "stages") {
      const list = $(".stage-list", box);
      const focused = document.activeElement?.dataset?.stage !== undefined ? [document.activeElement.dataset.stage, document.activeElement.dataset.side] : null;
      list.innerHTML = i.stages.map(([a, b], k) =>
        `<div class="stage"><span class="stage-n">${k + 1}</span>` +
        `<span class="numbox"><input type="number" inputmode="numeric" data-stage="${k}" data-side="0" value="${a}" aria-label="Stage ${k + 1} driver teeth"><span class="unit">T</span></span>` +
        `<span class="arrow" aria-hidden="true">→</span>` +
        `<span class="numbox"><input type="number" inputmode="numeric" data-stage="${k}" data-side="1" value="${b}" aria-label="Stage ${k + 1} driven teeth"><span class="unit">T</span></span>` +
        `<button type="button" class="icon-btn" data-remove="${k}" aria-label="Remove stage ${k + 1}" ${i.stages.length === 1 ? "disabled" : ""}>×</button></div>`).join("");
      if (focused) $(`input[data-stage="${focused[0]}"][data-side="${focused[1]}"]`, list)?.focus();
      $(".add-stage", box).disabled = i.stages.length >= 4;
    }
  }
}

// ------------------------------------------------------------------ compute

let computeSeq = 0;
let engineInfo = null;

async function compute() {
  if (state.route === "about") return;
  const mod = byId[state.route];
  const inputs = structuredClone(state.inputs[mod.id]);
  const my = ++computeSeq;
  await engine.ready;
  const req = mod.request(inputs);
  const res = await engine.call(req.name, req.args);
  if (my !== computeSeq || state.route !== mod.id) return; // a newer change won
  if (!res.ok) return showError(res.error);
  lastResult = res.result;
  showResult(mod, inputs, res.result, res.ms);
}

function showResult(mod, i, r, ms) {
  $("#results")?.classList.remove("error");
  const cells = mod.results(r, i);
  $("#results").innerHTML = cells.map((c) =>
    `<div class="cell ${c.tone ?? ""} ${c.wide ? "wide" : ""}">` +
    `<span class="k">${esc(c.label).replace(/([α-ωΔδσστ][₀-₉]*|[₀-₉]+)/g, '<span class="gk">$1</span>')}</span>` +
    `<span class="v"><span class="n">${esc(c.value)}</span>${c.unit ? `<span class="u">${esc(c.unit)}</span>` : ""}</span>` +
    (c.status ? `<span class="status"><i></i>${esc(c.status)}</span>` : c.sub ? `<span class="sub">${esc(c.sub)}</span>` : "") +
    `</div>`).join("");
  $("#reading").innerHTML = mod.reading(r, i);
  $("#viz").innerHTML = mod.viz(r, i, { motion: motionOK });
  $("#code").innerHTML = highlight(mod.code(i, materialName));
  setStatus("ready", `Python ${engineInfo?.python ?? ""} · ${ms < 1 ? "<1" : fmt(ms, 2)} ms`);
}

function showError(msg) {
  const r = $("#results");
  r.classList.add("error");
  r.innerHTML = `<div class="cell wide bad"><span class="k">Can't calculate this</span><span class="msg">${esc(msg)}</span></div>`;
  $("#reading").textContent = "Adjust the inputs above, or press Ctrl+Z to go back.";
}

function skeletonResults(mod) {
  $("#results").innerHTML = Array.from({ length: 4 }, () => `<div class="cell sk"><span class="k"></span><span class="v"></span></div>`).join("");
}

const materialName = (key) => {
  const m = catalog?.materials.find((q) => q.id === key);
  return m && m.name.toLowerCase() === key ? m.name : key;
};

// tiny Python highlighter: comments, strings, numbers, keywords
function highlight(src) {
  const KW = /\b(from|import|as|print|for|in|def|return|f)\b/;
  return src.split("\n").map((line) => {
    let out = "", rest = line;
    const re = /(#.*$)|(f?"[^"]*")|(\b\d+(?:\.\d+)?(?:e-?\d+)?\b)|(\b(?:from|import|as|for|in|def|return)\b)/;
    let m;
    while ((m = re.exec(rest))) {
      out += esc(rest.slice(0, m.index));
      const cls = m[1] ? "c" : m[2] ? "s" : m[3] ? "n" : "k";
      out += `<span class="${cls}">${esc(m[0])}</span>`;
      rest = rest.slice(m.index + m[0].length);
    }
    void KW;
    return out + esc(rest);
  }).join("\n");
}

// ------------------------------------------------------------------ undo / redo

function undo() {
  const step = history.undo(snapshot());
  if (!step) return toast("Nothing to undo");
  restore(step.snapshot);
  toast(`Undo · ${step.label}`, "Redo", redo);
}

function redo() {
  const step = history.redo(snapshot());
  if (!step) return toast("Nothing to redo");
  restore(step.snapshot);
  toast(`Redo · ${step.label}`, "Undo", undo);
}

function restore(snap) {
  const s = JSON.parse(snap);
  const routeChanged = s.route !== state.route;
  state.route = s.route;
  state.inputs = s.inputs;
  updateUndoButtons();
  writeHash();
  if (routeChanged) render(); else if (state.route !== "about") { buildForm(byId[state.route]); compute(); }
}

function updateUndoButtons() {
  $("#undo").disabled = !history.canUndo;
  $("#redo").disabled = !history.canRedo;
  $("#undo").title = history.canUndo ? `Undo: ${history.past[history.past.length - 1].label}  (Ctrl+Z)` : "Nothing to undo";
  $("#redo").title = history.canRedo ? `Redo: ${history.future[history.future.length - 1].label}  (Ctrl+Shift+Z)` : "Nothing to redo";
}

// ------------------------------------------------------------------ navigation + URL

function go(route, { record = true } = {}) {
  if (route === state.route) return;
  if (record) history.record(snapshot(), `Opened ${route === "about" ? "About" : byId[route].title}`);
  state.route = route;
  updateUndoButtons();
  writeHash();
  render();
  $("#main").focus({ preventScroll: true });
  window.scrollTo({ top: 0, behavior: motionOK ? "smooth" : "auto" });
}

function encode(mod, i) {
  const p = new URLSearchParams();
  const d = defaults(mod);
  for (const f of mod.fields) {
    const v = i[f.key];
    if (JSON.stringify(v) === JSON.stringify(d[f.key])) continue;
    p.set(f.key, f.type === "stages" ? v.map((s) => s.join("-")).join(".") : String(v));
  }
  return p.toString();
}

function writeHash() {
  const q = state.route === "about" ? "" : encode(byId[state.route], state.inputs[state.route]);
  const h = `#${state.route}${q ? "?" + q : ""}`;
  if (location.hash !== h) window.history.replaceState(null, "", h);
}

function readHash() {
  const [route, q] = location.hash.slice(1).split("?");
  if (route === "about") return { route };
  const mod = byId[route];
  if (!mod) return null;
  const i = defaults(mod);
  const p = new URLSearchParams(q || "");
  for (const f of mod.fields) {
    if (!p.has(f.key)) continue;
    const raw = p.get(f.key);
    if (f.type === "number") { const v = parseFloat(raw); if (Number.isFinite(v)) i[f.key] = v; }
    else if (f.type === "stages") {
      const st = raw.split(".").map((s) => s.split("-").map((n) => parseInt(n, 10))).filter((s) => s.length === 2 && s.every((n) => n >= 6 && n <= 400));
      if (st.length) i[f.key] = st.slice(0, 4);
    } else i[f.key] = raw;
  }
  return { route, inputs: i };
}

window.addEventListener("hashchange", () => {
  const h = readHash();
  if (!h) return;
  const same = h.route === state.route && (!h.inputs || JSON.stringify(h.inputs) === JSON.stringify(state.inputs[h.route]));
  if (same) return;
  history.record(snapshot(), h.route === "about" ? "Opened About" : `Opened ${byId[h.route].title}`);
  if (h.inputs) state.inputs[h.route] = h.inputs;
  const routeChanged = h.route !== state.route;
  state.route = h.route;
  updateUndoButtons();
  if (routeChanged) render(); else { buildForm(byId[state.route]); compute(); }
});

// ------------------------------------------------------------------ small UI bits

let toastTimer;
function toast(text, action, fn) {
  const t = $("#toast");
  t.innerHTML = `<span>${esc(text)}</span>${action ? `<button type="button">${esc(action)}</button>` : ""}`;
  if (action) $("button", t).onclick = () => { fn(); };
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2600);
}

async function copy(text, msg) {
  try { await navigator.clipboard.writeText(text); toast(msg); }
  catch { toast("Couldn't copy. Select the text and copy it manually"); }
}

function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem("mechlab-theme"); } catch { /* storage blocked */ }
  if (saved) document.documentElement.dataset.theme = saved;
  $("#theme").onclick = () => {
    const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("mechlab-theme", next); } catch { /* ignore */ }
  };
}

// ------------------------------------------------------------------ keyboard

window.addEventListener("keydown", (e) => {
  const mod = e.ctrlKey || e.metaKey;
  const k = e.key.toLowerCase();
  if (mod && !e.altKey && ((k === "z" && e.shiftKey) || k === "y")) { e.preventDefault(); history.seal(); redo(); return; }
  if (mod && !e.altKey && k === "z") { e.preventDefault(); history.seal(); undo(); return; }
  if (mod || e.altKey) return;
  const typing = e.target.closest?.("input, select, textarea, [contenteditable]");
  if (typing) return;
  if (/^[1-9]$/.test(e.key) && MODULES[+e.key - 1]) { go(MODULES[+e.key - 1].id); return; }
  if (e.key === "0") go("about");
});

document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-route]");
  if (a && !e.metaKey && !e.ctrlKey) { e.preventDefault(); go(a.dataset.route); return; }
  const set = e.target.closest("[data-set]");
  if (set && state.route !== "about") {
    const [key, value] = set.dataset.set.split("=");
    const mod = byId[state.route];
    const f = mod.fields.find((q) => q.key === key);
    if (f && state.inputs[mod.id][key] !== value) setValue(mod, f, value);
  }
});
document.addEventListener("keydown", (e) => {
  if ((e.key === "Enter" || e.key === " ") && e.target.matches?.("[data-set][role=button]")) { e.preventDefault(); e.target.click(); }
});

// ------------------------------------------------------------------ boot

function boot() {
  buildRail();
  initTheme();
  $("#undo").onclick = undo;
  $("#redo").onclick = redo;
  const h = readHash();
  if (h) { state.route = h.route; if (h.inputs) state.inputs[h.route] = h.inputs; }
  updateUndoButtons();
  render({ animate: false });
  writeHash();
  setStatus("loading", "Starting Python");
  engine.ready.then(async (info) => {
    engineInfo = info;
    const c = await engine.call("catalog", {});
    if (c.ok) catalog = c.result;
    setStatus("ready", `Python ${info.python} · ready`);
    if (state.route === "about") renderAbout(); else { syncForm(byId[state.route]); compute(); }
  });
}

boot();
