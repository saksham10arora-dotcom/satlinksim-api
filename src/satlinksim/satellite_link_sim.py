"""
Compatibility layer for satellite_link_sim logic, now moved to Domain and Application layers.
"""
from satlinksim.domain.models import StationResult, HandoffEvent, SatelliteGeometry
from satlinksim.domain.geometry.physics import geo_elevation_deg, geo_slant_range_km
from satlinksim.domain.link.itu_models import (
    itu_rain_coefficients, itu_rain_height, effective_path_length,
    rain_attenuation_db, gaseous_absorption_db, scintillation_sigma_db
)
from satlinksim.domain.link.budget import (
    fspl_db, noise_power_dbw, doppler_shift_hz, packet_loss_from_snr
)
from satlinksim.domain.rain.engine import CorrelatedRainProcess
from satlinksim.domain.handoff.manager import HandoffManager
from satlinksim.application.simulation_engine import (
    SimulationEngine, run_simulation,
    DEFAULT_CARRIER_FREQ_HZ, DEFAULT_BANDWIDTH_HZ, DEFAULT_POLARIZATION,
    DEFAULT_DT_S, DEFAULT_N_STEPS, SNR_THRESHOLD_DB
)
from satlinksim.ground_stations import GROUND_STATIONS

# Convenience aliases
def simulate_all_batched(*args, **kwargs):
    return SimulationEngine().simulate_all_batched(*args, **kwargs)

async def simulate_all_concurrent(*args, **kwargs):
    return await SimulationEngine().simulate_all_concurrent(*args, **kwargs)

def run_monte_carlo(*args, **kwargs):
    return SimulationEngine().run_monte_carlo(*args, **kwargs)

def simulate_station(gs, **kwargs):
    return simulate_all_batched([gs], **kwargs)[0]

def simulate_all(**kwargs):
    from satlinksim.ground_stations import GROUND_STATIONS
    return simulate_all_batched(GROUND_STATIONS, **kwargs)
