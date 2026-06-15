"""
Compatibility layer for propagation logic, now moved to Infrastructure layer.
"""
from satlinksim.domain.models import Satellite, Constellation, SatelliteGeometry
from satlinksim.infrastructure.tle.service import (
    SGP4Propagator as Propagator, geodetic_to_ecef, ecef_to_enu_matrix, get_gmst, rotate_teme_to_ecef,
    WGS84_A, WGS84_F, WGS84_E2, EARTH_OMEGA
)
