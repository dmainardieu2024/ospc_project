"""Shared-memory pool must reproduce the sequential baseline exactly."""

import os

import numpy as np

from calculations.parallel import result_digest
from calculations.parallel_shm import compute_shared
from calculations.simulate import Settings, compute


def main():
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            raise SystemExit(f"Set {name}=1 before starting Python.")
    settings = Settings(assets=7, days=20)
    scenarios, batch_size, seed = 1031, 128, 20261115   # 9 batches, last one partial
    allowed = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 2
    for model in ["normal", "crisis"]:
        baseline = compute(settings, scenarios, batch_size, seed, model)
        for workers in ([1, 2] if allowed >= 2 else [1]):
            result = compute_shared(settings, scenarios, batch_size, seed, model, workers)
            for got, expected in zip(result[:4], baseline[:4]):
                np.testing.assert_array_equal(got, expected)
            same = result_digest(result) == result_digest(baseline)
            print(f"PASS: {model}, shared memory, {workers} workers; byte-identical={same}")
    leftover = [f for f in os.listdir("/dev/shm") if f.startswith("psm_")]
    print("Leftover shared-memory blocks:", leftover or "none")


if __name__ == "__main__":
    main()