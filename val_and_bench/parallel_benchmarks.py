import time
import sys
import os
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timezone
from concurrent.futures import ProcessPoolExecutor

from satlinksim.satellite_link_sim import (
    simulate_all_batched, simulate_all_concurrent, run_monte_carlo,
    GROUND_STATIONS, DEFAULT_N_STEPS
)

def benchmark_concurrent_vs_batched():
    print("--- Concurrent vs. Batched Propagation Benchmark ---")
    n_steps = 10000
    n_trials = 5
    
    # Batched (Standard)
    batched_times = []
    for _ in range(n_trials):
        t0 = time.perf_counter()
        simulate_all_batched(GROUND_STATIONS, n_steps=n_steps)
        batched_times.append(time.perf_counter() - t0)
    avg_batched = np.mean(batched_times)
    
    # Concurrent (Async)
    concurrent_times = []
    for _ in range(n_trials):
        t0 = time.perf_counter()
        asyncio.run(simulate_all_concurrent(GROUND_STATIONS, n_steps=n_steps))
        concurrent_times.append(time.perf_counter() - t0)
    avg_concurrent = np.mean(concurrent_times)
    
    print(f"Batched Avg:    {avg_batched:.4f}s")
    print(f"Concurrent Avg: {avg_concurrent:.4f}s")
    print(f"Improvement:    {(avg_batched - avg_concurrent) / avg_batched * 100:.1f}%")
    
    return avg_batched, avg_concurrent

def benchmark_monte_carlo_scaling():
    print("\n--- Monte Carlo Scaling Benchmark ---")
    iteration_counts = [1, 2, 4, 8, 12, 16]
    n_steps = 5000
    
    sequential_times = []
    parallel_times = []
    
    for n_iter in iteration_counts:
        # Sequential baseline (simulated by running batched in a loop)
        t0 = time.perf_counter()
        for _ in range(n_iter):
            simulate_all_batched(GROUND_STATIONS, n_steps=n_steps)
        sequential_times.append(time.perf_counter() - t0)
        
        # Parallel (Multiprocessing)
        t0 = time.perf_counter()
        run_monte_carlo(n_iter, GROUND_STATIONS, n_steps=n_steps)
        parallel_times.append(time.perf_counter() - t0)
        
        speedup = sequential_times[-1] / parallel_times[-1]
        efficiency = speedup / n_iter
        print(f"Iter: {n_iter:2d} | Seq: {sequential_times[-1]:6.3f}s | Par: {parallel_times[-1]:6.3f}s | Speedup: {speedup:5.2f}x | Eff: {efficiency:5.2f}")
        
    return iteration_counts, sequential_times, parallel_times

def generate_parallel_plots(scaling_data, concurrent_data):
    print("\n--- Generating Parallel Benchmark Plots ---")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Scaling and Speedup
    iters, seq, par = scaling_data
    speedup = [s / p for s, p in zip(seq, par)]
    
    plt.figure(figsize=(12, 5))
    
    # Left: Execution Time
    plt.subplot(1, 2, 1)
    plt.plot(iters, seq, 'o--', label='Sequential', alpha=0.7)
    plt.plot(iters, par, 's-', label='Parallel (MP)', linewidth=2)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title("MC Execution Time")
    plt.xlabel("Iterations")
    plt.ylabel("Time (s)")
    
    # Right: Speedup
    plt.subplot(1, 2, 2)
    plt.plot(iters, speedup, 'd-', color='green', linewidth=2, label='Measured Speedup')
    plt.plot(iters, iters, 'k:', label='Ideal Scaling', alpha=0.5)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title("Monte Carlo Speedup")
    plt.xlabel("Number of Workers (Iterations)")
    plt.ylabel("Speedup Factor")
    
    plt.tight_layout()
    plt.savefig(os.path.join(base_dir, "bench_parallel_scaling.png"))
    
    # 2. Worker Efficiency
    efficiency = [s / (p * i) for s, p, i in zip(seq, par, iters)]
    plt.figure(figsize=(10, 4))
    plt.bar(iters, efficiency, color='skyblue', alpha=0.8)
    plt.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Ideal Efficiency')
    plt.title("Worker Efficiency (Multiprocessing)")
    plt.xlabel("Number of Workers")
    plt.ylabel("Efficiency Factor")
    plt.ylim(0, 1.2)
    plt.grid(axis='y', alpha=0.3)
    plt.savefig(os.path.join(base_dir, "bench_worker_efficiency.png"))
    
    print(f"Plots saved to {base_dir}")

if __name__ == "__main__":
    # Ensure we are in the right directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    c_data = benchmark_concurrent_vs_batched()
    s_data = benchmark_monte_carlo_scaling()
    generate_parallel_plots(s_data, c_data)
    
    print("\nParallel Benchmarks Completed.")
