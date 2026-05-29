# Benchmark Results

Performance is measured across three primary dimensions: throughput, scaling, and memory efficiency.

## 1. Simulation Throughput
The engine achieves approximately **60,000 timesteps/sec** for sequential vectorized execution. With multiprocessing enabled for Monte Carlo analysis, aggregate throughput scales to over **130,000 timesteps/sec**.

## 2. Propagation Latency
Individual SGP4 propagation calls average **18 microseconds (µs)** per step. Batch propagation reduces this overhead significantly via optimized orbital kernels.

## 3. Parallel Scaling Analysis
The system demonstrates strong speedup for Monte Carlo iterations:
- **Speedup**: ~2.5x speedup for typical workloads using multiprocessing (12 workers).
- **Efficiency**: Peak efficiency of ~60% observed at low worker counts.

## 4. Memory Efficiency
A 500,000-step simulation consumes approximately **122 MB** of RAM. Memory is fully reclaimed after garbage collection.
