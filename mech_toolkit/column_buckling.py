"""
column_buckling.py

Critical buckling load for axially loaded columns.

A slender column fails by buckling (sudden sideways bowing) long before
the material yields. A short, stocky column fails by crushing/yielding
instead. This module picks the right model automatically:

    - Euler formula for long (slender) columns
    - J.B. Johnson parabola for intermediate columns, where Euler would
      overpredict strength because the stress gets close to yield

The switch between the two happens at the transition slenderness ratio
(KL/r)_t = sqrt(2 * pi^2 * E / Sy), where the two curves meet tangentially.

Reference: Shigley's Mechanical Engineering Design, Ch. 4 (Columns).
"""

import math
from dataclasses import dataclass

from mech_toolkit.materials_database import Material, get_material


# Effective length factor K for the classic end conditions (theoretical
# values). Effective length Le = K * L.
END_CONDITIONS = {
    "pinned-pinned": 1.0,
    "fixed-free": 2.0,
    "fixed-pinned": 0.699,
    "fixed-fixed": 0.5,
}


@dataclass
class BucklingResult:
    critical_load: float          # N, load at which the column fails
    critical_stress: float        # Pa, critical_load / area
    slenderness_ratio: float      # K*L/r, unitless
    transition_slenderness: float # (KL/r) where Euler and Johnson meet
    method: str                   # "euler" or "johnson"
    applied_load: float = None    # N, optional

    @property
    def factor_of_safety(self) -> float:
        if not self.applied_load:
            return float("inf")
        return self.critical_load / self.applied_load

    @property
    def is_safe(self) -> bool:
        return self.factor_of_safety >= 1.0

    def report(self) -> str:
        lines = [
            "Column Buckling Analysis",
            "=" * 40,
            f"Method:               {self.method.title()}",
            f"Slenderness (KL/r):   {self.slenderness_ratio:.1f}",
            f"Transition (KL/r)_t:  {self.transition_slenderness:.1f}",
            f"Critical load:        {self.critical_load/1e3:.2f} kN",
            f"Critical stress:      {self.critical_stress/1e6:.1f} MPa",
        ]
        if self.applied_load:
            lines += [
                f"Applied load:         {self.applied_load/1e3:.2f} kN",
                f"Factor of safety:     {self.factor_of_safety:.2f}",
                f"Status:               {'SAFE' if self.is_safe else 'BUCKLES'}",
            ]
        return "\n".join(lines)


def effective_length_factor(end_condition: str) -> float:
    """Return K for an end condition name, e.g. 'pinned-pinned' or 'fixed-free'."""
    key = end_condition.strip().lower()
    if key not in END_CONDITIONS:
        raise ValueError(
            f"Unknown end condition '{end_condition}'. "
            f"Use one of: {', '.join(END_CONDITIONS)}"
        )
    return END_CONDITIONS[key]


def radius_of_gyration(moment_of_inertia: float, area: float) -> float:
    """r = sqrt(I / A), using the weak-axis I (the column buckles about it)."""
    if moment_of_inertia <= 0 or area <= 0:
        raise ValueError("moment_of_inertia and area must be positive.")
    return math.sqrt(moment_of_inertia / area)


def euler_critical_load(elastic_modulus: float, moment_of_inertia: float,
                        length: float, k: float = 1.0) -> float:
    """Euler buckling load: P_cr = pi^2 * E * I / (K * L)^2."""
    if length <= 0 or k <= 0:
        raise ValueError("length and k must be positive.")
    return math.pi ** 2 * elastic_modulus * moment_of_inertia / (k * length) ** 2


def transition_slenderness_ratio(elastic_modulus: float, yield_strength: float) -> float:
    """(KL/r)_t = sqrt(2 * pi^2 * E / Sy). Above this, Euler applies."""
    return math.sqrt(2.0 * math.pi ** 2 * elastic_modulus / yield_strength)


def johnson_critical_stress(elastic_modulus: float, yield_strength: float,
                            slenderness: float) -> float:
    """J.B. Johnson parabola: sigma_cr = Sy - (Sy * KL/r / (2*pi))^2 / E."""
    return yield_strength - (yield_strength * slenderness / (2.0 * math.pi)) ** 2 / elastic_modulus


def column_critical_load(length: float, area: float, moment_of_inertia: float,
                         material="Structural Steel A36",
                         end_condition: str = "pinned-pinned",
                         applied_load: float = None) -> BucklingResult:
    """
    Critical axial load for a column, choosing Euler or Johnson automatically.

    length: unsupported column length L (m)
    area: cross-sectional area A (m^2)
    moment_of_inertia: smallest second moment of area I (m^4)
    material: a Material, or a name from materials_database
    end_condition: 'pinned-pinned', 'fixed-free', 'fixed-pinned', 'fixed-fixed'
    applied_load: optional axial load (N), enables factor of safety
    """
    mat = material if isinstance(material, Material) else get_material(material)
    E, Sy = mat.elastic_modulus, mat.yield_strength

    k = effective_length_factor(end_condition)
    r = radius_of_gyration(moment_of_inertia, area)
    slenderness = k * length / r
    transition = transition_slenderness_ratio(E, Sy)

    if slenderness >= transition:
        method = "euler"
        p_cr = euler_critical_load(E, moment_of_inertia, length, k)
    else:
        method = "johnson"
        p_cr = johnson_critical_stress(E, Sy, slenderness) * area

    return BucklingResult(
        critical_load=p_cr,
        critical_stress=p_cr / area,
        slenderness_ratio=slenderness,
        transition_slenderness=transition,
        method=method,
        applied_load=applied_load,
    )
