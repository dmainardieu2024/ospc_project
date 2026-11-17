#!/bin/bash
#SBATCH --job-name=crash-normal
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:45:00
#SBATCH --output=normal-comparison-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

root="results/financial_comparison/job-${SLURM_JOB_ID}"
mkdir -p "${root}"
first_cpu=$(python -c 'import os; print(min(os.sched_getaffinity(0)))')
echo "Node: $(hostname), job: ${SLURM_JOB_ID}, pinned CPU: ${first_cpu}"
/usr/bin/time -v -o "${root}/resources.txt" \
    taskset -c "${first_cpu}" python -m calculations.simulate \
    --model normal --scenarios 64000000 --batch-size 4096 \
    --assets 50 --days 20 --seed 20261115 --output "${root}/data"

python -m calculations.layout "${root}"
