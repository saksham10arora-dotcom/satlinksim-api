import random
import numpy as np
import asyncio
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Union, Callable

from satlinksim.domain.models import StationResult, Constellation
from satlinksim.domain.interfaces import Propagator, RainModel
from satlinksim.domain.rain.engine import CorrelatedRainProcess
from satlinksim.domain.geometry.physics import geo_elevation_deg, geo_slant_range_km
from satlinksim.domain.link.itu_models import (
    itu_rain_coefficients, itu_rain_height, effective_path_length,
    rain_attenuation_db, gaseous_absorption_db, scintillation_sigma_db
)
from satlinksim.domain.link.budget import (
    fspl_db, noise_power_dbw, doppler_shift_hz, packet_loss_from_snr
)
from satlinksim.domain.handoff.manager import HandoffManager, HandoffPolicy, HighestElevationPolicy, HighestSNRPolicy
from satlinksim.infrastructure.tle.service import SGP4Propagator
from satlinksim.config import config
from satlinksim.ground_stations import GROUND_STATIONS

# Defaults
DEFAULT_CARRIER_FREQ_HZ = config.simulation.link.carrier_freq_hz
DEFAULT_BANDWIDTH_HZ    = config.simulation.link.bandwidth_hz
DEFAULT_POLARIZATION    = config.simulation.link.polarization
DEFAULT_DT_S            = config.simulation.dt_s
DEFAULT_N_STEPS         = config.simulation.n_steps
SNR_THRESHOLD_DB        = config.simulation.link.snr_threshold_db

class SimulationEngine:
    def __init__(self, propagator: Optional[Propagator] = None):
        self.propagator = propagator or SGP4Propagator()

    def simulate_all_batched(self, ground_stations: list[dict],
                             n_steps:         int   = DEFAULT_N_STEPS,
                             dt_s:            float = DEFAULT_DT_S,
                             start_time:      Optional[datetime] = None,
                             force_rain:      bool  = False,
                             seed:            Optional[int] = None,
                             freq_hz:         float = DEFAULT_CARRIER_FREQ_HZ,
                             eirp_offset_db:  float = 0.0,
                             bandwidth_hz:    float = DEFAULT_BANDWIDTH_HZ,
                             polarization:    str   = DEFAULT_POLARIZATION,
                             rain_rate_scale: float = 1.0,
                             constellation:   Optional[Constellation] = None,
                             handoff_policy:  Union[str, HandoffPolicy] = "highest_elevation",
                             hysteresis:      float = config.simulation.handoff.hysteresis_db,
                             min_dwell_steps: int = config.simulation.handoff.dwell_steps,
                             rain_model_factory: Optional[Callable[[dict], RainModel]] = None,
                             ) -> list[StationResult]:
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)

        curr_time = start_time or datetime.now(timezone.utc)
        times = [curr_time + timedelta(seconds=i*dt_s) for i in range(n_steps)]
        freq_ghz = freq_hz / 1e9

        itu_k, itu_a = itu_rain_coefficients(freq_ghz, polarization)
        results = []

        for i, gs in enumerate(ground_stations):
            noise_dbw = noise_power_dbw(gs["system_temp_k"], bandwidth_hz)
            eirp = gs["eirp_dbw"] + eirp_offset_db
            g_rx = gs["g_rx_dbi"]
            rain_h = itu_rain_height(gs["latitude"])

            candidates_geo = []
            if constellation:
                for sat in constellation.satellites:
                    geo = self.propagator.get_geometry_batch(sat, times, gs["latitude"], gs["longitude"], gs["altitude_km"])
                    if geo: candidates_geo.append(geo)
            else:
                sat_id = gs.get("norad_id") or gs.get("sat_name")
                if sat_id:
                    geo = self.propagator.get_geometry_batch(sat_id, times, gs["latitude"], gs["longitude"], gs["altitude_km"])
                    if geo: candidates_geo.append(geo)

            if not candidates_geo:
                # Fallback to GEO
                el_s = np.full(n_steps, geo_elevation_deg(gs["latitude"], gs["longitude"], gs.get("sat_lon_deg", 0)))
                slant_s = np.full(n_steps, geo_slant_range_km(gs["latitude"], gs["longitude"], gs.get("sat_lon_deg", 0)))
                dop_s = np.full(n_steps, doppler_shift_hz(gs.get("v_radial_ms", 0), freq_hz))
                sat_names = [gs.get("sat_name") or f"SAT-LAT{gs.get('sat_lon_deg',0)}"] * n_steps
                handoff_events = []
                rain_rate_s = np.zeros(n_steps)
                rain_db_s = np.zeros(n_steps)
                scint_s = np.zeros(n_steps)
                snr_s = np.full(n_steps, eirp - fspl_db(freq_hz, slant_s[0]) + g_rx - noise_dbw)
                pkt_s = packet_loss_from_snr(snr_s, SNR_THRESHOLD_DB)
                sorted_snr = sorted(snr_s.tolist())
                p10_idx = max(0, int(0.10 * n_steps) - 1)
            else:
                n_cands = len(candidates_geo)
                cand_names = [g.sat_name for g in candidates_geo]

                if rain_model_factory:
                    rain_proc = rain_model_factory(gs)
                else:
                    rain_proc = CorrelatedRainProcess([gs], dt_s=dt_s, force_rain=force_rain, 
                                                      rain_rate_scale=rain_rate_scale)
                rain_rate_s = rain_proc.generate_batch(n_steps)[:, 0]

                cand_snr_matrix = np.zeros((n_cands, n_steps))
                cand_el_matrix = np.zeros((n_cands, n_steps))
                cand_slant_matrix = np.zeros((n_cands, n_steps))
                cand_dop_matrix = np.zeros((n_cands, n_steps))
                cand_rain_db_matrix = np.zeros((n_cands, n_steps))
                cand_scint_db_matrix = np.zeros((n_cands, n_steps))
                
                for c_idx, geo in enumerate(candidates_geo):
                    pl = fspl_db(freq_hz, geo.slant_range_km)
                    gl = gaseous_absorption_db(freq_ghz, geo.elevation_deg, gs["wv_g_m3"])
                    ep = effective_path_length(geo.elevation_deg, rain_h, gs["altitude_km"], itu_k)
                    ra = rain_attenuation_db(rain_rate_s, itu_k, itu_a, ep)
                    ss = scintillation_sigma_db(freq_ghz, geo.elevation_deg, gs["antenna_diam_m"], gs["humidity_pct"])
                    scint_db = np.random.normal(0, ss)
                    
                    snr = eirp - pl - gl - ra - scint_db + g_rx - noise_dbw
                    cand_snr_matrix[c_idx] = snr
                    cand_el_matrix[c_idx] = geo.elevation_deg
                    cand_slant_matrix[c_idx] = geo.slant_range_km
                    cand_dop_matrix[c_idx] = doppler_shift_hz(geo.radial_velocity_ms, freq_hz)
                    cand_rain_db_matrix[c_idx] = ra
                    cand_scint_db_matrix[c_idx] = scint_db

                if isinstance(handoff_policy, str):
                    if handoff_policy == "highest_snr":
                        policy_obj = HighestSNRPolicy()
                    else:
                        policy_obj = HighestElevationPolicy()
                else:
                    policy_obj = handoff_policy
                
                hm = HandoffManager(policy=policy_obj, hysteresis=hysteresis, min_dwell_steps=min_dwell_steps)
                selected_indices = []
                for t in range(n_steps):
                    idx = hm.select(t, cand_names, cand_snr_matrix[:, t], cand_el_matrix[:, t])
                    selected_indices.append(idx)
                
                t_idx = np.arange(n_steps)
                s_idx = np.array(selected_indices)
                
                el_s = cand_el_matrix[s_idx, t_idx]
                slant_s = cand_slant_matrix[s_idx, t_idx]
                dop_s = cand_dop_matrix[s_idx, t_idx]
                snr_s = cand_snr_matrix[s_idx, t_idx]
                rain_db_s = cand_rain_db_matrix[s_idx, t_idx]
                scint_db_s = cand_scint_db_matrix[s_idx, t_idx]
                sat_names = [cand_names[i] for i in s_idx]
                handoff_events = hm.events

                pkt_s = packet_loss_from_snr(snr_s, SNR_THRESHOLD_DB).tolist()
                snr_s = snr_s.tolist()
                rain_rate_s = rain_rate_s.tolist()
                rain_db_s = rain_db_s.tolist()
                scint_s = scint_db_s.tolist()
                el_s = el_s.tolist()
                slant_s = slant_s.tolist()
                dop_s = dop_s.tolist()

                sorted_snr = sorted(snr_s)
                p10_idx = max(0, int(0.10 * n_steps) - 1)

            results.append(StationResult(
                name=gs["name"], elevation=el_s[0], slant_km=slant_s[0], doppler_hz=dop_s[0],
                path_loss=fspl_db(freq_hz, slant_s[0]),
                gas_loss=gaseous_absorption_db(freq_ghz, el_s[0], gs["wv_g_m3"]),
                rain_height=rain_h,
                eff_path=effective_path_length(el_s[0], rain_h, gs["altitude_km"], itu_k),
                itu_k=itu_k, itu_alpha=itu_a,
                scint_sig=scintillation_sigma_db(freq_ghz, el_s[0], gs["antenna_diam_m"], gs["humidity_pct"]),
                noise_floor=noise_dbw,
                snr_series=snr_s, rain_series=rain_rate_s, rain_db_series=rain_db_s,
                scint_series=scint_s, pkt_loss_series=pkt_s,
                elevation_series=el_s, slant_range_series=slant_s, doppler_series=dop_s,
                snr_mean=float(np.mean(snr_s)),
                snr_min=float(np.min(snr_s)),
                snr_std=float(np.std(snr_s, ddof=1)) if len(snr_s) > 1 else 0.0,
                snr_p10=float(sorted_snr[p10_idx]),
                rain_fraction=float(np.sum(np.array(rain_rate_s) > 0) / n_steps),
                avg_rain_db=float(np.mean([db for db in rain_db_s if db > 0])) if any(db > 0 for db in rain_db_s) else 0.0,
                avg_pkt_loss=float(np.mean(pkt_s)),
                outage_fraction=float(np.mean(pkt_s)),
                sat_name_series=sat_names,
                handoff_events=handoff_events
            ))

        return results

    async def simulate_all_concurrent(self, ground_stations: List[Dict], 
                                      constellation: Optional[Constellation] = None,
                                      **kwargs) -> List[StationResult]:
        n_steps = kwargs.get("n_steps", DEFAULT_N_STEPS)
        dt_s = kwargs.get("dt_s", DEFAULT_DT_S)
        start_time = kwargs.get("start_time") or datetime.now(timezone.utc)
        times = [start_time + timedelta(seconds=i*dt_s) for i in range(n_steps)]
        
        tasks = []
        for gs in ground_stations:
            if constellation:
                tasks.append(asyncio.sleep(0, result=None))
            else:
                sat_id = gs.get("norad_id") or gs.get("sat_name")
                if sat_id:
                    tasks.append(self.propagator.get_geometry_batch_async(
                        sat_id, times, gs["latitude"], gs["longitude"], gs["altitude_km"]
                    ))
                else:
                    tasks.append(asyncio.sleep(0, result=None))
                
        await asyncio.gather(*tasks)
        
        return self.simulate_all_batched(ground_stations, constellation=constellation, **kwargs)

    def run_monte_carlo(self, n_iterations: int, ground_stations: List[Dict], 
                        constellation: Optional[Constellation] = None,
                        **kwargs) -> List[List[StationResult]]:
        base_seed = kwargs.pop("seed", 42) or 42
        seeds = [base_seed + i for i in range(n_iterations)]
        
        with ProcessPoolExecutor() as executor:
            futures = [
                executor.submit(self.simulate_all_batched, ground_stations, seed=s, constellation=constellation, **kwargs)
                for s in seeds
            ]
            results = [f.result() for f in futures]
        return results

def run_simulation(*args, **kwargs):
    engine = SimulationEngine()
    return engine.simulate_all_batched(*args, **kwargs)
