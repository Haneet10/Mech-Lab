"""
example_beam_analysis.py

Cantilever beam analysis demo: a 2 m long steel bar, fixed at one
end, with a 400 N load at the free end. Prints a formatted report,
then generates a deflection plot.
"""

import os
from mech_toolkit import beam_calculator, plotting

# 25mm x 60mm rectangular steel bar
WIDTH = 0.025   # m
HEIGHT = 0.060  # m
LENGTH = 2.0    # m
LOAD = 400.0    # N
MATERIAL = "Structural Steel A36"


def main():
    I, c = beam_calculator.rectangular_section(WIDTH, HEIGHT)

    result = beam_calculator.cantilever_point_load(
        length=LENGTH, load=LOAD, moment_of_inertia=I,
        section_modulus_c=c, material=MATERIAL,
    )

    print(result.report())

    output_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, "cantilever_deflection.png")

    plotting.plot_cantilever_deflection(
        length=LENGTH, load=LOAD, elastic_modulus=result.elastic_modulus,
        moment_of_inertia=I, save_path=save_path,
    )
    print(f"\nDeflection plot saved to {save_path}")


if __name__ == "__main__":
    main()
