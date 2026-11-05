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

## Column Buckling

- Effective length: `Le = K * L`
  - `K = 1.0` pinned-pinned, `2.0` fixed-free, `0.699` fixed-pinned, `0.5` fixed-fixed (theoretical)
- Radius of gyration: `r = sqrt(I / A)`, using the weak-axis `I`
- Slenderness ratio: `K * L / r`
- Transition slenderness: `(KL/r)_t = sqrt(2 * pi^2 * E / Sy)`
- Long columns (`KL/r >= (KL/r)_t`), Euler: `P_cr = pi^2 * E * I / (K * L)^2`
- Intermediate columns (`KL/r < (KL/r)_t`), J.B. Johnson: `sigma_cr = Sy - (Sy * (KL/r) / (2 * pi))^2 / E`, `P_cr = sigma_cr * A`
- The two curves meet tangentially at `(KL/r)_t`, where `sigma_cr = Sy / 2`

## Fatigue

- Alternating and mean stress: `sigma_a = |sigma_max - sigma_min| / 2`, `sigma_m = (sigma_max + sigma_min) / 2`
- Uncorrected endurance limit (steel): `Se' = 0.5 * Sut` for `Sut <= 1400 MPa`, otherwise `Se' = 700 MPa`
- Corrected endurance limit (Marin): `Se = ka * kb * kc * Se'`
  - Surface: `ka = a * Sut^b`, `Sut` in MPa. `(a, b)` = ground `(1.58, -0.085)`, machined or cold-drawn `(4.51, -0.265)`, hot-rolled `(57.7, -0.718)`, as-forged `(272, -0.995)`
  - Size (round, bending or torsion): `kb = 1.24 * d^-0.107` for `2.79 <= d <= 51 mm`, `kb = 1.51 * d^-0.157` for `51 < d <= 254 mm`, `kb = 1` for axial
  - Load: `kc = 1` bending, `0.85` axial, `0.59` torsion
- Fatigue safety factor, load line through the origin (`sigma_m > 0`):
  - Goodman: `1/n = sigma_a/Se + sigma_m/Sut`
  - Soderberg: `1/n = sigma_a/Se + sigma_m/Sy`
  - Gerber: `n * sigma_a/Se + (n * sigma_m/Sut)^2 = 1`, so `n = 0.5 * (Sut/sigma_m)^2 * (sigma_a/Se) * (-1 + sqrt(1 + (2 * sigma_m * Se / (Sut * sigma_a))^2))`
  - For `sigma_m <= 0`: `n = Se / sigma_a`
- First-cycle yield: `n_y = Sy / (sigma_a + |sigma_m|)`
- Reference: Shigley's Mechanical Engineering Design, Ch. 6

## Notes on Assumptions

- Beam formulas assume linear-elastic material behavior, small deflections, and a beam that is long relative to its cross section (Euler-Bernoulli theory, not Timoshenko).
- Column buckling assumes a straight, concentrically loaded, prismatic column. Real columns have initial crookedness and load eccentricity, so use a generous factor of safety, and prefer the recommended design K values (AISC: 2.1 for fixed-free, 0.80 for fixed-pinned, 0.65 for fixed-fixed) over the theoretical ones.
- Material property values in `materials_database.py` are typical handbook figures. For a real design, confirm against a certified material data sheet or mill certificate.
- The stress-strain curve in `plotting.py` is a simplified elastic-perfectly-plastic model for visualization. It does not model strain hardening, necking, or a true tensile test curve.
