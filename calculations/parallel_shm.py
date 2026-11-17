"""Process pool whose workers write results straight into shared memory."""

import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import shared_memory

import numpy as np

from calculations.simulate import simulate_batch

# (name, dtype) of every output array; the order matches the sequential compute().
OUTPUTS = [("drawdowns", np.float64), ("final_values", np.float64),
           ("crisis_days", np.int32)]

_blocks = []   # keeps each worker's SharedMemory objects alive
_arrays = {}   # this worker's NumPy views of the shared blocks


def attach(block_names, scenarios):
    """Pool initializer: runs once per worker, before its first task."""
    for (name, dtype), block_name in zip(OUTPUTS, block_names):
        block = shared_memory.SharedMemory(name=block_name)
        _blocks.append(block)
        _arrays[name] = np.ndarray((scenarios,), dtype=dtype, buffer=block.buf)


def shm_task(task):
    start, count, batch_seed, settings, model = task
    values, drawdowns, crisis_days = simulate_batch(settings, count, batch_seed, model)
    stop = start + count
    _arrays["drawdowns"][start:stop] = drawdowns
    _arrays["final_values"][start:stop] = values[:, -1]
    _arrays["crisis_days"][start:stop] = crisis_days
    return values[:5].copy() if start == 0 else None


def compute_shared(settings, scenarios, batch_size, seed, model, workers):
    if min(scenarios, batch_size, workers) < 1:
        raise ValueError("Counts must be positive")
    if hasattr(os, "sched_getaffinity") and workers > len(os.sched_getaffinity(0)):
        raise ValueError("Worker count exceeds the logical CPUs allowed to this job")

    begin = time.perf_counter()
    blocks = []
    try:
        for name, dtype in OUTPUTS:
            blocks.append(shared_memory.SharedMemory(
                create=True, size=scenarios * np.dtype(dtype).itemsize))
        batches = (scenarios + batch_size - 1) // batch_size
        batch_seeds = np.random.SeedSequence(seed).spawn(batches)
        tasks = ((batch_id * batch_size,
                  min(batch_size, scenarios - batch_id * batch_size),
                  batch_seed, settings, model)
                 for batch_id, batch_seed in enumerate(batch_seeds))
        executor = ProcessPoolExecutor(
            max_workers=workers, mp_context=multiprocessing.get_context("spawn"),
            initializer=attach, initargs=([b.name for b in blocks], scenarios))
        example_paths = None
        with executor:
            for examples in executor.map(shm_task, tasks, chunksize=1):
                if examples is not None:
                    example_paths = examples
        # Copy out before unlinking: the views die with the blocks.
        results = [np.ndarray((scenarios,), dtype=dtype, buffer=block.buf).copy()
                   for (name, dtype), block in zip(OUTPUTS, blocks)]
    finally:
        for block in blocks:
            block.close()
            block.unlink()
    elapsed = time.perf_counter() - begin
    drawdowns, final_values, crisis_days = results
    return drawdowns, final_values, crisis_days, example_paths, elapsed