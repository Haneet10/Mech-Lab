# Formula Reference

This is the theory behind every calculation in the toolkit, so you (or anyone reviewing the code) can check it against a textbook. Notation follows standard Mechanics of Materials texts (Hibbeler, Beer & Johnston).

## Beam Calculator

**Cantilever beam, point load P at free end**
- Max moment (at fixed end): `M = P * L`
- Max deflection (at free end): `delta = P * L^3 / (3 * E * I)`

**Cantilever beam, uniformly distributed load w over length L**
- Max moment (at fixed end): `M = w * L^2 / 2`
- Max deflection (at free end): `delta = w * L^4 / (8 * E * I)`

**Simply supported beam, point load P at midspan**
- Max moment (at midspan): `M = P * L / 4`
- Max deflection (at midspan): `delta = P * L^3 / (48 * E * I)`

**Simply supported beam, uniformly distributed load w**
- Max moment (at midspan): `M = w * L^2 / 8`
- Max deflection (at midspan): `delta = 5 * w * L^4 / (384 * E * I)`

**Bending stress**
- `sigma = M * c / I`, where `c` is the distance from the neutral axis to the outer fiber.

**Section properties**
- Rectangle: `I = b * h^3 / 12`, `c = h / 2`
- Solid circle: `I = pi * d^4 / 64`, `c = d / 2`
- Hollow circle: `I = pi * (d_o^4 - d_i^4) / 64`, `c = d_o / 2`

## Stress Analysis

**Transverse shear**
- `tau = V * Q / (I * t)`
- Solid rectangle, max at neutral axis: `tau_max = 1.5 * V / A`
- Solid circle, max at neutral axis: `tau_max = (4/3) * V / A`

**Torsion (circular shaft)**
- `tau = T * r / J`
- Solid shaft: `J = pi * d^4 / 32`
- Hollow shaft: `J = pi * (d_o^4 - d_i^4) / 32`
- Angle of twist: `theta = T * L / (G * J)`

**Principal stresses (2D / plane stress)**
- `sigma_avg = (sigma_x + sigma_y) / 2`
- `R = sqrt( ((sigma_x - sigma_y)/2)^2 + tau_xy^2 )`
- `sigma_1 = sigma_avg + R`, `sigma_2 = sigma_avg - R`
- `tau_max = R`

**Von Mises equivalent stress**
- 2D: `sigma_vm = sqrt(sigma_x^2 - sigma_x*sigma_y + sigma_y^2 + 3*tau_xy^2)`
- 3D (principal stresses): `sigma_vm = sqrt( 0.5 * [(s1-s2)^2 + (s2-s3)^2 + (s3-s1)^2] )`

**Factor of safety**
- `FOS = yield_strength / applied_stress`

## Gear Ratio

- Single stage ratio: `ratio = driven_teeth / driver_teeth`
- Output speed: `N_out = N_in / ratio`
- Output torque: `T_out = T_in * ratio * efficiency`
- Compound train overall ratio: product of each stage's ratio
- Center distance: `C = m * (N1 + N2) / 2`, where `m` is the gear module

## Thermodynamics

- Linear thermal expansion: `dL = alpha * L0 * dT`
- Area expansion: `dA = 2 * alpha * A0 * dT`
- Volumetric expansion: `dV = 3 * alpha * V0 * dT`
- Thermal stress (fully constrained member): `sigma = E * alpha * dT`
- Ideal gas law: `P * V = n * R * T`, with `R = 8.314462618 J/(mol*K)`
- Conduction (Fourier's law): `Q = k * A * dT / L`
- Convection (Newton's law of cooling): `Q = h * A * dT`

## Bearing Life (ISO 281)

- `L10 = (C / P)^p`, in millions of revolutions
  - `p = 3` for ball bearings
  - `p = 10/3` for roller bearings
- `C` = dynamic load rating (from manufacturer catalog)
- `P` = equivalent dynamic load
- Life in hours: `L10_hours = (L10 * 10^6) / (N * 60)`, where `N` is speed in RPM

## Notes on Assumptions

- Beam formulas assume linear-elastic material behavior, small deflections, and a beam that is long relative to its cross section (Euler-Bernoulli theory, not Timoshenko).
- Material property values in `materials_database.py` are typical handbook figures. For a real design, confirm against a certified material data sheet or mill certificate.
- The stress-strain curve in `plotting.py` is a simplified elastic-perfectly-plastic model for visualization. It does not model strain hardening, necking, or a true tensile test curve.
