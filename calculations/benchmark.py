"""Repeated strong scaling, with one sequential reference and fixed scenarios."""

import argparse
import csv
import hashlib
import json
import os
import platform
import random
import resource
import socket
import statistics
import subprocess
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from calculations.parallel import compute_parallel, result_digest
from calculations.parallel_shm import compute_shared
from calculations.simulate import Settings, compute


def cpu_seconds():
    own = resource.getrusage(resource.RUSAGE_SELF)
    children = resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=int, default=2_097_152)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--assets", type=int, default=50)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--workers", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    parser.add_argument("--methods", nargs="+", choices=["threads", "processes", "shared"],
                        default=["threads", "processes"])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--local-preview", action="store_true")
    args = parser.parse_args()
    if min(args.scenarios, args.batch_size, args.assets, args.days, *args.workers) < 1:
        parser.error("All sizes and worker counts must be positive")
    if args.repeats < 5:
        parser.error("At least five repetitions are required")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory must be empty")
    if not args.local_preview and not os.environ.get("SLURM_JOB_ID"):
        parser.error("Submit with Slurm; --local-preview is only for development")
    allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else []
    if not args.local_preview and len(allowed) < 2 * max(args.workers):
        parser.error("This cluster has two logical CPUs per core: request 2 CPUs per worker")
    for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(name) != "1":
            parser.error(f"Set {name}=1 before starting Python")

    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings(assets=args.assets, days=args.days)
    metadata = {
        "context": "local_preview" if args.local_preview else "cluster_batch",
        "experiment": "first_strong_scaling", "model": "crisis",
        "settings": asdict(settings), "scenarios": args.scenarios,
        "batch_size": args.batch_size, "seed": args.seed,
        "workers": args.workers, "methods": args.methods, "repeats": args.repeats,
        "node": socket.gethostname(), "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_job_name": os.environ.get("SLURM_JOB_NAME"),
        "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "allowed_logical_cpus": allowed, "numpy_version": np.__version__,
        "python_version": platform.python_version(),
        "source_sha256": {
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ["simulate.py", "parallel.py", "parallel_shm.py", "benchmark.py"]
        },
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "timing_boundary": "allocation + seeds + pool lifecycle + simulation + gathering; excludes validation, statistics and disk output",
        "input_loading_seconds": 0,
        "workload_output_writing_seconds": 0,
        "note": "Synthetic input is generated inside the timed computation. Only timings are saved here, not full scenario datasets. Five repeats reuse the same scenarios; they do not estimate statistical sampling uncertainty.",
    }
    try:
        metadata["cpu_topology_lscpu"] = subprocess.check_output(
            ["lscpu", "-p=CPU,CORE,SOCKET"], text=True)
    except (OSError, subprocess.CalledProcessError):
        metadata["cpu_topology_lscpu"] = None
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    # One unreported sequential run supplies the full-workload correctness
    # reference and warms up this parent process. Worker starts remain timed.
    reference = compute(settings, args.scenarios, args.batch_size, args.seed, "crisis")
    expected_digest = result_digest(reference)
    del reference
    configurations = [("sequential", 1)] + [
        (method, workers) for method in dict.fromkeys(args.methods)
        for workers in sorted(set(args.workers))]
    fields = ["version", "workers", "problem_size", "assets", "days", "batch_size",
              "seed", "repetition", "elapsed_seconds", "cpu_seconds",
              "validation_seconds", "correct", "result_digest", "node",
              "slurm_job_id", "date_utc", "load1_at_start", "load5_at_start",
              "load15_at_start", "load1_at_end"]
    sequential_times = []
    with (args.output / "timings.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for repetition in range(1, args.repeats + 1):
            order = configurations.copy()
            random.Random(args.seed + repetition).shuffle(order)
            for method, workers in order:
                load = os.getloadavg()
                date = datetime.now(timezone.utc).isoformat()
                before_cpu = cpu_seconds()
                if method == "sequential":
                    result = compute(settings, args.scenarios, args.batch_size, args.seed, "crisis")
                elif method == "shared":
                    result = compute_shared(settings, args.scenarios, args.batch_size,
                                            args.seed, "crisis", workers)
                else:
                    result = compute_parallel(settings, args.scenarios, args.batch_size,
                                              args.seed, "crisis", workers, method)
                used_cpu = cpu_seconds() - before_cpu
                elapsed = result[-1]
                validation_start = time.perf_counter()
                digest = result_digest(result)
                correct = digest == expected_digest
                validation_seconds = time.perf_counter() - validation_start
                del result
                writer.writerow(dict(zip(fields, [
                    method, workers, args.scenarios, args.assets, args.days, args.batch_size,
                    args.seed, repetition, elapsed, used_cpu, validation_seconds,
                    correct, digest, metadata["node"], metadata["slurm_job_id"], date,
                    load[0], load[1], load[2], os.getloadavg()[0]])))
                file.flush()
                print(f"repeat {repetition}: {method:10s} {workers:2d} workers, "
                      f"{elapsed:.3f}s, correct={correct}", flush=True)
                if not correct:
                    raise RuntimeError("Full-workload output differs from baseline; do not report speedup")
                if method == "sequential":
                    sequential_times.append(elapsed)
    metadata["sequential_median_seconds"] = statistics.median(sequential_times)
    metadata["sequential_median_at_least_10_minutes"] = statistics.median(sequential_times) >= 600
    metadata["status"] = "completed"
    metadata["completed_utc"] = datetime.now(timezone.utc).isoformat()
    (args.output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Saved repeated timings to {args.output}")


if __name__ == "__main__":
    main()
