"""
Tests for gear_ratio.py, thermodynamics.py, unit_converter.py,
bearing_life.py, and materials_database.py.
"""

import math
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mech_toolkit import gear_ratio, thermodynamics, unit_converter, bearing_life, materials_database
from mech_toolkit.gear_ratio import GearStage, GearTrain


# ---------------------------------------------------------------------
# gear_ratio.py
# ---------------------------------------------------------------------

def test_gear_ratio_reduction():
    # 20 tooth driver, 60 tooth driven -> 3:1 reduction
    assert math.isclose(gear_ratio.gear_ratio(20, 60), 3.0, rel_tol=1e-9)


def test_gear_ratio_rejects_nonpositive_teeth():
    with pytest.raises(ValueError):
        gear_ratio.gear_ratio(0, 20)


def test_output_speed_and_torque():
    ratio = gear_ratio.gear_ratio(20, 60)  # 3:1
    speed = gear_ratio.output_speed(1800, ratio)
    assert math.isclose(speed, 600, rel_tol=1e-9)

    torque = gear_ratio.output_torque(10, ratio, efficiency=1.0)
    assert math.isclose(torque, 30, rel_tol=1e-9)


def test_gear_train_overall_ratio_multiplies_stages():
    train = GearTrain([GearStage(20, 60), GearStage(15, 45)])  # 3:1 * 3:1 = 9:1
    assert math.isclose(train.overall_ratio, 9.0, rel_tol=1e-9)


def test_gear_train_output_speed():
    train = GearTrain([GearStage(20, 60), GearStage(15, 45)])
    speed = train.output_speed(1800)
    assert math.isclose(speed, 200, rel_tol=1e-9)


def test_gear_train_requires_at_least_one_stage():
    with pytest.raises(ValueError):
        GearTrain([])


# ---------------------------------------------------------------------
# thermodynamics.py
# ---------------------------------------------------------------------

def test_linear_thermal_expansion():
    dl = thermodynamics.linear_thermal_expansion(1.0, 12e-6, 100)
    assert math.isclose(dl, 12e-6 * 1.0 * 100, rel_tol=1e-9)


def test_thermal_stress():
    stress = thermodynamics.thermal_stress(12e-6, 200e9, 50)
    assert math.isclose(stress, 200e9 * 12e-6 * 50, rel_tol=1e-9)


def test_ideal_gas_law_round_trip():
    P, V, n, T = 101325.0, 0.0224, 1.0, 273.15
    # Check PV = nRT roughly holds for one mole of gas at STP
    computed_T = thermodynamics.ideal_gas_temperature(P, V, n)
    assert math.isclose(computed_T, T, rel_tol=0.02)


def test_conduction_heat_transfer():
    Q = thermodynamics.conduction_heat_transfer(k=50, area=0.01, delta_t=100, thickness=0.005) \
        if False else thermodynamics.conduction_heat_transfer(50, 0.01, 100, 0.005)
    assert math.isclose(Q, 50 * 0.01 * 100 / 0.005, rel_tol=1e-9)


def test_convection_heat_transfer():
    Q = thermodynamics.convection_heat_transfer(25, 0.5, 40)
    assert math.isclose(Q, 25 * 0.5 * 40, rel_tol=1e-9)


# ---------------------------------------------------------------------
# unit_converter.py
# ---------------------------------------------------------------------

def test_convert_stress_psi_to_pa():
    result = unit_converter.convert_stress(1, "psi", "Pa")
    assert math.isclose(result, 6894.757293168, rel_tol=1e-6)


def test_convert_length_round_trip():
    val = unit_converter.convert_length(10, "ft", "m")
    back = unit_converter.convert_length(val, "m", "ft")
    assert math.isclose(back, 10, rel_tol=1e-9)


def test_convert_temperature_freezing_and_boiling():
    assert math.isclose(unit_converter.convert_temperature(0, "C", "F"), 32, rel_tol=1e-9)
    assert math.isclose(unit_converter.convert_temperature(100, "C", "F"), 212, rel_tol=1e-9)
    assert math.isclose(unit_converter.convert_temperature(0, "C", "K"), 273.15, rel_tol=1e-9)


def test_convert_unknown_unit_raises():
    with pytest.raises(ValueError):
        unit_converter.convert_length(1, "furlong", "m")


# ---------------------------------------------------------------------
# bearing_life.py
# ---------------------------------------------------------------------

def test_bearing_l10_life_ball():
    result = bearing_life.bearing_l10_life(dynamic_load_rating=10000, equivalent_load=2000, bearing_type="ball")
    expected = (10000 / 2000) ** 3
    assert math.isclose(result.l10_revolutions, expected, rel_tol=1e-9)


def test_bearing_l10_life_with_speed_gives_hours():
    result = bearing_life.bearing_l10_life(
        dynamic_load_rating=10000, equivalent_load=2000, bearing_type="ball", speed_rpm=1000
    )
    assert result.l10_hours is not None
    assert result.l10_hours > 0


def test_bearing_l10_invalid_type_raises():
    with pytest.raises(ValueError):
        bearing_life.bearing_l10_life(10000, 2000, bearing_type="square")


def test_required_dynamic_load_rating_round_trip():
    C = bearing_life.required_dynamic_load_rating(equivalent_load=2000, target_l10_millions_rev=125, bearing_type="ball")
    result = bearing_life.bearing_l10_life(C, 2000, bearing_type="ball")
    assert math.isclose(result.l10_revolutions, 125, rel_tol=1e-6)


# ---------------------------------------------------------------------
# materials_database.py
# ---------------------------------------------------------------------

def test_get_material_case_insensitive():
    m1 = materials_database.get_material("Structural Steel A36")
    m2 = materials_database.get_material("structural steel a36")
    assert m1 == m2


def test_get_material_unknown_raises():
    with pytest.raises(KeyError):
        materials_database.get_material("unobtainium")


def test_list_materials_nonempty():
    materials = materials_database.list_materials()
    assert len(materials) > 5


def test_add_material():
    custom = materials_database.Material(
        "Test Alloy X", "Experimental", 100e9, 200e6, 250e6, 5000, 0.30, 15e-6
    )
    materials_database.add_material(custom)
    fetched = materials_database.get_material("Test Alloy X")
    assert fetched.yield_strength == 200e6
