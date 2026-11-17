#!/bin/bash
#SBATCH --job-name=crash-full-base
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=full-baseline-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

first_cpu=$(python -c 'import os; print(min(os.sched_getaffinity(0)))')
root="results/one_cpu_baseline/job-${SLURM_JOB_ID}"
mkdir -p "${root}"
echo "Node: $(hostname), job: ${SLURM_JOB_ID}, pinned logical CPU: ${first_cpu}"
taskset -c "${first_cpu}" python -m calculations.checks.check
/usr/bin/time -v -o "${root}/resource_usage.txt" \
    taskset -c "${first_cpu}" python -m calculations.checks.full_baseline \
    --scenarios 64000000 --batch-size 4096 --assets 50 --days 20 \
    --output "${root}/data"

python -m calculations.layout "${root}"
