"""
example_thermal_expansion.py

Thermal expansion demo: how much does a 3 m aluminum guide rail grow
when it heats up from a cold shop (5 C) to full sun exposure (45 C)?
Also checks what stress would develop if the same rail were fully
constrained instead of free to expand.
"""

from mech_toolkit import thermodynamics, materials_database, unit_converter

RAIL_LENGTH_M = 3.0
COLD_TEMP_C = 5.0
HOT_TEMP_C = 45.0
MATERIAL = "Aluminum 6061-T6"


def main():
    mat = materials_database.get_material(MATERIAL)
    delta_t = HOT_TEMP_C - COLD_TEMP_C

    growth = thermodynamics.linear_thermal_expansion(
        RAIL_LENGTH_M, mat.thermal_expansion, delta_t
    )

    constrained_stress = thermodynamics.thermal_stress(
        mat.thermal_expansion, mat.elastic_modulus, delta_t
    )
    constrained_stress_mpa = unit_converter.convert_stress(constrained_stress, "Pa", "MPa")
    fos_if_constrained = mat.yield_strength / constrained_stress

    print("=" * 40)
    print("Thermal Expansion Analysis")
    print("=" * 40)
    print(f"\nMaterial:         {mat.name}")
    print(f"Rail length:      {RAIL_LENGTH_M} m")
    print(f"Temperature rise: {delta_t:.1f} C ({COLD_TEMP_C} C -> {HOT_TEMP_C} C)")
    print(f"\nFree expansion (unconstrained):")
    print(f"  Growth: {growth * 1000:.2f} mm")
    print(f"\nIf fully constrained instead:")
    print(f"  Induced stress: {constrained_stress_mpa:.1f} MPa")
    print(f"  Factor of safety vs yield: {fos_if_constrained:.2f}")
    print("=" * 40)


if __name__ == "__main__":
    main()
