"""
beam_calculator.py

Deflection, bending stress, and factor of safety for common beam
loading cases: cantilever and simply supported beams, under a point
load or a uniformly distributed load (UDL).

Formulas are standard Euler-Bernoulli beam theory (small deflection,
linear elastic material, constant cross section). Source: any
Mechanics of Materials text, e.g. Hibbeler, tables of beam
deflection.

Sign convention: deflection magnitude is reported as a positive
number (the "how far did it move" answer most people actually want),
not signed downward-negative.
"""

import math
from dataclasses import dataclass

from mech_toolkit.materials_database import get_material, Material


@dataclass
class BeamResult:
    beam_type: str
    length: float            # m
    load: float               # N (total load, or total of a UDL)
    material_name: str
    elastic_modulus: float    # Pa
    moment_of_inertia: float  # m^4
    max_moment: float         # N*m
    max_stress: float         # Pa
    max_deflection: float     # m
    yield_strength: float     # Pa

    @property
    def factor_of_safety(self) -> float:
        if self.max_stress == 0:
            return float("inf")
        return self.yield_strength / self.max_stress

    @property
    def is_safe(self) -> bool:
        return self.factor_of_safety >= 1.0

    def report(self) -> str:
        fos = self.factor_of_safety
        status = "SAFE" if self.is_safe else "UNSAFE - REDESIGN REQUIRED"
        fos_str = "inf" if math.isinf(fos) else f"{fos:.1f}"
        width = 40
        lines = [
            "=" * width,
            self.beam_type,
            "=" * width,
            "",
            f"Length:      {self.length:.2f} m",
            f"Load:        {self.load:.1f} N",
            f"Material:    {self.material_name}",
            "",
            "Maximum Bending Moment:",
            f"{self.max_moment:.1f} N*m",
            "",
            "Maximum Stress:",
            f"{self.max_stress/1e6:.1f} MPa",
            "",
            "Maximum Deflection:",
            f"{self.max_deflection*1000:.2f} mm",
            "",
            "Factor of Safety:",
            fos_str,
            "",
            "Beam Status:",
            status,
            "=" * width,
        ]
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.report()


# ---------------------------------------------------------------------
# Cross-section helpers
# ---------------------------------------------------------------------

def rectangular_section(width: float, height: float):
    """
    Returns (I, c) for a solid rectangular cross section.
    width, height in meters. Bending is assumed about the axis
    parallel to 'width' (i.e. 'height' is the dimension in the
    direction of bending).
    """
    I = width * height ** 3 / 12.0
    c = height / 2.0
    return I, c


def circular_section(diameter: float):
    """Returns (I, c) for a solid circular cross section."""
    I = math.pi * diameter ** 4 / 64.0
    c = diameter / 2.0
    return I, c


def hollow_circular_section(outer_diameter: float, inner_diameter: float):
    """Returns (I, c) for a hollow circular (tube) cross section."""
    I = math.pi * (outer_diameter ** 4 - inner_diameter ** 4) / 64.0
    c = outer_diameter / 2.0
    return I, c


# ---------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------

def _resolve_material(material) -> Material:
    if isinstance(material, Material):
        return material
    return get_material(material)


# ---------------------------------------------------------------------
# Cantilever beam
# ---------------------------------------------------------------------

def cantilever_point_load(length: float, load: float, moment_of_inertia: float,
                           section_modulus_c: float, material="Structural Steel A36") -> BeamResult:
    """
    Cantilever beam, fixed at one end, point load P at the free end.

    Max moment:      M = P * L                  (at the fixed end)
    Max deflection:  d = P * L^3 / (3 * E * I)   (at the free end)
    Max stress:      s = M * c / I
    """
    mat = _resolve_material(material)
    E = mat.elastic_modulus

    max_moment = load * length
    max_deflection = load * length ** 3 / (3 * E * moment_of_inertia)
    max_stress = max_moment * section_modulus_c / moment_of_inertia

    return BeamResult(
        beam_type="Cantilever Beam Analysis (Point Load)",
        length=length, load=load, material_name=mat.name,
        elastic_modulus=E, moment_of_inertia=moment_of_inertia,
        max_moment=max_moment, max_stress=max_stress,
        max_deflection=max_deflection, yield_strength=mat.yield_strength,
    )


def cantilever_udl(length: float, total_load: float, moment_of_inertia: float,
                    section_modulus_c: float, material="Structural Steel A36") -> BeamResult:
    """
    Cantilever beam, fixed at one end, uniformly distributed load
    over the full length. `total_load` is the total force (w * L),
    not the load-per-length.

    Max moment:      M = w * L^2 / 2 = (total_load * L) / 2
    Max deflection:  d = w * L^4 / (8 * E * I) = (total_load * L^3) / (8 * E * I)
    """
    mat = _resolve_material(material)
    E = mat.elastic_modulus
    w = total_load / length  # load per unit length

    max_moment = w * length ** 2 / 2.0
    max_deflection = w * length ** 4 / (8 * E * moment_of_inertia)
    max_stress = max_moment * section_modulus_c / moment_of_inertia

    return BeamResult(
        beam_type="Cantilever Beam Analysis (UDL)",
        length=length, load=total_load, material_name=mat.name,
        elastic_modulus=E, moment_of_inertia=moment_of_inertia,
        max_moment=max_moment, max_stress=max_stress,
        max_deflection=max_deflection, yield_strength=mat.yield_strength,
    )


# ---------------------------------------------------------------------
# Simply supported beam
# ---------------------------------------------------------------------

def simply_supported_center_load(length: float, load: float, moment_of_inertia: float,
                                  section_modulus_c: float, material="Structural Steel A36") -> BeamResult:
    """
    Simply supported beam, point load P at midspan.

    Max moment:      M = P * L / 4              (at midspan)
    Max deflection:  d = P * L^3 / (48 * E * I)  (at midspan)
    """
    mat = _resolve_material(material)
    E = mat.elastic_modulus

    max_moment = load * length / 4.0
    max_deflection = load * length ** 3 / (48 * E * moment_of_inertia)
    max_stress = max_moment * section_modulus_c / moment_of_inertia

    return BeamResult(
        beam_type="Simply Supported Beam Analysis (Center Point Load)",
        length=length, load=load, material_name=mat.name,
        elastic_modulus=E, moment_of_inertia=moment_of_inertia,
        max_moment=max_moment, max_stress=max_stress,
        max_deflection=max_deflection, yield_strength=mat.yield_strength,
    )


def simply_supported_udl(length: float, total_load: float, moment_of_inertia: float,
                          section_modulus_c: float, material="Structural Steel A36") -> BeamResult:
    """
    Simply supported beam, uniformly distributed load over the full
    span. `total_load` is the total force (w * L).

    Max moment:      M = w * L^2 / 8              (at midspan)
    Max deflection:  d = 5 * w * L^4 / (384 * E * I)
    """
    mat = _resolve_material(material)
    E = mat.elastic_modulus
    w = total_load / length

    max_moment = w * length ** 2 / 8.0
    max_deflection = 5 * w * length ** 4 / (384 * E * moment_of_inertia)
    max_stress = max_moment * section_modulus_c / moment_of_inertia

    return BeamResult(
        beam_type="Simply Supported Beam Analysis (UDL)",
        length=length, load=total_load, material_name=mat.name,
        elastic_modulus=E, moment_of_inertia=moment_of_inertia,
        max_moment=max_moment, max_stress=max_stress,
        max_deflection=max_deflection, yield_strength=mat.yield_strength,
    )


# ---------------------------------------------------------------------
# Deflection curves (used by plotting.py)
# ---------------------------------------------------------------------

def cantilever_point_load_curve(length: float, load: float, elastic_modulus: float,
                                 moment_of_inertia: float, num_points: int = 100):
    """
    Returns (x, y) arrays of the deflection shape for a cantilever
    beam with a point load at the free end. y(x) = P*x^2*(3L - x) / (6EI)
    """
    xs = [length * i / (num_points - 1) for i in range(num_points)]
    ys = [
        (load * x ** 2 * (3 * length - x)) / (6 * elastic_modulus * moment_of_inertia)
        for x in xs
    ]
    return xs, ys


def simply_supported_center_load_curve(length: float, load: float, elastic_modulus: float,
                                        moment_of_inertia: float, num_points: int = 100):
    """
    Returns (x, y) arrays of the deflection shape for a simply
    supported beam with a point load at midspan. Uses the standard
    piecewise closed-form solution.
    """
    E, I, P, L = elastic_modulus, moment_of_inertia, load, length
    xs = [L * i / (num_points - 1) for i in range(num_points)]
    ys = []
    for x in xs:
        if x <= L / 2:
            y = (P * x * (3 * L ** 2 - 4 * x ** 2)) / (48 * E * I)
        else:
            xp = L - x
            y = (P * xp * (3 * L ** 2 - 4 * xp ** 2)) / (48 * E * I)
        ys.append(y)
    return xs, ys
