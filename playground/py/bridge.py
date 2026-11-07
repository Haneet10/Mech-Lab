"""
bridge.py

Thin adapter between the browser playground and mech_toolkit.

The playground sends one JSON object per calculation (all values already in
SI units) and gets one JSON object back. Every engineering number in the
response comes from a mech_toolkit function; this file only picks the right
function, samples curves for plotting, and packages the results.

It runs inside Pyodide (CPython compiled to WebAssembly), but it is plain
Python, so you can also call it from a terminal:

    >>> import json, bridge
    >>> bridge.call("beam", json.dumps({...}))
"""

from __future__ import annotations

import json
import math

from mech_toolkit import (
    beam_calculator,
    bearing_life,
    column_buckling,
    gear_ratio,
    materials_database,
    stress_analysis,
    thermodynamics,
    unit_converter,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _materials():
    # The database is keyed by a short lowercase name; use those keys as ids.
    return materials_database._MATERIALS


def _material(key: str):
    try:
        return _materials()[key]
    except KeyError:
        return materials_database.get_material(key)


def _finite(x):
    """JSON has no Infinity; send None and let the UI show an infinity sign."""
    if x is None or isinstance(x, bool):
        return x
    if isinstance(x, (int, float)) and not math.isfinite(x):
        return None
    return x


def _clean(obj):
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    return _finite(obj)


def _section(args):
    """Return (I, c, A, label) for the chosen cross section, in SI units."""
    kind = args.get("section", "rect")
    if kind == "rect":
        b, h = args["b"], args["h"]
        I, c = beam_calculator.rectangular_section(width=b, height=h)
        # weak axis, for buckling
        I_weak = h * b ** 3 / 12.0
        return I, c, b * h, I_weak
    if kind == "circle":
        d = args["d"]
        I, c = beam_calculator.circular_section(diameter=d)
        return I, c, math.pi * d ** 2 / 4.0, I
    if kind == "tube":
        do, di = args["do"], args["di"]
        if di >= do:
            raise ValueError("The inner diameter has to be smaller than the outer diameter.")
        I, c = beam_calculator.hollow_circular_section(outer_diameter=do, inner_diameter=di)
        return I, c, math.pi * (do ** 2 - di ** 2) / 4.0, I
    raise ValueError(f"Unknown section '{kind}'.")


def _material_info(mat):
    return {
        "name": mat.name,
        "category": mat.category,
        "E": mat.elastic_modulus,
        "Sy": mat.yield_strength,
        "Su": mat.ultimate_strength,
        "rho": mat.density,
        "nu": mat.poisson_ratio,
        "alpha": mat.thermal_expansion,
    }


# ---------------------------------------------------------------------------
# 01 Beams
# ---------------------------------------------------------------------------


def beam(args):
    support = args["support"]          # "cantilever" | "simple"
    load_type = args["load_type"]      # "point" | "udl"
    L, P = args["L"], args["P"]
    mat = _material(args["material"])
    I, c, A, _ = _section(args)
    E = mat.elastic_modulus

    fn = {
        ("cantilever", "point"): beam_calculator.cantilever_point_load,
        ("cantilever", "udl"): beam_calculator.cantilever_udl,
        ("simple", "point"): beam_calculator.simply_supported_center_load,
        ("simple", "udl"): beam_calculator.simply_supported_udl,
    }[(support, load_type)]
    curve = {
        ("cantilever", "point"): beam_calculator.cantilever_point_load_curve,
        ("cantilever", "udl"): beam_calculator.cantilever_udl_curve,
        ("simple", "point"): beam_calculator.simply_supported_center_load_curve,
        ("simple", "udl"): beam_calculator.simply_supported_udl_curve,
    }[(support, load_type)]

    r = fn(L, P, I, c, mat)
    n = 121
    xs, ys = curve(L, P, E, I, num_points=n)

    # Shear and bending moment along the span (sagging moment positive).
    w = P / L
    V, M = [], []
    for x in xs:
        if support == "cantilever" and load_type == "point":
            v, m = P, -P * (L - x)
        elif support == "cantilever":
            v, m = w * (L - x), -w * (L - x) ** 2 / 2.0
        elif load_type == "point":
            v = P / 2.0 if x < L / 2.0 else -P / 2.0
            m = P * x / 2.0 if x <= L / 2.0 else P * (L - x) / 2.0
        else:
            v, m = w * (L / 2.0 - x), w * x * (L - x) / 2.0
        V.append(v)
        M.append(m)

    return {
        "max_moment": r.max_moment,
        "max_stress": r.max_stress,
        "max_deflection": r.max_deflection,
        "fos": r.factor_of_safety,
        "safe": r.is_safe,
        "I": I, "c": c, "A": A,
        "mass": A * L * mat.density,
        "material": _material_info(mat),
        "x": xs, "y": ys, "V": V, "M": M,
        "report": r.report(),
    }


# ---------------------------------------------------------------------------
# 02 Stress
# ---------------------------------------------------------------------------


def stress(args):
    sx, sy, txy = args["sx"], args["sy"], args["txy"]
    mat = _material(args["material"])
    p = stress_analysis.principal_stresses(sx, sy, txy)
    vm = stress_analysis.von_mises_stress(sx, sy, txy)
    fos = stress_analysis.factor_of_safety(mat.yield_strength, vm) if vm > 0 else float("inf")
    # Tresca, for comparison: max shear including the out-of-plane third principal (0)
    s3 = 0.0
    tresca = max(abs(p.sigma_1 - p.sigma_2), abs(p.sigma_1 - s3), abs(p.sigma_2 - s3))
    return {
        "sigma_1": p.sigma_1,
        "sigma_2": p.sigma_2,
        "tau_max": p.max_shear_stress,
        "theta_p": p.angle_principal_deg,
        "center": (sx + sy) / 2.0,
        "von_mises": vm,
        "tresca": tresca,
        "fos": fos,
        "safe": stress_analysis.is_safe(mat.yield_strength, vm) if vm > 0 else True,
        "material": _material_info(mat),
    }


# ---------------------------------------------------------------------------
# 03 Gears
# ---------------------------------------------------------------------------


def gears(args):
    stages = [gear_ratio.GearStage(int(a), int(b)) for a, b in args["stages"]]
    train = gear_ratio.GearTrain(stages)
    rpm, T, eff = args["rpm"], args["torque"], args["efficiency"]
    m = args["module"]
    shafts = [{"rpm": rpm, "torque": T}]
    speed, torque = rpm, T
    rows = []
    for s in stages:
        speed = gear_ratio.output_speed(speed, s.ratio)
        torque = gear_ratio.output_torque(torque, s.ratio, eff)
        shafts.append({"rpm": speed, "torque": torque})
        rows.append({
            "driver": s.driver_teeth,
            "driven": s.driven_teeth,
            "ratio": s.ratio,
            "center_distance": gear_ratio.center_distance(m, s.driver_teeth, s.driven_teeth),
            "d_driver": gear_ratio.pitch_diameter(m, s.driver_teeth),
            "d_driven": gear_ratio.pitch_diameter(m, s.driven_teeth),
        })
    return {
        "overall_ratio": train.overall_ratio,
        "output_rpm": train.output_speed(rpm),
        "output_torque": train.output_torque(T, eff),
        "overall_efficiency": eff ** len(stages),
        "power_in": T * rpm * 2 * math.pi / 60.0,
        "power_out": train.output_torque(T, eff) * train.output_speed(rpm) * 2 * math.pi / 60.0,
        "stages": rows,
        "shafts": shafts,
        "report": train.report(rpm, T, eff),
    }


# ---------------------------------------------------------------------------
# 04 Thermal
# ---------------------------------------------------------------------------


def thermal(args):
    if args.get("mode") == "heat":
        k, A, t, dT, h = args["k"], args["A"], args["t"], args["dT"], args["h"]
        q_cond = thermodynamics.conduction_heat_transfer(k, A, dT, t)
        R_cond = thermodynamics.thermal_resistance_conduction(t, k, A)
        R_conv = thermodynamics.thermal_resistance_convection(h, A) if h > 0 else 0.0
        R_total = R_cond + R_conv
        q = dT / R_total
        # temperature at the wall/fluid interface, measured from the cold side
        T_interface = q * R_conv
        return {
            "mode": "heat", "q_wall_only": q_cond, "q": q,
            "R_cond": R_cond, "R_conv": R_conv, "R_total": R_total,
            "flux": q / A, "dT_wall": q * R_cond, "dT_film": T_interface,
        }

    mat = _material(args["material"])
    L, dT = args["L"], args["dT"]
    a, E = mat.thermal_expansion, mat.elastic_modulus
    dL = thermodynamics.linear_thermal_expansion(L, a, dT)
    sigma = thermodynamics.thermal_stress(a, E, abs(dT))
    fos = stress_analysis.factor_of_safety(mat.yield_strength, sigma) if sigma > 0 else float("inf")
    # temperature change that would just reach yield if the bar is clamped
    dT_yield = mat.yield_strength / (E * a)
    return {
        "mode": "expansion", "dL": dL, "strain": dL / L, "stress": sigma,
        "fos": fos, "safe": fos >= 1.0, "dT_yield": dT_yield,
        "material": _material_info(mat),
    }


# ---------------------------------------------------------------------------
# 05 Bearings
# ---------------------------------------------------------------------------


def bearing(args):
    C, P, kind, rpm = args["C"], args["P"], args["type"], args["rpm"]
    target_h = args["target_hours"]
    r = bearing_life.bearing_l10_life(C, P, kind, rpm)
    target_rev = target_h * rpm * 60.0 / 1e6
    C_req = bearing_life.required_dynamic_load_rating(P, target_rev, kind)
    loads = [P * (0.25 + 2.75 * i / 80) for i in range(81)]
    curve = [bearing_life.bearing_l10_life(C, p, kind, rpm).l10_hours for p in loads]
    return {
        "l10_rev": r.l10_revolutions,
        "l10_hours": r.l10_hours,
        "required_C": C_req,
        "meets_target": r.l10_hours >= target_h,
        "years_8h": r.l10_hours / (8 * 250),          # one shift, 250 working days
        "years_24h": r.l10_hours / (24 * 365),
        "curve_P": loads,
        "curve_h": curve,
        "exponent": 3.0 if kind == "ball" else 10.0 / 3.0,
    }


# ---------------------------------------------------------------------------
# 06 Buckling
# ---------------------------------------------------------------------------


def buckling(args):
    mat = _material(args["material"])
    _, _, A, I_weak = _section(args)
    L, end, Papp = args["L"], args["end"], args["P"]
    r = column_buckling.column_critical_load(L, A, I_weak, mat, end, Papp or None)
    E, Sy = mat.elastic_modulus, mat.yield_strength
    t = r.transition_slenderness
    s_max = max(250.0, r.slenderness_ratio * 1.25)
    sl, euler, johnson = [], [], []
    for i in range(1, 161):
        s = s_max * i / 160
        sl.append(s)
        euler.append(math.pi ** 2 * E / s ** 2)
        johnson.append(column_buckling.johnson_critical_stress(E, Sy, s) if s < t else None)
    return {
        "critical_load": r.critical_load,
        "critical_stress": r.critical_stress,
        "slenderness": r.slenderness_ratio,
        "transition": t,
        "method": r.method,
        "K": column_buckling.effective_length_factor(end),
        "r": column_buckling.radius_of_gyration(I_weak, A),
        "A": A,
        "I": I_weak,
        "fos": r.factor_of_safety if Papp else None,
        "safe": r.is_safe if Papp else None,
        "applied_stress": (Papp / A) if Papp else None,
        "material": _material_info(mat),
        "curve_s": sl, "curve_euler": euler, "curve_johnson": johnson,
    }


# ---------------------------------------------------------------------------
# 07 Materials
# ---------------------------------------------------------------------------


def materials(args):
    out = []
    for key, m in _materials().items():
        info = _material_info(m)
        info["id"] = key
        info["specific_stiffness"] = m.elastic_modulus / m.density
        info["specific_strength"] = m.yield_strength / m.density
        out.append(info)
    return {"materials": out}


# ---------------------------------------------------------------------------
# 08 Units
# ---------------------------------------------------------------------------

_UNIT_TABLES = {
    "length": (unit_converter._LENGTH_TO_M, unit_converter.convert_length),
    "force": (unit_converter._FORCE_TO_N, unit_converter.convert_force),
    "stress": (unit_converter._STRESS_TO_PA, unit_converter.convert_stress),
    "torque": (unit_converter._TORQUE_TO_NM, unit_converter.convert_torque),
    "power": (unit_converter._POWER_TO_W, unit_converter.convert_power),
}


def units(args):
    cat, value, frm, to = args["category"], args["value"], args["from"], args["to"]
    if cat == "temperature":
        options = ["C", "F", "K"]
        conv = unit_converter.convert_temperature
    else:
        table, conv = _UNIT_TABLES[cat]
        options = list(table.keys())
    return {
        "result": conv(value, frm, to),
        "all": [{"unit": u, "value": conv(value, frm, u)} for u in options],
        "options": options,
    }


def unit_options():
    out = {cat: list(t.keys()) for cat, (t, _) in _UNIT_TABLES.items()}
    out["temperature"] = ["C", "F", "K"]
    return out


def catalog(_args=None):
    """Everything the UI needs to build its dropdowns."""
    return {
        "materials": [{"id": k, "name": m.name, "category": m.category}
                      for k, m in _materials().items()],
        "units": unit_options(),
        "end_conditions": list(column_buckling.END_CONDITIONS.keys()),
    }


# ---------------------------------------------------------------------------

HANDLERS = {
    "beam": beam, "stress": stress, "gears": gears, "thermal": thermal,
    "bearing": bearing, "buckling": buckling, "materials": materials,
    "units": units, "catalog": catalog,
}


def call(name: str, payload: str) -> str:
    """Entry point used by the web worker: JSON in, JSON out, errors included."""
    try:
        args = json.loads(payload) if payload else {}
        result = HANDLERS[name](args)
        return json.dumps({"ok": True, "result": _clean(result)})
    except Exception as exc:  # surface any problem to the UI as a message
        return json.dumps({"ok": False, "error": str(exc), "error_type": type(exc).__name__})
