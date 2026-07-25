"""
thermodynamics.py

Thermal expansion, thermal stress, ideal gas law, and basic
conduction/convection heat transfer calculations commonly needed for
mechanical design (fits, clearances, thermal loading on constrained
parts, simple heat transfer estimates).
"""

import math


# ---------------------------------------------------------------------
# Thermal expansion
# ---------------------------------------------------------------------

def linear_thermal_expansion(original_length: float, expansion_coeff: float,
                              delta_t: float) -> float:
    """
    Change in length due to a temperature change: dL = alpha * L0 * dT

    original_length: m
    expansion_coeff: linear thermal expansion coefficient (1/K)
    delta_t: temperature change (K or C, same magnitude either way)
    """
    return expansion_coeff * original_length * delta_t


def area_thermal_expansion(original_area: float, expansion_coeff: float,
                            delta_t: float) -> float:
    """
    Change in area due to a temperature change: dA = 2*alpha * A0 * dT
    (area expansion coefficient is approximately 2x the linear one)
    """
    return 2 * expansion_coeff * original_area * delta_t


def volumetric_thermal_expansion(original_volume: float, expansion_coeff: float,
                                  delta_t: float) -> float:
    """
    Change in volume due to a temperature change: dV = 3*alpha * V0 * dT
    (volumetric expansion coefficient is approximately 3x the linear one)
    """
    return 3 * expansion_coeff * original_volume * delta_t


def thermal_stress(expansion_coeff: float, elastic_modulus: float, delta_t: float) -> float:
    """
    Stress induced in a fully constrained member (both ends fixed, so
    it cannot expand or contract freely) due to a temperature change:
    sigma = E * alpha * dT

    Positive delta_t (heating a constrained member) gives a positive
    (compressive, by convention here) stress magnitude.
    """
    return elastic_modulus * expansion_coeff * delta_t


# ---------------------------------------------------------------------
# Ideal gas law: P*V = n*R*T
# ---------------------------------------------------------------------

R_UNIVERSAL = 8.314462618  # J / (mol*K)


def ideal_gas_pressure(volume: float, moles: float, temperature_k: float) -> float:
    """Solve for pressure (Pa) given volume (m^3), moles (mol), T (K)."""
    return moles * R_UNIVERSAL * temperature_k / volume


def ideal_gas_volume(pressure: float, moles: float, temperature_k: float) -> float:
    """Solve for volume (m^3) given pressure (Pa), moles (mol), T (K)."""
    return moles * R_UNIVERSAL * temperature_k / pressure


def ideal_gas_temperature(pressure: float, volume: float, moles: float) -> float:
    """Solve for temperature (K) given pressure (Pa), volume (m^3), moles (mol)."""
    return pressure * volume / (moles * R_UNIVERSAL)


def ideal_gas_moles(pressure: float, volume: float, temperature_k: float) -> float:
    """Solve for moles given pressure (Pa), volume (m^3), T (K)."""
    return pressure * volume / (R_UNIVERSAL * temperature_k)


# ---------------------------------------------------------------------
# Heat transfer (steady state, simple 1D cases)
# ---------------------------------------------------------------------

def conduction_heat_transfer(thermal_conductivity: float, area: float,
                              delta_t: float, thickness: float) -> float:
    """
    Steady-state 1D conduction (Fourier's law):
    Q = k * A * dT / L

    thermal_conductivity: W/(m*K)
    area: cross sectional area normal to heat flow (m^2)
    delta_t: temperature difference across the thickness (K)
    thickness: material thickness in the direction of heat flow (m)
    Returns heat transfer rate Q in watts.
    """
    return thermal_conductivity * area * delta_t / thickness


def convection_heat_transfer(convection_coeff: float, area: float, delta_t: float) -> float:
    """
    Newton's law of cooling: Q = h * A * dT

    convection_coeff: convective heat transfer coefficient (W/(m^2*K))
    area: surface area exposed to the fluid (m^2)
    delta_t: temperature difference between surface and fluid (K)
    Returns heat transfer rate Q in watts.
    """
    return convection_coeff * area * delta_t


def thermal_resistance_conduction(thickness: float, thermal_conductivity: float, area: float) -> float:
    """Conduction thermal resistance, R = L / (k * A), in K/W."""
    return thickness / (thermal_conductivity * area)


def thermal_resistance_convection(convection_coeff: float, area: float) -> float:
    """Convection thermal resistance, R = 1 / (h * A), in K/W."""
    return 1.0 / (convection_coeff * area)
