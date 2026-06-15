import numpy as np

# ── Physical constants ────────────────────────────────────────────────────────
C     = 2.998e8
K_B   = 1.380649e-23

def fspl_db(freq_hz, distance_km):
    return 92.45 + 20*np.log10(freq_hz/1e9) + 20*np.log10(distance_km)

def noise_power_dbw(T_sys_K, B_hz):
    return 10 * np.log10(K_B * T_sys_K * B_hz)

def doppler_shift_hz(v_radial_ms, freq_hz):
    return (v_radial_ms / C) * freq_hz

def packet_loss_from_snr(snr_db, threshold_db):
    return 1.0 / (1.0 + np.exp(0.8 * (snr_db - threshold_db)))
