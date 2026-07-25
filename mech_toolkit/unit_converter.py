"""
unit_converter.py

Simple, explicit unit conversions for the quantities that show up
constantly in mechanical engineering coursework: length, force,
stress/pressure, torque, temperature, and power.

Design choice: every category converts through one SI base unit
(meters, newtons, pascals, newton-meters, kelvin, watts), so adding
a new unit only means adding one conversion factor, not one factor
per unit pair.
"""

# Each dict maps unit name -> multiplier to reach the SI base unit.
_LENGTH_TO_M = {
    "m": 1.0,
    "mm": 1e-3,
    "cm": 1e-2,
    "km": 1e3,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
}

_FORCE_TO_N = {
    "N": 1.0,
    "kN": 1e3,
    "lbf": 4.4482216153,
    "kgf": 9.80665,
}

_STRESS_TO_PA = {
    "Pa": 1.0,
    "kPa": 1e3,
    "MPa": 1e6,
    "GPa": 1e9,
    "psi": 6894.757293168,
    "ksi": 6894757.293168,
}

_TORQUE_TO_NM = {
    "N*m": 1.0,
    "kN*m": 1e3,
    "lbf*ft": 1.3558179483,
    "lbf*in": 0.1129848290,
}

_POWER_TO_W = {
    "W": 1.0,
    "kW": 1e3,
    "hp": 745.6998716,
}


def _convert_through_base(value: float, from_unit: str, to_unit: str, table: dict, category: str) -> float:
    if from_unit not in table:
        raise ValueError(f"Unknown {category} unit '{from_unit}'. Options: {list(table.keys())}")
    if to_unit not in table:
        raise ValueError(f"Unknown {category} unit '{to_unit}'. Options: {list(table.keys())}")
    base_value = value * table[from_unit]
    return base_value / table[to_unit]


def convert_length(value: float, from_unit: str, to_unit: str) -> float:
    return _convert_through_base(value, from_unit, to_unit, _LENGTH_TO_M, "length")


def convert_force(value: float, from_unit: str, to_unit: str) -> float:
    return _convert_through_base(value, from_unit, to_unit, _FORCE_TO_N, "force")


def convert_stress(value: float, from_unit: str, to_unit: str) -> float:
    return _convert_through_base(value, from_unit, to_unit, _STRESS_TO_PA, "stress")


def convert_torque(value: float, from_unit: str, to_unit: str) -> float:
    return _convert_through_base(value, from_unit, to_unit, _TORQUE_TO_NM, "torque")


def convert_power(value: float, from_unit: str, to_unit: str) -> float:
    return _convert_through_base(value, from_unit, to_unit, _POWER_TO_W, "power")


def convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    """
    Temperature does not scale through a single multiplier (there are
    offsets), so it gets its own conversion path via Celsius.
    """
    from_unit = from_unit.upper()
    to_unit = to_unit.upper()

    # Convert input to Celsius first.
    if from_unit == "C":
        celsius = value
    elif from_unit == "F":
        celsius = (value - 32) * 5.0 / 9.0
    elif from_unit == "K":
        celsius = value - 273.15
    else:
        raise ValueError(f"Unknown temperature unit '{from_unit}'. Options: C, F, K")

    # Convert Celsius to the target unit.
    if to_unit == "C":
        return celsius
    elif to_unit == "F":
        return celsius * 9.0 / 5.0 + 32
    elif to_unit == "K":
        return celsius + 273.15
    else:
        raise ValueError(f"Unknown temperature unit '{to_unit}'. Options: C, F, K")
