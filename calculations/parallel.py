"""Run the existing monthly simulation using a thread pool or a process pool.

Every execution method uses the same batch sizes and SeedSequence children.
Only the execution changes; the financial model and arithmetic do not.
"""

import argparse
import hashlib
import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

import numpy as np

from calculations.simulate import Settings, simulate_batch


def batch_task(task):
    """A top-level function so that process workers can import it."""
    start, count, batch_seed, settings, model = task
    values, drawdowns, crisis_days = simulate_batch(settings, count, batch_seed, model)
    examples = values[:5].copy() if start == 0 else None
    # Return monthly summaries, not every daily path from every worker.
    return start, drawdowns, values[:, -1].copy(), crisis_days, examples


def compute_parallel(settings, scenarios, batch_size, seed, model, workers, method):
    if method not in {"threads", "processes"}:
        raise ValueError("method must be threads or processes")
    if min(scenarios, batch_size, workers) < 1:
        raise ValueError("Counts must be positive")
    if hasattr(os, "sched_getaffinity") and workers > len(os.sched_getaffinity(0)):
        raise ValueError("Worker count exceeds the logical CPUs allowed to this job")

    begin = time.perf_counter()
    drawdowns = np.empty(scenarios)
    final_values = np.empty(scenarios)
    crisis_days = np.empty(scenarios, dtype=np.int32)
    example_paths = None
    batches = (scenarios + batch_size - 1) // batch_size
    batch_seeds = np.random.SeedSequence(seed).spawn(batches)
    tasks = ((batch_id * batch_size,
              min(batch_size, scenarios - batch_id * batch_size),
              batch_seed, settings, model)
             for batch_id, batch_seed in enumerate(batch_seeds))
    if method == "threads":
        executor = ThreadPoolExecutor(max_workers=workers)
    else:
        # Explicit spawn gives the same start method on Linux and macOS and
        # avoids inheriting numerical-library thread state from the parent.
        executor = ProcessPoolExecutor(max_workers=workers,
                                       mp_context=multiprocessing.get_context("spawn"))
    with executor:
        # map preserves batch order. Each output slice is written by the parent
        # once; no concurrent shared counter or floating-point reduction.
        for start, batch_drawdowns, batch_values, batch_days, examples in executor.map(
                batch_task, tasks, chunksize=1):
            stop = start + len(batch_drawdowns)
            drawdowns[start:stop] = batch_drawdowns
            final_values[start:stop] = batch_values
            crisis_days[start:stop] = batch_days
            if start == 0:
                example_paths = examples
    elapsed = time.perf_counter() - begin
    # Includes output allocation, seed preparation, pool start/stop, transfers,
    # simulation, and gathering. Excludes risk statistics and disk output.
    return drawdowns, final_values, crisis_days, example_paths, elapsed


def result_digest(result):
    digest = hashlib.sha256()
    for array in result[:3]:
        digest.update(np.ascontiguousarray(array).tobytes())
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", choices=["threads", "processes"], required=True)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--scenarios", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--assets", type=int, default=50)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--model", choices=["normal", "crisis"], default="crisis")
    args = parser.parse_args()
    if min(args.workers, args.scenarios, args.batch_size, args.assets, args.days) < 1:
        parser.error("Counts must be positive")
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            parser.error(f"Set {name}=1 before starting Python")
    settings = Settings(days=args.days, assets=args.assets)
    result = compute_parallel(settings, args.scenarios, args.batch_size, args.seed,
                              args.model, args.workers, args.method)
    drawdowns = result[0]
    tail_count = max(1, int(np.ceil(0.01 * args.scenarios)))
    tail = np.partition(drawdowns, args.scenarios - tail_count)[-tail_count:]
    print(json.dumps({
        "method": args.method, "workers": args.workers, "model": args.model,
        "scenarios": args.scenarios, "assets": args.assets, "days": args.days,
        "batch_size": args.batch_size, "seed": args.seed,
        "compute_seconds_including_pool": result[-1],
        "drawdown_99th_percentile": float(np.quantile(drawdowns, 0.99)),
        "mean_drawdown_worst_one_percent": float(tail.mean()),
        "result_digest": result_digest(result),
        "note": "Development output. Use repeated batch experiments for performance claims.",
    }, indent=2))


if __name__ == "__main__":
    main()
