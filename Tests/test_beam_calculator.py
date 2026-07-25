"""
Tests for beam_calculator.py, checked against hand-calculated values
from standard cantilever and simply-supported beam formulas.
"""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mech_toolkit import beam_calculator


def test_rectangular_section_properties():
    I, c = beam_calculator.rectangular_section(width=0.02, height=0.04)
    assert math.isclose(I, 0.02 * 0.04 ** 3 / 12, rel_tol=1e-9)
    assert math.isclose(c, 0.02, rel_tol=1e-9)


def test_circular_section_properties():
    I, c = beam_calculator.circular_section(diameter=0.05)
    assert math.isclose(I, math.pi * 0.05 ** 4 / 64, rel_tol=1e-9)
    assert math.isclose(c, 0.025, rel_tol=1e-9)


def test_hollow_circular_section_properties():
    I, c = beam_calculator.hollow_circular_section(outer_diameter=0.05, inner_diameter=0.04)
    expected_I = math.pi * (0.05 ** 4 - 0.04 ** 4) / 64
    assert math.isclose(I, expected_I, rel_tol=1e-9)
    assert math.isclose(c, 0.025, rel_tol=1e-9)


def test_cantilever_point_load_matches_hand_calc():
    # Hand calc: L=1m, P=1000N, rectangular 0.02 x 0.04 m section, steel E=200GPa
    length, load = 1.0, 1000.0
    I, c = beam_calculator.rectangular_section(0.02, 0.04)
    result = beam_calculator.cantilever_point_load(
        length, load, I, c, material="Structural Steel A36"
    )

    expected_moment = load * length  # 1000 N*m
    expected_deflection = load * length ** 3 / (3 * 200e9 * I)
    expected_stress = expected_moment * c / I

    assert math.isclose(result.max_moment, expected_moment, rel_tol=1e-6)
    assert math.isclose(result.max_deflection, expected_deflection, rel_tol=1e-6)
    assert math.isclose(result.max_stress, expected_stress, rel_tol=1e-6)


def test_cantilever_factor_of_safety_and_status():
    # Small load -> high FOS -> should be SAFE
    I, c = beam_calculator.rectangular_section(0.025, 0.06)
    result = beam_calculator.cantilever_point_load(2.0, 50, I, c, material="Structural Steel A36")
    assert result.is_safe
    assert result.factor_of_safety > 1.0

    # Huge load -> low FOS -> should be UNSAFE
    result_unsafe = beam_calculator.cantilever_point_load(2.0, 50000, I, c, material="Structural Steel A36")
    assert not result_unsafe.is_safe
    assert result_unsafe.factor_of_safety < 1.0


def test_simply_supported_center_load_matches_hand_calc():
    length, load = 2.0, 800.0
    I, c = beam_calculator.rectangular_section(0.03, 0.05)
    result = beam_calculator.simply_supported_center_load(length, load, I, c)

    expected_moment = load * length / 4.0
    expected_deflection = load * length ** 3 / (48 * result.elastic_modulus * I)

    assert math.isclose(result.max_moment, expected_moment, rel_tol=1e-6)
    assert math.isclose(result.max_deflection, expected_deflection, rel_tol=1e-6)


def test_simply_supported_udl_matches_hand_calc():
    length, total_load = 3.0, 900.0
    I, c = beam_calculator.rectangular_section(0.03, 0.06)
    result = beam_calculator.simply_supported_udl(length, total_load, I, c)

    w = total_load / length
    expected_moment = w * length ** 2 / 8.0
    expected_deflection = 5 * w * length ** 4 / (384 * result.elastic_modulus * I)

    assert math.isclose(result.max_moment, expected_moment, rel_tol=1e-6)
    assert math.isclose(result.max_deflection, expected_deflection, rel_tol=1e-6)


def test_cantilever_udl_matches_hand_calc():
    length, total_load = 2.0, 1000.0
    I, c = beam_calculator.rectangular_section(0.02, 0.05)
    result = beam_calculator.cantilever_udl(length, total_load, I, c)

    w = total_load / length
    expected_moment = w * length ** 2 / 2.0
    expected_deflection = w * length ** 4 / (8 * result.elastic_modulus * I)

    assert math.isclose(result.max_moment, expected_moment, rel_tol=1e-6)
    assert math.isclose(result.max_deflection, expected_deflection, rel_tol=1e-6)


def test_report_contains_expected_fields():
    I, c = beam_calculator.rectangular_section(0.025, 0.06)
    result = beam_calculator.cantilever_point_load(2.0, 400, I, c)
    report = result.report()
    assert "Cantilever Beam Analysis" in report
    assert "Maximum Stress" in report
    assert "Maximum Deflection" in report
    assert "Factor of Safety" in report
    assert "Beam Status" in report
