#!/bin/bash
#SBATCH --job-name=crash-resume
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=64
#SBATCH --mem=16G
#SBATCH --time=08:00:00
#SBATCH --output=resume-scaling-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
export PATH="/data/software/envs/ospc/bin:${PATH}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export MPLCONFIGDIR="${SLURM_SUBMIT_DIR}/results/matplotlib-cache"

# Submit on haskell, then stop JupyterHub to release its 2-CPU allocation.
# A subsequent preemption can safely restart this resumption script.
output="${1:-results/full-scaling-30691}"
echo "Resuming ${output}; node $(hostname); job ${SLURM_JOB_ID}; restart ${SLURM_RESTART_COUNT:-0}"
python resume_scaling.py --output "${output}"
python plot_scaling.py "${output}"
