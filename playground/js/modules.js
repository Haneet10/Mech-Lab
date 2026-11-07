// modules.js — one entry per mech_toolkit module.
//
// Each module declares:
//   fields   the inputs, in the units a person would type (mm, kN, MPa ...)
//   request  turns those inputs into an SI call to py/bridge.py
//   results  the headline numbers
//   reading  a plain-language sentence on what the numbers mean
//   viz      the drawing / chart, as an SVG (or HTML) string
//   code     the equivalent Python, so anyone can reproduce the result
//
// To add a module: add an entry here, a handler in py/bridge.py, and notes
// in content.js. The rest of the app picks it up automatically.

import { esc, fmt, fixed, linear, log, niceDomain, path, area, frame, svg, arrowDown, dim, wall, pin, roller, groundH, gearPath } from "./viz.js";

const MM = 1e-3, KN = 1e3, MPA = 1e6;

const materialField = (def) => ({ key: "material", label: "Material", type: "select", options: "materials", def });

const sectionFields = [
  { key: "section", label: "Cross section", type: "seg", def: "rect", options: [["rect", "Rectangle"], ["circle", "Round"], ["tube", "Tube"]] },
  { key: "b", label: "Width b", type: "number", unit: "mm", def: 25, min: 2, max: 300, step: 1, when: (i) => i.section === "rect" },
  { key: "h", label: "Height h", type: "number", unit: "mm", def: 60, min: 2, max: 300, step: 1, when: (i) => i.section === "rect" },
  { key: "d", label: "Diameter d", type: "number", unit: "mm", def: 30, min: 2, max: 300, step: 1, when: (i) => i.section === "circle" },
  { key: "do", label: "Outer diameter", type: "number", unit: "mm", def: 60, min: 4, max: 300, step: 1, when: (i) => i.section === "tube" },
  { key: "di", label: "Inner diameter", type: "number", unit: "mm", def: 50, min: 0, max: 296, step: 1, when: (i) => i.section === "tube" },
];

const sectionArgs = (i) => ({ section: i.section, b: i.b * MM, h: i.h * MM, d: i.d * MM, do: i.do * MM, di: i.di * MM });

const sectionCode = (i, fnName = "I, c") => {
  if (i.section === "rect") return `${fnName} = beam_calculator.rectangular_section(width=${i.b * MM}, height=${i.h * MM})`;
  if (i.section === "circle") return `${fnName} = beam_calculator.circular_section(diameter=${i.d * MM})`;
  return `${fnName} = beam_calculator.hollow_circular_section(outer_diameter=${i.do * MM}, inner_diameter=${i.di * MM})`;
};

const sectionLabel = (i) =>
  i.section === "rect" ? `${i.b} × ${i.h} mm bar` : i.section === "circle" ? `Ø${i.d} mm rod` : `Ø${i.do} × ${(i.do - i.di) / 2} mm tube`;

const statusCell = (safe, fos, okWord = "Safe", badWord = "Fails") => ({
  label: "Safety factor",
  value: fos === null ? "∞" : fixed(fos, 2),
  status: safe ? okWord : badWord,
  tone: safe ? "ok" : "bad",
});

// ===================================================================== 01 BEAMS

const beams = {
  id: "beams",
  title: "Beams",
  py: "beam_calculator",
  tagline: "How far a beam bends under load, how hard it is stressed, and whether it holds.",
  fields: [
    { key: "support", label: "Supports", type: "seg", def: "cantilever", options: [["cantilever", "Cantilever"], ["simple", "Simply supported"]] },
    { key: "load_type", label: "Load", type: "seg", def: "point", options: [["point", "Point load"], ["udl", "Spread evenly"]] },
    { key: "L", label: "Span L", type: "number", unit: "m", def: 2, min: 0.2, max: 10, step: 0.05 },
    { key: "P", label: (i) => (i.load_type === "udl" ? "Total load" : "Load P"), type: "number", unit: "N", def: 400, min: 0, max: 20000, step: 10 },
    ...sectionFields,
    materialField("structural steel a36"),
  ],
  request: (i) => ({ name: "beam", args: { support: i.support, load_type: i.load_type, L: i.L, P: i.P, material: i.material, ...sectionArgs(i) } }),
  results: (r) => [
    { label: "Max stress", value: fmt(r.max_stress / MPA), unit: "MPa", tone: "result" },
    { label: "Max deflection", value: fmt(r.max_deflection / MM), unit: "mm", tone: "result" },
    { label: "Max moment", value: fmt(Math.abs(r.max_moment)), unit: "N·m" },
    statusCell(r.safe, r.fos),
  ],
  reading: (r, i) => {
    const ratio = r.max_deflection > 0 ? i.L / r.max_deflection : Infinity;
    const where = i.support === "cantilever" ? "The free end drops" : "The middle sags";
    const service = !Number.isFinite(ratio) ? "" : ratio >= 360
      ? ` That is span/${fmt(ratio, 3)}, stiffer than the common span/360 limit for floors.`
      : ` That is span/${fmt(ratio, 3)}, more flexible than the span/360 limit often used for floors, so it may feel bouncy even though it is strong enough.`;
    const verdict = r.safe
      ? `It carries the load with a safety factor of <b>${fixed(r.fos, 1)}</b>: the ${esc(r.material.name)} would only start to permanently bend at about ${fixed(r.fos, 1)}× this load.`
      : `It <b>fails</b>: the bending stress of ${fmt(r.max_stress / MPA)} MPa is above the ${fmt(r.material.Sy / MPA)} MPa yield strength of ${esc(r.material.name)}. Make the section deeper, shorten the span, or pick a stronger material.`;
    return `${verdict} ${where} <b>${fmt(r.max_deflection / MM)} mm</b>.${service} The beam weighs about ${fmt(r.mass)} kg.`;
  },
  viz: (r, i) => {
    const W = 720, H = 520, x0 = 96, x1 = 636;
    const sx = linear(0, i.L, x0, x1);
    const by = 112, amp = 42;
    const ymax = Math.max(...r.y.map(Math.abs)) || 1;
    const sy = (v) => by + (v / ymax) * amp;
    const ys = r.y;
    let s = "";
    // schematic
    s += `<text class="cap" x="${x0}" y="28">ELEVATION · DEFLECTION EXAGGERATED</text>`;
    s += `<path class="phantom" d="M${x0} ${by}H${x1}"/>`;
    s += `<path class="beam" d="${path(r.x, ys, sx, sy)}"/>`;
    s += `<path class="neutral" d="${path(r.x, ys, sx, sy)}"/>`;
    if (i.support === "cantilever") s += wall(x0, by - 34, by + 34);
    else s += pin(x0, by + 5) + roller(x1, by + 5) + groundH(x0 - 18, x0 + 18, by + 20) + groundH(x1 - 18, x1 + 18, by + 25);
    const tipX = i.support === "cantilever" ? x1 : (x0 + x1) / 2;
    const tipIdx = i.support === "cantilever" ? r.x.length - 1 : Math.floor(r.x.length / 2);
    if (i.load_type === "point") {
      s += arrowDown(tipX, sy(ys[tipIdx]) - 6, 54, "load", 9);
      s += `<text class="lbl load-t" x="${tipX + (i.support === "cantilever" ? -12 : 12)}" y="${sy(ys[tipIdx]) - 46}" text-anchor="${i.support === "cantilever" ? "end" : "start"}">P = ${fmt(i.P)} N</text>`;
    } else {
      const n = 13;
      let top = "";
      for (let k = 0; k < n; k++) {
        const xv = (i.L * (k + 0.5)) / n;
        const j = Math.round((xv / i.L) * (r.x.length - 1));
        const yy = sy(ys[j]) - 6;
        s += arrowDown(sx(xv), yy, 26, "load thin", 6);
        top += `${k ? "L" : "M"}${sx(xv).toFixed(1)} ${(yy - 26).toFixed(1)}`;
      }
      s += `<path class="load-line" d="${top}"/>`;
      s += `<text class="lbl load-t" x="${x1}" y="${by - 52}" text-anchor="end">w = ${fmt(i.P / i.L)} N/m</text>`;
    }
    // delta marker
    const dx = i.support === "cantilever" ? x1 + 22 : (x0 + x1) / 2 + 26;
    const dyv = sy(ys[tipIdx]);
    s += `<g class="res"><line x1="${dx}" y1="${by}" x2="${dx}" y2="${dyv}"/><path class="fill" d="M${dx} ${by}l-3 7h6Z M${dx} ${dyv}l-3 -7h6Z"/>` +
      `<text class="lbl" x="${dx + 8}" y="${(by + dyv) / 2 + 4}">δ ${fmt(r.max_deflection / MM)} mm</text></g>`;
    s += dim(x0, x1, by + 64, `L = ${fmt(i.L)} m`);

    // shear and moment strips
    const strip = (vals, top, h, label, unit, cls) => {
      const m = Math.max(...vals.map(Math.abs)) || 1;
      const yy = linear(-m, m, top + h, top);
      let g = `<text class="cap" x="${x0}" y="${top - 26}">${label}</text>`;
      g += `<line class="zero" x1="${x0}" x2="${x1}" y1="${yy(0)}" y2="${yy(0)}"/>`;
      g += `<path class="area ${cls}" d="${area(r.x, vals, sx, yy)}"/>`;
      g += `<path class="curve ${cls}" d="${path(r.x, vals, sx, yy)}"/>`;
      // annotate the extreme
      let k = 0;
      vals.forEach((v, j) => { if (Math.abs(v) > Math.abs(vals[k])) k = j; });
      const tx = sx(r.x[k]), ty = yy(vals[k]);
      const anchor = tx > x1 - 80 ? "end" : tx < x0 + 80 ? "start" : "middle";
      g += `<circle class="dot ${cls}" cx="${tx}" cy="${ty}" r="3"/>`;
      g += `<text class="lbl ${cls}-t" x="${tx + (anchor === "start" ? 8 : anchor === "end" ? -8 : 0)}" y="${vals[k] >= 0 ? ty - 9 : ty + 17}" text-anchor="${anchor}">${fmt(vals[k])} ${unit}</text>`;
      g += `<text class="tick" x="${x0 - 10}" y="${yy(0) + 4}" text-anchor="end">0</text>`;
      return g;
    };
    s += strip(r.V, 268, 70, "SHEAR FORCE  V(x)", "N", "v");
    s += strip(r.M, 408, 70, "BENDING MOMENT  M(x)", "N·m", "m");
    for (const t of sx.ticks(5)) s += `<text class="tick" x="${sx(t)}" y="${H - 14}" text-anchor="middle">${fmt(t)} m</text>`;
    return svg(W, H, s, "Beam elevation with deflected shape, shear force and bending moment diagrams");
  },
  code: (i, m) => {
    const fn = { "cantilever.point": "cantilever_point_load", "cantilever.udl": "cantilever_udl", "simple.point": "simply_supported_center_load", "simple.udl": "simply_supported_udl" }[`${i.support}.${i.load_type}`];
    const loadKw = i.load_type === "udl" ? "total_load" : "load";
    return `from mech_toolkit import beam_calculator

${sectionCode(i)}

beam = beam_calculator.${fn}(
    length=${i.L}, ${loadKw}=${i.P},
    moment_of_inertia=I, section_modulus_c=c,
    material="${m(i.material)}",
)
print(beam.report())`;
  },
};

// ===================================================================== 02 STRESS

const stress = {
  id: "stress",
  title: "Stress",
  py: "stress_analysis",
  tagline: "Combine the stresses at one point and see if the material can take them.",
  fields: [
    { key: "sx", label: "Normal stress σx", type: "number", unit: "MPa", def: 80, min: -400, max: 400, step: 1 },
    { key: "sy", label: "Normal stress σy", type: "number", unit: "MPa", def: -20, min: -400, max: 400, step: 1 },
    { key: "txy", label: "Shear stress τxy", type: "number", unit: "MPa", def: 30, min: -300, max: 300, step: 1 },
    materialField("structural steel a36"),
  ],
  request: (i) => ({ name: "stress", args: { sx: i.sx * MPA, sy: i.sy * MPA, txy: i.txy * MPA, material: i.material } }),
  results: (r) => [
    { label: "Principal σ₁", value: fmt(r.sigma_1 / MPA), unit: "MPa", tone: "result" },
    { label: "Principal σ₂", value: fmt(r.sigma_2 / MPA), unit: "MPa", tone: "result" },
    { label: "Von Mises", value: fmt(r.von_mises / MPA), unit: "MPa" },
    statusCell(r.safe, r.fos, "Holds", "Yields"),
  ],
  reading: (r) => {
    const verdict = r.safe
      ? `The material holds with a safety factor of <b>${fixed(r.fos, 2)}</b>.`
      : `The material <b>yields</b>: ${fmt(r.von_mises / MPA)} MPa is above its ${fmt(r.material.Sy / MPA)} MPa yield strength.`;
    return `Rotate the element by <b>${fixed(r.theta_p, 1)}°</b> and the shear disappears, leaving pure pull of ${fmt(r.sigma_1 / MPA)} MPa and ${r.sigma_2 < 0 ? "push" : "pull"} of ${fmt(Math.abs(r.sigma_2) / MPA)} MPa. Von Mises rolls everything into one number, <b>${fmt(r.von_mises / MPA)} MPa</b>, to compare against the yield strength of ${esc(r.material.name)}. ${verdict} The more cautious Tresca check gives ${fmt(r.tresca / MPA)} MPa.`;
  },
  viz: (r, i) => {
    const W = 720, H = 440;
    const s1 = r.sigma_1 / MPA, s2 = r.sigma_2 / MPA, c = r.center / MPA, R = r.tau_max / MPA;
    const lo = Math.min(s2, 0), hi = Math.max(s1, 0);
    const spanS = Math.max(hi - lo, 1), spanT = Math.max(2 * R, 1);
    const box = { x0: 70, y0: 50, x1: 450, y1: 400 };
    const k = Math.min((box.x1 - box.x0) / (spanS * 1.25), (box.y1 - box.y0) / (spanT * 1.25));
    const midS = (lo + hi) / 2, cxp = (box.x0 + box.x1) / 2, cyp = (box.y0 + box.y1) / 2;
    const X = (v) => cxp + (v - midS) * k;
    const Y = (t) => cyp + t * k; // τ plotted positive downward (clockwise convention)
    let g = `<text class="cap" x="${box.x0}" y="26">MOHR'S CIRCLE · MPa</text>`;
    g += `<line class="axis" x1="${box.x0 - 10}" x2="${box.x1 + 10}" y1="${Y(0)}" y2="${Y(0)}"/>`;
    if (X(0) > box.x0 - 10 && X(0) < box.x1 + 10) g += `<line class="axis" x1="${X(0)}" x2="${X(0)}" y1="${box.y0 - 10}" y2="${box.y1 + 10}"/>`;
    g += `<text class="axis-label" x="${box.x1 + 14}" y="${Y(0) + 4}">σ</text><text class="axis-label" x="${X(0) + 8}" y="${box.y1 + 6}">τ</text>`;
    g += `<circle class="mohr" cx="${X(c)}" cy="${Y(0)}" r="${R * k}"/>`;
    // 2θp arc from X point to σ1
    const ax = X(i.sx), ay = Y(i.txy), bx = X(i.sy), byy = Y(-i.txy);
    const a0 = Math.atan2(ay - Y(0), ax - X(c));
    const ar = Math.min(28, R * k * 0.5);
    if (Math.abs(a0) > 0.02 && R * k > 20) {
      const sweep = a0 > 0 ? 0 : 1;
      g += `<path class="arc" d="M${X(c) + ar * Math.cos(a0)} ${Y(0) + ar * Math.sin(a0)}A${ar} ${ar} 0 0 ${sweep} ${X(c) + ar} ${Y(0)}"/>`;
      g += `<text class="lbl" x="${X(c) + ar + 6}" y="${Y(0) + (a0 > 0 ? 16 : -8)}">2θp</text>`;
    }
    g += `<line class="diam" x1="${ax}" y1="${ay}" x2="${bx}" y2="${byy}"/>`;
    g += `<circle class="pt load" cx="${ax}" cy="${ay}" r="4.5"/><circle class="pt load" cx="${bx}" cy="${byy}" r="4.5"/>`;
    g += `<text class="lbl load-t" x="${ax + 8}" y="${ay + (i.txy >= 0 ? 16 : -8)}">x (${fmt(i.sx)}, ${fmt(i.txy)})</text>`;
    g += `<text class="lbl load-t" x="${bx + 8}" y="${byy + (i.txy >= 0 ? -8 : 16)}">y (${fmt(i.sy)}, ${fmt(-i.txy)})</text>`;
    g += `<circle class="pt res" cx="${X(s1)}" cy="${Y(0)}" r="4"/><circle class="pt res" cx="${X(s2)}" cy="${Y(0)}" r="4"/>`;
    g += `<text class="lbl res-t" x="${X(s1) + 6}" y="${Y(0) + 18}">σ₁ ${fmt(s1)}</text><text class="lbl res-t" x="${X(s2) - 6}" y="${Y(0) + 18}" text-anchor="end">σ₂ ${fmt(s2)}</text>`;
    g += `<circle class="dot muted" cx="${X(c)}" cy="${Y(0)}" r="2"/>`;
    g += `<line class="dashed" x1="${X(c)}" y1="${Y(0)}" x2="${X(c)}" y2="${Y(-R)}"/><text class="lbl" x="${X(c) + 6}" y="${Y(-R) - 6}">τmax ${fmt(R)}</text>`;

    // principal element
    const ex = 585, ey = 215, half = 36;
    const th = -r.theta_p;
    const arrow = (len, compress, cls) => {
      const L = Math.min(48, 14 + Math.abs(len) * 0.12);
      return compress
        ? `<g class="${cls}"><line x1="${half + L + 6}" y1="0" x2="${half + 10}" y2="0"/><path class="fill" d="M${half + 3} 0l8 -4v8Z"/></g>`
        : `<g class="${cls}"><line x1="${half + 4}" y1="0" x2="${half + L}" y2="0"/><path class="fill" d="M${half + L + 7} 0l-8 -4v8Z"/></g>`;
    };
    g += `<text class="cap" x="${ex - 110}" y="26">PRINCIPAL ELEMENT</text>`;
    g += `<g transform="translate(${ex} ${ey})"><rect class="ghost" x="${-half}" y="${-half}" width="${half * 2}" height="${half * 2}"/>`;
    g += `<g transform="rotate(${th})"><rect class="element" x="${-half}" y="${-half}" width="${half * 2}" height="${half * 2}"/>`;
    for (const rot of [0, 180]) g += `<g transform="rotate(${rot})">${arrow(s1, s1 < 0, "res")}</g>`;
    for (const rot of [90, 270]) g += `<g transform="rotate(${rot})">${arrow(s2, s2 < 0, "res")}</g>`;
    g += `</g><text class="lbl" x="0" y="${half + 92}" text-anchor="middle">rotated ${fixed(r.theta_p, 1)}°</text></g>`;
    g += `<text class="lbl" x="${ex}" y="${ey + half + 112}" text-anchor="middle" class="muted">→ pull  ← push</text>`;
    return svg(W, H, g, "Mohr's circle and the principal stress element");
  },
  code: (i, m) => `from mech_toolkit import stress_analysis, materials_database

sx, sy, txy = ${i.sx}e6, ${i.sy}e6, ${i.txy}e6        # Pa

p = stress_analysis.principal_stresses(sx, sy, txy)
vm = stress_analysis.von_mises_stress(sx, sy, txy)

steel = materials_database.get_material("${m(i.material)}")
fos = stress_analysis.factor_of_safety(steel.yield_strength, vm)

print(p.sigma_1 / 1e6, p.sigma_2 / 1e6, p.angle_principal_deg)
print(f"von Mises {vm/1e6:.1f} MPa, factor of safety {fos:.2f}")`,
};

// ===================================================================== 03 GEARS

const gears = {
  id: "gears",
  title: "Gears",
  py: "gear_ratio",
  tagline: "Trade speed for torque through a chain of gears, stage by stage.",
  fields: [
    { key: "stages", label: "Stages", type: "stages", def: [[18, 54], [16, 48]] },
    { key: "rpm", label: "Input speed", type: "number", unit: "rpm", def: 1750, min: 10, max: 10000, step: 10 },
    { key: "torque", label: "Input torque", type: "number", unit: "N·m", def: 4.5, min: 0.1, max: 500, step: 0.1 },
    { key: "eff", label: "Efficiency per mesh", type: "number", unit: "%", def: 97, min: 50, max: 100, step: 0.5 },
    { key: "module", label: "Gear module", type: "number", unit: "mm", def: 2, min: 0.5, max: 10, step: 0.25 },
  ],
  request: (i) => ({ name: "gears", args: { stages: i.stages, rpm: i.rpm, torque: i.torque, efficiency: i.eff / 100, module: i.module } }),
  results: (r) => [
    { label: "Overall ratio", value: fixed(r.overall_ratio, 2), unit: ": 1", tone: "result" },
    { label: "Output speed", value: fmt(r.output_rpm), unit: "rpm", tone: "result" },
    { label: "Output torque", value: fmt(r.output_torque), unit: "N·m", tone: "result" },
    { label: "Power lost", value: fmt(r.power_in - r.power_out), unit: "W", sub: `${fixed(r.overall_efficiency * 100, 1)}% efficient` },
  ],
  reading: (r, i) =>
    `The motor's ${fmt(i.rpm)} rpm comes out at <b>${fmt(r.output_rpm)} rpm</b>, ${fixed(r.overall_ratio, 1)}× slower, and in exchange the torque grows from ${fmt(i.torque)} to <b>${fmt(r.output_torque)} N·m</b>. ` +
    `It would be a clean ${fixed(r.overall_ratio, 1)}× if gears were perfect, but each mesh loses ${fixed(100 - i.eff, 1)}%, so ${i.stages.length} stage${i.stages.length > 1 ? "s" : ""} turn ${fmt(r.power_in - r.power_out)} W into heat. ` +
    `With a ${fmt(i.module)} mm module, the first pair sits ${fmt(r.stages[0].center_distance)} mm apart.`,
  viz: (r, i, ctx) => {
    const W = 720, H = 380;
    const st = i.stages;
    // layout in "module units": shaft k at x_k
    const xs = [0];
    st.forEach(([a, b]) => xs.push(xs[xs.length - 1] + (a + b) / 2));
    const radii = xs.map((_, k) => Math.max(k > 0 ? st[k - 1][1] / 2 : 0, k < st.length ? st[k][0] / 2 : 0) + 1);
    const left = -radii[0], right = xs[xs.length - 1] + radii[radii.length - 1];
    const maxR = Math.max(...radii);
    const m = Math.min((W - 80) / (right - left), (H - 130) / (2 * maxR));
    const ox = (W - (right - left) * m) / 2 - left * m, oy = 170;
    const period0 = 6; // seconds per input-shaft revolution, for display
    let g = "";
    const anim = ctx.motion;
    const shaftGear = (cx, z, phase, dir, period, cls) => {
      const rot = anim
        ? `<animateTransform attributeName="transform" type="rotate" from="0 ${cx} ${oy}" to="${dir * 360} ${cx} ${oy}" dur="${period.toFixed(3)}s" repeatCount="indefinite"/>`
        : "";
      const rp = (m * z) / 2;
      return `<g>${rot}<g transform="rotate(${phase} ${cx} ${oy})"><path class="gear ${cls}" d="${gearPath(cx, oy, z, m)}"/>` +
        `<circle class="pitch" cx="${cx}" cy="${oy}" r="${rp}"/></g></g>`;
    };
    const periodOf = (k) => period0 * (r.shafts[k].rpm ? i.rpm / r.shafts[k].rpm : 1);
    const dirOf = (k) => (k % 2 === 0 ? 1 : -1);
    // one plane per stage; later stages are drawn in front, as in a real compound reducer
    st.forEach(([a, b], s) => {
      const plane = s % 2 ? "p1" : "p0";
      g += `<g class="plane ${plane}">`;
      g += shaftGear(ox + xs[s] * m, a, 0, dirOf(s), periodOf(s), `driver ${plane}`);
      g += shaftGear(ox + xs[s + 1] * m, b, 180 - 180 / b, dirOf(s + 1), periodOf(s + 1), `driven ${plane}`);
      g += `</g>`;
    });
    for (let k = 0; k < xs.length; k++) {
      const cx = ox + xs[k] * m;
      g += `<circle class="shaft" cx="${cx}" cy="${oy}" r="${Math.max(3, m * 1.6)}"/>`;
      const lbl = k === 0 ? "IN" : k === st.length ? "OUT" : `SHAFT ${k}`;
      g += `<g class="shaft-label"><text class="cap" x="${cx}" y="${H - 64}" text-anchor="middle">${lbl}</text>` +
        `<text class="val" x="${cx}" y="${H - 42}" text-anchor="middle">${fmt(r.shafts[k].rpm)} rpm</text>` +
        `<text class="val sub" x="${cx}" y="${H - 22}" text-anchor="middle">${fmt(r.shafts[k].torque)} N·m</text></g>`;
      g += `<line class="leader" x1="${cx}" x2="${cx}" y1="${oy + Math.max(3, m * 1.6) + 4}" y2="${H - 84}"/>`;
    }
    st.forEach(([a, b], k) => {
      const cx = ox + ((xs[k] + xs[k + 1]) / 2) * m;
      g += `<text class="lbl" x="${cx}" y="34" text-anchor="middle">${a}T → ${b}T · ${fixed(b / a, 2)}:1</text>`;
    });
    g += `<text class="cap" x="20" y="34">${anim ? "SPEEDS TO SCALE" : ""}</text>`;
    return svg(W, H, g, "Gear train, each shaft labelled with speed and torque");
  },
  code: (i) => `from mech_toolkit.gear_ratio import GearStage, GearTrain

train = GearTrain([
${i.stages.map(([a, b]) => `    GearStage(driver_teeth=${a}, driven_teeth=${b}),`).join("\n")}
])

print(train.report(
    input_speed_rpm=${i.rpm},
    input_torque=${i.torque},
    efficiency_per_stage=${i.eff / 100},
))`,
};

// ===================================================================== 04 THERMAL

const thermal = {
  id: "thermal",
  title: "Thermal",
  py: "thermodynamics",
  tagline: "What heat does to parts: they grow, they push, and heat leaks through walls.",
  fields: [
    { key: "mode", label: "Problem", type: "seg", def: "expansion", options: [["expansion", "Expansion"], ["heat", "Heat loss"]] },
    { ...materialField("aluminum 6061-t6"), when: (i) => i.mode === "expansion" },
    { key: "L", label: "Bar length", type: "number", unit: "m", def: 1, min: 0.05, max: 50, step: 0.05, when: (i) => i.mode === "expansion" },
    { key: "dT", label: "Temperature change", type: "number", unit: "°C", def: 60, min: -150, max: 400, step: 1, when: (i) => i.mode === "expansion" },
    { key: "k", label: "Conductivity k", type: "number", unit: "W/m·K", def: 0.8, min: 0.02, max: 400, step: 0.01, when: (i) => i.mode === "heat", hint: "brick ≈ 0.8, concrete ≈ 1.4, fibreglass ≈ 0.04, steel ≈ 50" },
    { key: "t", label: "Wall thickness", type: "number", unit: "mm", def: 200, min: 1, max: 1000, step: 1, when: (i) => i.mode === "heat" },
    { key: "A", label: "Wall area", type: "number", unit: "m²", def: 10, min: 0.1, max: 500, step: 0.1, when: (i) => i.mode === "heat" },
    { key: "dTw", label: "Inside − outside", type: "number", unit: "°C", def: 20, min: 1, max: 200, step: 1, when: (i) => i.mode === "heat" },
    { key: "h", label: "Outside air h", type: "number", unit: "W/m²·K", def: 10, min: 0, max: 200, step: 1, when: (i) => i.mode === "heat", hint: "still air ≈ 5–10, windy ≈ 25+" },
  ],
  request: (i) => i.mode === "heat"
    ? { name: "thermal", args: { mode: "heat", k: i.k, A: i.A, t: i.t * MM, dT: i.dTw, h: i.h } }
    : { name: "thermal", args: { mode: "expansion", material: i.material, L: i.L, dT: i.dT } },
  results: (r, i) => r.mode === "heat"
    ? [
      { label: "Heat loss", value: fmt(r.q), unit: "W", tone: "result" },
      { label: "Heat flux", value: fmt(r.flux), unit: "W/m²", tone: "result" },
      { label: "Wall resistance", value: fmt(r.R_cond), unit: "K/W" },
      { label: "Air film share", value: fixed((r.R_conv / r.R_total) * 100, 0), unit: "%", sub: "of total resistance" },
    ]
    : [
      { label: "Free growth ΔL", value: fmt(r.dL / MM), unit: "mm", tone: "result" },
      { label: "Clamped stress", value: fmt(r.stress / MPA), unit: "MPa", tone: "result" },
      { label: "Yields at ΔT", value: fmt(r.dT_yield), unit: "°C", sub: "if clamped" },
      statusCell(r.safe, r.fos, "Holds", "Yields"),
    ],
  reading: (r, i) => r.mode === "heat"
    ? `About <b>${fmt(r.q)} W</b> leaks through the wall, roughly ${fmt(r.q * 24 / 1000)} kWh a day. The wall itself takes ${fmt(r.dT_wall)} °C of the ${fmt(i.dTw)} °C drop and the thin layer of outside air takes ${fmt(r.dT_film)} °C. ` +
      (r.R_conv > 0 ? `Ignoring that air layer would overestimate the loss as ${fmt(r.q_wall_only)} W, which is why the two resistances are added in series.` : `With no air film, the wall is the only resistance.`)
    : `Left free, the ${fmt(i.L)} m ${esc(r.material.name)} bar ${i.dT >= 0 ? "grows" : "shrinks"} by <b>${fmt(Math.abs(r.dL) / MM)} mm</b>. Clamped between rigid walls it can't, so it ${i.dT >= 0 ? "pushes" : "pulls"} on them with a stress of <b>${fmt(r.stress / MPA)} MPa</b>, whatever its length. ` +
      (r.safe ? `That is under yield. It would take a ${fmt(r.dT_yield)} °C swing to permanently deform it.` : `That is past yield, so the bar would permanently deform. Leave room for it to move, like an expansion joint.`),
  viz: (r, i) => {
    const W = 720, H = 420;
    if (r.mode === "heat") {
      const wx0 = 250, wx1 = 360, top = 70, bot = 330;
      const Tin = i.dTw, total = i.dTw;
      const ty = linear(0, total, bot - 20, top + 20);
      let g = `<text class="cap" x="40" y="34">SECTION THROUGH WALL · TEMPERATURE ABOVE OUTSIDE AIR</text>`;
      g += `<rect class="slab" x="${wx0}" y="${top}" width="${wx1 - wx0}" height="${bot - top}"/>`;
      for (let y = top - (wx1 - wx0); y < bot; y += 12) g += `<line class="hatch" x1="${wx0}" y1="${y + (wx1 - wx0)}" x2="${wx1}" y2="${y}"/>`;
      g += `<rect class="slab-edge" x="${wx0}" y="${top}" width="${wx1 - wx0}" height="${bot - top}"/>`;
      // profile: inside (flat) -> wall (linear) -> air film (curved) -> ambient
      const Tw = r.dT_film; // outer wall surface temperature above ambient
      let d = `M60 ${ty(Tin)}H${wx0}L${wx1} ${ty(Tw)}`;
      d += `C${wx1 + 40} ${ty(Tw * 0.15)} ${wx1 + 70} ${ty(0)} ${wx1 + 140} ${ty(0)}H680`;
      g += `<path class="curve hot" d="${d}"/>`;
      g += `<text class="lbl hot-t" x="70" y="${ty(Tin) - 10}">inside +${fmt(Tin)} °C</text>`;
      g += `<text class="lbl" x="${wx1 + 10}" y="${ty(Tw) - 8}">surface +${fmt(Tw)} °C</text>`;
      g += `<text class="lbl" x="670" y="${ty(0) - 10}" text-anchor="end">outside air</text>`;
      for (let k = 0; k < 4; k++) g += `<path class="air" d="M${wx1 + 170} ${top + 50 + k * 60}c20 -10 40 10 60 0s40 10 60 0"/>`;
      // heat flow arrows
      for (let k = 0; k < 3; k++) {
        const y = top + 80 + k * 70;
        g += `<g class="load"><line x1="${wx0 - 70}" y1="${y}" x2="${wx0 - 14}" y2="${y}"/><path class="fill" d="M${wx0 - 6} ${y}l-9 -4v8Z"/></g>`;
      }
      g += `<text class="lbl load-t" x="${wx0 - 72}" y="${top + 60}">q = ${fmt(r.q)} W</text>`;
      g += dim(wx0, wx1, bot + 26, `${fmt(i.t)} mm`);
      // resistor network
      const ny = H - 30;
      const res = (x, w, label) => {
        let z = `M${x} ${ny}`;
        for (let k = 0; k < 6; k++) z += `l${w / 12} ${k % 2 ? 7 : -7}l${w / 12} ${k % 2 ? -7 : 7}`;
        return `<path class="resistor" d="${z}"/><text class="lbl" x="${x + w / 2}" y="${ny - 14}" text-anchor="middle">${label}</text>`;
      };
      g += `<line class="wire" x1="120" x2="220" y1="${ny}" y2="${ny}"/>` + res(220, 90, `R wall ${fmt(r.R_cond)}`) +
        `<line class="wire" x1="310" x2="400" y1="${ny}" y2="${ny}"/>` + res(400, 90, `R air ${fmt(r.R_conv)}`) +
        `<line class="wire" x1="490" x2="600" y1="${ny}" y2="${ny}"/>` +
        `<text class="cap" x="112" y="${ny + 4}" text-anchor="end">T in</text><text class="cap" x="608" y="${ny + 4}">T out</text>`;
      return svg(W, H, g, "Temperature profile through a wall and its thermal resistance network");
    }
    const x0 = 110, len = 440, h = 34;
    const strain = r.dL / i.L;
    const exag = Math.min(0.22 / Math.max(Math.abs(strain), 1e-9), 4000);
    const grow = strain * exag * len;
    const heat = i.dT >= 0 ? "hot" : "cold";
    let g = `<text class="cap" x="${x0}" y="34">FREE TO MOVE</text>`;
    const y1 = 70;
    g += wall(x0, y1 - 18, y1 + h + 18);
    g += `<rect class="bar-ghost" x="${x0}" y="${y1}" width="${len}" height="${h}"/>`;
    g += `<rect class="bar ${heat}" x="${x0}" y="${y1}" width="${Math.max(10, len + grow)}" height="${h}"/>`;
    g += dim(x0 + len, x0 + len + grow, y1 + h + 26, `ΔL ${fmt(Math.abs(r.dL) / MM)} mm`, "dim res");
    g += `<text class="lbl muted" x="${x0 + 8}" y="${y1 + h / 2 + 4}">${esc(r.material.name)} · ${fmt(i.L)} m</text>`;
    const y2 = 230;
    g += `<text class="cap" x="${x0}" y="${y2 - 36}">CLAMPED BETWEEN RIGID WALLS</text>`;
    g += wall(x0, y2 - 18, y2 + h + 18) + wall(x0 + len, y2 - 18, y2 + h + 18, "right");
    g += `<rect class="bar ${heat} stressed" x="${x0}" y="${y2}" width="${len}" height="${h}"/>`;
    const push = i.dT >= 0;
    for (const [x, dir] of [[x0 + 30, push ? -1 : 1], [x0 + len - 30, push ? 1 : -1]]) {
      g += `<g class="res"><line x1="${x}" y1="${y2 + h / 2}" x2="${x + dir * 22}" y2="${y2 + h / 2}"/><path class="fill" d="M${x + dir * 29} ${y2 + h / 2}l${-dir * 8} -4v8Z"/></g>`;
    }
    g += `<text class="lbl res-t" x="${x0 + len / 2}" y="${y2 + h / 2 + 4}" text-anchor="middle">σ = ${fmt(r.stress / MPA)} MPa ${push ? "compression" : "tension"}</text>`;
    // stress vs ΔT mini chart
    const cx0 = x0, cx1 = x0 + len, cy0 = 320, cy1 = 392;
    const dmax = Math.max(r.dT_yield * 1.15, Math.abs(i.dT) * 1.1);
    const sxx = linear(0, dmax, cx0, cx1), syy = linear(0, r.material.Sy / MPA * 1.15, cy1, cy0);
    g += `<text class="cap" x="${cx0}" y="${cy0 - 12}">CLAMPED STRESS VS |ΔT|</text>`;
    g += `<path class="axis" d="M${cx0} ${cy0}V${cy1}H${cx1}"/>`;
    g += `<line class="yield" x1="${cx0}" x2="${cx1}" y1="${syy(r.material.Sy / MPA)}" y2="${syy(r.material.Sy / MPA)}"/><text class="lbl" x="${cx1}" y="${syy(r.material.Sy / MPA) - 6}" text-anchor="end">yield ${fmt(r.material.Sy / MPA)} MPa</text>`;
    g += `<line class="curve res" x1="${sxx(0)}" y1="${syy(0)}" x2="${sxx(dmax)}" y2="${syy((r.material.E * r.material.alpha * dmax) / MPA)}"/>`;
    g += `<circle class="pt res" cx="${sxx(Math.abs(i.dT))}" cy="${syy(r.stress / MPA)}" r="4"/>`;
    g += `<text class="tick" x="${cx1}" y="${cy1 + 16}" text-anchor="end">${fmt(dmax)} °C</text><text class="tick" x="${cx0}" y="${cy1 + 16}">0</text>`;
    g += `<text class="cap" x="${W - 24}" y="34" text-anchor="end">GROWTH SHOWN ×${fmt(exag, 2)}</text>`;
    return svg(W, H, g, "A bar expanding freely, and the same bar clamped between walls");
  },
  code: (i, m) => i.mode === "heat"
    ? `from mech_toolkit import thermodynamics as th

k, A, t, dT, h = ${i.k}, ${i.A}, ${i.t * MM}, ${i.dTw}, ${i.h}

R_wall = th.thermal_resistance_conduction(t, k, A)
R_air = th.thermal_resistance_convection(h, A)
q = dT / (R_wall + R_air)

print(f"Heat loss {q:.0f} W")`
    : `from mech_toolkit import thermodynamics as th, materials_database

mat = materials_database.get_material("${m(i.material)}")

dL = th.linear_thermal_expansion(${i.L}, mat.thermal_expansion, ${i.dT})
stress = th.thermal_stress(mat.thermal_expansion, mat.elastic_modulus, ${Math.abs(i.dT)})

print(f"Free growth {dL*1000:.2f} mm, clamped stress {stress/1e6:.1f} MPa")`,
};

// ===================================================================== 05 BEARINGS

const bearings = {
  id: "bearings",
  title: "Bearings",
  py: "bearing_life",
  tagline: "How long a bearing lasts at a given load and speed, and which one to buy.",
  fields: [
    { key: "type", label: "Bearing type", type: "seg", def: "ball", options: [["ball", "Ball"], ["roller", "Roller"]] },
    { key: "C", label: "Catalogue rating C", type: "number", unit: "kN", def: 14, min: 1, max: 500, step: 0.1, hint: "the dynamic load rating printed in the bearing catalogue" },
    { key: "P", label: "Load on bearing P", type: "number", unit: "kN", def: 2, min: 0.05, max: 300, step: 0.05 },
    { key: "rpm", label: "Shaft speed", type: "number", unit: "rpm", def: 1800, min: 1, max: 30000, step: 10 },
    { key: "target", label: "Life you need", type: "number", unit: "h", def: 20000, min: 100, max: 200000, step: 100, hint: "≈ 20,000 h for machines used 8 h a day" },
  ],
  request: (i) => ({ name: "bearing", args: { C: i.C * KN, P: i.P * KN, type: i.type, rpm: i.rpm, target_hours: i.target } }),
  results: (r) => [
    { label: "L10 life", value: fmt(r.l10_hours), unit: "h", tone: "result" },
    { label: "Revolutions", value: fmt(r.l10_rev), unit: "million", tone: "result" },
    { label: "Rating needed", value: fmt(r.required_C / KN), unit: "kN", sub: "for your target" },
    { label: "Target", value: r.meets_target ? "Met" : "Short", status: r.meets_target ? "Lasts" : "Too short", tone: r.meets_target ? "ok" : "bad" },
  ],
  reading: (r, i) =>
    `90% of bearings like this will still be running after <b>${fmt(r.l10_hours)} hours</b>, that's about ${fmt(r.years_8h, 2)} years of single-shift work or ${fmt(r.years_24h, 2)} years non-stop. ` +
    (r.meets_target
      ? `That clears your ${fmt(i.target)} h target. `
      : `That falls short of your ${fmt(i.target)} h target, so pick a bearing with a rating of at least <b>${fmt(r.required_C / KN)} kN</b>. `) +
    `Life drops with load to the power ${r.exponent === 3 ? "3" : "10/3"}, so doubling the load cuts life to ${fmt(100 / 2 ** r.exponent, 2)}%.`,
  viz: (r, i) => {
    const W = 720, H = 430, box = [86, 70, 680, 370];
    const Ps = r.curve_P.map((p) => p / KN), hs = r.curve_h;
    const yMin = Math.min(...hs, i.target) * 0.6, yMax = Math.max(...hs, i.target) * 1.6;
    const x = log(Ps[0], Ps[Ps.length - 1], box[0], box[2]);
    const y = log(yMin, yMax, box[3], box[1]);
    let g = frame({ x, y, box, xLabel: "load on bearing P (kN)", yLabel: "L10 LIFE (HOURS)", yFmt: (v) => fmt(v), xTicks: logTicksFine(Ps[0], Ps[Ps.length - 1]) });
    g += `<path class="curve res" d="${path(Ps, hs, x, y)}"/>`;
    g += `<line class="target" x1="${box[0]}" x2="${box[2]}" y1="${y(i.target)}" y2="${y(i.target)}"/>`;
    g += `<text class="lbl load-t" x="${box[2]}" y="${y(i.target) - 8}" text-anchor="end">target ${fmt(i.target)} h</text>`;
    const px = x(i.P), py = y(r.l10_hours);
    g += `<line class="dashed" x1="${px}" x2="${px}" y1="${py}" y2="${box[3]}"/><line class="dashed" x1="${box[0]}" x2="${px}" y1="${py}" y2="${py}"/>`;
    g += `<circle class="pt res" cx="${px}" cy="${py}" r="5"/>`;
    g += `<text class="lbl res-t" x="${px + 10}" y="${py - 10}">${fmt(r.l10_hours)} h at ${fmt(i.P)} kN</text>`;
    // where the curve crosses the target
    const Pcross = (i.C) / Math.pow((i.target * i.rpm * 60) / 1e6, 1 / r.exponent);
    if (Pcross > Ps[0] && Pcross < Ps[Ps.length - 1]) {
      g += `<circle class="pt load" cx="${x(Pcross)}" cy="${y(i.target)}" r="3.5"/>`;
      g += `<text class="lbl" x="${x(Pcross) + 8}" y="${y(i.target) - 8}" text-anchor="start">max ${fmt(Pcross)} kN for target</text>`;
    }
    g += `<text class="cap" x="${box[0]}" y="26">${i.type === "ball" ? "BALL BEARING · L10 = (C/P)³" : "ROLLER BEARING · L10 = (C/P)^10/3"} · C = ${fmt(i.C)} kN · ${fmt(i.rpm)} rpm</text>`;
    return svg(W, H, g, "Bearing life against load, on log scales");
  },
  code: (i) => `from mech_toolkit import bearing_life

life = bearing_life.bearing_l10_life(
    dynamic_load_rating=${i.C * KN}, equivalent_load=${i.P * KN},
    bearing_type="${i.type}", speed_rpm=${i.rpm},
)
print(f"L10: {life.l10_hours:,.0f} hours")

# The catalogue rating needed to last ${i.target} h:
target_rev = ${i.target} * ${i.rpm} * 60 / 1e6
print(bearing_life.required_dynamic_load_rating(${i.P * KN}, target_rev, "${i.type}"))`,
};

function logTicksFine(a, b) {
  const out = [];
  for (let e = Math.floor(Math.log10(a)); e <= Math.ceil(Math.log10(b)); e++)
    for (const m of [1, 2, 5]) { const t = m * 10 ** e; if (t >= a * 0.999 && t <= b * 1.001) out.push(t); }
  return out;
}

// ===================================================================== 06 BUCKLING

const END_LABELS = { "pinned-pinned": "Pinned both ends", "fixed-free": "Fixed base, free top", "fixed-pinned": "Fixed base, pinned top", "fixed-fixed": "Fixed both ends" };

const buckling = {
  id: "buckling",
  title: "Buckling",
  py: "column_buckling",
  tagline: "Will a column bow sideways and collapse before the material itself gives out?",
  fields: [
    { key: "end", label: "End supports", type: "select", def: "pinned-pinned", options: Object.entries(END_LABELS) },
    { key: "L", label: "Column length", type: "number", unit: "m", def: 1.5, min: 0.1, max: 12, step: 0.05 },
    { key: "P", label: "Applied load", type: "number", unit: "kN", def: 20, min: 0, max: 2000, step: 0.5 },
    ...sectionFields.map((f) => ({ ...f, def: { section: "circle", b: 30, h: 40, d: 30, do: 48, di: 40 }[f.key] ?? f.def })),
    materialField("structural steel a36"),
  ],
  request: (i) => ({ name: "buckling", args: { L: i.L, end: i.end, P: i.P * KN, material: i.material, ...sectionArgs(i) } }),
  results: (r) => [
    { label: "Critical load", value: fmt(r.critical_load / KN), unit: "kN", tone: "result" },
    { label: "Slenderness KL/r", value: fmt(r.slenderness), unit: "", tone: "result", sub: `transition ${fmt(r.transition)}` },
    { label: "Method", value: r.method === "euler" ? "Euler" : "Johnson", unit: "", sub: r.method === "euler" ? "long, slender" : "short, stocky" },
    r.fos === null ? { label: "Safety factor", value: "—", sub: "add a load" } : statusCell(r.safe, r.fos, "Stands", "Buckles"),
  ],
  reading: (r, i) => {
    const kind = r.method === "euler"
      ? `It is slender (KL/r ${fmt(r.slenderness)} is above the ${fmt(r.transition)} transition), so it fails by bowing sideways. The Euler formula applies, and the material's strength barely matters, only its stiffness.`
      : `It is fairly stocky (KL/r ${fmt(r.slenderness)} is below the ${fmt(r.transition)} transition), so Euler would overestimate its strength. The Johnson formula takes over, because here yielding and buckling interact.`;
    const verdict = r.fos === null ? "" : r.safe
      ? ` Under ${fmt(i.P)} kN it stands with a safety factor of <b>${fixed(r.fos, 2)}</b>.`
      : ` Under ${fmt(i.P)} kN it <b>buckles</b>. Use a shorter or thicker column, or fix the ends.`;
    return `The column can carry <b>${fmt(r.critical_load / KN)} kN</b> before it collapses. ${kind}${verdict}`;
  },
  viz: (r, i) => {
    const W = 720, H = 430, box = [86, 70, 560, 370];
    const Sy = r.material.Sy / MPA;
    const sMax = r.curve_s[r.curve_s.length - 1];
    const x = linear(0, sMax, box[0], box[2]);
    const y = linear(0, Sy * 1.15, box[3], box[1]);
    const clip = (v) => (v === null ? null : Math.min(v / MPA, Sy * 1.15));
    const eul = r.curve_euler.map(clip), joh = r.curve_johnson.map(clip);
    const eulG = r.curve_s.map((s, k) => (s >= r.transition ? eul[k] : null));
    const eulNG = r.curve_s.map((s, k) => (s <= r.transition * 1.02 ? eul[k] : null));
    let g = frame({ x, y, box, xLabel: "slenderness KL/r", yLabel: "CRITICAL STRESS (MPa)" });
    g += `<line class="yield" x1="${box[0]}" x2="${box[2]}" y1="${y(Sy)}" y2="${y(Sy)}"/><text class="lbl" x="${box[2]}" y="${y(Sy) - 6}" text-anchor="end">yield ${fmt(Sy)}</text>`;
    g += `<path class="curve faint" d="${path(r.curve_s, eulNG, x, y)}"/>`;
    g += `<path class="curve res" d="${path(r.curve_s, eulG, x, y)}"/>`;
    g += `<path class="curve res2" d="${path(r.curve_s, joh, x, y)}"/>`;
    g += `<line class="dashed" x1="${x(r.transition)}" x2="${x(r.transition)}" y1="${box[1]}" y2="${box[3]}"/>`;
    g += `<text class="lbl" x="${x(r.transition) + 6}" y="${box[1] + 12}">transition ${fmt(r.transition)}</text>`;
    g += `<text class="lbl res2-t" x="${x(r.transition * 0.35)}" y="${y(Sy * 0.97) + 26}" text-anchor="middle">Johnson</text>`;
    const eLabelS = [r.transition * 1.3, sMax * 0.92].sort((p, q) => Math.abs(q - r.slenderness) - Math.abs(p - r.slenderness))[0];
    g += `<text class="lbl res-t" x="${x(eLabelS) + 8}" y="${y(Math.PI ** 2 * r.material.E / eLabelS ** 2 / MPA) - 8}">Euler</text>`;
    const px = x(r.slenderness), py = y(Math.min(r.critical_stress / MPA, Sy * 1.15));
    g += `<circle class="pt res" cx="${px}" cy="${py}" r="5"/><text class="lbl res-t" x="${px + 9}" y="${py - 9}">fails at ${fmt(r.critical_stress / MPA)} MPa</text>`;
    if (r.applied_stress) {
      const ay = y(Math.min(r.applied_stress / MPA, Sy * 1.15));
      g += `<line class="load" x1="${px}" x2="${px}" y1="${ay}" y2="${box[3]}"/>`;
      g += `<circle class="pt load" cx="${px}" cy="${ay}" r="4"/><text class="lbl load-t" x="${px + 9}" y="${ay + 14}">applied ${fmt(r.applied_stress / MPA)} MPa</text>`;
    }
    // mode shape inset
    const gx = 640, gy0 = 80, gy1 = 330, a = 26;
    const shapes = {
      "pinned-pinned": (s) => Math.sin(Math.PI * s),
      "fixed-free": (s) => 1 - Math.cos((Math.PI * s) / 2),
      "fixed-fixed": (s) => (1 - Math.cos(2 * Math.PI * s)) / 2,
      "fixed-pinned": (s) => (s * s * (1 - s)) / (4 / 27),
    };
    const f = shapes[i.end];
    let d = "";
    for (let k = 0; k <= 40; k++) { const s = k / 40; d += `${k ? "L" : "M"}${(gx + a * f(s)).toFixed(1)} ${(gy1 - (gy1 - gy0) * s).toFixed(1)}`; }
    g += `<text class="cap" x="${gx}" y="34" text-anchor="middle">MODE SHAPE · K = ${fmt(r.K)}</text>`;
    g += `<line class="phantom" x1="${gx}" x2="${gx}" y1="${gy0}" y2="${gy1}"/><path class="beam thin" d="${d}"/>`;
    const fixedBase = i.end.startsWith("fixed");
    g += fixedBase ? groundH(gx - 20, gx + 20, gy1) : pin(gx, gy1) + groundH(gx - 16, gx + 16, gy1 + 14);
    if (i.end === "fixed-fixed") g += `<g transform="rotate(180 ${gx} ${gy0})">${groundH(gx - 20, gx + 20, gy0)}</g>`;
    if (i.end === "pinned-pinned" || i.end === "fixed-pinned") g += `<circle class="hinge" cx="${gx}" cy="${gy0}" r="4"/><line class="support-line" x1="${gx - 14}" x2="${gx + 14}" y1="${gy0 - 6}" y2="${gy0 - 6}"/>`;
    g += arrowDown(gx + (i.end === "fixed-free" ? a : 0), gy0 - 10, 34, "load", 8);
    return svg(W, H, g, "Euler and Johnson buckling curves with this column marked");
  },
  code: (i, m) => `from mech_toolkit import column_buckling, beam_calculator
import math

${i.section === "rect" ? `A = ${i.b * MM} * ${i.h * MM}\nI = ${i.h * MM} * ${i.b * MM}**3 / 12          # weak axis` : i.section === "circle" ? `A = math.pi * ${i.d * MM}**2 / 4\nI, _ = beam_calculator.circular_section(${i.d * MM})` : `A = math.pi * (${i.do * MM}**2 - ${i.di * MM}**2) / 4\nI, _ = beam_calculator.hollow_circular_section(${i.do * MM}, ${i.di * MM})`}

col = column_buckling.column_critical_load(
    length=${i.L}, area=A, moment_of_inertia=I,
    material="${m(i.material)}",
    end_condition="${i.end}", applied_load=${i.P * KN},
)
print(col.report())`,
};

// ===================================================================== 07 MATERIALS

const PROPS = {
  rho: { label: "Density", unit: "kg/m³", k: 1 },
  E: { label: "Stiffness E", unit: "GPa", k: 1e9 },
  Sy: { label: "Yield strength", unit: "MPa", k: 1e6 },
  Su: { label: "Ultimate strength", unit: "MPa", k: 1e6 },
  alpha: { label: "Thermal expansion", unit: "µm/m·K", k: 1e-6 },
  specific_stiffness: { label: "Stiffness / weight", unit: "MN·m/kg", k: 1e6 },
  specific_strength: { label: "Strength / weight", unit: "kN·m/kg", k: 1e3 },
};
const propOpts = Object.entries(PROPS).map(([k, v]) => [k, v.label]);

const materials = {
  id: "materials",
  title: "Materials",
  py: "materials_database",
  tagline: "Compare the materials every other module draws from, and pick the right one.",
  fields: [
    { key: "x", label: "Horizontal axis", type: "select", def: "rho", options: propOpts },
    { key: "y", label: "Vertical axis", type: "select", def: "Sy", options: propOpts },
    materialField("aluminum 6061-t6"),
  ],
  request: () => ({ name: "materials", args: {} }),
  results: (r, i) => {
    const m = r.materials.find((q) => q.id === i.material) || r.materials[0];
    return [
      { label: "Stiffness E", value: fmt(m.E / 1e9), unit: "GPa", tone: "result" },
      { label: "Yield strength", value: fmt(m.Sy / MPA), unit: "MPa", tone: "result" },
      { label: "Density", value: fmt(m.rho), unit: "kg/m³" },
      { label: "Strength / weight", value: fmt(m.specific_strength / 1e3), unit: "kN·m/kg", sub: rankText(r.materials, m, "specific_strength") },
    ];
  },
  reading: (r, i) => {
    const m = r.materials.find((q) => q.id === i.material) || r.materials[0];
    const steel = r.materials.find((q) => q.id === "structural steel a36");
    const vsSteel = steel && m.id !== steel.id
      ? ` Compared with A36 steel it is ${fmt(m.rho / steel.rho, 2)}× as heavy, ${fmt(m.E / steel.E, 2)}× as stiff and ${fmt(m.Sy / steel.Sy, 2)}× as strong.`
      : "";
    return `<b>${esc(m.name)}</b> (${esc(m.category.toLowerCase())}) ranks ${rankText(r.materials, m, "specific_strength")} for strength per kilogram and ${rankText(r.materials, m, "specific_stiffness")} for stiffness per kilogram.${vsSteel} Click any point on the chart to switch.`;
  },
  viz: (r, i) => {
    const W = 720, H = 450, box = [92, 70, 690, 386];
    const px = PROPS[i.x], py = PROPS[i.y];
    const xs = r.materials.map((m) => m[i.x] / px.k), ys = r.materials.map((m) => m[i.y] / py.k);
    const span = (v) => [Math.min(...v) / 1.6, Math.max(...v) * 1.6];
    const [xa, xb] = span(xs), [ya, yb] = span(ys);
    const x = log(xa, xb, box[0], box[2]), y = log(ya, yb, box[3], box[1]);
    let g = frame({ x, y, box, xLabel: `${px.label.toLowerCase()} (${px.unit})`, yLabel: `${py.label.toUpperCase()} (${py.unit})`, xTicks: logTicksFine(xa, xb), yTicks: logTicksFine(ya, yb) });
    const cats = [...new Set(r.materials.map((m) => m.category))];
    const placed = [];
    const order = r.materials.map((m, k) => k).sort((a, b) => (r.materials[b].id === i.material) - (r.materials[a].id === i.material));
    const labelY = {};
    for (const k of order) {
      const cx = x(xs[k]), cy = y(ys[k]);
      const w = shortName(r.materials[k].name).length * 6.7 + 10;
      const free = (ly) => placed.every((b) => cx + 9 > b.x + b.w || cx + 9 + w < b.x || ly - 9 > b.y + 3 || ly + 3 < b.y - 9);
      const ly = [cy + 4, cy + 15, cy - 7, cy + 26, cy - 18].find(free);
      if (ly !== undefined) { placed.push({ x: cx + 9, y: ly, w }); labelY[k] = ly; }
    }
    r.materials.forEach((m, k) => {
      const sel = m.id === i.material;
      const cx = x(xs[k]), cy = y(ys[k]);
      g += `<g class="mat ${sel ? "sel" : ""}" data-set="material=${esc(m.id)}" tabindex="0" role="button" aria-label="${esc(m.name)}">` +
        `<circle class="hit" cx="${cx}" cy="${cy}" r="14"/>` +
        `<circle class="pt cat${cats.indexOf(m.category) % 6}" cx="${cx}" cy="${cy}" r="${sel ? 6.5 : 4.5}"/>` +
        (labelY[k] !== undefined ? `<text class="lbl" x="${cx + 9}" y="${labelY[k]}">${esc(shortName(m.name))}</text>` : `<title>${esc(m.name)}</title>`) + `</g>`;
    });
    g += `<text class="cap" x="${box[0]}" y="22">${r.materials.length} MATERIALS · LOG SCALES · CLICK TO SELECT</text>`;
    return svg(W, H, g, "Scatter chart of material properties");
  },
  code: (i, m) => `from mech_toolkit import materials_database

mat = materials_database.get_material("${m(i.material)}")
print(mat)

for m in materials_database.list_materials():
    print(f"{m.name:32s} {m.yield_strength/m.density/1e3:6.1f} kN·m/kg")`,
};

function rankText(list, m, key) {
  const sorted = [...list].sort((a, b) => b[key] - a[key]);
  const n = sorted.findIndex((q) => q.id === m.id) + 1;
  return `#${n} of ${list.length}`;
}
const shortName = (n) => n.replace(/\s*\(.*?\)/, "").replace("Structural ", "").replace(" Plastic", "");

// ===================================================================== 08 UNITS

const UNIT_LABEL = { "N*m": "N·m", "kN*m": "kN·m", "lbf*ft": "lbf·ft", "lbf*in": "lbf·in", C: "°C", F: "°F", K: "K" };
const ul = (u) => UNIT_LABEL[u] ?? u;
const UNIT_DEFAULTS = { length: ["in", "mm"], force: ["lbf", "N"], stress: ["ksi", "MPa"], torque: ["lbf*ft", "N*m"], power: ["hp", "kW"], temperature: ["F", "C"] };

const units = {
  id: "units",
  title: "Units",
  py: "unit_converter",
  tagline: "Imperial to SI and back, for every quantity the other modules use.",
  fields: [
    { key: "category", label: "Quantity", type: "select", def: "stress", options: [["length", "Length"], ["force", "Force"], ["stress", "Stress / pressure"], ["torque", "Torque"], ["power", "Power"], ["temperature", "Temperature"]],
      onChange: (i) => { const [f, t] = UNIT_DEFAULTS[i.category]; i.from = f; i.to = t; } },
    { key: "value", label: "Value", type: "number", unit: "", def: 36, min: -1e9, max: 1e9, step: 0.1, slider: false },
    { key: "from", label: "From", type: "select", def: "ksi", options: (i, cat) => (cat?.units?.[i.category] ?? []).map((u) => [u, ul(u)]) },
    { key: "to", label: "To", type: "select", def: "MPa", options: (i, cat) => (cat?.units?.[i.category] ?? []).map((u) => [u, ul(u)]) },
  ],
  request: (i) => ({ name: "units", args: { category: i.category, value: i.value, from: i.from, to: i.to } }),
  results: (r, i) => [
    { label: "Result", value: fmt(r.result, 5), unit: ul(i.to), tone: "result", wide: true },
    { label: "Factor", value: i.category === "temperature" ? "offset" : fmt(r.result / (i.value || 1), 5), unit: i.category === "temperature" ? "" : `${ul(i.to)} per ${ul(i.from)}` },
  ],
  reading: (r, i) => i.category === "temperature"
    ? `Temperature scales have different zero points, so they can't use a single multiplier. The converter goes through Celsius first, then out to ${ul(i.to)}.`
    : `Every unit is stored once, as its size in SI. Converting ${ul(i.from)} to ${ul(i.to)} multiplies into SI and divides back out, so adding a new unit takes one line of code, not one per pair.`,
  viz: (r, i) => {
    let rows = r.all.map((a) => {
      const sel = a.unit === i.to, src = a.unit === i.from;
      return `<button class="unit-row ${sel ? "sel" : ""} ${src ? "src" : ""}" data-set="to=${esc(a.unit)}" type="button">` +
        `<span class="u">${esc(ul(a.unit))}</span><span class="v">${esc(fmt(a.value, 6))}</span><span class="tag">${src ? "input" : sel ? "result" : ""}</span></button>`;
    }).join("");
    return `<div class="units-viz"><div class="units-hero"><div class="from"><span class="num">${esc(fmt(i.value, 6))}</span><span class="unit">${esc(ul(i.from))}</span></div>` +
      `<div class="eq" aria-hidden="true">=</div><div class="to"><span class="num">${esc(fmt(r.result, 6))}</span><span class="unit">${esc(ul(i.to))}</span></div></div>` +
      `<div class="unit-list" role="list">${rows}</div></div>`;
  },
  code: (i) => i.category === "temperature"
    ? `from mech_toolkit import unit_converter\n\nprint(unit_converter.convert_temperature(${i.value}, "${i.from}", "${i.to}"))`
    : `from mech_toolkit import unit_converter\n\nprint(unit_converter.convert_${i.category}(${i.value}, "${i.from}", "${i.to}"))`,
};

export const MODULES = [beams, stress, gears, thermal, bearings, buckling, materials, units];
MODULES.forEach((m, k) => (m.num = String(k + 1).padStart(2, "0")));

export function defaults(mod) {
  const o = {};
  for (const f of mod.fields) o[f.key] = structuredClone(f.def);
  return o;
}
