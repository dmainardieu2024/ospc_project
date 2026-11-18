#!/bin/bash
#SBATCH --job-name=parameter-sensitivity
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:15:00
#SBATCH --output=parameter-sensitivity-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
root="results/parameter_sensitivity/job-${SLURM_JOB_ID}"
mkdir -p "${root}/run_details"
python -m calculations.checks.check
/usr/bin/time -v -o "${root}/run_details/resources.txt" \
  python -m calculations.parameter_sensitivity --scenarios 262144 --batch-size 4096 \
  --seeds 101 202 303 404 505 --output "${root}/measurements"
