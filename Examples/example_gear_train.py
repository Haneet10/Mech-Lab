"""
example_gear_train.py

Two-stage gear reducer demo: an electric motor at 1750 RPM driving a
compound gear train, stepping speed down and torque up before it
reaches the output shaft.
"""

import os
from mech_toolkit.gear_ratio import GearStage, GearTrain
from mech_toolkit import plotting

MOTOR_SPEED_RPM = 1750
MOTOR_TORQUE_NM = 4.5
STAGE_EFFICIENCY = 0.97  # typical for a well-lubricated spur gear mesh


def main():
    train = GearTrain([
        GearStage(driver_teeth=18, driven_teeth=54, name="Reduction Stage 1"),
        GearStage(driver_teeth=16, driven_teeth=48, name="Reduction Stage 2"),
    ])

    print(train.report(
        input_speed_rpm=MOTOR_SPEED_RPM,
        input_torque=MOTOR_TORQUE_NM,
        efficiency_per_stage=STAGE_EFFICIENCY,
    ))

    output_dir = os.path.join(os.path.dirname(__file__), "..", "assets")
    os.makedirs(output_dir, exist_ok=True)
    save_path = os.path.join(output_dir, "gear_train_schematic.png")

    plotting.plot_gear_train(train, save_path=save_path)
    print(f"\nGear train schematic saved to {save_path}")


if __name__ == "__main__":
    main()
