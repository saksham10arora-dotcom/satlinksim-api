# Physics Models — Detailed Explanation

The simulator computes a full link budget at each time step. A link budget is an accounting of every gain and every loss that a signal experiences from transmitter power amplifier to receiver decoder. The SNR at the receiver is:

```
SNR = EIRP − FSPL − L_gas − L_rain − L_scint + G_rx − N
```

where every term is in decibels (dB) or dBW.

## 1. Dynamic Orbital Geometry (SGP4)
For any station linked to a `norad_id`, the simulator fetches the latest TLE (Two-Line Element) and propagates the orbit to the current simulation epoch.
- **ECEF State**: Returns (x, y, z) position and velocity in Earth-Centered, Earth-Fixed coordinates.
- **Topocentric Transformation**: Converts ECEF vectors into **ENU (East-North-Up)** coordinates relative to the ground station's WGS84 geodetic position.
- **Dynamic Geometry**: Recomputes Elevation (El) and Azimuth (Az) at every step.

## 2. Free-Space Path Loss
FSPL(dB) = 92.45 + 20·log₁₀(f_GHz) + 20·log₁₀(d_km).
Accuracy within $10^{-4}$ dB.

## 3. Thermal Noise Power
N(dBW) = −228.6 + 10·log₁₀(T_sys) + 10·log₁₀(B).

## 4. Rain Statistics — ITU-R P.837-7
The probability that rain of a given intensity is occurring at a location on Earth is highly non-uniform. We use R₀.₀₁, R₀.₁, R₁ exceedance probabilities and $P_{rain}$ fractions to fit lognormal distributions.

## 5. Rain Attenuation Coefficients — ITU-R P.838-3
Specific attenuation $\gamma_R = k \cdot R^\alpha$ [dB/km].
Coefficients are implemented via log-linear interpolation of ITU-R P.838-3 tables.

## 6. Rain Height — ITU-R P.839-4
Latitude-dependent mean rain height formula based on the $0^\circ C$ isotherm.

## 7. Effective Slant Path — ITU-R P.618-13
Calculates the slant distance through the rain column, including path reduction factors for low elevation angles.

## 8. Rain Attenuation on the Path
$A_{rain} = k \cdot R^\alpha \cdot L_{eff}$ [dB].

## 9. Gaseous Absorption — ITU-R P.676-12
Simplified model for oxygen ($O_2$) and water vapour ($H_2O$) absorption.

## 10. Tropospheric Scintillation — ITU-R P.618-13 §2.4
Rapid, small-amplitude fluctuations caused by atmospheric turbulence. Modeled as Gaussian noise with ITU-calculated standard deviation.

## 11. Dynamic Doppler Shift
Computed live from the satellite's state vector: $f_D = (v_{radial} / c) \cdot f_c$.

## 12. Packet Loss Model
Sigmoid mapping from SNR to packet loss probability:
$P_{loss} = 1 / (1 + \exp(0.8 \cdot (SNR - 10)))$.
Threshold corresponds to DVB-S2 Eb/N0 floors.
