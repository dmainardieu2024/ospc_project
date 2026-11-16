"""Verify the proposed 64-million-month workload on a single cluster CPU."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np

from simulate import Settings, run


def inspect_saved_arrays(directory, scenarios, days):
    """Check every stored result in chunks and fingerprint baseline outputs."""
    digest = hashlib.sha256()
    files = [("crisis_drawdowns.npy", np.dtype("float64"), 0, 1),
             ("crisis_final_values.npy", np.dtype("float64"), 0, None),
             ("crisis_crisis_days.npy", np.dtype("int32"), 0, days)]
    for name, dtype, lower, upper in files:
        array = np.load(directory / name, mmap_mode="r", allow_pickle=False)
        if array.shape != (scenarios,) or array.dtype != dtype:
            raise ValueError(f"Unexpected shape or type in {name}")
        for start in range(0, scenarios, 1_000_000):
            chunk = array[start:start + 1_000_000]
            if not np.all(np.isfinite(chunk)) or np.any(chunk < lower):
                raise ValueError(f"Invalid results in {name}")
            if name == "crisis_final_values.npy" and np.any(chunk <= 0):
                raise ValueError("Portfolio values must remain positive")
            if upper is not None:
                invalid = chunk >= upper if name == "crisis_drawdowns.npy" else chunk > upper
                if np.any(invalid):
                    raise ValueError(f"Results exceed valid bounds in {name}")
            digest.update(memoryview(chunk).cast("B"))
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=int, default=64_000_000)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--assets", type=int, default=50)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--local-preview", action="store_true")
    args = parser.parse_args()
    if min(args.scenarios, args.batch_size, args.assets, args.days) < 1:
        parser.error("Counts must be positive")
    if not args.local_preview:
        if not os.environ.get("SLURM_JOB_ID") or len(os.sched_getaffinity(0)) != 1:
            parser.error("Submit through Slurm and pin the program to one logical CPU")
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            parser.error(f"Set {name}=1 before Python starts")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory must be empty")

    # Small unit checks already test the underlying model. This run establishes
    # the actual workload duration, saves full results, and checks their bounds.
    settings = Settings(assets=args.assets, days=args.days)
    summary = run(settings, args.scenarios, args.batch_size, args.seed,
                  "crisis", args.output, "binary")
    digest = inspect_saved_arrays(args.output, args.scenarios, args.days)
    verification = {
        "context": "local_preview" if args.local_preview else "single_cpu_cluster_batch",
        "scenarios": args.scenarios, "assets": args.assets, "days": args.days,
        "batch_size": args.batch_size, "seed": args.seed,
        "allowed_logical_cpus": sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "array_bounds_and_shapes_passed": True,
        "result_digest": digest,
        "compute_seconds": summary["path_generation_and_drawdown_seconds"],
        "ten_minute_workload_verified": not args.local_preview and summary["path_generation_and_drawdown_seconds"] >= 600,
        "source_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ["simulate.py", "full_baseline.py"]},
        "note": "One full-size qualification run, not five performance repetitions. Repeated full-size scaling is still required. This is not statistical uncertainty estimation or a complete independent model validation.",
    }
    (args.output / "baseline_verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(json.dumps(verification, indent=2), flush=True)
    if not args.local_preview and not verification["ten_minute_workload_verified"]:
        raise SystemExit("Results saved, but this size took under 10 minutes. Increase N before finalizing the workload.")


if __name__ == "__main__":
    main()
