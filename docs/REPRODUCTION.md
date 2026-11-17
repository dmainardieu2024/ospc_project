# Reproduction check (package A)

**Who:** Mia Marcelli
**When:** Monday 16 November 2026, 12:40 CET
**Where:** cluster account pc75, node haskell, interactive JupyterLab session (2 CPUs)
**Source:** ZIP of the `main` branch downloaded from GitHub on 16 November 2026 (no Git history)
**Environment:** Python 3.12.15, NumPy 2.5.4 (`/data/software/envs/ospc/bin/python`), the same versions as the
earlier runs in PROJECT_LOG.md.

## What I did

```bash
cd ~
unzip -q ospc_project-main.zip
cd ospc_project-main
export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

mkdir -p results/teammate_reproduction
python -m calculations.checks.check > results/teammate_reproduction/check_outputs/check.txt 2>&1
python -m calculations.checks.check_parallel > results/teammate_reproduction/check_outputs/check_parallel.txt 2>&1
python -m calculations.simulate --scenarios 1000 --batch-size 4096 --output results/teammate_reproduction/demo > results/teammate_reproduction/check_outputs/demo.txt 2>&1
python -m calculations.plot_scaling archive/preliminary_scaling
```

All commands finished in about a minute in the 2-CPU JupyterLab session. No new Slurm jobs were submitted.

## Results

**check.py: PASS.** Hand-calculated drawdowns, flat market, disabled crises, repeatability, batch ordering, forced
crises, positive values, drawdown bounds, binary outputs, tail summaries, output protection and production-size
selection.

**check_parallel.py: PASS, 8 of 8.** Normal and crisis models, threads and processes, 1 and 2 workers. Every
output was byte-identical to the sequential baseline. Only 1 and 2 workers were tested because the
JupyterLab session has 2 CPUs.

**Demo (1,000 months, seed 20261115).** My results are identical to the ones recorded in PROJECT_LOG.md from
Diego's account:

| Statistic | Normal | Crisis |
|---|---:|---:|
| 99th percentile of maximum drawdown | 6.5199% | 15.7697% |
| Mean maximum drawdown in the worst 1% | 7.2408% | 18.5853% |
| Fraction of months with drawdown above 20% | 0% | 0.2% |
| Fraction of months with crisis days | 0% | 19% |

The example paths in `crisis_example_paths.csv` start at EUR 100,000 on day 0 and have 20 daily values, as
expected.

**Scaling plot (job 30338): PASS.** `plot_scaling.py` rebuilt `strong_scaling.png`, `strong_scaling.pdf` and
`scaling_summary.csv` from the saved `timings.csv` without rerunning any simulation (the three files show a new
modification time, while `timings.csv` and `metadata.json` are unchanged). The redrawn graph matches the one in
the repository. Note that the script overwrites these three files in place.

## Problems and corrections

1. **Files missing from GitHub.** README.md and TEAM_TASKS.md refer to `profile_baseline.slurm`,
   `normal_comparison.slurm` and `prepare_full.slurm`, but they are not in the repository. Packages B and D
   cannot start until they are pushed.
2. **Out-of-date message in check.py.** Its last line says "Still required: analytical normal-return benchmark
   and parallel equivalence tests". The parallel equivalence tests now exist (`check_parallel.py`) and pass;
   only the analytical benchmark is still missing (package C).
3. **Opening the ZIP in JupyterLab.** Double-clicking the uploaded ZIP in the file browser gives a
   "not UTF-8 encoded" error. This is harmless: unzip it in the terminal instead. Worth one line in the README.
4. **Equivalence check covers only 1 and 2 workers.** It would be stronger with 4 and 8 workers in a batch job.

## Conclusion

A second team member reproduced the correctness checks and the small financial demo from the GitHub code, in a
different cluster account, with identical results. This does **not** yet test the full-size runs, the Slurm job
scripts or a fresh `git clone`; those still need to be checked before the final submission.
