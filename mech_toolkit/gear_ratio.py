"""
gear_ratio.py

Gear ratio, speed, torque, and simple spur gear geometry
calculations, including multi-stage (compound) gear trains.

Convention: ratio is defined as driven_teeth / driver_teeth, i.e. a
ratio > 1 means the output turns slower than the input (a speed
reducer), matching common usage in torque/speed gearbox specs.
"""

from dataclasses import dataclass


def gear_ratio(driver_teeth: int, driven_teeth: int) -> float:
    """
    Ratio of a single gear pair. > 1 = speed reduction (torque
    increase), < 1 = speed increase (torque reduction).
    """
    if driver_teeth <= 0 or driven_teeth <= 0:
        raise ValueError("Tooth counts must be positive integers.")
    return driven_teeth / driver_teeth


def output_speed(input_speed_rpm: float, ratio: float) -> float:
    """Output speed (RPM) given input speed and overall gear ratio."""
    return input_speed_rpm / ratio


def output_torque(input_torque: float, ratio: float, efficiency: float = 1.0) -> float:
    """
    Output torque given input torque, overall gear ratio, and
    mechanical efficiency (0 to 1, default 1.0 = ideal/lossless).
    """
    if not (0 < efficiency <= 1.0):
        raise ValueError("Efficiency must be between 0 (exclusive) and 1 (inclusive).")
    return input_torque * ratio * efficiency


def center_distance(module: float, teeth_1: int, teeth_2: int) -> float:
    """
    Center distance between two meshing spur gears.
    module: gear module (m), in meters if teeth-per-meter convention,
        but commonly specified in mm (just be consistent with output units)
    """
    return module * (teeth_1 + teeth_2) / 2.0


def pitch_diameter(module: float, teeth: int) -> float:
    """Pitch diameter of a spur gear: d = m * N"""
    return module * teeth


@dataclass
class GearStage:
    driver_teeth: int
    driven_teeth: int
    name: str = ""

    @property
    def ratio(self) -> float:
        return gear_ratio(self.driver_teeth, self.driven_teeth)


class GearTrain:
    """
    Models a compound (multi-stage) gear train as a sequence of
    GearStage objects, where the driven gear of one stage is assumed
    to be mechanically coupled (same shaft) to the driver gear of the
    next stage.
    """

    def __init__(self, stages: list):
        if not stages:
            raise ValueError("A gear train needs at least one stage.")
        self.stages = stages

    @property
    def overall_ratio(self) -> float:
        ratio = 1.0
        for stage in self.stages:
            ratio *= stage.ratio
        return ratio

    def output_speed(self, input_speed_rpm: float) -> float:
        return output_speed(input_speed_rpm, self.overall_ratio)

    def output_torque(self, input_torque: float, efficiency_per_stage: float = 1.0) -> float:
        overall_efficiency = efficiency_per_stage ** len(self.stages)
        return output_torque(input_torque, self.overall_ratio, overall_efficiency)

    def report(self, input_speed_rpm: float = None, input_torque: float = None,
               efficiency_per_stage: float = 1.0) -> str:
        lines = ["=" * 40, "Gear Train Analysis", "=" * 40, ""]
        for i, stage in enumerate(self.stages, start=1):
            label = f" ({stage.name})" if stage.name else ""
            lines.append(
                f"Stage {i}{label}: {stage.driver_teeth}T -> {stage.driven_teeth}T"
                f"  (ratio {stage.ratio:.3f})"
            )
        lines.append("")
        lines.append(f"Overall Ratio: {self.overall_ratio:.3f} : 1")

        if input_speed_rpm is not None:
            lines.append(f"Output Speed: {self.output_speed(input_speed_rpm):.1f} RPM")
        if input_torque is not None:
            out_t = self.output_torque(input_torque, efficiency_per_stage)
            lines.append(f"Output Torque: {out_t:.2f} N*m")
        lines.append("=" * 40)
        return "\n".join(lines)
