"""
materials_database.py

Lookup table of common engineering material properties, used by the
other modules in this toolkit (stress analysis, beam calculator, etc).

All values are stored in SI base units:
    - Young's modulus (E)        -> Pa
    - Yield strength             -> Pa
    - Ultimate tensile strength  -> Pa
    - Density                    -> kg/m^3
    - Poisson's ratio            -> unitless
    - Thermal expansion coeff.   -> 1/K

Values are typical published handbook figures (e.g. MatWeb, ASM
handbooks). Real designs should confirm properties against a
certified material data sheet or mill cert, this database is for
estimation and coursework use.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    category: str
    elastic_modulus: float        # Pa
    yield_strength: float         # Pa
    ultimate_strength: float      # Pa
    density: float                # kg/m^3
    poisson_ratio: float
    thermal_expansion: float      # 1/K

    def __str__(self) -> str:
        return (
            f"{self.name} ({self.category})\n"
            f"  E   = {self.elastic_modulus/1e9:.1f} GPa\n"
            f"  Sy  = {self.yield_strength/1e6:.0f} MPa\n"
            f"  Su  = {self.ultimate_strength/1e6:.0f} MPa\n"
            f"  rho = {self.density:.0f} kg/m^3\n"
            f"  nu  = {self.poisson_ratio:.2f}\n"
            f"  alpha = {self.thermal_expansion:.2e} 1/K"
        )


# Handbook-typical values. Keys are lowercase for lookup convenience.
_MATERIALS = {
    "structural steel a36": Material(
        "Structural Steel A36", "Steel",
        200e9, 250e6, 400e6, 7850, 0.26, 12.0e-6,
    ),
    "stainless steel 304": Material(
        "Stainless Steel 304", "Steel",
        193e9, 215e6, 505e6, 8000, 0.29, 17.3e-6,
    ),
    "stainless steel 316": Material(
        "Stainless Steel 316", "Steel",
        193e9, 240e6, 550e6, 8000, 0.28, 16.0e-6,
    ),
    "aisi 1045 steel": Material(
        "AISI 1045 Steel (normalized)", "Steel",
        205e9, 375e6, 625e6, 7870, 0.29, 11.5e-6,
    ),
    "aluminum 6061-t6": Material(
        "Aluminum 6061-T6", "Aluminum",
        68.9e9, 276e6, 310e6, 2700, 0.33, 23.6e-6,
    ),
    "aluminum 7075-t6": Material(
        "Aluminum 7075-T6", "Aluminum",
        71.7e9, 503e6, 572e6, 2810, 0.33, 23.4e-6,
    ),
    "titanium ti-6al-4v": Material(
        "Titanium Ti-6Al-4V", "Titanium",
        113.8e9, 880e6, 950e6, 4430, 0.34, 8.6e-6,
    ),
    "gray cast iron": Material(
        "Gray Cast Iron (ASTM 40)", "Cast Iron",
        110e9, 152e6, 293e6, 7150, 0.26, 10.8e-6,
    ),
    "brass c360": Material(
        "Brass C360", "Copper Alloy",
        97e9, 124e6, 338e6, 8500, 0.34, 20.5e-6,
    ),
    "copper c101": Material(
        "Copper C101", "Copper",
        117e9, 69e6, 220e6, 8940, 0.34, 17.0e-6,
    ),
    "abs plastic": Material(
        "ABS Plastic", "Polymer",
        2.3e9, 40e6, 43e6, 1050, 0.35, 90.0e-6,
    ),
    "nylon 6/6": Material(
        "Nylon 6/6", "Polymer",
        2.9e9, 45e6, 83e6, 1140, 0.39, 80.0e-6,
    ),
}


def get_material(name: str) -> Material:
    """
    Look up a material by name (case-insensitive). Raises KeyError with
    a helpful message if not found.
    """
    key = name.strip().lower()
    if key not in _MATERIALS:
        available = ", ".join(m.name for m in _MATERIALS.values())
        raise KeyError(
            f"Material '{name}' not found. Available materials: {available}"
        )
    return _MATERIALS[key]


def list_materials() -> list:
    """Return a list of all Material entries in the database."""
    return list(_MATERIALS.values())


def add_material(material: Material) -> None:
    """Add or override a material entry at runtime."""
    _MATERIALS[material.name.strip().lower()] = material
