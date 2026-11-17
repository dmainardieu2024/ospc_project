"""Choose a production size using sequential, one-core cluster pilot timings."""

import argparse
import csv
import json
import math
import os
import socket
import statistics
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path

from calculations.simulate import Settings, compute


def choose_count(seconds_per_scenario, target_seconds, batch_size, maximum):
    count = max(100_000, math.ceil(target_seconds / seconds_per_scenario))
    count = math.ceil(count / batch_size) * batch_size
    if count > maximum:
        raise ValueError(
            f"Estimated size {count:,} exceeds the {maximum:,} scenario safety cap. "
            "Review workload dimensions/resources instead of allocating more automatically.")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", type=int, default=50)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=4096)
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--target-seconds", type=float, default=900)
    parser.add_argument("--maximum-scenarios", type=int, default=100_000_000)
    parser.add_argument("--output", type=Path, default=Path("results/calibration"))
    parser.add_argument("--local-preview", action="store_true",
                        help="Development only; output cannot establish a final cluster size.")
    args = parser.parse_args()
    if min(args.assets, args.days, args.batch_size, args.maximum_scenarios) < 1:
        parser.error("Counts must be positive.")
    if args.target_seconds < 600:
        parser.error("Production target must be at least 600 seconds.")
    if not args.local_preview and not os.environ.get("SLURM_JOB_ID"):
        parser.error("Submit as a Slurm job, or use --local-preview for development only.")
    # One logical CPU guarantees the pilots have at most one physical core.
    if not args.local_preview and len(os.sched_getaffinity(0)) != 1:
        parser.error("Calibration needs exactly one allowed logical CPU; use taskset in the job script.")
    for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(variable) != "1":
            parser.error(f"Set {variable}=1 before starting Python.")
    if (args.output / "plan.json").exists():
        parser.error("Calibration already exists; choose a new --output directory.")

    settings = Settings(days=args.days, assets=args.assets)
    # The same scenario set and batch size are reused across timed repetitions.
    compute(settings, min(args.batch_size, 4096), args.batch_size, args.seed, "crisis")
    rows = []
    rates = []
    args.output.mkdir(parents=True, exist_ok=True)
    for scenarios in [4 * args.batch_size, 16 * args.batch_size]:
        times = []
        for repetition in range(1, 6):
            start_load = list(os.getloadavg())
            result = compute(settings, scenarios, args.batch_size, args.seed, "crisis")
            seconds = result[-1]
            del result
            times.append(seconds)
            rows.append({
                "version": "sequential_crisis", "workers": 1,
                "problem_size": scenarios, "assets": args.assets, "days": args.days,
                "batch_size": args.batch_size, "repetition": repetition,
                "elapsed_seconds": seconds, "node": socket.gethostname(),
                "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local_preview"),
                "date_utc": datetime.now(timezone.utc).isoformat(),
                "load1_at_start": start_load[0], "load5_at_start": start_load[1],
                "load15_at_start": start_load[2],
            })
            print(f"Pilot {scenarios:,}, repeat {repetition}: {seconds:.3f}s", flush=True)
        rates.append(statistics.median(times) / scenarios)

    with (args.output / "pilot_timings.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    # Use the faster median rate to reduce the chance of undersizing the full run.
    seconds_per_scenario = min(rates)
    scenarios = choose_count(seconds_per_scenario, args.target_seconds,
                             args.batch_size, args.maximum_scenarios)
    plan = {
        "status": "local_preview_only" if args.local_preview else "cluster_calibrated_estimate",
        "scenarios_per_model": scenarios, "assets": args.assets, "days": args.days,
        "batch_size": args.batch_size, "seed": args.seed,
        "settings": asdict(settings),
        "target_compute_seconds_per_model": args.target_seconds,
        "estimated_crisis_compute_seconds": scenarios * seconds_per_scenario,
        "nominal_candidate_before_calibration": 64_000_000,
        "array_storage_bytes_per_model": scenarios * 20,
        "asset_day_updates_per_model": scenarios * args.assets * args.days,
        "note": "Estimate only. Confirm >=600 seconds in the actual one-core full run; otherwise increase N and rerun.",
    }
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    print(json.dumps(plan, indent=2))


if __name__ == "__main__":
    main()
