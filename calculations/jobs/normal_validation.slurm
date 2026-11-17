#!/bin/bash
#SBATCH --job-name=normal-validation
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=normal-validation-%j.out
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
root="results/mathematical_check/job-${SLURM_JOB_ID}"
mkdir -p "$root"
/usr/bin/time -v -o "$root/resources.txt" python -m calculations.checks.validate_normal \
  --scenarios 1000000 --seed 11 22 33 --batch-size 4096 \
  --output "$root/validation.csv"

python -m calculations.layout "${root}"
