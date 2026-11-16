#!/bin/bash
#SBATCH --job-name=crash-full-scale
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=64
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=full-scaling-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export MPLCONFIGDIR="${SLURM_SUBMIT_DIR}/results/matplotlib-cache"

# Submit once, then stop JupyterHub to release its 2-CPU allocation. This job
# uses the whole 64-CPU student allowance. Closing a browser tab is not enough.
echo "Node: $(hostname), job: ${SLURM_JOB_ID}, logical CPUs: ${SLURM_CPUS_PER_TASK}"
python check_parallel.py
output="results/full-scaling-${SLURM_JOB_ID}"
python benchmark.py --scenarios 64000000 --batch-size 4096 \
    --assets 50 --days 20 --seed 20261115 \
    --workers 1 2 4 8 16 32 --repeats 5 --output "${output}"
python plot_scaling.py "${output}"
