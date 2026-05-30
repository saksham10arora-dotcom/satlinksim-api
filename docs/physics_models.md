# Physics Models — Detailed Technical Reference

The simulator computes a full link budget at each time step. A link budget is an accounting of every gain and every loss that a signal experiences from transmitter power amplifier to receiver decoder. The SNR at the receiver is:

```
SNR = EIRP − FSPL − L_gas − L_rain − L_scint + G_rx − N
```

where every term is in decibels (dB) or dBW. The sections below derive each term from first principles and ITU-R recommendations.

---

## 1. Dynamic Orbital Geometry (SGP4)

The project utilizes live orbital data via the `propogate.py` layer, moving beyond static GEO assumptions to support LEO, MEO, and drifting GEO orbits.

- **SGP4 Propagation**: For any station linked to a `norad_id`, the simulator fetches the latest TLE (Two-Line Element) from `satellites.db` and propagates the orbit to the current simulation epoch using the SGP4 (Simplified General Perturbations) model.
- **ECEF State**: The propagator returns position (x, y, z) and velocity vectors in **Earth-Centered, Earth-Fixed** coordinates.
- **Topocentric Transformation**: ECEF vectors are converted into **ENU (East-North-Up)** coordinates relative to the ground station's WGS84 geodetic position.
- **Dynamic Metrics**: Recomputes **Elevation**, **Slant Range**, and **Azimuth** at every 60-second timestep.

**Why this matters**:
- **Slant Range Variation**: As a satellite moves closer to the horizon, the **Free-Space Path Loss** and **Rain Path Length** increase dynamically.
- **Doppler Dynamics**: Radial velocity is derived from the dot product of the relative velocity vector and the range vector, allowing for accurate Doppler shift modeling.

---

## 2. Free-Space Path Loss (FSPL)

FSPL is the attenuation a radio wave experiences purely from spreading out over distance. It follows the inverse-square law: power is spread over an expanding sphere of area $4\pi d^2$.

The ITU-R formulation in dB is:
```
FSPL(dB) = 92.45 + 20·log₁₀(f_GHz) + 20·log₁₀(d_km)
```

- **20 log₁₀(f)**: Arises because a fixed-gain antenna has an effective aperture that decreases as frequency increases ($\text{aperture} \propto \lambda^2 \propto 1/f^2$).
- **20 log₁₀(d)**: Represents the inverse-square spreading.
- **At 14 GHz and 40,000 km**: $FSPL \approx 207\text{ dB}$.

---

## 3. Thermal Noise Power

Every receiver generates thermal noise due to the random motion of electrons. The noise power $N$ in watts for a receiver with system noise temperature $T_{sys}$ and bandwidth $B$ is:
```
N = k_B · T_sys · B
```
where $k_B = 1.381 \times 10^{-23} \text{ J/K}$ is Boltzmann's constant. In dBW:
```
N(dBW) = −228.6 + 10·log₁₀(T_sys) + 10·log₁₀(B)
```

$T_{sys}$ captures contributions from the antenna (sky/earth noise), LNA, feedline losses, and receiver stages (typically 290–600 K for Ku-band).

---

## 4. Rain Statistics (ITU-R P.837-7)

Rain intensity is highly non-uniform globally. Tropical regions experience intense convective rain cells, while temperate regions see more widespread, lower-intensity stratiform rain.

The simulator utilizes ITU-R P.837-7 exceedance probabilities derived from digital map grids:
- **$R_{0.01}$**: Rain rate exceeded 0.01% of an average year (~53 mins/year).
- **$R_{0.1}$**: Rain rate exceeded 0.1% of an average year (~8.8 hours/year).
- **$P_{rain}$**: Fraction of the year when rain occurs.

These quantiles are used to fit a **lognormal distribution** for the rain process, parameterizing the AR(1) model used for time-series synthesis.

---

## 5. Rain Attenuation Coefficients (ITU-R P.838-3)

Microwave signals passing through rain experience **Absorption** (molecular excitation) and **Scattering** (Mie scattering). This is captured by the specific attenuation $\gamma_R$:
```
γ_R = k · R^α    [dB/km]
```
- **$k, \alpha$**: Depend on frequency and polarization.
- **Polarization**: Horizontal polarization ($k_H, \alpha_H$) suffers higher attenuation than vertical ($k_V, \alpha_V$) because falling raindrops are oblate (flattened horizontally by air resistance).
- **Interpolation**: The simulator performs log-linear interpolation of ITU-R P.838 tables to support arbitrary carrier frequencies.

**Typical attenuation** ranges from a few dB during moderate rain to **>20 dB** during severe convective storms.

---

## 6. Rain Height (ITU-R P.839-4)

Rain attenuation occurs only below the freezing level (the $0^\circ C$ isotherm). Above this height, precipitation is ice or snow, which has significantly lower attenuation.

Rain height $h_R$ is a function of latitude $\phi$:
- **Equatorial ($|\phi| \le 23^\circ$)**: $h_R = 5.0\text{ km}$.
- **High Latitudes ($|\phi| > 36^\circ$)**: $h_R$ descends toward $2.0\text{ km}$.

---

## 7. Effective Slant Path (ITU-R P.618-13)

The actual distance a signal travels through rain depends on the elevation angle $El$. The slant distance $L_s$ through a rain column of height $(h_R - h_s)$ is:
```
L_s = (h_R − h_s) / sin(El)
```

For low elevation angles ($< 10^\circ$), a **path reduction factor** $r$ accounts for the horizontal inhomogeneity of rain cells, preventing overestimation of attenuation at grazing angles.

---

## 8. Rain Attenuation on the Path

Combining specific attenuation with the effective path length gives the total rain loss:
```
A_rain = k · R^α · L_eff    [dB]
```
This term accounts for the largest source of variability in Ku-band links.

---

## 9. Gaseous Absorption (ITU-R P.676-12)

Molecular resonances in Oxygen ($O_2$) and Water Vapour ($H_2O$) absorb microwave energy.
- **Oxygen**: Broad absorption band near 60 GHz.
- **Water Vapour**: Resonance line at 22.235 GHz.
- **Scaling**: Zenith attenuation is scaled by $1/\sin(El)$ to account for the slant path through the atmosphere.

Typically contributes **0.5–1.5 dB** for Ku-band GEO links.

---

## 10. Tropospheric Scintillation (ITU-R P.618-13 §2.4)

Rapid amplitude fluctuations caused by turbulent irregularities in the refractive index of the troposphere.
- **Wet Refractivity**: Proportional to surface humidity.
- **Aperture Averaging**: Larger antennas average out more of the wavefront, reducing scintillation.
- **Modeling**: Implemented as Gaussian noise with a standard deviation $\sigma_s$ derived from ITU-R P.618-13.

Typical fade amplitudes range from **0.5–2 dB** for Ku-band systems.

---

## 11. Temporally Correlated Rain (ITU-R P.1853)

The simulator implements the **Maseng-Bakken AR(1) model** to ensure rain fade events have realistic persistence (tens of minutes) rather than being memoryless.

- **Layer 1 (Occurrence)**: A two-state Markov chain (Clear/Raining).
- **Layer 2 (Intensity)**: While raining, log-rain-rate $\ln(R)$ evolves as:
  $$\ln(R[t]) = \rho \cdot \ln(R[t−1]) + \sqrt{1 − \rho^2} \cdot \sigma_{ln} \cdot N(0,1) + (1 − \rho) \cdot \mu_{ln}$$
- **Correlation**: $\rho = \exp(-\Delta t / 300)$ ensures an 82% correlation between 1-minute steps.

---

## 12. Dynamic Doppler Shift

With SGP4 integration, the Doppler shift is computed live from the satellite's state vector:
```
f_D = (v_radial / c) · f_c
```
Where `v_radial` is the projection of the relative velocity vector (Satellite - Ground Station) onto the line-of-sight vector. This allows the simulator to model the rapid Doppler sweeps characteristic of non-GEO satellites.

---

## 13. The Link Budget Equation

Every physical effect computed above combines into the link budget equation evaluated at each time step $t$:

```
SNR[t] = EIRP_eff − FSPL − A_gas − A_rain[t] − L_scint[t] + G_rx − N(T_sys, B)
```

All terms in dBW or dB:

| Term | Symbol | Source | Typical value |
|---|---|---|---|
| Effective transmit power | $EIRP_{eff}$ | Hardware + UI slider | 50–54 dBW |
| Free-space path loss | $FSPL$ | Geometry + frequency | ~207 dB at 14 GHz |
| Gaseous absorption | $A_{gas}$ | ITU-R P.676 | 0.5–1.5 dB |
| Rain attenuation | $A_{rain}[t]$ | ITU-R P.838 × P.618 path | 0–30+ dB |
| Scintillation | $L_{scint}[t]$ | ITU-R P.618 §2.4 | ±0.5–2 dB |
| Receive antenna gain | $G_{rx}$ | Hardware | 44–48 dBi |
| Thermal noise | $N$ | $k_B \cdot T_{sys} \cdot B$ | −130 to −125 dBW |

---

## 14. Packet Loss Model

SNR is mapped to packet loss probability using a sigmoid function centered at the **Ku-band DVB-S2 floor** ($10\text{ dB}$):
```
P_loss = 1 / (1 + exp(0.8 · (SNR − 10)))
```
This steep transition correctly models the behavior of Forward Error Correction (FEC) codes, which exhibit "brick-wall" performance near their SNR thresholds.
