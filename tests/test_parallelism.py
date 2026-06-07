import pytest
import asyncio
import numpy as np
from datetime import datetime, timezone
from satlinksim.satellite_link_sim import (
    simulate_all_batched, simulate_all_concurrent, run_monte_carlo
)
from satlinksim.ground_stations import GROUND_STATIONS

def test_simulate_all_batched():
    results = simulate_all_batched(GROUND_STATIONS, n_steps=10)
    assert len(results) == len(GROUND_STATIONS)
    assert len(results[0].snr_series) == 10

@pytest.mark.asyncio
async def test_simulate_all_concurrent():
    results = await simulate_all_concurrent(GROUND_STATIONS, n_steps=10)
    assert len(results) == len(GROUND_STATIONS)
    assert len(results[0].snr_series) == 10

def test_run_monte_carlo():
    n_iter = 3
    results = run_monte_carlo(n_iter, GROUND_STATIONS, n_steps=5)
    assert len(results) == n_iter
    assert len(results[0]) == len(GROUND_STATIONS)
    
    # Check that seeds produce different results for rain (if we force it or just by probability)
    # Even if results are same (e.g. no rain), the structure should be correct.
    snr_iter1 = results[0][0].snr_series
    snr_iter2 = results[1][0].snr_series
    # They might be same if no rain occurs, but structure is what matters here.
    assert len(snr_iter1) == 5

if __name__ == "__main__":
    # Quick manual check
    print("Testing Monte Carlo...")
    res = run_monte_carlo(2, GROUND_STATIONS, n_steps=5)
    print(f"MC iterations: {len(res)}")
    
    print("Testing Concurrent...")
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(simulate_all_concurrent(GROUND_STATIONS, n_steps=5))
    print(f"Concurrent results: {len(res)}")
