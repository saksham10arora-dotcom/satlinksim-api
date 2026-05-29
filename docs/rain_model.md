# Temporally Correlated Rain — ITU-R P.1853 / Maseng-Bakken

Rain is not a memoryless process. When it starts raining, it typically continues raining for tens of minutes to hours. This simulator implements the **Maseng-Bakken first-order autoregressive model**, standardized in ITU-R P.1853.

## Layer 1 — Rain occurrence (two-state Markov chain)
The process is either in a CLEAR state or a RAINING state.
- Transition from CLEAR to RAINING with probability: $p_{onset} = 1 − \exp(−\Delta t / \tau_{clear})$
- Transition from RAINING to CLEAR with probability: $p_{clear} = 1 − \exp(−\Delta t / \tau_{rain})$
where $\tau_{rain} = \tau_c = 300\text{s}$ (5 minutes, the empirical rain cell coherence time).

## Layer 2 — Rain rate (AR(1) lognormal process)
While in the RAINING state, the log-rain-rate $\ln(R)$ evolves as:
$\ln(R[t]) = \rho \cdot \ln(R[t−1]) + \sqrt{1 − \rho^2} \cdot \sigma_{ln} \cdot N(0,1) + (1 − \rho) \cdot \mu_{ln}$
The autocorrelation coefficient $\rho = \exp(-\Delta t/\tau_c) \approx 0.819$ for 1-minute steps.

This model correctly reproduces:
- Realistic persistence of rain events (5–30 minutes).
- Gradual ramp-up and ramp-down fade slopes.
- Station-specific severity and annual statistics.
