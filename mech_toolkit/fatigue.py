"""
fatigue.py

Fatigue life check for parts under repeated (cyclic) loading.

A shaft, spring or bracket that sees a load go up and down millions of
times can crack at a stress well below its yield strength. This module
estimates the material's endurance limit, corrects it for the real part
(surface finish, size, type of loading), and then checks a fluctuating
stress against the classic fatigue failure lines:

    - Goodman   (the usual design choice, slightly conservative)
    - Soderberg (most conservative, uses yield instead of ultimate)
    - Gerber    (parabola, closest to test data for ductile metals)

It also reports the first-cycle yield safety factor, since a part can
pass the fatigue check and still yield on the very first load cycle.

The endurance-limit estimate (Se' = 0.5 * Sut) is for steels. Aluminum
and other non-ferrous metals have no true endurance limit, so pass a
measured fatigue strength via `endurance_limit=` for those.

Reference: Shigley's Mechanical Engineering Design, Ch. 6 (Fatigue).
"""

import math
from dataclasses import dataclass

from mech_toolkit.materials_database import Material, get_material


# Surface factor ka = a * Sut^b, Sut in MPa (Shigley Table 6-2).
SURFACE_FINISH = {
    "ground": (1.58, -0.085),
    "machined": (4.51, -0.265),
    "cold-drawn": (4.51, -0.265),
    "hot-rolled": (57.7, -0.718),
    "as-forged": (272.0, -0.995),
}

# Load factor kc (Shigley Eq. 6-26).
LOAD_TYPE = {"bending": 1.0, "axial": 0.85, "torsion": 0.59}

CRITERIA = ("goodman", "soderberg", "gerber")


@dataclass
class FatigueResult:
    alternating_stress: float   # Pa, sigma_a
    mean_stress: float          # Pa, sigma_m
    endurance_limit: float      # Pa, corrected Se
    criterion: str
    factor_of_safety: float     # fatigue safety factor n_f
    yield_factor_of_safety: float  # first-cycle yield n_y

    @property
    def is_safe(self) -> bool:
        return min(self.factor_of_safety, self.yield_factor_of_safety) >= 1.0

    def report(self) -> str:
        return "\n".join([
            "Fatigue Analysis",
            "=" * 40,
            f"Alternating stress:   {self.alternating_stress/1e6:.1f} MPa",
            f"Mean stress:          {self.mean_stress/1e6:.1f} MPa",
            f"Endurance limit Se:   {self.endurance_limit/1e6:.1f} MPa",
            f"Criterion:            {self.criterion.title()}",
            f"Fatigue FoS:          {self.factor_of_safety:.2f}",
            f"Yield FoS:            {self.yield_factor_of_safety:.2f}",
            f"Status:               {'SAFE' if self.is_safe else 'FAILS'}",
        ])


def _lookup(table: dict, key: str, what: str):
    k = key.strip().lower()
    if k not in table:
        raise ValueError(f"Unknown {what} '{key}'. Use one of: {', '.join(table)}")
    return table[k]


def uncorrected_endurance_limit(ultimate_strength: float) -> float:
    """Se' for steel: 0.5 * Sut, capped at 700 MPa when Sut > 1400 MPa."""
    if ultimate_strength <= 0:
        raise ValueError("ultimate_strength must be positive.")
    return min(0.5 * ultimate_strength, 700e6)


def surface_factor(ultimate_strength: float, finish: str = "machined") -> float:
    """Marin surface factor ka = a * Sut^b (Sut converted to MPa)."""
    a, b = _lookup(SURFACE_FINISH, finish, "surface finish")
    return a * (ultimate_strength / 1e6) ** b


def size_factor(diameter: float = None, load_type: str = "bending") -> float:
    """Marin size factor kb for a round part (diameter in m). 1.0 for axial or no diameter."""
    if diameter is None or load_type.strip().lower() == "axial":
        return 1.0
    d_mm = diameter * 1e3
    if d_mm <= 0:
        raise ValueError("diameter must be positive.")
    if d_mm <= 2.79:
        return 1.0
    if d_mm <= 51:
        return 1.24 * d_mm ** -0.107
    if d_mm <= 254:
        return 1.51 * d_mm ** -0.157
    raise ValueError("Size factor correlation only covers diameters up to 254 mm.")


def corrected_endurance_limit(ultimate_strength: float, finish: str = "machined",
                              diameter: float = None, load_type: str = "bending") -> float:
    """Se = ka * kb * kc * Se'."""
    kc = _lookup(LOAD_TYPE, load_type, "load type")
    return (surface_factor(ultimate_strength, finish)
            * size_factor(diameter, load_type)
            * kc
            * uncorrected_endurance_limit(ultimate_strength))


def alternating_and_mean(max_stress: float, min_stress: float):
    """sigma_a = |max - min| / 2, sigma_m = (max + min) / 2."""
    return abs(max_stress - min_stress) / 2.0, (max_stress + min_stress) / 2.0


def fatigue_factor_of_safety(alternating_stress: float, mean_stress: float,
                             endurance_limit: float, ultimate_strength: float,
                             yield_strength: float = None,
                             criterion: str = "goodman") -> float:
    """Fatigue safety factor n_f for the chosen criterion (load line through the origin)."""
    sa, sm, se = alternating_stress, mean_stress, endurance_limit
    crit = criterion.strip().lower()
    if crit not in CRITERIA:
        raise ValueError(f"Unknown criterion '{criterion}'. Use one of: {', '.join(CRITERIA)}")
    if sa < 0:
        raise ValueError("alternating_stress must be non-negative.")
    if sm <= 0:
        # A compressive mean stress doesn't help or hurt in these models:
        # failure is governed by the alternating stress alone.
        return math.inf if sa == 0 else se / sa
    if crit == "goodman":
        return 1.0 / (sa / se + sm / ultimate_strength)
    if crit == "soderberg":
        if yield_strength is None:
            raise ValueError("Soderberg needs yield_strength.")
        return 1.0 / (sa / se + sm / yield_strength)
    # Gerber: n*sa/Se + (n*sm/Sut)^2 = 1, solved for n.
    if sa == 0:
        return ultimate_strength / sm
    r = 2.0 * sm * se / (ultimate_strength * sa)
    return 0.5 * (ultimate_strength / sm) ** 2 * (sa / se) * (-1.0 + math.sqrt(1.0 + r ** 2))


def fatigue_analysis(max_stress: float, min_stress: float,
                     material="AISI 1045 Steel", finish: str = "machined",
                     diameter: float = None, load_type: str = "bending",
                     criterion: str = "goodman",
                     endurance_limit: float = None) -> FatigueResult:
    """
    Full fatigue check for a stress that cycles between min_stress and max_stress (Pa).

    material: a Material, or a name from materials_database
    finish: 'ground', 'machined', 'cold-drawn', 'hot-rolled', 'as-forged'
    diameter: round part diameter (m) for the size factor, optional
    load_type: 'bending', 'axial' or 'torsion'
    criterion: 'goodman', 'soderberg' or 'gerber'
    endurance_limit: override the estimated, corrected Se (Pa)
    """
    mat = material if isinstance(material, Material) else get_material(material)
    sut, sy = mat.ultimate_strength, mat.yield_strength
    se = endurance_limit or corrected_endurance_limit(sut, finish, diameter, load_type)
    sa, sm = alternating_and_mean(max_stress, min_stress)
    n_f = fatigue_factor_of_safety(sa, sm, se, sut, sy, criterion)
    peak = sa + abs(sm)
    n_y = math.inf if peak == 0 else sy / peak
    return FatigueResult(sa, sm, se, criterion.strip().lower(), n_f, n_y)
