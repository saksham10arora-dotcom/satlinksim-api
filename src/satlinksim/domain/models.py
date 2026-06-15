from dataclasses import dataclass
from typing import List, Optional, Union, Any
import numpy as np
from datetime import datetime

@dataclass
class SatelliteGeometry:
    elevation_deg: np.ndarray  # Shape: (n_steps,)
    slant_range_km: np.ndarray # Shape: (n_steps,)
    radial_velocity_ms: np.ndarray # Shape: (n_steps,)
    azimuth_deg: np.ndarray = None # Shape: (n_steps,)
    sat_name: Union[str, List[str]] = None # Name(s) of the satellite(s) providing this geometry

@dataclass
class Satellite:
    norad_id: int
    name: str
    tle_line1: Optional[str] = None
    tle_line2: Optional[str] = None

    @property
    def tle(self):
        return (self.tle_line1, self.tle_line2)

@dataclass
class Constellation:
    name: str
    satellites: List[Satellite]

    @classmethod
    def from_norad_ids(cls, name: str, ids: List[int]):
        """Create a constellation from a list of NORAD IDs (will be fetched from DB)."""
        return cls(name=name, satellites=[Satellite(norad_id=i, name=str(i)) for i in ids])

    @classmethod
    def from_tle_file(cls, name: str, file_path: str):
        """Parse a TLE file (3-line format or 2-line) into a constellation."""
        sats = []
        with open(file_path, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        
        # Determine if 2-line or 3-line format
        if len(lines) >= 3 and not lines[0].startswith("1 ") and not lines[0].startswith("2 "):
            # 3-line format (Name, L1, L2)
            for i in range(0, len(lines) - 2, 3):
                sat_name = lines[i]
                l1 = lines[i+1]
                l2 = lines[i+2]
                try:
                    norad_id = int(l1[2:7])
                    sats.append(Satellite(norad_id=norad_id, name=sat_name, tle_line1=l1, tle_line2=l2))
                except: continue
        else:
            # 2-line format
            for i in range(0, len(lines) - 1, 2):
                l1 = lines[i]
                l2 = lines[i+1]
                try:
                    norad_id = int(l1[2:7])
                    sats.append(Satellite(norad_id=norad_id, name=f"SAT-{norad_id}", tle_line1=l1, tle_line2=l2))
                except: continue
        return cls(name=name, satellites=sats)

@dataclass
class HandoffEvent:
    time_step: int
    old_sat: str
    new_sat: str
    reason: str
    metric_delta: float

@dataclass
class StationResult:
    name:          str
    elevation:     float
    slant_km:      float
    doppler_hz:    float
    path_loss:     float
    gas_loss:      float
    rain_height:   float
    eff_path:      float
    itu_k:         float
    itu_alpha:     float
    scint_sig:     float
    noise_floor:   float
    snr_series:        list
    rain_series:       list
    rain_db_series:    list
    scint_series:      list
    pkt_loss_series:   list
    elevation_series:  list
    slant_range_series: list
    doppler_series:    list
    snr_mean:        float
    snr_min:         float
    snr_std:         float
    snr_p10:         float
    rain_fraction:   float
    avg_rain_db:     float
    avg_pkt_loss:    float
    outage_fraction: float
    sat_name_series:   list = None
    handoff_events:    List[HandoffEvent] = None
