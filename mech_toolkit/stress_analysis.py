"""
stress_analysis.py

Core stress calculations: bending stress, transverse shear stress,
torsional shear stress, combined/principal stresses, von Mises
equivalent stress, and factor of safety.

All inputs and outputs are in SI base units (Pa, N, m, N*m) unless
noted otherwise.
"""

import math
from dataclasses import dataclass


# ---------------------------------------------------------------------
# Bending
# ---------------------------------------------------------------------

def bending_stress(moment: float, c: float, moment_of_inertia: float) -> float:
    """
    Normal stress due to bending: sigma = M * c / I

    moment: bending moment (N*m)
    c: distance from the neutral axis to the outer fiber (m)
    moment_of_inertia: second moment of area of the cross section (m^4)
    """
    return moment * c / moment_of_inertia


# ---------------------------------------------------------------------
# Shear
# ---------------------------------------------------------------------

def transverse_shear_stress(shear_force: float, first_moment_q: float,
                             moment_of_inertia: float, thickness: float) -> float:
    """
    Transverse shear stress at a point in a beam cross section:
    tau = V * Q / (I * t)

    shear_force: internal shear force at the section (N)
    first_moment_q: first moment of area above/below the point of
        interest about the neutral axis (m^3)
    moment_of_inertia: second moment of area of the full cross section (m^4)
    thickness: width of the cross section at the point of interest (m)
    """
    return shear_force * first_moment_q / (moment_of_inertia * thickness)


def rectangular_max_shear_stress(shear_force: float, width: float, height: float) -> float:
    """
    Max transverse shear stress for a solid rectangular section
    (occurs at the neutral axis): tau_max = 1.5 * V / A
    """
    area = width * height
    return 1.5 * shear_force / area


def circular_max_shear_stress(shear_force: float, diameter: float) -> float:
    """
    Max transverse shear stress for a solid circular section
    (occurs at the neutral axis): tau_max = 4/3 * V / A
    """
    area = math.pi * diameter ** 2 / 4.0
    return (4.0 / 3.0) * shear_force / area


# ---------------------------------------------------------------------
# Torsion
# ---------------------------------------------------------------------

def torsional_shear_stress(torque: float, r: float, polar_moment_j: float) -> float:
    """
    Shear stress in a circular shaft under torsion: tau = T * r / J

    torque: applied torque (N*m)
    r: radial distance from the shaft center (m), use r = d/2 for the
       max stress at the outer surface
    polar_moment_j: polar second moment of area (m^4)
    """
    return torque * r / polar_moment_j


def solid_shaft_polar_moment(diameter: float) -> float:
    """Polar moment of area, J, for a solid circular shaft."""
    return math.pi * diameter ** 4 / 32.0


def hollow_shaft_polar_moment(outer_diameter: float, inner_diameter: float) -> float:
    """Polar moment of area, J, for a hollow circular shaft."""
    return math.pi * (outer_diameter ** 4 - inner_diameter ** 4) / 32.0


def shaft_angle_of_twist(torque: float, length: float, shear_modulus: float,
                          polar_moment_j: float) -> float:
    """
    Angle of twist (radians) for a circular shaft: theta = T * L / (G * J)
    """
    return torque * length / (shear_modulus * polar_moment_j)


def max_torque_for_solid_shaft(diameter: float, allowable_shear_stress: float) -> float:
    """
    Max torque a solid circular shaft can carry before exceeding an
    allowable shear stress. Rearranges tau = T*r/J for T.
    """
    J = solid_shaft_polar_moment(diameter)
    r = diameter / 2.0
    return allowable_shear_stress * J / r


# ---------------------------------------------------------------------
# Combined / principal stress
# ---------------------------------------------------------------------

@dataclass
class PrincipalStressResult:
    sigma_1: float          # max principal stress (Pa)
    sigma_2: float          # min principal stress (Pa)
    max_shear_stress: float  # max in-plane shear stress (Pa)
    angle_principal_deg: float  # angle to the principal plane (degrees)


def principal_stresses(sigma_x: float, sigma_y: float, tau_xy: float) -> PrincipalStressResult:
    """
    2D (plane stress) principal stresses from Mohr's circle relations.
    """
    avg = (sigma_x + sigma_y) / 2.0
    radius = math.sqrt(((sigma_x - sigma_y) / 2.0) ** 2 + tau_xy ** 2)

    sigma_1 = avg + radius
    sigma_2 = avg - radius
    max_shear = radius

    if sigma_x == sigma_y:
        angle_rad = math.pi / 4.0 if tau_xy != 0 else 0.0
    else:
        angle_rad = 0.5 * math.atan2(2 * tau_xy, (sigma_x - sigma_y))
    angle_deg = math.degrees(angle_rad)

    return PrincipalStressResult(sigma_1, sigma_2, max_shear, angle_deg)


def von_mises_stress(sigma_x: float, sigma_y: float, tau_xy: float) -> float:
    """
    Von Mises equivalent stress for a 2D (plane stress) state:
    sigma_vm = sqrt(sigma_x^2 - sigma_x*sigma_y + sigma_y^2 + 3*tau_xy^2)
    """
    return math.sqrt(sigma_x ** 2 - sigma_x * sigma_y + sigma_y ** 2 + 3 * tau_xy ** 2)


def von_mises_stress_3d(sigma_1: float, sigma_2: float, sigma_3: float) -> float:
    """
    Von Mises equivalent stress from the three principal stresses:
    sigma_vm = sqrt(0.5 * [(s1-s2)^2 + (s2-s3)^2 + (s3-s1)^2])
    """
    return math.sqrt(0.5 * (
        (sigma_1 - sigma_2) ** 2 + (sigma_2 - sigma_3) ** 2 + (sigma_3 - sigma_1) ** 2
    ))


# ---------------------------------------------------------------------
# Factor of safety
# ---------------------------------------------------------------------

def factor_of_safety(yield_strength: float, applied_stress: float) -> float:
    """
    Factor of safety = yield strength / applied (working) stress.
    Returns float('inf') if the applied stress is zero.
    """
    if applied_stress == 0:
        return float("inf")
    return yield_strength / applied_stress


def is_safe(yield_strength: float, applied_stress: float, min_fos: float = 1.0) -> bool:
    """True if factor_of_safety >= min_fos."""
    return factor_of_safety(yield_strength, applied_stress) >= min_fos
