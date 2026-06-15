"""
Compatibility layer for geometry logic, now moved to Domain layer.
"""
from satlinksim.domain.geometry.physics import (
    geo_elevation_deg, geo_slant_range_km
)

def slant_range(altitude_km, elevation_deg):
    import math
    Re = 6371.0
    el = math.radians(elevation_deg)
    h = altitude_km
    return math.sqrt((Re + h)**2 - (Re * math.cos(el))**2) - Re * math.sin(el)

def effective_elevation(global_elev, latitude):
    return max(5.0, global_elev - (abs(latitude) / 90.0 * 20.0))
