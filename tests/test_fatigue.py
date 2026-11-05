"""
Tests for fatigue.py. Expected values are hand calculations.
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mech_toolkit import fatigue as f

MPa = 1e6

# Round numbers for the failure criteria:
#   Se = 200 MPa, Sut = 600 MPa, Sy = 400 MPa, sigma_a = 80 MPa, sigma_m = 120 MPa
SE, SUT, SY, SA, SM = 200 * MPa, 600 * MPa, 400 * MPa, 80 * MPa, 120 * MPa


def test_alternating_and_mean():
    # Cycling 200 to -40 MPa: sigma_a = 120, sigma_m = 80
    sa, sm = f.alternating_and_mean(200 * MPa, -40 * MPa)
    assert math.isclose(sa, 120 * MPa)
    assert math.isclose(sm, 80 * MPa)


def test_uncorrected_endurance_limit_and_cap():
    assert math.isclose(f.uncorrected_endurance_limit(625 * MPa), 312.5 * MPa)
    # Above Sut = 1400 MPa the estimate caps at 700 MPa
    assert math.isclose(f.uncorrected_endurance_limit(1600 * MPa), 700 * MPa)


def test_surface_factor_machined_1045():
    # ka = 4.51 * 625^-0.265 = 0.8190
    assert math.isclose(f.surface_factor(625 * MPa, "machined"), 0.8190, rel_tol=1e-3)


def test_size_factor_ranges():
    # d = 30 mm: kb = 1.24 * 30^-0.107 = 0.8618
    assert math.isclose(f.size_factor(0.030), 0.8618, rel_tol=1e-3)
    # d = 100 mm: kb = 1.51 * 100^-0.157 = 0.7328
    assert math.isclose(f.size_factor(0.100), 0.7328, rel_tol=1e-3)
    assert f.size_factor(0.030, "axial") == 1.0
    assert f.size_factor(None) == 1.0


def test_corrected_endurance_limit_1045_shaft():
    # Se = 0.8190 * 0.8617 * 1.0 * 312.5 MPa = 220.5 MPa
    se = f.corrected_endurance_limit(625 * MPa, "machined", 0.030, "bending")
    assert math.isclose(se, 220.5 * MPa, rel_tol=1e-3)


def test_goodman():
    # n = 1 / (80/200 + 120/600) = 1 / 0.6 = 1.667
    n = f.fatigue_factor_of_safety(SA, SM, SE, SUT, SY, "goodman")
    assert math.isclose(n, 5 / 3, rel_tol=1e-9)


def test_soderberg():
    # n = 1 / (80/200 + 120/400) = 1 / 0.7 = 1.4286
    n = f.fatigue_factor_of_safety(SA, SM, SE, SUT, SY, "soderberg")
    assert math.isclose(n, 1 / 0.7, rel_tol=1e-9)


def test_gerber():
    # r = 2*120*200/(600*80) = 1, n = 0.5 * 5^2 * 0.4 * (sqrt(2) - 1) = 2.0711
    n = f.fatigue_factor_of_safety(SA, SM, SE, SUT, SY, "gerber")
    assert math.isclose(n, 5 * (math.sqrt(2) - 1), rel_tol=1e-9)
    # It lands exactly on the Gerber parabola
    assert math.isclose(n * SA / SE + (n * SM / SUT) ** 2, 1.0, rel_tol=1e-9)


def test_criteria_ordering():
    # Soderberg is most conservative, Gerber least
    ns = [f.fatigue_factor_of_safety(SA, SM, SE, SUT, SY, c)
          for c in ("soderberg", "goodman", "gerber")]
    assert ns == sorted(ns)


def test_fully_reversed_ignores_mean_criterion():
    # sigma_m = 0: every criterion gives n = Se / sigma_a = 2.5
    for c in f.CRITERIA:
        assert math.isclose(f.fatigue_factor_of_safety(SA, 0, SE, SUT, SY, c), 2.5)


def test_full_analysis_reports_yield_check():
    # Override Se so the numbers match the hand calc above.
    # 1045: Sy = 375 MPa. Peak = 80 + 120 = 200 MPa, n_y = 1.875
    result = f.fatigue_analysis(200 * MPa, 40 * MPa, "AISI 1045 Steel",
                                endurance_limit=SE)
    assert math.isclose(result.alternating_stress, SA)
    assert math.isclose(result.mean_stress, SM)
    # Goodman with Sut = 625 MPa: 1 / (0.4 + 0.192) = 1.689
    assert math.isclose(result.factor_of_safety, 1 / (0.4 + 120 / 625), rel_tol=1e-9)
    assert math.isclose(result.yield_factor_of_safety, 1.875, rel_tol=1e-9)
    assert result.is_safe
    assert "Goodman" in result.report()


def test_bad_inputs():
    with pytest.raises(ValueError):
        f.surface_factor(625 * MPa, "polished-ish")
    with pytest.raises(ValueError):
        f.fatigue_factor_of_safety(SA, SM, SE, SUT, SY, "morrow")
    with pytest.raises(ValueError):
        f.fatigue_factor_of_safety(SA, SM, SE, SUT, None, "soderberg")
