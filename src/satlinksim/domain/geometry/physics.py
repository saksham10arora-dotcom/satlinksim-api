import numpy as np

# ── Physical constants ────────────────────────────────────────────────────────
R_E   = 6371.0
R_GEO = 42_164.0

def geo_elevation_deg(lat_deg, lon_deg, sat_lon_deg):
    lat       = np.radians(lat_deg)
    dlon      = np.radians(lon_deg - sat_lon_deg)
    cos_gamma = np.cos(lat) * np.cos(dlon)
    d         = geo_slant_range_km(lat_deg, lon_deg, sat_lon_deg)
    sin_el    = (R_GEO * cos_gamma - R_E) / d
    return np.degrees(np.arcsin(np.clip(sin_el, -1.0, 1.0)))

def geo_slant_range_km(lat_deg, lon_deg, sat_lon_deg):
    lat       = np.radians(lat_deg)
    dlon      = np.radians(lon_deg - sat_lon_deg)
    cos_gamma = np.cos(lat) * np.cos(dlon)
    return np.sqrt(R_GEO**2 + R_E**2 - 2 * R_GEO * R_E * cos_gamma)
