"""Compare every monthly output of each pool with the existing baseline."""

import os

import numpy as np

from calculations.parallel import compute_parallel, result_digest
from calculations.simulate import Settings, compute


def main():
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            raise SystemExit(f"Set {name}=1 before starting Python.")
    settings = Settings(assets=7, days=20)
    # Nine batches, including a partial final batch. More than one batch is
    # essential: a 1,000-scenario test with batch size 4,096 uses only one worker.
    scenarios, batch_size, seed = 1031, 128, 20261115
    allowed = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 2
    worker_counts = [1, 2] if allowed >= 2 else [1]
    for model in ["normal", "crisis"]:
        baseline = compute(settings, scenarios, batch_size, seed, model)
        for method in ["threads", "processes"]:
            for workers in worker_counts:
                result = compute_parallel(settings, scenarios, batch_size, seed,
                                          model, workers, method)
                # No cross-worker reduction occurs. Exact float equality is
                # expected in one environment; tight tolerance admits harmless
                # compiled-library roundoff, not a change of random scenarios.
                np.testing.assert_allclose(result[0], baseline[0], rtol=1e-12, atol=1e-12)
                np.testing.assert_allclose(result[1], baseline[1], rtol=1e-12, atol=1e-10)
                np.testing.assert_array_equal(result[2], baseline[2])
                np.testing.assert_allclose(result[3], baseline[3], rtol=1e-12, atol=1e-10)
                exact = result_digest(result) == result_digest(baseline)
                print(f"PASS: {model}, {method}, {workers} workers; byte-identical={exact}")
    print("All tested parallel outputs match the sequential baseline.")
    print("This checks correctness, not scaling performance.")
    if allowed < 2:
        print("Only one CPU was available. Repeat with >=2 CPUs to check multiple workers.")


if __name__ == "__main__":
    main()
