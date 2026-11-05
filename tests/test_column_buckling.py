"""
Tests for column_buckling.py. Expected values are hand calculations.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mech_toolkit import column_buckling as cb
from mech_toolkit.beam_calculator import circular_section


# Solid round A36 bar, d = 20 mm:
#   A = pi*0.02^2/4 = 3.14159e-4 m^2
#   I = pi*0.02^4/64 = 7.85398e-9 m^4
#   r = d/4 = 5 mm
D = 0.02
A = math.pi * D ** 2 / 4
I, _ = circular_section(D)


def test_radius_of_gyration_round_bar():
    assert math.isclose(cb.radius_of_gyration(I, A), D / 4, rel_tol=1e-9)


def test_transition_slenderness_a36():
    # sqrt(2 * pi^2 * 200e9 / 250e6) = 125.66
    assert math.isclose(cb.transition_slenderness_ratio(200e9, 250e6), 125.66, rel_tol=1e-3)


def test_euler_long_pinned_column():
    # L = 1 m, K = 1: KL/r = 200 > 125.7, so Euler applies.
    # P_cr = pi^2 * 200e9 * 7.85398e-9 / 1^2 = 15503 N
    result = cb.column_critical_load(1.0, A, I, "Structural Steel A36", "pinned-pinned")
    assert result.method == "euler"
    assert math.isclose(result.slenderness_ratio, 200.0, rel_tol=1e-9)
    assert math.isclose(result.critical_load, 15503, rel_tol=1e-3)


def test_fixed_free_quarter_of_pinned():
    # K = 2 doubles effective length, so P_cr drops by a factor of 4.
    pinned = cb.euler_critical_load(200e9, I, 1.0, k=1.0)
    flagpole = cb.euler_critical_load(200e9, I, 1.0, k=2.0)
    assert math.isclose(flagpole, pinned / 4, rel_tol=1e-12)


def test_johnson_intermediate_column():
    # L = 0.4 m, K = 1: KL/r = 80 < 125.7, so Johnson applies.
    # sigma_cr = 250e6 - (250e6 * 80 / (2*pi))^2 / 200e9 = 250 - 50.66 = 199.34 MPa
    # P_cr = 199.34e6 * 3.14159e-4 = 62624 N
    result = cb.column_critical_load(0.4, A, I, "Structural Steel A36")
    assert result.method == "johnson"
    assert math.isclose(result.critical_stress, 199.34e6, rel_tol=1e-3)
    assert math.isclose(result.critical_load, 62624, rel_tol=1e-3)


def test_curves_meet_at_transition():
    # At (KL/r)_t, Johnson stress equals Euler stress (= Sy / 2).
    E, Sy = 200e9, 250e6
    t = cb.transition_slenderness_ratio(E, Sy)
    euler_stress = math.pi ** 2 * E / t ** 2
    assert math.isclose(cb.johnson_critical_stress(E, Sy, t), euler_stress, rel_tol=1e-9)
    assert math.isclose(euler_stress, Sy / 2, rel_tol=1e-9)


def test_factor_of_safety():
    result = cb.column_critical_load(1.0, A, I, applied_load=5000)
    assert math.isclose(result.factor_of_safety, 15503 / 5000, rel_tol=1e-3)
    assert result.is_safe
    assert "SAFE" in result.report()


def test_unknown_end_condition():
    with pytest.raises(ValueError):
        cb.effective_length_factor("glued-on")
