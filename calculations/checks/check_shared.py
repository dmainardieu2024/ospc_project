"""Shared-memory pool must reproduce the sequential baseline exactly."""

import os
from multiprocessing import shared_memory

import numpy as np

from calculations.parallel import result_digest
from calculations.parallel_shm import compute_shared
from calculations.simulate import Settings, compute

created = []  # names of every block compute_shared creates during this test


class RecordingSharedMemory(shared_memory.SharedMemory):
    """Behaves like SharedMemory, but remembers the name of each new block."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if kwargs.get("create"):
            created.append(self.name)


def assert_removed(names):
    for name in names:
        try:
            leftover = shared_memory.SharedMemory(name=name)
        except FileNotFoundError:
            continue  # correctly unlinked
        leftover.close()
        raise AssertionError(f"Shared-memory block {name} was not removed")


def main():
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            raise SystemExit(f"Set {name}=1 before starting Python.")
    settings = Settings(assets=7, days=20)
    scenarios, batch_size, seed = 1031, 128, 20261115   # 9 batches, last one partial
    allowed = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else 2
    original = shared_memory.SharedMemory
    shared_memory.SharedMemory = RecordingSharedMemory
    try:
        for model in ["normal", "crisis"]:
            baseline = compute(settings, scenarios, batch_size, seed, model)
            for workers in ([1, 2] if allowed >= 2 else [1]):
                created.clear()
                result = compute_shared(settings, scenarios, batch_size, seed, model, workers)
                for got, expected in zip(result[:4], baseline[:4]):
                    np.testing.assert_array_equal(got, expected)
                same = result_digest(result) == result_digest(baseline)
                assert len(created) == 3, f"expected 3 blocks, recorded {len(created)}"
                assert_removed(created)
                print(f"PASS: {model}, shared memory, {workers} workers; "
                      f"byte-identical={same}; 3 blocks created and removed")
    finally:
        shared_memory.SharedMemory = original
    print("All shared-memory outputs match the sequential baseline; no blocks left behind.")


if __name__ == "__main__":
    main()