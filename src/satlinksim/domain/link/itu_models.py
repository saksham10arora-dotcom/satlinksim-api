import numpy as np

def itu_rain_coefficients(freq_ghz, polarization):
    table = np.array([
        ( 1,  0.0000259, 0.9691, 0.0000308, 0.8592),
        ( 2,  0.0000847, 1.0664, 0.0000998, 0.9490),
        ( 4,  0.0001071, 1.6009, 0.0002461, 1.2476),
        ( 6,  0.007056,  1.590,  0.004115,  1.590 ),
        ( 7,  0.001915,  1.481,  0.001128,  1.457 ),
        ( 8,  0.004115,  1.590,  0.002455,  1.584 ),
        (10,  0.01217,   1.261,  0.01129,   1.3026),
        (12,  0.02386,   1.179,  0.01731,   1.2070),
        (15,  0.04481,   1.154,  0.03979,   1.1820),
        (20,  0.09164,   1.099,  0.08084,   1.0993),
        (25,  0.1571,    1.046,  0.1378,    1.0639),
        (30,  0.2403,    1.021,  0.2101,    1.0299),
        (35,  0.3374,    0.979,  0.2991,    0.9876),
        (40,  0.4743,    0.939,  0.4285,    0.9491),
    ])
    freqs  = table[:, 0]
    kH_tab = table[:, 1]; aH_tab = table[:, 2]
    kV_tab = table[:, 3]; aV_tab = table[:, 4]

    if polarization.lower() == "horizontal":
        k = 10**np.interp(np.log10(freq_ghz), np.log10(freqs), np.log10(kH_tab))
        alpha = np.interp(freq_ghz, freqs, aH_tab)
    else:
        k = 10**np.interp(np.log10(freq_ghz), np.log10(freqs), np.log10(kV_tab))
        alpha = np.interp(freq_ghz, freqs, aV_tab)
    return k, alpha

def itu_rain_height(lat_deg):
    is_scalar = np.isscalar(lat_deg)
    a = np.atleast_1d(np.abs(lat_deg))
    h = np.full_like(a, 5.0, dtype=float)
    mask1 = (a > 23) & (a < 36)
    h[mask1] = np.maximum(5.0 - 0.075 * (a[mask1] - 23.0), 3.0)
    mask2 = (a >= 36)
    h[mask2] = np.maximum(5.0 - 0.1 * (a[mask2] - 36.0), 2.0)
    return h[0] if is_scalar else h

def effective_path_length(elevation_deg, rain_height_km, station_altitude_km, itu_k):
    el_rad  = np.radians(np.maximum(elevation_deg, 5.0))
    h_delta = rain_height_km - station_altitude_km
    L_s = np.where(h_delta > 0, h_delta / np.sin(el_rad), 0.0)
    L_g = np.where(h_delta > 0, h_delta / np.tan(el_rad), 0.0)
    r = np.where(elevation_deg <= 10,
                 1.0 / (1.0 + 0.78 * np.sqrt(L_g * itu_k) - 0.38 * (1 - np.exp(-2 * L_g))),
                 1.0)
    return L_s * r

def rain_attenuation_db(rain_rate_mmh, itu_k, itu_alpha, eff_path_km):
    return np.where((rain_rate_mmh > 0) & (eff_path_km > 0),
                    itu_k * (rain_rate_mmh ** itu_alpha) * eff_path_km,
                    0.0)

def gaseous_absorption_db(freq_ghz, elevation_deg, water_vapour_g_m3):
    f = freq_ghz
    gamma_oxy = np.maximum((7.2/(f**2+0.34) + 0.62/((54-f)**1.16+0.83))
                    * (f/22.235)**2 * 1e-3, 0.0078)
    gamma_wv  = (0.050 + 0.0021*water_vapour_g_m3
                 + 3.6  / ((f-22.235)**2 + 8.5)
                 + 10.6 / ((f-183.31)**2 + 9.0)
                 + 8.9  / ((f-325.153)**2 + 26.3)) * water_vapour_g_m3 * f**2 * 1e-4
    return (gamma_oxy + gamma_wv) * 10.0 / np.sin(np.radians(np.maximum(elevation_deg, 5.0)))

def scintillation_sigma_db(freq_ghz, elevation_deg, antenna_diam_m, humidity_pct):
    el_rad    = np.radians(np.maximum(elevation_deg, 5.0))
    Nwet      = 0.75 * humidity_pct
    sigma_ref = 0.5509 * Nwet * np.sqrt(1e-3) / (np.sin(el_rad) ** 1.2)
    eta       = 0.5
    D_eff     = np.sqrt(eta) * antenna_diam_m
    x         = 1.22 * D_eff**2 * (freq_ghz / 300.0)
    g_x       = np.sqrt(np.maximum(3.86*(x**2+1)**0.116
                               * np.cos(np.arctan(x)*11.0/6.0)
                               - 7.08*x**(5.0/6.0), 1e-6))
    return sigma_ref * g_x * 1e-3
