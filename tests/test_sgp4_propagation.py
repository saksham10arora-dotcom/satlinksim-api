
import pytest
import numpy as np
from datetime import datetime, timezone, timedelta
import sys
import os

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from propogate import Propagator, Satellite

def test_sgp4_geo_ecef_stability():
    """Verify that a GEO satellite remains nearly stationary in ECEF."""
    # INTELSAT 10 (GEO)
    l1 = "1 26766U 01019A   26035.04021726 -.00000036  00000+0  00000+0 0  9994"
    l2 = "2 26766   8.7570  60.6079 0008434 252.6678 104.5252  0.99072725 44254"
    sat = Satellite(norad_id=26766, name="IS-10", tle_line1=l1, tle_line2=l2)
    
    prop = Propagator(db_path=":memory:")
    
    # Check over 6 hours
    start_dt = datetime(2026, 2, 4, 12, 0, 0, tzinfo=timezone.utc)
    dts = [start_dt + timedelta(hours=i) for i in range(7)]
    
    # Use a dummy ground station at (0,0,0) to get raw vectors if needed,
    # but get_geometry_batch returns elevation etc. 
    # Let's check elevation from a station directly below it.
    # GEO is approx at 60.6 deg E (from TLE RAAN/ArgPerigee/MeanAnomaly)
    # Actually, let's just check slant range stability.
    geo = prop.get_geometry_batch(sat, dts, 0.0, 60.0, 0.0)
    
    # Slant range for GEO should be very stable (~42164 km from center)
    # Variations are due to slight eccentricity and inclination.
    mean_slant = np.mean(geo.slant_range_km)
    max_dev = np.max(np.abs(geo.slant_range_km - mean_slant))
    
    print(f"Mean Slant Range: {mean_slant:.2f} km")
    print(f"Max Deviation: {max_dev:.2f} km")
    
    # If the bug were present, slant range would vary by thousands of km 
    # as the ground station rotates away from the satellite's TEME position.
    assert max_dev < 100, f"GEO slant range is unstable! Max deviation: {max_dev:.2f} km"

def test_sgp4_vs_satnogs_static():
    """Static regression test against a known SatNOGS observation."""
    # CONNECTA IOT-1 (60472)
    # Obs 14217654
    tle1 = "1 60472U 24149E   26153.18620229  .00004418  00000-0  18856-3 0  9994"
    tle2 = "2 60472  97.3762 229.7318 0001676  25.2916 334.8403 15.23416626 99517"
    sat = Satellite(norad_id=60472, name="CONNECTA", tle_line1=tle1, tle_line2=tle2)
    
    prop = Propagator(db_path=":memory:")
    
    # Time of peak elevation in SatNOGS observation
    # (Approx midpoint of 16:06:08 to 16:11:00)
    dt = datetime(2026, 6, 2, 16, 8, 34, tzinfo=timezone.utc)
    
    res = prop.get_geometry(sat, dt, 33.797628, -79.159123, 12/1000.0)
    
    print(f"Calculated Elevation: {res.elevation_deg:.2f}")
    # SatNOGS reported max_altitude: 79.0
    assert abs(res.elevation_deg - 79.0) < 5.0

if __name__ == "__main__":
    pytest.main([__file__])
