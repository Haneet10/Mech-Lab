"""
generate.py

Builds the animated SVG artwork used in the project README.

GitHub renders README images through <img>, so these SVGs can't run
JavaScript. Every animation here is plain SMIL (<animate>,
<animateTransform>), which GitHub, Chrome, Firefox and Safari all play.

Each piece is written twice, once per colour theme, and the README picks
between them with <picture> + prefers-color-scheme.

Run from the repo root:

    python assets/readme/generate.py

The numbers shown in the artwork (deflection, stress, factor of safety,
gear ratio ...) are computed with mech_toolkit itself, so the banner can
never drift out of step with what the code actually returns.
"""

from __future__ import annotations

import math
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))

from mech_toolkit import beam_calculator  # noqa: E402

# --------------------------------------------------------------------------
# Theme
# --------------------------------------------------------------------------

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "grid": "#151b23",
        "grid_major": "#1c232d",
        "line": "#2a313c",
        "ink": "#e6edf3",
        "muted": "#8b949e",
        "faint": "#484f58",
        "steel": "#a9bcd0",
        "steel_fill": "#1b2633",
        "load": "#ff8a3d",      # forces / loads: signal orange
        "result": "#4fc3f7",    # measured results: instrument cyan
        "ok": "#3fb950",
    },
    "light": {
        "bg": "#ffffff",
        "grid": "#f3f5f8",
        "grid_major": "#e6eaef",
        "line": "#d0d7de",
        "ink": "#1f2328",
        "muted": "#59636e",
        "faint": "#afb8c1",
        "steel": "#3d5a78",
        "steel_fill": "#e9eef4",
        "load": "#d9480f",
        "result": "#0969da",
        "ok": "#1a7f37",
    },
}

SANS = ("-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', "
        "Helvetica, Arial, sans-serif")
MONO = ("ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, "
        "'Liberation Mono', monospace")

EASE = "0.45 0 0.2 1"     # ease-in-out cubic bezier for keySplines
HOLD = "0 0 1 1"


# --------------------------------------------------------------------------
# Numbers from the toolkit
# --------------------------------------------------------------------------

def beam_numbers():
    I, c = beam_calculator.rectangular_section(width=0.025, height=0.060)
    r = beam_calculator.cantilever_point_load(
        length=2.0, load=400, moment_of_inertia=I, section_modulus_c=c,
        material="Structural Steel A36",
    )
    return {
        "L": 2.0,
        "P": 400,
        "M": r.max_moment,
        "sigma": r.max_stress / 1e6,
        "delta": r.max_deflection * 1e3,
        "fos": r.factor_of_safety,
        "safe": r.is_safe,
    }


# --------------------------------------------------------------------------
# Small SVG helpers
# --------------------------------------------------------------------------

def f(x: float) -> str:
    """Compact number formatting for coordinates."""
    s = f"{x:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def anim(attr: str, times, values, dur: float, spline=EASE, extra="") -> str:
    """A looping SMIL <animate> with eased segments."""
    n = len(times) - 1
    splines = ";".join([spline] * n)
    return (f'<animate attributeName="{attr}" dur="{f(dur)}s" '
            f'repeatCount="indefinite" calcMode="spline" '
            f'keyTimes="{";".join(f(t) for t in times)}" '
            f'values="{";".join(str(v) for v in values)}" '
            f'keySplines="{splines}" {extra}/>')


def spin(cx, cy, seconds, clockwise=True, start=0.0) -> str:
    a0, a1 = start, start + (360 if clockwise else -360)
    return (f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{f(a0)} {f(cx)} {f(cy)}" to="{f(a1)} {f(cx)} {f(cy)}" '
            f'dur="{f(seconds)}s" repeatCount="indefinite"/>')


def svg_open(w, h, title, desc) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-labelledby="t d">'
            f'<title id="t">{escape(title)}</title>'
            f'<desc id="d">{escape(desc)}</desc>')


def grid(w, h, t, minor=16, major=80, inset=0) -> str:
    return (
        '<defs>'
        f'<pattern id="gmin" width="{minor}" height="{minor}" patternUnits="userSpaceOnUse">'
        f'<path d="M{minor} 0H0V{minor}" fill="none" stroke="{t["grid"]}" stroke-width="1"/></pattern>'
        f'<pattern id="gmaj" width="{major}" height="{major}" patternUnits="userSpaceOnUse">'
        f'<rect width="{major}" height="{major}" fill="url(#gmin)"/>'
        f'<path d="M{major} 0H0V{major}" fill="none" stroke="{t["grid_major"]}" stroke-width="1"/></pattern>'
        '</defs>'
        f'<rect x="{inset}" y="{inset}" width="{w - 2*inset}" height="{h - 2*inset}" fill="url(#gmaj)"/>'
    )


def text(x, y, s, t, size=13, color="ink", family=MONO, weight=400,
         anchor="start", spacing=0, extra="") -> str:
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{t[color]}" text-anchor="{anchor}" '
            f'letter-spacing="{spacing}" xml:space="preserve" {extra}>{escape(s)}</text>')


def gear_path(cx, cy, teeth, module, phase_deg=0.0) -> str:
    """Spur-gear outline with trapezoidal teeth (visual, not exact involute)."""
    r = module * teeth / 2
    ra, rf = r + module, r - 1.25 * module
    p = 2 * math.pi / teeth
    ph = math.radians(phase_deg)
    pts = []
    for i in range(teeth):
        c = ph + i * p
        for rad, da in ((rf, -0.30), (ra, -0.14), (ra, 0.14), (rf, 0.30)):
            a = c + da * p
            pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    d = "M" + "L".join(f"{f(x)} {f(y)}" for x, y in pts) + "Z"
    return d


def gear(cx, cy, teeth, module, t, seconds, clockwise, phase=0.0, bore=None,
         holes=0) -> str:
    r = module * teeth / 2
    bore = bore or max(3.0, r * 0.18)
    out = [f'<g>{spin(cx, cy, seconds, clockwise)}',
           f'<path d="{gear_path(cx, cy, teeth, module, phase)}" fill="{t["steel_fill"]}" '
           f'stroke="{t["steel"]}" stroke-width="1.4" stroke-linejoin="round"/>',
           f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="none" stroke="{t["faint"]}" '
           f'stroke-width="0.8" stroke-dasharray="6 3 1 3"/>']
    for k in range(holes):
        a = 2 * math.pi * k / holes + math.radians(phase)
        hx, hy = cx + 0.52 * r * math.cos(a), cy + 0.52 * r * math.sin(a)
        out.append(f'<circle cx="{f(hx)}" cy="{f(hy)}" r="{f(r*0.14)}" fill="{t["bg"]}" '
                   f'stroke="{t["steel"]}" stroke-width="1"/>')
    out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(bore)}" fill="{t["bg"]}" '
               f'stroke="{t["steel"]}" stroke-width="1.4"/>')
    # keyway, so the rotation is readable
    out.append(f'<rect x="{f(cx - bore*0.3)}" y="{f(cy - bore - bore*0.45)}" '
               f'width="{f(bore*0.6)}" height="{f(bore*0.55)}" fill="{t["steel"]}"/>')
    out.append('</g>')
    return "".join(out)


def arrow_down(x, y_tip, length, t, color="load", width=2, head=8) -> str:
    c = t[color]
    return (f'<line x1="{f(x)}" y1="{f(y_tip - length)}" x2="{f(x)}" y2="{f(y_tip - head)}" '
            f'stroke="{c}" stroke-width="{width}"/>'
            f'<path d="M{f(x - head*0.55)} {f(y_tip - head)}L{f(x)} {f(y_tip)}L{f(x + head*0.55)} '
            f'{f(y_tip - head)}Z" fill="{c}"/>')


def wall(x, y0, y1, t, side="left", step=9) -> str:
    """Fixed support: a heavy line with hatching on the 'ground' side."""
    sgn = -1 if side == "left" else 1
    out = [f'<line x1="{f(x)}" y1="{f(y0)}" x2="{f(x)}" y2="{f(y1)}" stroke="{t["steel"]}" stroke-width="2"/>']
    y = y0 + 2
    while y < y1:
        out.append(f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(x + sgn*10)}" y2="{f(y + 10)}" '
                   f'stroke="{t["faint"]}" stroke-width="1"/>')
        y += step
    return "".join(out)


def deflected(x0, x1, y, amp, n=24, shape="cantilever"):
    """Polyline points for a beam's elastic curve (same point count either way)."""
    pts = []
    for i in range(n + 1):
        s = i / n
        if shape == "cantilever":          # y = P x^2 (3L - x) / 6EI, normalised
            v = s * s * (3 - s) / 2
        elif shape == "udl_ss":            # simply supported, UDL, normalised
            v = (s - 2 * s**3 + s**4) / (5 / 16)
        elif shape == "sine":
            v = math.sin(math.pi * s)
        else:
            v = 0
        pts.append((x0 + (x1 - x0) * s, y + amp * v))
    return "M" + "L".join(f"{f(a)} {f(b)}" for a, b in pts)


def vdeflected(x, y0, y1, amp, n=24):
    """Vertical column buckling shape (half sine), bowing to +x."""
    pts = []
    for i in range(n + 1):
        s = i / n
        pts.append((x + amp * math.sin(math.pi * s), y0 + (y1 - y0) * s))
    return "M" + "L".join(f"{f(a)} {f(b)}" for a, b in pts)


# --------------------------------------------------------------------------
# 1. Hero banner
# --------------------------------------------------------------------------

FORMULAS = [
    "δmax = P·L³ / 3EI",
    "σ = M·c / I",
    "τ = T·r / J",
    "σvm = √(σ₁² − σ₁σ₂ + σ₂²)",
    "Pcr = π²EI / (KL)²",
    "L10 = (C / P)³",
]


def ticker(x, y, t, size=20, per=3.2):
    """Typewriter cycling through FORMULAS, with a blinking cursor."""
    char_w = size * 0.6
    n = len(FORMULAS)
    total = n * per
    out = []
    for k, s in enumerate(FORMULAS):
        t0, t1 = k * per / total, (k + 1) * per / total
        type_end = t0 + min(0.9, 0.06 * len(s)) / total
        erase_start = t1 - 0.35 / total
        chars = len(s)
        # discrete clip width steps: one per character while typing
        times, widths = [0.0], [0]
        if t0 > 0:
            times.append(t0); widths.append(0)
        for i in range(1, chars + 1):
            times.append(t0 + (type_end - t0) * i / chars)
            widths.append(f(char_w * i + 2))
        times.append(erase_start); widths.append(f(char_w * chars + 2))
        times.append(min(t1, 0.9999)); widths.append(0)
        if times[-1] < 1:
            times.append(1.0); widths.append(0)
        cid = f"tk{k}"
        kt = ";".join(f(tt) for tt in times)
        kt = ";".join(f"{tt:.4f}" for tt in times)
        vals = ";".join(str(wv) for wv in widths)
        out.append(
            f'<clipPath id="{cid}"><rect x="{f(x)}" y="{f(y - size)}" height="{f(size * 1.5)}" width="0">'
            f'<animate attributeName="width" dur="{f(total)}s" repeatCount="indefinite" '
            f'calcMode="discrete" keyTimes="{kt}" values="{vals}"/></rect></clipPath>'
            f'<g clip-path="url(#{cid})">{text(x, y, s, t, size=size, color="ink")}</g>'
        )
        # cursor follows the clip edge
        xs = ";".join(f(x + (float(wv) if wv else 0) + 2) for wv in widths)
        vis = ";".join("1" if (tt >= t0 and tt < min(t1, 0.9999)) else "0" for tt in times)
        out.append(
            f'<rect y="{f(y - size * 0.82)}" width="{f(size*0.5)}" height="{f(size)}" fill="{t["load"]}" x="{f(x)}" opacity="0">'
            f'<animate attributeName="x" dur="{f(total)}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{kt}" values="{xs}"/>'
            f'<animate attributeName="opacity" dur="{f(total)}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="{kt}" values="{vis}"/>'
            f'</rect>'
        )
    return "".join(out)


def hero(t, nums) -> str:
    W, H = 1280, 420
    D = 8.0  # seconds per loop
    o = [svg_open(W, H, "Mech Lab",
                  "A cantilever beam deflecting under a 400 N load, next to the Mech Lab title.")]
    o.append(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    o.append(grid(W, H, t, inset=16))

    # Drawing-sheet border with zone markers
    o.append(f'<rect x="16.5" y="16.5" width="{W-33}" height="{H-33}" fill="none" stroke="{t["line"]}"/>')
    for i, zx in enumerate(range(16 + 160, W - 16, 160)):
        o.append(f'<line x1="{zx}" y1="16" x2="{zx}" y2="24" stroke="{t["line"]}"/>')
        o.append(f'<line x1="{zx}" y1="{H-16}" x2="{zx}" y2="{H-24}" stroke="{t["line"]}"/>')
    for i, label in enumerate("12345678"):
        o.append(text(16 + 80 + 160 * i, 13, label, t, size=9, color="faint", anchor="middle"))
    for i, label in enumerate("ABC"):
        o.append(text(9, 16 + 70 + 130 * i, label, t, size=9, color="faint", anchor="middle"))

    # ---- left: title -----------------------------------------------------
    o.append(text(72, 84, "MECH—LAB  /  PYTHON TOOLKIT  /  REV 1.0", t, size=12,
                  color="muted", spacing=2.5))
    o.append(f'<rect x="72" y="104" width="28" height="3" fill="{t["load"]}"/>')
    o.append(text(68, 196, "Mech Lab", t, size=104, family=SANS, weight=700, spacing=-4))
    o.append(text(72, 240, "Mechanical engineering hand calculations,", t, size=21,
                  family=SANS, color="muted"))
    o.append(text(72, 268, "solved, checked and plotted in Python.", t, size=21,
                  family=SANS, color="muted"))
    o.append(text(72, 326, "›", t, size=22, color="load", weight=700))
    o.append(ticker(96, 326, t, size=20))
    o.append(text(72, 372, "beams · stress · gears · thermal · bearings · buckling · materials · units",
                  t, size=12, color="faint", spacing=0.5))

    # ---- right: cantilever ------------------------------------------------
    bx0, bx1, by, amp = 768, 1150, 196, 44
    o.append(wall(bx0, by - 58, by + 58, t))
    straight = deflected(bx0, bx1, by, 0)
    bent = deflected(bx0, bx1, by, amp)
    kt = [0, 0.12, 0.28, 0.48, 0.80, 0.93, 1]
    # phantom line: undeflected position
    o.append(f'<path d="{straight}" fill="none" stroke="{t["faint"]}" stroke-width="1" '
             f'stroke-dasharray="14 4 3 4"/>')
    # the beam itself
    o.append(f'<path d="{straight}" fill="none" stroke="{t["steel"]}" stroke-width="14" stroke-linecap="butt">'
             + anim("d", kt, [straight, straight, straight, bent, bent, straight, straight], D) + '</path>')
    o.append(f'<path d="{straight}" fill="none" stroke="{t["bg"]}" stroke-width="10" stroke-linecap="butt">'
             + anim("d", kt, [straight, straight, straight, bent, bent, straight, straight], D) + '</path>')
    # elastic curve (neutral axis) in result colour
    o.append(f'<path d="{straight}" fill="none" stroke="{t["result"]}" stroke-width="1.5" opacity="0">'
             + anim("d", kt, [straight, straight, straight, bent, bent, straight, straight], D)
             + anim("opacity", kt, [0, 0, 0, 1, 1, 0, 0], D) + '</path>')

    # load arrow: drops in, rides the tip down, lifts away
    o.append(f'<g opacity="0">'
             + anim("opacity", kt, [0, 0, 1, 1, 1, 0, 0], D)
             + f'<animateTransform attributeName="transform" type="translate" dur="{f(D)}s" '
               f'repeatCount="indefinite" calcMode="spline" keyTimes="{";".join(f(k) for k in kt)}" '
               f'values="0 -40;0 -40;0 0;0 {f(amp)};0 {f(amp)};0 -40;0 -40" '
               f'keySplines="{";".join([EASE]*6)}"/>'
             + arrow_down(bx1, by - 9, 74, t, width=2.5, head=11)
             + text(bx1 - 14, by - 64, f"P = {nums['P']:.0f} N", t, size=13, color="load", anchor="end")
             + '</g>')

    # length dimension
    dy = by + 96
    o.append(f'<line x1="{bx0}" y1="{by + 66}" x2="{bx0}" y2="{dy + 6}" stroke="{t["faint"]}"/>')
    o.append(f'<line x1="{bx1}" y1="{by + 66}" x2="{bx1}" y2="{dy + 6}" stroke="{t["faint"]}"/>')
    o.append(f'<line x1="{bx0}" y1="{dy}" x2="{bx1}" y2="{dy}" stroke="{t["muted"]}"/>')
    for x, sgn in ((bx0, 1), (bx1, -1)):
        o.append(f'<path d="M{x} {dy}l{sgn*9} -3v6Z" fill="{t["muted"]}"/>')
    o.append(f'<rect x="{(bx0+bx1)/2 - 46}" y="{dy - 9}" width="92" height="18" fill="{t["bg"]}"/>')
    o.append(text((bx0 + bx1) / 2, dy + 4, f"L = {nums['L']:.2f} m", t, size=12, color="muted", anchor="middle"))

    # tip deflection dimension
    tx = bx1 + 34
    o.append(f'<g opacity="0">' + anim("opacity", kt, [0, 0, 0, 1, 1, 0, 0], D)
             + f'<line x1="{bx1 + 10}" y1="{by}" x2="{tx + 6}" y2="{by}" stroke="{t["faint"]}"/>'
             + f'<line x1="{bx1 + 10}" y1="{by + amp}" x2="{tx + 6}" y2="{by + amp}" stroke="{t["faint"]}"/>'
             + f'<line x1="{tx}" y1="{by}" x2="{tx}" y2="{by + amp}" stroke="{t["result"]}"/>'
             + f'<path d="M{tx} {by}l-3 8h6Z" fill="{t["result"]}"/>'
             + f'<path d="M{tx} {by + amp}l-3 -8h6Z" fill="{t["result"]}"/>'
             + text(tx + 10, by + amp / 2 + 5, "δ", t, size=15, color="result")
             + '</g>')

    # results table, styled as a drawing title block
    tbx, tby, tbw, tbh = 768, 330, 436, 58
    cells = [
        ("δ MAX", f"{nums['delta']:.2f} mm", "result"),
        ("σ MAX", f"{nums['sigma']:.1f} MPa", "result"),
        ("FoS", f"{nums['fos']:.1f}  {'SAFE' if nums['safe'] else 'FAIL'}", "ok"),
    ]
    cw = tbw / len(cells)
    o.append(f'<rect x="{tbx + .5}" y="{tby + .5}" width="{tbw}" height="{tbh}" fill="{t["bg"]}" stroke="{t["line"]}"/>')
    for i, (lab, val, col) in enumerate(cells):
        cx = tbx + i * cw
        if i:
            o.append(f'<line x1="{f(cx + .5)}" y1="{tby}" x2="{f(cx + .5)}" y2="{tby + tbh}" stroke="{t["line"]}"/>')
        o.append(text(cx + 14, tby + 20, lab, t, size=10, color="muted", spacing=1.5))
        o.append(f'<g opacity="0.25">' + anim("opacity", kt, [0.25, 0.25, 0.25, 1, 1, 0.25, 0.25], D)
                 + text(cx + 14, tby + 44, val, t, size=17, color=col, weight=600) + '</g>')
    o.append(text(tbx + tbw, tby - 8, "A36 STEEL · 25 × 60 mm · CANTILEVER", t, size=10,
                  color="faint", anchor="end", spacing=1))
    o.append('</svg>')
    return "".join(o)


# --------------------------------------------------------------------------
# 2. Module panel: one animated glyph per module
# --------------------------------------------------------------------------

def g_beams(x, y, t):
    """Simply supported beam under a UDL, sagging."""
    D = 6.0
    x0, x1, by, amp = x + 20, x + 220, y + 66, 14
    s, b = deflected(x0, x1, by, 0, shape="udl_ss"), deflected(x0, x1, by, amp, shape="udl_ss")
    kt = [0, 0.15, 0.45, 0.75, 1]
    o = [f'<path d="{s}" fill="none" stroke="{t["steel"]}" stroke-width="6">'
         + anim("d", kt, [s, s, b, b, s], D) + '</path>']
    # supports
    for sx in (x0, x1):
        o.append(f'<path d="M{sx} {by + 3}l-8 13h16Z" fill="none" stroke="{t["steel"]}" stroke-width="1.4"/>')
    o.append(f'<line x1="{x0 - 14}" y1="{by + 20}" x2="{x0 + 14}" y2="{by + 20}" stroke="{t["faint"]}"/>')
    o.append(f'<line x1="{x1 - 14}" y1="{by + 20}" x2="{x1 + 14}" y2="{by + 20}" stroke="{t["faint"]}"/>')
    # distributed load arrows ride the beam
    for i in range(9):
        ax = x0 + 12 + i * (x1 - x0 - 24) / 8
        sv = (ax - x0) / (x1 - x0)
        v = amp * (sv - 2 * sv**3 + sv**4) / (5 / 16)
        o.append(f'<g>' + f'<animateTransform attributeName="transform" type="translate" dur="{D}s" '
                 f'repeatCount="indefinite" calcMode="spline" keyTimes="0;0.15;0.45;0.75;1" '
                 f'values="0 0;0 0;0 {f(v)};0 {f(v)};0 0" keySplines="{";".join([EASE]*4)}"/>'
                 + arrow_down(ax, by - 5, 22, t, width=1.3, head=6) + '</g>')
    o.append(f'<line x1="{x0 + 12}" y1="{by - 27}" x2="{x1 - 12}" y2="{by - 27}" stroke="{t["load"]}" stroke-width="1.3">'
             + f'<animateTransform attributeName="transform" type="translate" dur="{D}s" repeatCount="indefinite" '
             f'calcMode="spline" keyTimes="0;0.15;0.45;0.75;1" values="0 0;0 0;0 3;0 3;0 0" '
             f'keySplines="{";".join([EASE]*4)}"/></line>')
    return "".join(o)


def g_stress(x, y, t):
    """Mohr's circle with the stress-element diameter rotating."""
    cx, cy, r = x + 120, y + 62, 40
    o = [f'<line x1="{x + 30}" y1="{cy}" x2="{x + 210}" y2="{cy}" stroke="{t["faint"]}"/>',
         f'<line x1="{cx - r - 26}" y1="{y + 10}" x2="{cx - r - 26}" y2="{y + 114}" stroke="{t["faint"]}"/>',
         text(x + 212, cy + 4, "σ", t, size=11, color="muted"),
         text(cx - r - 22, y + 16, "τ", t, size=11, color="muted"),
         f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{t["steel"]}" stroke-width="1.6"/>',
         f'<circle cx="{cx - r}" cy="{cy}" r="3.2" fill="{t["result"]}"/>',
         f'<circle cx="{cx + r}" cy="{cy}" r="3.2" fill="{t["result"]}"/>',
         text(cx + r + 4, cy + 16, "σ₁", t, size=10, color="result"),
         text(cx - r - 18, cy + 16, "σ₂", t, size=10, color="result"),
         f'<g>{spin(cx, cy, 9, clockwise=False, start=30)}'
         f'<line x1="{cx - r}" y1="{cy}" x2="{cx + r}" y2="{cy}" stroke="{t["load"]}" stroke-width="1.4"/>'
         f'<circle cx="{cx + r}" cy="{cy}" r="4" fill="{t["bg"]}" stroke="{t["load"]}" stroke-width="1.6"/>'
         f'<circle cx="{cx - r}" cy="{cy}" r="4" fill="{t["bg"]}" stroke="{t["load"]}" stroke-width="1.6"/>'
         f'</g>',
         f'<circle cx="{cx}" cy="{cy}" r="2" fill="{t["muted"]}"/>']
    return "".join(o)


def g_gears(x, y, t):
    m = 4.2
    z1, z2 = 11, 19
    c1 = (x + 62, y + 66)
    c2 = (c1[0] + m * (z1 + z2) / 2, c1[1])
    base = 0.55
    return (gear(*c1, z1, m, t, seconds=base * z1, clockwise=True, phase=0, holes=0)
            + gear(*c2, z2, m, t, seconds=base * z2, clockwise=False,
                   phase=180 + 180 / z2, holes=5))


def g_thermal(x, y, t):
    """Bar heated between walls: it lengthens and glows."""
    D = 5.0
    x0, y0, h = x + 24, y + 48, 26
    L0, dL = 150, 26
    kt = [0, 0.2, 0.5, 0.75, 1]
    o = [wall(x0, y0 - 14, y0 + h + 14, t)]
    o.append(f'<rect x="{x0}" y="{y0}" height="{h}" width="{L0}" fill="{t["steel_fill"]}" stroke="{t["steel"]}" stroke-width="1.4">'
             + anim("width", kt, [L0, L0, L0 + dL, L0 + dL, L0], D) + '</rect>')
    o.append(f'<rect x="{x0}" y="{y0}" height="{h}" width="{L0}" fill="{t["load"]}" opacity="0">'
             + anim("width", kt, [L0, L0, L0 + dL, L0 + dL, L0], D)
             + anim("opacity", kt, [0, 0, 0.35, 0.35, 0], D) + '</rect>')
    # flame-ish heat marks underneath
    for i in range(5):
        hx = x0 + 18 + i * 28
        o.append(f'<path d="M{hx} {y0 + h + 22}q-5 -6 0 -12q5 -6 0 -12" fill="none" stroke="{t["load"]}" '
                 f'stroke-width="1.3" opacity="0">'
                 + anim("opacity", kt, [0, 0.9, 0.9, 0.2, 0], D) + '</path>')
    # ΔL dimension
    o.append(f'<g opacity="0">' + anim("opacity", kt, [0, 0, 1, 1, 0], D)
             + f'<line x1="{x0 + L0}" y1="{y0 - 12}" x2="{x0 + L0 + dL}" y2="{y0 - 12}" stroke="{t["result"]}"/>'
             + f'<line x1="{x0 + L0}" y1="{y0 - 18}" x2="{x0 + L0}" y2="{y0 - 6}" stroke="{t["result"]}"/>'
             + f'<line x1="{x0 + L0 + dL}" y1="{y0 - 18}" x2="{x0 + L0 + dL}" y2="{y0 - 6}" stroke="{t["result"]}"/>'
             + text(x0 + L0 + dL / 2, y0 - 22, "ΔL", t, size=11, color="result", anchor="middle")
             + '</g>')
    return "".join(o)


def g_bearing(x, y, t):
    """Deep-groove ball bearing: inner race spins, balls orbit at cage speed."""
    cx, cy = x + 120, y + 62
    ro, ri, rb = 52, 24, 6.8
    rp = 38
    shaft_s = 3.0
    cage_s = shaft_s / 0.42          # cage turns at ~0.42 x shaft speed
    o = [f'<circle cx="{cx}" cy="{cy}" r="{ro}" fill="{t["steel_fill"]}" stroke="{t["steel"]}" stroke-width="1.4"/>',
         f'<circle cx="{cx}" cy="{cy}" r="{ro - 7}" fill="{t["bg"]}" stroke="{t["steel"]}" stroke-width="1"/>']  # outer race groove at r=45
    balls = [f'<g>{spin(cx, cy, cage_s)}']
    for k in range(9):
        a = 2 * math.pi * k / 9
        bx, by = cx + rp * math.cos(a), cy + rp * math.sin(a)
        balls.append(f'<circle cx="{f(bx)}" cy="{f(by)}" r="{rb}" fill="{t["bg"]}" stroke="{t["result"]}" stroke-width="1.3"/>')
        balls.append(f'<circle cx="{f(bx - 2.4)}" cy="{f(by - 2.4)}" r="1.6" fill="{t["result"]}" opacity="0.6"/>')
    balls.append(f'<circle cx="{cx}" cy="{cy}" r="{f(rp)}" fill="none" stroke="{t["faint"]}" stroke-dasharray="2 4"/></g>')
    o.extend(balls)
    o.append(f'<g>{spin(cx, cy, shaft_s)}'
             f'<circle cx="{cx}" cy="{cy}" r="{ri + 7}" fill="{t["bg"]}" stroke="{t["steel"]}" stroke-width="1"/>'
             f'<circle cx="{cx}" cy="{cy}" r="{ri}" fill="{t["steel_fill"]}" stroke="{t["steel"]}" stroke-width="1.4"/>'
             f'<circle cx="{cx}" cy="{cy}" r="13" fill="{t["bg"]}" stroke="{t["steel"]}" stroke-width="1.2"/>'
             f'<rect x="{cx - 3}" y="{cy - 17}" width="6" height="6" fill="{t["steel"]}"/>'
             f'</g>')
    return "".join(o)


def g_buckling(x, y, t):
    """Pinned-pinned column: load ramps, column snaps into a half-sine bow."""
    D = 6.0
    cx, y0, y1, amp = x + 120, y + 30, y + 112, 16
    s, b = vdeflected(cx, y0, y1, 0), vdeflected(cx, y0, y1, amp)
    kt = [0, 0.2, 0.42, 0.75, 1]
    o = [f'<path d="{s}" fill="none" stroke="{t["faint"]}" stroke-dasharray="10 3 2 3"/>',
         f'<path d="{s}" fill="none" stroke="{t["steel"]}" stroke-width="5">'
         + anim("d", kt, [s, s, b, b, s], D) + '</path>',
         f'<circle cx="{cx}" cy="{y0}" r="4" fill="{t["bg"]}" stroke="{t["steel"]}" stroke-width="1.4"/>',
         f'<path d="M{cx} {y1}l-9 12h18Z" fill="none" stroke="{t["steel"]}" stroke-width="1.4"/>',
         f'<line x1="{cx - 16}" y1="{y1 + 16}" x2="{cx + 16}" y2="{y1 + 16}" stroke="{t["faint"]}"/>',
         f'<circle cx="{cx}" cy="{y1}" r="4" fill="{t["bg"]}" stroke="{t["steel"]}" stroke-width="1.4"/>',
         f'<g>' + f'<animateTransform attributeName="transform" type="translate" dur="{D}s" repeatCount="indefinite" '
         f'calcMode="spline" keyTimes="{";".join(f(k) for k in kt)}" values="0 -6;0 0;0 3;0 3;0 -6" '
         f'keySplines="{";".join([EASE]*4)}"/>' + arrow_down(cx, y0 - 5, 24, t, width=2, head=8) + '</g>',
         f'<g opacity="0">' + anim("opacity", kt, [0, 0, 1, 1, 0], D)
         + text(cx + 26, (y0 + y1) / 2 + 4, "Pcr", t, size=11, color="result") + '</g>']
    return "".join(o)


def g_materials(x, y, t):
    """Stress-strain curve traced point by point, with yield marked."""
    D = 6.0
    ox, oy = x + 34, y + 108
    pts = [(0, 0), (34, -70), (40, -76), (60, -80), (100, -88), (140, -92), (170, -86), (182, -78)]
    d = "M" + "L".join(f"{f(ox + a)} {f(oy + b)}" for a, b in pts[:2])
    d += "C" + " ".join(f"{f(ox + a)} {f(oy + b)}" for a, b in ((38, -76), (52, -80), (70, -82)))
    d += "S" + " ".join(f"{f(ox + a)} {f(oy + b)}" for a, b in ((150, -96), (182, -78)))
    length = 260
    kt = [0, 0.1, 0.6, 0.85, 1]
    o = [f'<line x1="{ox}" y1="{oy}" x2="{ox + 196}" y2="{oy}" stroke="{t["faint"]}"/>',
         f'<line x1="{ox}" y1="{oy}" x2="{ox}" y2="{oy - 104}" stroke="{t["faint"]}"/>',
         text(ox + 198, oy + 4, "ε", t, size=11, color="muted"),
         text(ox - 4, oy - 106, "σ", t, size=11, color="muted", anchor="end"),
         f'<line x1="{ox}" y1="{oy - 76}" x2="{ox + 40}" y2="{oy - 76}" stroke="{t["faint"]}" stroke-dasharray="2 3"/>',
         text(ox - 4, oy - 72, "Sy", t, size=10, color="muted", anchor="end"),
         f'<path d="{d}" fill="none" stroke="{t["result"]}" stroke-width="1.8" stroke-dasharray="{length}" '
         f'stroke-dashoffset="{length}" stroke-linecap="round">'
         + anim("stroke-dashoffset", kt, [length, length, 0, 0, length], D) + '</path>',
         f'<g opacity="0">' + anim("opacity", kt, [0, 0, 0.2, 1, 0], D)
         + text(ox + 22, oy - 30, "E", t, size=12, color="load", weight=600) + '</g>']
    return "".join(o)


def g_units(x, y, t):
    """Unit conversions flipping like a split-flap display."""
    pairs = [("1 in", "25.4 mm"), ("1 lbf", "4.448 N"), ("1 ksi", "6.895 MPa"),
             ("1 hp", "745.7 W"), ("1 ft·lbf", "1.356 N·m"), ("68 °F", "20 °C")]
    per, n = 2.0, len(pairs)
    D = per * n
    o = []
    for k, (a, b) in enumerate(pairs):
        t0, t1 = k / n, (k + 1) / n
        fade = 0.06 / n * 3
        times = sorted({0, max(0, t0 - 1e-4), t0, t0 + fade, t1 - fade, t1, 1})
        vals = []
        for tt in times:
            if tt < t0 or tt > t1:
                vals.append(0)
            elif tt == t0 or tt == t1:
                vals.append(0)
            else:
                vals.append(1)
        kt = ";".join(f"{tt:.4f}" for tt in times)
        vs = ";".join(str(v) for v in vals)
        o.append(f'<g opacity="0"><animate attributeName="opacity" dur="{f(D)}s" repeatCount="indefinite" '
                 f'keyTimes="{kt}" values="{vs}"/>'
                 + text(x + 120, y + 52, a, t, size=20, color="ink", anchor="middle", weight=600)
                 + text(x + 120, y + 92, b, t, size=20, color="result", anchor="middle", weight=600)
                 + '</g>')
    o.append(f'<line x1="{x + 54}" y1="{y + 66}" x2="{x + 186}" y2="{y + 66}" stroke="{t["line"]}"/>')
    o.append(f'<circle cx="{x + 120}" cy="{y + 66}" r="9" fill="{t["bg"]}" stroke="{t["load"]}" stroke-width="1.3"/>')
    o.append(f'<path d="M{x + 116} {y + 63}l4 4l4 -4" fill="none" stroke="{t["load"]}" stroke-width="1.4"/>')
    return "".join(o)


MODULES = [
    ("01", "BEAMS", "beam_calculator", "How far it bends, and will it hold.", g_beams),
    ("02", "STRESS", "stress_analysis", "Shear, torsion, Mohr's circle, von Mises.", g_stress),
    ("03", "GEARS", "gear_ratio", "Speed and torque through gear trains.", g_gears),
    ("04", "THERMAL", "thermodynamics", "Expansion, thermal stress, heat flow.", g_thermal),
    ("05", "BEARINGS", "bearing_life", "How long a bearing lasts (ISO 281).", g_bearing),
    ("06", "BUCKLING", "column_buckling", "Will a column bow out under load?", g_buckling),
    ("07", "MATERIALS", "materials_database", "Steel, aluminum, titanium and more.", g_materials),
    ("08", "UNITS", "unit_converter", "Imperial ↔ SI for every quantity.", g_units),
]


def modules(t) -> str:
    cols, rows = 4, 2
    cw, ch = 320, 250
    W, H = cols * cw, rows * ch
    o = [svg_open(W, H, "Mech Lab modules",
                  "Eight animated diagrams, one for each module: beams, stress, gears, thermal, "
                  "bearings, buckling, materials and units.")]
    o.append(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    for i, (num, name, mod, blurb, glyph) in enumerate(MODULES):
        c, r = i % cols, i // cols
        x, y = c * cw, r * ch
        o.append(f'<rect x="{x + .5}" y="{y + .5}" width="{cw - 1}" height="{ch - 1}" fill="none" stroke="{t["line"]}"/>')
        # corner registration ticks
        o.append(f'<path d="M{x + 12} {y + 20}v-8h8M{x + cw - 20} {y + 12}h8v8" fill="none" stroke="{t["faint"]}"/>')
        o.append(text(x + 28, y + 36, num, t, size=11, color="load", weight=600, spacing=1))
        o.append(text(x + 52, y + 36, name, t, size=11, color="ink", weight=600, spacing=2.5))
        o.append(glyph(x + 40, y + 52, t))
        o.append(text(x + 28, y + 206, mod, t, size=12, color="result"))
        o.append(text(x + 28, y + 228, blurb, t, size=12.5, family=SANS, color="muted"))
    o.append('</svg>')
    return "".join(o)


# --------------------------------------------------------------------------
# 3. Terminal: the example script printing its report
# --------------------------------------------------------------------------

def terminal(t, nums) -> str:
    W = 1280
    lines = [
        ("$ python examples/example_beam_analysis.py", "muted"),
        ("", None),
        ("Cantilever Beam Analysis (Point Load)", "ink"),
        ("────────────────────────────────────────", "faint"),
        (f"Length        {nums['L']:.2f} m", "ink"),
        (f"Load          {nums['P']:.1f} N", "load"),
        ("Material      Structural Steel A36", "ink"),
        ("", None),
        (f"Max moment    {nums['M']:.1f} N·m", "ink"),
        (f"Max stress    {nums['sigma']:.1f} MPa", "result"),
        (f"Max deflect.  {nums['delta']:.2f} mm", "result"),
        (f"Safety factor {nums['fos']:.1f}", "ink"),
        ("", None),
        ("Beam status   SAFE", "ok"),
    ]
    lh, top = 24, 70
    H = top + lh * len(lines) + 40
    D = 12.0
    o = [svg_open(W, H, "Example run",
                  "Terminal output of the cantilever beam example: 53.3 MPa stress, 11.85 mm deflection, safe.")]
    o.append(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    o.append(f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" fill="none" stroke="{t["line"]}"/>')
    o.append(f'<line x1="0" y1="40.5" x2="{W}" y2="40.5" stroke="{t["line"]}"/>')
    o.append(text(24, 26, "TERMINAL", t, size=10.5, color="muted", spacing=2.5))
    o.append(text(W - 24, 26, "zsh — mech-lab", t, size=10.5, color="faint", anchor="end", spacing=1))
    o.append(f'<circle cx="{W - 136}" cy="22" r="3.5" fill="{t["ok"]}">'
             f'<animate attributeName="opacity" values="1;0.25;1" dur="2s" repeatCount="indefinite"/></circle>')

    # right-hand side: a mini plot of the deflection curve that draws with the run
    px0, py0, pw, ph = 760, 110, 440, 200
    o.append(text(px0, py0 - 22, "DEFLECTION  y(x)", t, size=10.5, color="muted", spacing=2))
    o.append(f'<line x1="{px0}" y1="{py0}" x2="{px0 + pw}" y2="{py0}" stroke="{t["faint"]}"/>')
    o.append(f'<line x1="{px0}" y1="{py0 - 8}" x2="{px0}" y2="{py0 + ph}" stroke="{t["faint"]}"/>')
    for i in range(1, 5):
        gx = px0 + pw * i / 4
        o.append(f'<line x1="{f(gx)}" y1="{py0}" x2="{f(gx)}" y2="{py0 + ph}" stroke="{t["grid_major"]}"/>')
        o.append(text(gx, py0 + ph + 18, f"{nums['L'] * i / 4:.1f} m", t, size=10, color="faint", anchor="middle"))
    for i in range(1, 4):
        gy = py0 + ph * i / 3
        o.append(f'<line x1="{px0}" y1="{f(gy)}" x2="{px0 + pw}" y2="{f(gy)}" stroke="{t["grid_major"]}"/>')
    curve = deflected(px0, px0 + pw, py0, ph * 0.9, n=40)
    clen = 520
    t_draw0 = (2 + 10 * 0.42) / D
    t_draw1 = t_draw0 + 0.12
    kt = [0, t_draw0, t_draw1, 0.92, 1]
    o.append(f'<path d="{curve}" fill="none" stroke="{t["result"]}" stroke-width="2" stroke-dasharray="{clen}" '
             f'stroke-dashoffset="{clen}">' + anim("stroke-dashoffset", kt, [clen, clen, 0, 0, clen], D) + '</path>')
    tipx, tipy = px0 + pw, py0 + ph * 0.9
    o.append(f'<g opacity="0">' + anim("opacity", kt, [0, 0, 1, 1, 0], D)
             + f'<circle cx="{tipx}" cy="{f(tipy)}" r="4" fill="{t["result"]}"/>'
             + text(tipx - 12, tipy + 4, f"−{nums['delta']:.2f} mm", t, size=12, color="result", anchor="end")
             + '</g>')

    # left: lines appear one by one, then everything clears and repeats
    start, step = 0.5 / D, 0.42 / D
    for i, (s, col) in enumerate(lines):
        if not s:
            continue
        ty = top + i * lh
        a = start + i * step if i else 0.0001
        times = [0, a, a + 0.001, 0.92, 0.93, 1]
        if i == 0:
            times = [0, 0.0005, 0.001, 0.92, 0.93, 1]
        o.append(f'<g opacity="0"><animate attributeName="opacity" dur="{f(D)}s" repeatCount="indefinite" '
                 f'keyTimes="{";".join(f"{v:.4f}" for v in times)}" values="0;0;1;1;0;0"/>'
                 + text(24, ty, s, t, size=15, color=col or "ink", weight=600 if col == "ok" else 400)
                 + '</g>')
    # blinking cursor under the last line
    o.append(f'<rect x="24" y="{top + lh * len(lines) - 14}" width="9" height="17" fill="{t["load"]}">'
             f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" dur="1s" repeatCount="indefinite"/></rect>')
    o.append('</svg>')
    return "".join(o)


# --------------------------------------------------------------------------
# 4. Section divider
# --------------------------------------------------------------------------

def divider(t) -> str:
    W, H = 1280, 28
    y = 14
    o = [svg_open(W, H, "Divider", "A dimension line used as a section divider.")]
    o.append(f'<line x1="8" y1="{y}" x2="{W - 8}" y2="{y}" stroke="{t["line"]}"/>')
    o.append(f'<line x1="8" y1="{y - 7}" x2="8" y2="{y + 7}" stroke="{t["faint"]}"/>')
    o.append(f'<line x1="{W - 8}" y1="{y - 7}" x2="{W - 8}" y2="{y + 7}" stroke="{t["faint"]}"/>')
    o.append(f'<path d="M8 {y}l10 -3.5v7Z" fill="{t["faint"]}"/>')
    o.append(f'<path d="M{W - 8} {y}l-10 -3.5v7Z" fill="{t["faint"]}"/>')
    for i in range(1, 32):
        x = 8 + (W - 16) * i / 32
        hgt = 5 if i % 4 == 0 else 2.5
        o.append(f'<line x1="{f(x)}" y1="{f(y - hgt)}" x2="{f(x)}" y2="{y}" stroke="{t["faint"]}"/>')
    o.append(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;{W - 60} 0;0 0" '
             f'dur="14s" repeatCount="indefinite" calcMode="spline" keyTimes="0;0.5;1" keySplines="{EASE};{EASE}"/>'
             f'<rect x="22" y="{y - 1}" width="16" height="2" fill="{t["load"]}"/></g>')
    o.append('</svg>')
    return "".join(o)


# --------------------------------------------------------------------------

def main():
    nums = beam_numbers()
    out = HERE
    for name, t in THEMES.items():
        files = {
            f"hero-{name}.svg": hero(t, nums),
            f"modules-{name}.svg": modules(t),
            f"terminal-{name}.svg": terminal(t, nums),
            f"divider-{name}.svg": divider(t),
        }
        for fn, svg in files.items():
            (out / fn).write_text(svg + "\n", encoding="utf-8")
            print(f"wrote {fn:24s} {len(svg)/1024:6.1f} KB")


if __name__ == "__main__":
    main()
