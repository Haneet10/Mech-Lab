"""
gui.py

A simple Tkinter desktop GUI wrapping the toolkit's core
calculations: beam analysis, gear train analysis, and unit
conversion. Tkinter ships with the Python standard library on
Windows and macOS installers, so this has no extra dependencies
beyond the toolkit itself.

Run it directly with:
    python -m mech_toolkit.gui
"""

import tkinter as tk
from tkinter import ttk, messagebox

from mech_toolkit import beam_calculator, gear_ratio, unit_converter, materials_database


class MechToolkitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mechanical Engineering Toolkit")
        self.geometry("640x520")
        self.resizable(False, False)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.beam_tab = BeamTab(notebook)
        self.gear_tab = GearTab(notebook)
        self.convert_tab = ConvertTab(notebook)

        notebook.add(self.beam_tab, text="Beam Calculator")
        notebook.add(self.gear_tab, text="Gear Train")
        notebook.add(self.convert_tab, text="Unit Converter")


class BeamTab(ttk.Frame):
    """
    Cantilever beam analysis: point load at the free end, rectangular
    cross section.
    """

    def __init__(self, parent):
        super().__init__(parent, padding=15)

        materials = [m.name for m in materials_database.list_materials()]

        self.length_var = tk.StringVar(value="2.0")
        self.load_var = tk.StringVar(value="400")
        self.width_var = tk.StringVar(value="25")
        self.height_var = tk.StringVar(value="60")
        self.material_var = tk.StringVar(value="Structural Steel A36")

        row = 0
        ttk.Label(self, text="Cantilever Beam, Point Load at Free End",
                  font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1

        self._add_field(row, "Length (m):", self.length_var); row += 1
        self._add_field(row, "Load (N):", self.load_var); row += 1
        self._add_field(row, "Cross-section width (mm):", self.width_var); row += 1
        self._add_field(row, "Cross-section height (mm):", self.height_var); row += 1

        ttk.Label(self, text="Material:").grid(row=row, column=0, sticky="w", pady=4)
        material_menu = ttk.Combobox(self, textvariable=self.material_var, values=materials, state="readonly")
        material_menu.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ttk.Button(self, text="Calculate", command=self.calculate).grid(
            row=row, column=0, columnspan=2, pady=10)
        row += 1

        self.output = tk.Text(self, height=16, width=60, font=("Courier", 10))
        self.output.grid(row=row, column=0, columnspan=2, pady=5)

        self.columnconfigure(1, weight=1)

    def _add_field(self, row, label, var):
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(self, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)

    def calculate(self):
        try:
            length = float(self.length_var.get())
            load = float(self.load_var.get())
            width = float(self.width_var.get()) / 1000.0   # mm -> m
            height = float(self.height_var.get()) / 1000.0  # mm -> m
            material = self.material_var.get()

            if length <= 0 or load <= 0 or width <= 0 or height <= 0:
                raise ValueError("All dimensions and loads must be positive numbers.")

            I, c = beam_calculator.rectangular_section(width, height)
            result = beam_calculator.cantilever_point_load(
                length=length, load=load, moment_of_inertia=I,
                section_modulus_c=c, material=material,
            )

            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, result.report())

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Something went wrong: {e}")


class GearTab(ttk.Frame):
    """Single-stage gear ratio, speed, and torque calculator."""

    def __init__(self, parent):
        super().__init__(parent, padding=15)

        self.driver_var = tk.StringVar(value="20")
        self.driven_var = tk.StringVar(value="60")
        self.speed_var = tk.StringVar(value="1750")
        self.torque_var = tk.StringVar(value="5.0")
        self.efficiency_var = tk.StringVar(value="0.98")

        row = 0
        ttk.Label(self, text="Single-Stage Gear Calculator",
                  font=("TkDefaultFont", 11, "bold")).grid(row=row, column=0, columnspan=2, pady=(0, 10))
        row += 1

        self._add_field(row, "Driver gear teeth:", self.driver_var); row += 1
        self._add_field(row, "Driven gear teeth:", self.driven_var); row += 1
        self._add_field(row, "Input speed (RPM):", self.speed_var); row += 1
        self._add_field(row, "Input torque (N*m):", self.torque_var); row += 1
        self._add_field(row, "Efficiency (0-1):", self.efficiency_var); row += 1

        ttk.Button(self, text="Calculate", command=self.calculate).grid(
            row=row, column=0, columnspan=2, pady=10)
        row += 1

        self.output = tk.Text(self, height=12, width=60, font=("Courier", 10))
        self.output.grid(row=row, column=0, columnspan=2, pady=5)

        self.columnconfigure(1, weight=1)

    def _add_field(self, row, label, var):
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(self, textvariable=var).grid(row=row, column=1, sticky="ew", pady=4)

    def calculate(self):
        try:
            driver = int(self.driver_var.get())
            driven = int(self.driven_var.get())
            speed = float(self.speed_var.get())
            torque = float(self.torque_var.get())
            efficiency = float(self.efficiency_var.get())

            ratio = gear_ratio.gear_ratio(driver, driven)
            out_speed = gear_ratio.output_speed(speed, ratio)
            out_torque = gear_ratio.output_torque(torque, ratio, efficiency)

            lines = [
                "=" * 40,
                "Gear Calculation Results",
                "=" * 40,
                "",
                f"Gear Ratio:      {ratio:.3f} : 1",
                f"Output Speed:    {out_speed:.1f} RPM",
                f"Output Torque:   {out_torque:.2f} N*m",
                "=" * 40,
            ]

            self.output.delete("1.0", tk.END)
            self.output.insert(tk.END, "\n".join(lines))

        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Something went wrong: {e}")


class ConvertTab(ttk.Frame):
    """Quick unit conversion for stress, force, length, and temperature."""

    CATEGORIES = {
        "Stress/Pressure": (unit_converter.convert_stress, ["Pa", "kPa", "MPa", "GPa", "psi", "ksi"]),
        "Force": (unit_converter.convert_force, ["N", "kN", "lbf", "kgf"]),
        "Length": (unit_converter.convert_length, ["m", "mm", "cm", "km", "in", "ft", "yd"]),
        "Torque": (unit_converter.convert_torque, ["N*m", "kN*m", "lbf*ft", "lbf*in"]),
        "Temperature": (unit_converter.convert_temperature, ["C", "F", "K"]),
    }

    def __init__(self, parent):
        super().__init__(parent, padding=15)

        self.category_var = tk.StringVar(value="Stress/Pressure")
        self.value_var = tk.StringVar(value="100")
        self.from_var = tk.StringVar(value="psi")
        self.to_var = tk.StringVar(value="MPa")
        self.result_var = tk.StringVar(value="")

        ttk.Label(self, text="Unit Converter", font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=2, pady=(0, 10))

        ttk.Label(self, text="Category:").grid(row=1, column=0, sticky="w", pady=4)
        category_menu = ttk.Combobox(self, textvariable=self.category_var,
                                      values=list(self.CATEGORIES.keys()), state="readonly")
        category_menu.grid(row=1, column=1, sticky="ew", pady=4)
        category_menu.bind("<<ComboboxSelected>>", self._on_category_change)

        ttk.Label(self, text="Value:").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(self, textvariable=self.value_var).grid(row=2, column=1, sticky="ew", pady=4)

        ttk.Label(self, text="From unit:").grid(row=3, column=0, sticky="w", pady=4)
        self.from_menu = ttk.Combobox(self, textvariable=self.from_var, state="readonly")
        self.from_menu.grid(row=3, column=1, sticky="ew", pady=4)

        ttk.Label(self, text="To unit:").grid(row=4, column=0, sticky="w", pady=4)
        self.to_menu = ttk.Combobox(self, textvariable=self.to_var, state="readonly")
        self.to_menu.grid(row=4, column=1, sticky="ew", pady=4)

        ttk.Button(self, text="Convert", command=self.calculate).grid(
            row=5, column=0, columnspan=2, pady=10)

        ttk.Label(self, textvariable=self.result_var, font=("TkDefaultFont", 12, "bold")).grid(
            row=6, column=0, columnspan=2, pady=10)

        self.columnconfigure(1, weight=1)
        self._on_category_change()

    def _on_category_change(self, event=None):
        _, units = self.CATEGORIES[self.category_var.get()]
        self.from_menu["values"] = units
        self.to_menu["values"] = units
        if self.from_var.get() not in units:
            self.from_var.set(units[0])
        if self.to_var.get() not in units:
            self.to_var.set(units[-1])

    def calculate(self):
        try:
            value = float(self.value_var.get())
            convert_fn, _ = self.CATEGORIES[self.category_var.get()]
            result = convert_fn(value, self.from_var.get(), self.to_var.get())
            self.result_var.set(f"{value} {self.from_var.get()} = {result:.4g} {self.to_var.get()}")
        except ValueError as e:
            messagebox.showerror("Input Error", str(e))
        except Exception as e:
            messagebox.showerror("Error", f"Something went wrong: {e}")


def main():
    app = MechToolkitApp()
    app.mainloop()


if __name__ == "__main__":
    main()
