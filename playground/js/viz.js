// viz.js — tiny SVG charting helpers (no dependencies).
// Every chart in the playground is drawn from these few functions so the
// visual language stays consistent: hairline axes, mono tick labels,
// one accent colour for loads and one for results.

export const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------------------------------------------------------------- numbers

/** Format a number with `sig` significant figures and thousands separators. */
export function fmt(v, sig = 3) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  if (!Number.isFinite(v)) return "∞";
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e9 || a < 1e-4) {
    const [m, e] = v.toExponential(sig - 1).split("e");
    return `${m}×10${sup(e)}`;
  }
  const rounded = Number(v.toPrecision(sig));
  const decimals = Math.max(0, sig - 1 - Math.floor(Math.log10(a)));
  return rounded.toLocaleString("en-US", { maximumFractionDigits: Math.min(decimals, 6) });
}

const SUP = { "-": "⁻", "+": "", 0: "⁰", 1: "¹", 2: "²", 3: "³", 4: "⁴", 5: "⁵", 6: "⁶", 7: "⁷", 8: "⁸", 9: "⁹" };
const sup = (s) => String(s).split("").map((c) => SUP[c] ?? c).join("");

/** Fixed decimals, with separators. */
export const fixed = (v, d = 1) =>
  v === null || v === undefined || !Number.isFinite(v) ? (v === null ? "∞" : "—")
    : v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

// ---------------------------------------------------------------- scales

export function linear(d0, d1, r0, r1) {
  const k = (r1 - r0) / (d1 - d0 || 1);
  const f = (v) => r0 + (v - d0) * k;
  f.domain = [d0, d1];
  f.ticks = (n = 5) => niceTicks(d0, d1, n);
  return f;
}

export function log(d0, d1, r0, r1) {
  const l0 = Math.log10(d0), l1 = Math.log10(d1);
  const f = (v) => r0 + ((Math.log10(Math.max(v, 1e-300)) - l0) / (l1 - l0 || 1)) * (r1 - r0);
  f.domain = [d0, d1];
  f.ticks = () => {
    const out = [];
    for (let e = Math.floor(l0); e <= Math.ceil(l1); e++) {
      const t = 10 ** e;
      if (t >= d0 * 0.999 && t <= d1 * 1.001) out.push(t);
    }
    return out;
  };
  return f;
}

export function niceTicks(min, max, count = 5) {
  if (min === max) return [min];
  const span = Math.abs(max - min);
  const raw = span / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const lo = Math.ceil(Math.min(min, max) / step) * step;
  const out = [];
  for (let t = lo; t <= Math.max(min, max) + step * 1e-9; t += step) out.push(Math.abs(t) < step * 1e-9 ? 0 : t);
  return out;
}

/** Expand a [min,max] range a little and snap to nice numbers. */
export function niceDomain(min, max, padFrac = 0.08) {
  if (min === max) { const d = Math.abs(min) || 1; return [min - d, max + d]; }
  const pad = (max - min) * padFrac;
  return [min - pad, max + pad];
}

// ---------------------------------------------------------------- paths

export function path(xs, ys, sx, sy) {
  let d = "", pen = false;
  for (let i = 0; i < xs.length; i++) {
    const y = ys[i];
    if (y === null || y === undefined || !Number.isFinite(y)) { pen = false; continue; }
    d += `${pen ? "L" : "M"}${sx(xs[i]).toFixed(2)} ${sy(y).toFixed(2)}`;
    pen = true;
  }
  return d;
}

/** Closed area between a curve and the baseline y=0. */
export function area(xs, ys, sx, sy) {
  const base = sy(0);
  let d = `M${sx(xs[0]).toFixed(2)} ${base.toFixed(2)}`;
  for (let i = 0; i < xs.length; i++) d += `L${sx(xs[i]).toFixed(2)} ${sy(ys[i]).toFixed(2)}`;
  return d + `L${sx(xs[xs.length - 1]).toFixed(2)} ${base.toFixed(2)}Z`;
}

// ---------------------------------------------------------------- frames

/**
 * Axes + grid for a chart region.
 * opts: {x, y, box:[x0,y0,x1,y1], xLabel, yLabel, xFmt, yFmt, xTicks, yTicks}
 */
export function frame(o) {
  const [x0, y0, x1, y1] = o.box;
  const xt = o.xTicks ?? o.x.ticks(5);
  const yt = o.yTicks ?? o.y.ticks(4);
  const xf = o.xFmt ?? ((v) => fmt(v));
  const yf = o.yFmt ?? ((v) => fmt(v));
  let s = `<g class="frame">`;
  for (const t of yt) {
    const y = o.y(t);
    s += `<line class="grid" x1="${x0}" x2="${x1}" y1="${y}" y2="${y}"/>`;
    s += `<text class="tick" x="${x0 - 8}" y="${y + 3.5}" text-anchor="end">${esc(yf(t))}</text>`;
  }
  for (const t of xt) {
    const x = o.x(t);
    s += `<line class="grid" x1="${x}" x2="${x}" y1="${y0}" y2="${y1}"/>`;
    s += `<text class="tick" x="${x}" y="${y1 + 16}" text-anchor="middle">${esc(xf(t))}</text>`;
  }
  s += `<path class="axis" d="M${x0} ${y0}V${y1}H${x1}"/>`;
  if (o.xLabel) s += `<text class="axis-label" x="${x1}" y="${y1 + 34}" text-anchor="end">${esc(o.xLabel)}</text>`;
  if (o.yLabel) s += `<text class="axis-label" x="${x0}" y="${y0 - 12}" text-anchor="start">${esc(o.yLabel)}</text>`;
  return s + `</g>`;
}

export const svg = (w, h, body, label = "") =>
  `<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="${esc(label)}" preserveAspectRatio="xMidYMid meet">${body}</svg>`;

export function arrowDown(x, yTip, len, cls = "load", head = 7) {
  return `<g class="${cls}"><line x1="${x}" y1="${yTip - len}" x2="${x}" y2="${yTip - head}"/>` +
    `<path class="fill" d="M${x - head * 0.55} ${yTip - head}L${x} ${yTip}L${x + head * 0.55} ${yTip - head}Z"/></g>`;
}

/** Dimension line with end ticks and a centred label. */
export function dim(x0, x1, y, label, cls = "dim") {
  const mx = (x0 + x1) / 2;
  const w = label.length * 6.6 + 14;
  return `<g class="${cls}"><line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}"/>` +
    `<path class="fill" d="M${x0} ${y}l8 -3v6Z M${x1} ${y}l-8 -3v6Z"/>` +
    `<line x1="${x0}" y1="${y - 8}" x2="${x0}" y2="${y + 8}"/><line x1="${x1}" y1="${y - 8}" x2="${x1}" y2="${y + 8}"/>` +
    `<rect class="knock" x="${mx - w / 2}" y="${y - 9}" width="${w}" height="18"/>` +
    `<text x="${mx}" y="${y + 4}" text-anchor="middle">${esc(label)}</text></g>`;
}

/** Hatched fixed support (wall). side = "left" | "right" | "bottom" | "top" */
export function wall(x, y0, y1, side = "left") {
  const sg = side === "left" ? -1 : 1;
  let s = `<g class="support"><line x1="${x}" y1="${y0}" x2="${x}" y2="${y1}" class="heavy"/>`;
  for (let y = y0 + 3; y < y1; y += 8) s += `<line x1="${x}" y1="${y}" x2="${x + sg * 9}" y2="${y + 9}"/>`;
  return s + `</g>`;
}

export function groundH(x0, x1, y) {
  let s = `<g class="support"><line x1="${x0}" y1="${y}" x2="${x1}" y2="${y}" class="heavy"/>`;
  for (let x = x0 + 3; x < x1; x += 8) s += `<line x1="${x}" y1="${y}" x2="${x - 8}" y2="${y + 8}"/>`;
  return s + `</g>`;
}

export function pin(x, y, r = 4) {
  return `<g class="support"><path d="M${x} ${y}l-9 14h18Z" class="tri"/><circle cx="${x}" cy="${y}" r="${r}" class="hinge"/></g>`;
}

export function roller(x, y) {
  return `<g class="support"><path d="M${x} ${y}l-9 12h18Z" class="tri"/><circle cx="${x - 5}" cy="${y + 15.5}" r="3" class="hinge"/><circle cx="${x + 5}" cy="${y + 15.5}" r="3" class="hinge"/></g>`;
}

// ---------------------------------------------------------------- gears

export function gearPath(cx, cy, teeth, module) {
  const r = (module * teeth) / 2, ra = r + module, rf = r - 1.25 * module;
  const p = (2 * Math.PI) / teeth;
  const pts = [];
  for (let i = 0; i < teeth; i++) {
    const c = i * p;
    for (const [rad, da] of [[rf, -0.3], [ra, -0.14], [ra, 0.14], [rf, 0.3]]) {
      const a = c + da * p;
      pts.push(`${(cx + rad * Math.cos(a)).toFixed(2)} ${(cy + rad * Math.sin(a)).toFixed(2)}`);
    }
  }
  return "M" + pts.join("L") + "Z";
}
