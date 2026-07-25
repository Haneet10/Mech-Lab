"""
Mechanical Engineering Toolkit
===============================

A Python package for common mechanical engineering hand calculations:
beam deflection and stress, torsion and shear, gear trains, thermal
expansion and heat transfer, bearing life, unit conversion, and a
material property database.

Quick start:

    from mech_toolkit import beam_calculator

    I, c = beam_calculator.circular_section(diameter=0.03)
    result = beam_calculator.cantilever_point_load(
        length=2.0, load=400, moment_of_inertia=I, section_modulus_c=c,
        material="Structural Steel A36",
    )
    print(result.report())
"""

__version__ = "1.0.0"

from mech_toolkit import (
    beam_calculator,
    stress_analysis,
    gear_ratio,
    thermodynamics,
    unit_converter,
    materials_database,
    bearing_life,
    plotting,
)

__all__ = [
    "beam_calculator",
    "stress_analysis",
    "gear_ratio",
    "thermodynamics",
    "unit_converter",
    "materials_database",
    "bearing_life",
    "plotting",
]
