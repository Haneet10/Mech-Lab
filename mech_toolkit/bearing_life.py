"""
bearing_life.py

L10 basic rating life for rolling element bearings, per the standard
ISO 281 approach (the same method used in most bearing manufacturer
catalogs, e.g. SKF, Timken).

L10 is the life that 90% of a population of identical bearings is
expected to reach or exceed, under a given constant load, before the
first sign of fatigue.
"""

from dataclasses import dataclass


@dataclass
class BearingLifeResult:
    l10_revolutions: float   # millions of revolutions
    l10_hours: float = None  # hours, only if speed was provided


def bearing_l10_life(dynamic_load_rating: float, equivalent_load: float,
                      bearing_type: str = "ball", speed_rpm: float = None) -> BearingLifeResult:
    """
    L10 life in millions of revolutions: L10 = (C / P)^p

    dynamic_load_rating: C, the bearing's basic dynamic load rating (N),
        this comes from the bearing manufacturer's catalog
    equivalent_load: P, the equivalent dynamic bearing load (N)
    bearing_type: 'ball' (p=3) or 'roller' (p=10/3)
    speed_rpm: optional, if given, also computes life in hours

    Reference: ISO 281, basic rating life.
    """
    bearing_type = bearing_type.lower().strip()
    if bearing_type == "ball":
        p = 3.0
    elif bearing_type == "roller":
        p = 10.0 / 3.0
    else:
        raise ValueError("bearing_type must be 'ball' or 'roller'")

    if equivalent_load <= 0:
        raise ValueError("equivalent_load must be positive.")

    l10_millions_rev = (dynamic_load_rating / equivalent_load) ** p

    l10_hours = None
    if speed_rpm is not None and speed_rpm > 0:
        l10_hours = (l10_millions_rev * 1e6) / (speed_rpm * 60.0)

    return BearingLifeResult(l10_revolutions=l10_millions_rev, l10_hours=l10_hours)


def required_dynamic_load_rating(equivalent_load: float, target_l10_millions_rev: float,
                                  bearing_type: str = "ball") -> float:
    """
    Rearranges the L10 equation to solve for the dynamic load rating
    C a bearing needs in order to hit a target L10 life.
    """
    bearing_type = bearing_type.lower().strip()
    if bearing_type == "ball":
        p = 3.0
    elif bearing_type == "roller":
        p = 10.0 / 3.0
    else:
        raise ValueError("bearing_type must be 'ball' or 'roller'")

    return equivalent_load * (target_l10_millions_rev ** (1.0 / p))
