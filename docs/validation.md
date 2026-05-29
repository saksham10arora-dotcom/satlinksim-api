# Validation Methodology

The simulator includes an automated suite to ensure physical accuracy against ITU standards and analytical references.

## 1. Free-Space Path Loss (ITU-R P.525)
Validated against the standard formula: $L_{fs} = 92.45 + 20\log_{10}(f_{GHz}) + 20\log_{10}(d_{km})$. 

## 2. Rain Attenuation (ITU-R P.838 / P.839)
- **Coefficients:** Verified via log-linear interpolation of ITU-R P.838-3 tables.
- **Rain Height:** Latitude-dependent model (P.839-4) tested for climate zone accuracy.

## 3. Geometry & SGP4
- **Slant Range:** Analytical checks for Zenith ($90^\circ$) and Horizon ($0^\circ$) elevations.
- **SGP4 vs. Analytical:** Cross-validation of SGP4-propagated slant range against GEO analytical models.

## 4. Stochastic Rain Process (ITU-R P.1853)
- **Autocorrelation:** Verified decay constant $\rho = e^{-dt/\tau_c}$ matches the 5-minute ($\sim 300\text{s}$) correlation time.
- **Stationary Distribution:** Convergence to ITU-R P.837 lognormal mean across varying time steps.
