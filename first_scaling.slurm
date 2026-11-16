#!/bin/bash
#SBATCH --job-name=crash-scaling
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=64
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=first-scaling-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export MPLCONFIGDIR="${SLURM_SUBMIT_DIR}/results/matplotlib-cache"

echo "Node: $(hostname), job: ${SLURM_JOB_ID}, logical CPUs: ${SLURM_CPUS_PER_TASK}"
python check_parallel.py
output="results/scaling-${SLURM_JOB_ID}"
python benchmark.py --scenarios 2097152 --batch-size 4096 \
    --workers 1 2 4 8 16 32 --repeats 5 --output "${output}"
python plot_scaling.py "${output}"
