"""Continue an interrupted benchmark without repeating complete CSV rows.

Run in a Slurm allocation. Existing measurements remain unchanged; new rows
identify the new job. Resumption spans allocations and must be disclosed.
"""

import argparse
import csv
import fcntl
import hashlib
import json
import math
import os
import random
import socket
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from benchmark import cpu_seconds
from parallel import compute_parallel, result_digest
from simulate import Settings, compute


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_metadata(path, metadata):
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2) + "\n")
    temporary.replace(path)


def validated_rows(metadata, csv_path):
    """Reject partial, duplicate, incompatible or failed measurements."""
    configurations = [("sequential", 1)] + [
        (method, workers) for method in dict.fromkeys(metadata["methods"])
        for workers in sorted(set(metadata["workers"]))]
    expected = {(method, workers, repetition)
                for repetition in range(1, metadata["repeats"] + 1)
                for method, workers in configurations}
    if not csv_path.read_bytes().endswith(b"\n"):
        raise ValueError("CSV ends with a partial row; preserve it for manual recovery")
    with csv_path.open(newline="") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames
        rows = list(reader)
    seen = set()
    digests = set()
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("CSV contains an incomplete row")
        key = (row["version"], int(row["workers"]), int(row["repetition"]))
        if key not in expected or key in seen:
            raise ValueError("Unexpected or duplicate measurement: " + str(key))
        for field, target in [
            ("problem_size", metadata["scenarios"]),
            ("assets", metadata["settings"]["assets"]),
            ("days", metadata["settings"]["days"]),
            ("batch_size", metadata["batch_size"]), ("seed", metadata["seed"])]:
            if int(row[field]) != target:
                raise ValueError("CSV settings differ from metadata: " + field)
        elapsed = float(row["elapsed_seconds"])
        if row["correct"] != "True" or not math.isfinite(elapsed) or elapsed <= 0:
            raise ValueError("Incorrect result or invalid timing in saved CSV")
        if row["node"] != metadata["node"]:
            raise ValueError("Saved CSV contains measurements from a different node")
        digest = row["result_digest"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Invalid saved result digest")
        digests.add(digest)
        seen.add(key)
    if not rows or len(digests) != 1:
        raise ValueError("Need consistent, nonempty validated measurements to resume")
    return fields, rows, configurations, expected, seen, digests.pop()


def resume(directory, local_preview=False):
    # Linux releases this lock when a preempted process exits. Prevent two
    # simultaneous allocations from appending to the same experiment.
    with (directory / "resume.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        metadata_path = directory / "metadata.json"
        csv_path = directory / "timings.csv"
        metadata = json.loads(metadata_path.read_text())
        fields, rows, configurations, expected, seen, expected_digest = validated_rows(metadata, csv_path)
        if metadata["model"] != "crisis" or metadata["repeats"] < 5:
            raise ValueError("Only the existing crisis strong-scaling experiment is supported")
        if metadata["context"] != ("local_preview" if local_preview else "cluster_batch"):
            raise ValueError("Cannot mix local and cluster measurements")
        if not local_preview and not os.environ.get("SLURM_JOB_ID"):
            raise ValueError("Submit resumption with Slurm")
        if socket.gethostname() != metadata["node"]:
            raise ValueError("Resume on the original node: " + metadata["node"])
        if np.__version__ != metadata["numpy_version"]:
            raise ValueError("NumPy version differs from original experiment")
        import platform
        if platform.python_version() != metadata["python_version"]:
            raise ValueError("Python version differs from original experiment")
        allowed = sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else []
        if not local_preview and len(allowed) < 2 * max(metadata["workers"]):
            raise ValueError("Request 2 logical CPUs per maximum worker")
        for name in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
            if os.environ.get(name) != "1":
                raise ValueError("Set " + name + "=1")
        for name, original_hash in metadata["source_sha256"].items():
            actual = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            if actual != original_hash:
                raise ValueError("Source changed since original measurements: " + name)
        if seen == expected and metadata.get("status") == "completed":
            print("All measurements already completed; nothing to repeat.", flush=True)
            return
        # Keep exact originals in addition to the append-only measurements.
        backup = directory / "before-resumption"
        backup.mkdir(exist_ok=True)
        for source in [metadata_path, csv_path]:
            target = backup / source.name
            if not target.exists():
                with target.open("xb") as file:
                    file.write(source.read_bytes())
        metadata["status"] = "in_progress"
        metadata["resumption_note"] = (
            "Interrupted by Slurm preemption; measurements span allocations. "
            "Not an uninterrupted single-allocation experiment. "
            "See each CSV row and resume_attempts for job IDs and CPU affinity.")
        attempt = {
            "job_id": os.environ.get("SLURM_JOB_ID"), "node": socket.gethostname(),
            "started_utc": utc_now(), "allowed_logical_cpus": allowed,
            "completed_measurements_at_start": len(rows),
            "resume_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        metadata.setdefault("resume_attempts", []).append(attempt)
        save_metadata(metadata_path, metadata)
        print(f"Preserved {len(seen)} of {len(expected)} measurements; {len(expected - seen)} remain.", flush=True)
        settings = Settings(**metadata["settings"])
        print("Checking a fresh sequential reference against saved result digests...", flush=True)
        reference = compute(settings, metadata["scenarios"], metadata["batch_size"], metadata["seed"], "crisis")
        if result_digest(reference) != expected_digest:
            raise ValueError("Fresh reference does not match saved measurements")
        del reference
        with csv_path.open("a", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            for repetition in range(1, metadata["repeats"] + 1):
                order = configurations.copy()
                random.Random(metadata["seed"] + repetition).shuffle(order)
                for method, workers in order:
                    if (method, workers, repetition) in seen:
                        continue
                    load = os.getloadavg()
                    date = utc_now()
                    before_cpu = cpu_seconds()
                    args = (settings, metadata["scenarios"], metadata["batch_size"], metadata["seed"], "crisis")
                    result = compute(*args) if method == "sequential" else compute_parallel(*args, workers, method)
                    used_cpu = cpu_seconds() - before_cpu
                    elapsed = result[-1]
                    begin = time.perf_counter()
                    digest = result_digest(result)
                    validation_seconds = time.perf_counter() - begin
                    del result
                    if digest != expected_digest:
                        raise ValueError("New result differs from original reference; stopping before append")
                    row = dict(zip(fields, [
                        method, workers, metadata["scenarios"], settings.assets, settings.days,
                        metadata["batch_size"], metadata["seed"], repetition, elapsed, used_cpu,
                        validation_seconds, True, digest, socket.gethostname(),
                        os.environ.get("SLURM_JOB_ID"), date, *load, os.getloadavg()[0]]))
                    writer.writerow(row)
                    file.flush()
                    os.fsync(file.fileno())
                    rows.append(row)
                    print(f"repeat {repetition}: {method:10s} {workers:2d} workers, {elapsed:.3f}s, correct=True", flush=True)
        validated_rows(metadata, csv_path)
        median = statistics.median(float(r["elapsed_seconds"]) for r in rows if r["version"] == "sequential")
        metadata["sequential_median_seconds"] = median
        metadata["sequential_median_at_least_10_minutes"] = median >= 600
        metadata["status"] = "completed"
        metadata["completed_utc"] = utc_now()
        attempt["completed_utc"] = utc_now()
        save_metadata(metadata_path, metadata)
        print("Completed all measurements. Original rows preserved; new rows identify the resumption job.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--local-preview", action="store_true")
    parser.add_argument("--inspect", action="store_true",
                        help="Check saved measurements and source hashes without running simulations")
    args = parser.parse_args()
    if args.inspect:
        metadata = json.loads((args.output / "metadata.json").read_text())
        _, rows, _, expected, seen, _ = validated_rows(metadata, args.output / "timings.csv")
        for name, original_hash in metadata["source_sha256"].items():
            actual = hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            if actual != original_hash:
                raise ValueError("Source changed since original measurements: " + name)
        print(f"PASS: {len(rows)} saved measurements validated; source hashes match.")
        print(f"{len(expected - seen)} of {len(expected)} measurements remain. No simulations run.")
    else:
        resume(args.output, args.local_preview)
