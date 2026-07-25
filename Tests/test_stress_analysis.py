"""
Tests for stress_analysis.py.
"""

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mech_toolkit import stress_analysis


def test_bending_stress():
    # sigma = M*c/I
    result = stress_analysis.bending_stress(moment=1000, c=0.05, moment_of_inertia=2e-6)
    assert math.isclose(result, 1000 * 0.05 / 2e-6, rel_tol=1e-9)


def test_rectangular_max_shear_stress():
    # tau_max = 1.5 * V / A
    result = stress_analysis.rectangular_max_shear_stress(shear_force=1000, width=0.02, height=0.04)
    area = 0.02 * 0.04
    assert math.isclose(result, 1.5 * 1000 / area, rel_tol=1e-9)


def test_circular_max_shear_stress():
    result = stress_analysis.circular_max_shear_stress(shear_force=500, diameter=0.03)
    area = math.pi * 0.03 ** 2 / 4
    assert math.isclose(result, (4.0 / 3.0) * 500 / area, rel_tol=1e-9)


def test_solid_shaft_polar_moment():
    J = stress_analysis.solid_shaft_polar_moment(diameter=0.02)
    assert math.isclose(J, math.pi * 0.02 ** 4 / 32, rel_tol=1e-9)


def test_torsional_shear_stress():
    J = stress_analysis.solid_shaft_polar_moment(0.02)
    tau = stress_analysis.torsional_shear_stress(torque=50, r=0.01, polar_moment_j=J)
    assert math.isclose(tau, 50 * 0.01 / J, rel_tol=1e-9)


def test_max_torque_for_solid_shaft_round_trip():
    diameter = 0.025
    allowable = 80e6
    T_max = stress_analysis.max_torque_for_solid_shaft(diameter, allowable)

    J = stress_analysis.solid_shaft_polar_moment(diameter)
    r = diameter / 2
    back_calc_stress = stress_analysis.torsional_shear_stress(T_max, r, J)
    assert math.isclose(back_calc_stress, allowable, rel_tol=1e-6)


def test_principal_stresses_pure_uniaxial():
    # Pure uniaxial stress: sigma_x=100MPa, sigma_y=0, tau_xy=0
    # Principal stresses should just be 100MPa and 0.
    result = stress_analysis.principal_stresses(100e6, 0, 0)
    assert math.isclose(result.sigma_1, 100e6, rel_tol=1e-6)
    assert math.isclose(result.sigma_2, 0, abs_tol=1e-3)
    assert math.isclose(result.max_shear_stress, 50e6, rel_tol=1e-6)


def test_von_mises_pure_uniaxial_equals_stress():
    # Under pure uniaxial stress, von Mises stress should equal the applied stress
    result = stress_analysis.von_mises_stress(150e6, 0, 0)
    assert math.isclose(result, 150e6, rel_tol=1e-6)


def test_von_mises_pure_shear():
    # Under pure shear, von Mises stress = sqrt(3) * tau
    tau = 40e6
    result = stress_analysis.von_mises_stress(0, 0, tau)
    assert math.isclose(result, math.sqrt(3) * tau, rel_tol=1e-6)


def test_factor_of_safety():
    assert math.isclose(stress_analysis.factor_of_safety(250e6, 100e6), 2.5, rel_tol=1e-9)
    assert stress_analysis.factor_of_safety(250e6, 0) == float("inf")


def test_is_safe():
    assert stress_analysis.is_safe(250e6, 100e6)
    assert not stress_analysis.is_safe(250e6, 300e6)
