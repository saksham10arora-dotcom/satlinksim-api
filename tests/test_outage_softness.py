import pytest
import sys
import os
import numpy as np
from datetime import datetime, timezone

# Allow standalone execution: add 'src' to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from satellite_link_sim import simulate_station, SNR_THRESHOLD_DB
from ground_stations import GROUND_STATIONS

def test_outage_softness():
    """Verify that outage_fraction is now a soft metric (mean packet loss)."""
    gs = GROUND_STATIONS[0] # Delhi
    
    # Force a marginal link by adjusting EIRP offset
    # Let's say we want SNR to be exactly at the threshold
    # From previous runs, Delhi clear sky is ~9.9 dB.
    # So threshold 10dB is very close.
    
    res = simulate_station(gs, n_steps=100, eirp_offset_db=0.0, seed=42)
    
    # In the old version, if SNR was 9.9 for all steps, outage would be 100%.
    # In the new version, if SNR is 9.9, packet loss is ~52%.
    # So outage_fraction should be around 0.52.
    
    print(f"SNR mean: {res.snr_mean}, Outage: {res.outage_fraction}")
    
    assert 0.0 < res.outage_fraction < 1.0
    assert res.outage_fraction == pytest.approx(res.avg_pkt_loss)

def test_outage_transition():
    """Verify that outage transitions smoothly as EIRP offset changes."""
    gs = GROUND_STATIONS[1] # Tokyo (high margin)
    
    # High margin -> low outage
    res_high = simulate_station(gs, n_steps=10, eirp_offset_db=10.0)
    # Low margin -> high outage
    res_low = simulate_station(gs, n_steps=10, eirp_offset_db=-20.0)
    # Marginal -> intermediate outage
    res_mid = simulate_station(gs, n_steps=10, eirp_offset_db=-11.0)
    
    print(f"High: {res_high.outage_fraction}, Mid: {res_mid.outage_fraction}, Low: {res_low.outage_fraction}")
    
    assert res_high.outage_fraction < 0.05
    assert res_low.outage_fraction > 0.95
    assert 0.05 < res_mid.outage_fraction < 0.95

if __name__ == "__main__":
    pytest.main([__file__])
