import sqlite3
import os
import asyncio
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from sgp4.api import Satrec, jday
from typing import List, Optional, Union

from satlinksim.domain.models import Satellite, SatelliteGeometry, Constellation
from satlinksim.infrastructure.persistence.database import init_db

# ── WGS84 Constants ──────────────────────────────────────────────────────────
WGS84_A = 6378.137             # Semi-major axis (km)
WGS84_F = 1/298.257223563      # Flattening
WGS84_E2 = (2*WGS84_F - WGS84_F**2) # Squared eccentricity
EARTH_OMEGA = 7.292115e-5      # Earth rotation rate (rad/s)

def geodetic_to_ecef(lat_deg, lon_deg, alt_km):
    """Convert geodetic (lat, lon, alt) to ECEF (x, y, z) in km. Supports arrays."""
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    n = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat)**2)
    
    x = (n + alt_km) * np.cos(lat) * np.cos(lon)
    y = (n + alt_km) * np.cos(lat) * np.sin(lon)
    z = (n * (1 - WGS84_E2) + alt_km) * np.sin(lat)
    return np.stack([x, y, z], axis=-1)

def ecef_to_enu_matrix(lat_deg, lon_deg):
    """Create a rotation matrix from ECEF to ENU. Supports arrays."""
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    
    sin_lat, cos_lat = np.sin(lat), np.cos(lat)
    sin_lon, cos_lon = np.sin(lon), np.cos(lon)
    
    # Return shape (..., 3, 3)
    return np.array([
        [-sin_lon,           cos_lon,            np.zeros_like(lat)],
        [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
        [cos_lat * cos_lon,  cos_lat * sin_lon,  sin_lat]
    ]).transpose(2, 0, 1) if np.ndim(lat) > 0 else np.array([
        [-sin_lon,           cos_lon,            0],
        [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
        [cos_lat * cos_lon,  cos_lat * sin_lon,  sin_lat]
    ])

def get_gmst(jds, frs):
    """Calculate Greenwich Mean Sidereal Time (GMST) in radians. Supports arrays."""
    t = (jds + frs - 2451545.0) / 36525.0
    gmst_s = 67310.54841 + (876600.0 * 3600 + 8640184.812866) * t + 0.093104 * t**2 - 6.2e-6 * t**3
    return (gmst_s * (np.pi / 180.0) / 240.0) % (2 * np.pi)

def rotate_teme_to_ecef(pos_teme, vel_teme, gmst):
    """Rotate TEME vectors to ECEF. Supports arrays."""
    cos_g = np.cos(gmst)
    sin_g = np.sin(gmst)
    
    x = pos_teme[:, 0] * cos_g + pos_teme[:, 1] * sin_g
    y = -pos_teme[:, 0] * sin_g + pos_teme[:, 1] * cos_g
    z = pos_teme[:, 2]
    pos_ecef = np.stack([x, y, z], axis=-1)
    
    vx = vel_teme[:, 0] * cos_g + vel_teme[:, 1] * sin_g
    vy = -vel_teme[:, 0] * sin_g + vel_teme[:, 1] * cos_g
    vz = vel_teme[:, 2]
    vel_ecef = np.stack([vx, vy, vz], axis=-1)
    
    return pos_ecef, vel_ecef

class Propagator:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "satellites.db")
        self.db_path = db_path
        
        if self.db_path != ":memory:":
            init_db(self.db_path)
            
        self.cache = {}
        self._executor = None

    @property
    def executor(self):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=os.cpu_count())
        return self._executor

    def get_sat_rec(self, identifier):
        if isinstance(identifier, Satellite):
            if identifier.tle_line1 and identifier.tle_line2:
                sat = Satrec.twoline2rv(identifier.tle_line1, identifier.tle_line2)
                return identifier.name, sat
            identifier = identifier.norad_id

        if identifier in self.cache:
            return self.cache[identifier]
        
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        if isinstance(identifier, (int, np.integer)):
            cur.execute("SELECT name, tle_line1, tle_line2 FROM satellites WHERE norad_id=?", (int(identifier),))
        else:
            cur.execute("SELECT name, tle_line1, tle_line2 FROM satellites WHERE name LIKE ?", (f"%{identifier}%",))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            name, l1, l2 = row
            sat = Satrec.twoline2rv(l1, l2)
            self.cache[identifier] = (name, sat)
            return name, sat
        return None

    def get_geometry_batch(self, identifier, dts: list[datetime], gs_lat, gs_lon, gs_alt):
        res = self.get_sat_rec(identifier)
        if not res: return None
        name, sat = res
        
        jds = []
        frs = []
        for dt in dts:
            jd, fr = jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond/1e6)
            jds.append(jd)
            frs.append(fr)
        
        jds = np.array(jds)
        frs = np.array(frs)
        
        error, sat_pos_teme, sat_vel_teme = sat.sgp4_array(jds, frs)
        if np.any(error != 0): 
            return None
        
        gmst = get_gmst(jds, frs)
        sat_pos, sat_vel = rotate_teme_to_ecef(sat_pos_teme, sat_vel_teme, gmst)
        gs_pos = geodetic_to_ecef(gs_lat, gs_lon, gs_alt)
        
        rho_ecef = sat_pos - gs_pos
        slant_range = np.linalg.norm(rho_ecef, axis=1)
        
        m = ecef_to_enu_matrix(gs_lat, gs_lon)
        rho_enu = np.einsum('ij,nj->ni', m, rho_ecef)
        
        el = np.arctan2(rho_enu[:, 2], np.sqrt(rho_enu[:, 0]**2 + rho_enu[:, 1]**2))
        az = np.arctan2(rho_enu[:, 0], rho_enu[:, 1])
        
        gs_vel = np.array([-EARTH_OMEGA * gs_pos[1], EARTH_OMEGA * gs_pos[0], 0])
        rel_vel = sat_vel - gs_vel
        v_radial = np.einsum('ni,ni->n', rel_vel, rho_ecef) / slant_range
        
        return SatelliteGeometry(
            elevation_deg=np.degrees(el),
            slant_range_km=slant_range,
            radial_velocity_ms=v_radial * 1000.0,
            azimuth_deg=np.degrees(az),
            sat_name=name
        )

    async def get_geometry_batch_async(self, identifier, dts: list[datetime], gs_lat, gs_lon, gs_alt):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self.executor, 
            self.get_geometry_batch, 
            identifier, dts, gs_lat, gs_lon, gs_alt
        )

    def get_geometry(self, identifier, dt: datetime, gs_lat, gs_lon, gs_alt):
        """Maintains backward compatibility for single-step calls."""
        res = self.get_geometry_batch(identifier, [dt], gs_lat, gs_lon, gs_alt)
        if not res: return None
        return SatelliteGeometry(
            elevation_deg=res.elevation_deg[0],
            slant_range_km=res.slant_range_km[0],
            radial_velocity_ms=res.radial_velocity_ms[0],
            azimuth_deg=res.azimuth_deg[0]
        )
