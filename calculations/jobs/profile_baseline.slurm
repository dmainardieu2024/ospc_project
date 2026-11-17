#!/bin/bash
#SBATCH --job-name=crash-profile
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=profile-baseline-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

root="results/profiling/job-${SLURM_JOB_ID}"
mkdir -p "${root}"
first_cpu=$(python -c 'import os; print(min(os.sched_getaffinity(0)))')
echo "Node: $(hostname), job: ${SLURM_JOB_ID}, pinned CPU: ${first_cpu}"
# Profiling is diagnostic work at a smaller size, not a replacement for the
# separately measured full-size performance baseline.
/usr/bin/time -v -o "${root}/resources.txt" \
    taskset -c "${first_cpu}" python -m cProfile -o "${root}/baseline.pstats" \
    -m calculations.simulate --model crisis --scenarios 1048576 --batch-size 4096 \
    --assets 50 --days 20 --seed 20261115 --output "${root}/data"

python - "${root}" <<'PY'
import json
import pstats
import sys
from pathlib import Path

root = Path(sys.argv[1])
with (root / "top25.txt").open("w") as report:
    stats = pstats.Stats(str(root / "baseline.pstats"), stream=report)
    stats.strip_dirs().sort_stats("cumulative").print_stats(25)
    stats.sort_stats("tottime").print_stats(25)

stats = pstats.Stats(str(root / "baseline.pstats"))
batch_seconds = sum(value[3] for key, value in stats.stats.items()
                    if key[2] == "simulate_batch" and key[0].endswith("simulate.py"))
summary = json.loads((root / "data/crisis_summary.json").read_text())
compute_seconds = summary["path_generation_and_drawdown_seconds"]
(root / "profile_summary.json").write_text(json.dumps({
    "profiled_compute_seconds": compute_seconds,
    "simulate_batch_cumulative_seconds": batch_seconds,
    "rough_non_batch_fraction": (compute_seconds - batch_seconds) / compute_seconds,
    "caution": "Diagnostic estimate only. Profiler overhead and timer boundaries affect it. Native NumPy calls hide internal work. Do not sum overlapping cumulative times or claim this explains all parallel overhead.",
}, indent=2) + "\n")
PY

python -m calculations.layout "${root}"
