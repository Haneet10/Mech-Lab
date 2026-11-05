"""
Tests for playground/py/bridge.py, the adapter the live web playground uses.

Each handler must succeed on the playground's default inputs, return
numbers that match calling mech_toolkit directly, and report bad input as
a message instead of crashing.
"""

import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "playground", "py"))

import bridge  # noqa: E402
from mech_toolkit import beam_calculator, bearing_life, column_buckling, gear_ratio  # noqa: E402


def call(name, args):
    out = json.loads(bridge.call(name, json.dumps(args)))
    return out


def ok(name, args):
    out = call(name, args)
    assert out["ok"], out
    return out["result"]


BEAM = dict(support="cantilever", load_type="point", L=2.0, P=400.0, material="structural steel a36",
            section="rect", b=0.025, h=0.060, d=0.03, do=0.06, di=0.05)


def test_beam_matches_toolkit_for_every_case():
    I, c = beam_calculator.rectangular_section(0.025, 0.060)
    cases = {
        ("cantilever", "point"): beam_calculator.cantilever_point_load,
        ("cantilever", "udl"): beam_calculator.cantilever_udl,
        ("simple", "point"): beam_calculator.simply_supported_center_load,
        ("simple", "udl"): beam_calculator.simply_supported_udl,
    }
    for (support, load_type), fn in cases.items():
        r = ok("beam", {**BEAM, "support": support, "load_type": load_type})
        ref = fn(2.0, 400.0, I, c, "structural steel a36")
        assert math.isclose(r["max_stress"], ref.max_stress)
        assert math.isclose(r["max_deflection"], ref.max_deflection)
        # the plotted curve must reach the reported maximum
        assert math.isclose(max(abs(y) for y in r["y"]), ref.max_deflection, rel_tol=1e-6)
        # bending moment diagram peaks at the reported max moment
        assert math.isclose(max(abs(m) for m in r["M"]), abs(ref.max_moment), rel_tol=1e-3)


def test_beam_bad_tube_is_an_error_message():
    out = call("beam", {**BEAM, "section": "tube", "do": 0.04, "di": 0.05})
    assert not out["ok"] and "inner diameter" in out["error"]


def test_stress_principal_values():
    r = ok("stress", dict(sx=80e6, sy=-20e6, txy=30e6, material="structural steel a36"))
    assert math.isclose(r["sigma_1"] + r["sigma_2"], 60e6)
    assert math.isclose(r["tau_max"], math.hypot(50e6, 30e6))
    assert r["safe"] is True


def test_gears_shaft_speeds_and_torques():
    r = ok("gears", dict(stages=[[18, 54], [16, 48]], rpm=1750, torque=4.5, efficiency=0.97, module=2))
    train = gear_ratio.GearTrain([gear_ratio.GearStage(18, 54), gear_ratio.GearStage(16, 48)])
    assert math.isclose(r["overall_ratio"], 9.0)
    assert math.isclose(r["shafts"][-1]["rpm"], train.output_speed(1750))
    assert math.isclose(r["shafts"][-1]["torque"], train.output_torque(4.5, 0.97))
    assert math.isclose(r["stages"][0]["center_distance"], 72.0)


def test_thermal_both_modes():
    r = ok("thermal", dict(mode="expansion", material="aluminum 6061-t6", L=1.0, dT=60))
    assert math.isclose(r["dL"], 23.6e-6 * 60)
    h = ok("thermal", dict(mode="heat", k=0.8, A=10, t=0.2, dT=20, h=10))
    assert math.isclose(h["q"], 20 / (0.2 / 8 + 1 / 100))
    assert math.isclose(h["dT_wall"] + h["dT_film"], 20)


def test_bearing_life_and_required_rating_agree():
    r = ok("bearing", dict(C=14000, P=2000, type="ball", rpm=1800, target_hours=20000))
    assert math.isclose(r["l10_hours"], bearing_life.bearing_l10_life(14000, 2000, "ball", 1800).l10_hours)
    # a bearing with exactly the required rating just meets the target
    again = bearing_life.bearing_l10_life(r["required_C"], 2000, "ball", 1800).l10_hours
    assert math.isclose(again, 20000, rel_tol=1e-9)


def test_buckling_matches_toolkit():
    args = dict(section="circle", d=0.03, b=0.03, h=0.04, do=0.048, di=0.04, L=1.5,
                end="pinned-pinned", P=20000, material="structural steel a36")
    r = ok("buckling", args)
    A = math.pi * 0.03 ** 2 / 4
    I, _ = beam_calculator.circular_section(0.03)
    ref = column_buckling.column_critical_load(1.5, A, I, "structural steel a36", "pinned-pinned", 20000)
    assert math.isclose(r["critical_load"], ref.critical_load)
    assert r["method"] == ref.method


def test_materials_units_and_catalog():
    mats = ok("materials", {})["materials"]
    assert any(m["id"] == "structural steel a36" for m in mats)
    u = ok("units", {"category": "length", "value": 1, "from": "in", "to": "mm"})
    assert math.isclose(u["result"], 25.4)
    t = ok("units", {"category": "temperature", "value": 212, "from": "F", "to": "C"})
    assert math.isclose(t["result"], 100)
    cat = ok("catalog", {})
    assert set(cat["end_conditions"]) == set(column_buckling.END_CONDITIONS)
    # every material id in the catalog resolves (some display names differ from their keys)
    for m in cat["materials"]:
        ok("thermal", dict(mode="expansion", material=m["id"], L=1, dT=10))


def test_bridge_imports_without_numpy_or_matplotlib():
    """The browser build ships no numpy/matplotlib, so the bridge must not need them."""
    import subprocess
    code = ("import sys; sys.path[:0] = [%r, %r]; import bridge; "
            "assert 'matplotlib' not in sys.modules and 'numpy' not in sys.modules") % (
        ROOT, os.path.join(ROOT, "playground", "py"))
    subprocess.run([sys.executable, "-c", code], check=True)
