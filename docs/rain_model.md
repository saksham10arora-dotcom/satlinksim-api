# Temporally Correlated Rain — ITU-R P.1853 / Maseng-Bakken

Rain is not a memoryless process. When it starts raining, it typically continues raining for tens of minutes to hours. Sampling rain intensity independently at every timestep produces unrealistic fluctuations and underestimates fade persistence.

To address this, the simulator implements the Maseng-Bakken first-order autoregressive model standardized in ITU-R P.1853.

## Layer 1 — Rain Occurrence (Two-State Markov Chain)

The process exists in either a CLEAR or RAINING state.

- **CLEAR → RAINING**:
  $p_{onset} = 1 − \exp(−\Delta t / \tau_{clear})$

- **RAINING → CLEAR**:
  $p_{clear} = 1 − \exp(−\Delta t / \tau_{rain})$

where $\tau_{rain} = \tau_c = 300\text{ s}$ (the empirical rain-cell coherence time).

## Layer 2 — Rain Intensity (AR(1) Lognormal Process)

While in the RAINING state, the log-rain-rate evolves as:

$$\ln(R[t]) = \rho \ln(R[t−1]) + \sqrt{1−\rho^2} \sigma_{ln} N(0,1) + (1−\rho) \mu_{ln}$$

The autocorrelation coefficient

$$\rho = \exp(−\Delta t / \tau_c) \approx 0.819$$

ensures that adjacent one-minute samples retain approximately 82% correlation.

The stationary distribution of $\ln(R)$ is $N(\mu_{ln}, \sigma_{ln}^2)$, ensuring that long-run rain statistics remain consistent with the ITU-R P.837 exceedance probabilities used to parameterize the model.

This model reproduces:

- **Realistic persistence** of rain events (5–30 minutes)
- **Gradual fade** ramp-up and ramp-down behavior
- **Station-specific** rain severity
- **Long-run climatological** rain statistics
