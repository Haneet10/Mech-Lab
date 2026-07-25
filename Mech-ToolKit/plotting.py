"""
plotting.py

Matplotlib-based visualizations: beam deflection curves, shear/moment
diagrams, material stress-strain curves, and a simple gear train
schematic.

Every function returns the matplotlib Figure object (it does not
call plt.show() itself), so the caller decides whether to display it,
save it to a file, or embed it in a GUI.
"""

import matplotlib
matplotlib.use("Agg")  # safe default for headless / non-interactive use
import matplotlib.pyplot as plt
import numpy as np

from mech_toolkit import beam_calculator
from mech_toolkit.materials_database import get_material, Material


def plot_cantilever_deflection(length: float, load: float, elastic_modulus: float,
                                moment_of_inertia: float, save_path: str = None):
    """
    Plots the deflection shape of a cantilever beam with a point load
    at the free end.
    """
    xs, ys = beam_calculator.cantilever_point_load_curve(
        length, load, elastic_modulus, moment_of_inertia, num_points=200
    )
    ys_mm = [y * 1000 for y in ys]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(xs, ys_mm, linewidth=2, color="#1f6feb")
    ax.fill_between(xs, ys_mm, alpha=0.15, color="#1f6feb")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_xlabel("Position along beam (m)")
    ax.set_ylabel("Deflection (mm)")
    ax.set_title("Cantilever Beam Deflection (Point Load at Free End)")
    ax.invert_yaxis()  # downward deflection reads as "down" on the plot
    ax.grid(True, alpha=0.3)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_simply_supported_deflection(length: float, load: float, elastic_modulus: float,
                                      moment_of_inertia: float, save_path: str = None):
    """
    Plots the deflection shape of a simply supported beam with a
    point load at midspan.
    """
    xs, ys = beam_calculator.simply_supported_center_load_curve(
        length, load, elastic_modulus, moment_of_inertia, num_points=200
    )
    ys_mm = [y * 1000 for y in ys]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(xs, ys_mm, linewidth=2, color="#1f6feb")
    ax.fill_between(xs, ys_mm, alpha=0.15, color="#1f6feb")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.plot([0, length], [0, 0], "^", color="black", markersize=12)
    ax.set_xlabel("Position along beam (m)")
    ax.set_ylabel("Deflection (mm)")
    ax.set_title("Simply Supported Beam Deflection (Center Point Load)")
    ax.invert_yaxis()
    ax.grid(True, alpha=0.3)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_shear_moment_diagram_simply_supported_center_load(length: float, load: float,
                                                             save_path: str = None):
    """
    Shear force and bending moment diagrams for a simply supported
    beam with a point load P at midspan.
    """
    xs = np.linspace(0, length, 200)
    reaction = load / 2.0

    shear = np.where(xs < length / 2, reaction, -reaction)
    moment = np.where(
        xs <= length / 2,
        reaction * xs,
        reaction * (length - xs),
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

    ax1.plot(xs, shear, color="#d9534f", linewidth=2)
    ax1.fill_between(xs, shear, alpha=0.15, color="#d9534f")
    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_ylabel("Shear Force (N)")
    ax1.set_title("Shear Force Diagram")
    ax1.grid(True, alpha=0.3)

    ax2.plot(xs, moment, color="#1f6feb", linewidth=2)
    ax2.fill_between(xs, moment, alpha=0.15, color="#1f6feb")
    ax2.axhline(0, color="black", linewidth=0.8)
    ax2.set_xlabel("Position along beam (m)")
    ax2.set_ylabel("Bending Moment (N*m)")
    ax2.set_title("Bending Moment Diagram")
    ax2.grid(True, alpha=0.3)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_stress_strain(material, strain_max: float = 0.02, save_path: str = None):
    """
    Simplified elastic-perfectly-plastic stress-strain curve for a
    material from the database (or a Material instance). This is a
    teaching approximation, not a true material test curve: strain
    hardening after yield is not modeled.
    """
    mat = material if isinstance(material, Material) else get_material(material)

    yield_strain = mat.yield_strength / mat.elastic_modulus
    strain_elastic = np.linspace(0, yield_strain, 50)
    stress_elastic = strain_elastic * mat.elastic_modulus

    strain_plastic = np.linspace(yield_strain, strain_max, 50)
    stress_plastic = np.full_like(strain_plastic, mat.yield_strength)

    strain = np.concatenate([strain_elastic, strain_plastic])
    stress = np.concatenate([stress_elastic, stress_plastic]) / 1e6  # MPa

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(strain, stress, linewidth=2, color="#1f6feb")
    ax.axvline(yield_strain, color="gray", linestyle="--", linewidth=1)
    ax.annotate(
        "Yield point",
        xy=(yield_strain, mat.yield_strength / 1e6),
        xytext=(yield_strain * 1.3, mat.yield_strength / 1e6 * 0.8),
        arrowprops=dict(arrowstyle="->", color="gray"),
    )
    ax.set_xlabel("Strain (mm/mm)")
    ax.set_ylabel("Stress (MPa)")
    ax.set_title(f"Simplified Stress-Strain Curve: {mat.name}")
    ax.grid(True, alpha=0.3)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig


def plot_gear_train(gear_train, save_path: str = None):
    """
    Simple schematic of a gear train as a row of circles sized
    proportionally to tooth count. Not to precise engineering scale,
    intended as a quick visual sanity check of stage sizing.
    """
    stages = gear_train.stages
    fig, ax = plt.subplots(figsize=(2.5 * (len(stages) + 1), 4))

    x_pos = 0.0
    max_radius = max(max(s.driver_teeth, s.driven_teeth) for s in stages)
    scale = 1.0 / max_radius

    colors = plt.cm.tab10.colors
    prev_driven_radius = None

    for i, stage in enumerate(stages):
        driver_r = stage.driver_teeth * scale
        driven_r = stage.driven_teeth * scale

        if prev_driven_radius is None:
            driver_x = x_pos + driver_r
        else:
            driver_x = x_pos + driver_r
        driver_circle = plt.Circle((driver_x, 0), driver_r, fill=False,
                                    edgecolor=colors[i % len(colors)], linewidth=2)
        ax.add_patch(driver_circle)
        ax.text(driver_x, 0, f"{stage.driver_teeth}T", ha="center", va="center", fontsize=9)

        driven_x = driver_x + driver_r + driven_r
        driven_circle = plt.Circle((driven_x, 0), driven_r, fill=False,
                                    edgecolor=colors[i % len(colors)], linewidth=2)
        ax.add_patch(driven_circle)
        ax.text(driven_x, 0, f"{stage.driven_teeth}T", ha="center", va="center", fontsize=9)

        x_pos = driven_x
        prev_driven_radius = driven_r

    ax.set_xlim(-0.5, x_pos + 1.0)
    ax.set_ylim(-1.2, 1.2)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"Gear Train Schematic (Overall Ratio {gear_train.overall_ratio:.2f}:1)")

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
