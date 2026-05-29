# System Architecture

The simulator is built with a modular, high-performance architecture designed to handle thousands of ground stations and satellites with millisecond latency.

## Core Modules
- **`app.py`**: Streamlit dashboard providing UI controls, scoring, and visualization.
- **`satellite_link_sim.py`**: High-performance ITU-R physics engine.
- **`propogate.py`**: SGP4 Propagation Layer with async support.
- **`ground_stations.py`**: Single source of truth for station parameters.

## High-Performance Engineering
The simulator has transitioned from a scalar loop to a **vectorized matrix engine**:
- **NumPy Vectorization**: Link budget calculations are processed as matrix operations, achieving >10x speedup.
- **Async Concurrency**: `asyncio` is used to overlap CPU-intensive orbital calculations.
- **Multiprocessing**: Monte Carlo iterations are distributed across CPU cores using `ProcessPoolExecutor`.

## Simulation Workflow
1. **Initialize**: Load satellite TLEs and ground station parameters.
2. **Propagate**: Compute orbital states in bulk (standard) or concurrently (async).
3. **Link Budget**: Apply vectorized atmospheric models across the entire time series.
4. **Scoring**: Feed summary statistics into the XGBoost model.
5. **Display**: Render interactive plots and ranking tables in Streamlit.
