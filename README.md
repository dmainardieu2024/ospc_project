# OSPC: portfolio crashes and parallel simulation

**Start here.** This README is the project's front page: what it does, what has
actually been completed, and how a teammate can run a small example.

Read [TEAM_TASKS.md](TEAM_TASKS.md) for exact teammate assignments and commands.
Read [PROJECT_LOG.md](PROJECT_LOG.md) for decisions, settings and experiment evidence.

## 1. The question in plain English

Imagine EUR 100,000 invested equally in 50 fictional stocks. We buy and hold for
20 trading days (one month). The stocks change value each day. We record the
portfolio's **maximum drawdown**: the biggest percentage fall from a previous high.

Example: EUR 100,000 rises to EUR 110,000, falls to EUR 77,000 and finishes at
EUR 102,000. It finishes up 2%, but suffered a maximum drawdown of 30%.

We generate many possible months and examine the largest 1% of their drawdowns:
the 99th-percentile threshold and the average maximum drawdown in that tail.

We compare two synthetic market models:

| Normal | Normal/crisis |
|---|---|
| Same assumptions every day. | Can switch into crisis conditions lasting several days. |
| Smaller typical fluctuations. | Larger fluctuations and more negative average log returns in crisis. |
| Moderate common movement between stocks. | Stronger common stock movement in crisis. |

These are chosen assumptions, not historical estimates or real crash forecasts.
The professor approved the original Monte Carlo direction; this revised question
still needs specific feedback. We retain the original normal one-day question
as a planned known-answer validation case. Monthly drawdown statistics are not
the original one-day VaR/ES.

## 2. The computing experiment

The same calculation runs sequentially, in a thread pool, or in a process pool.
Workers calculate different batches of months and the parent collects results.
The financial model is unchanged when the execution method changes.

- **50 stocks** = investments in the portfolio.
- **20 days** = length of each simulated month.
- **64 million months** = independent scenario paths in the full-size workload.
- **1, 2, 4, 8, 16, 32 workers** = the execution configurations being compared.
- **Five repetitions** = rerun each whole configuration to measure timing variation.

The repeated timing runs reuse the same seed and scenarios. They do not provide
additional independent observations for estimating financial uncertainty.
SeedSequence.spawn assigns random streams to fixed batches, not workers, so
changing the worker count must preserve the results. Production batch size: 4,096.

Scenarios are generated as the program runs. We do not first build a giant
stock-price spreadsheet. We retain monthly results, not every asset's daily path.

## 3. Verified progress as of 16 November 2026

| Experiment | Status and finding |
|---|---|
| Small checks and 1,000-month financial demo | Completed on the cluster. |
| Thread/process equivalence checks | Passed for both market models at 1/2 workers; byte-identical outputs. |
| Preliminary scaling, job 30338 | Completed: 2,097,152 months, both pools at 1-32 workers, five repeats. Every timed result matched. |
| Full sequential baseline, job 30375 | Completed: 64 million months, one pinned CPU, computation 799.94 s, peak RSS about 1.77 GiB. Meets >=10-minute workload criterion. |
| Full repeated scaling, job 30691 | Submitted; start/completion/results not yet verified here. |

Preliminary result: sequential median 25.21 s; fastest tested configuration was
16 threads, 1.91 s (13.21x). Adding workers beyond 16 did not help at that size.
Do not present those numbers as the still-pending full-size scaling results.

The full-size crisis model gave a 15.40% drawdown threshold for the worst 1%
and a 19.19% average maximum drawdown within that tail. Full-size normal-model
comparison, uncertainty intervals and sensitivity analysis are still pending.

Tomorrow's 17 November progress review asks for progress, a first scaling plot
and current problems. We already have the preliminary plot. A successfully
completed full-size job generates the updated plot automatically. We still need
to understand/explain the work, profile it, document limitations and obtain feedback.

## 4. Tools and files

| Tool/file | What it does |
|---|---|
| JupyterLab | Workspace on the university computer: editor, files, terminal, notebooks. |
| GitHub | Shared, versioned code, documentation and small evidence files. |
| Slurm / sbatch | Allocates resources and runs batch experiments. |
| NumPy | Random generation and numerical array operations. |
| simulate.py | Shared financial model, sequential calculation and saved financial results. |
| parallel.py | Thread/process pools using the same financial kernel and batch streams. |
| check.py / check_parallel.py | Automated small-case and equivalence checks. |
| benchmark.py | Repeated fixed-size timing experiments; checks every output against a reference. |
| plot_scaling.py | Rebuilds runtime/speedup graphs from timing CSVs. |
| full_baseline.py / full_baseline.slurm | Full-size one-CPU qualification and output inspection. |
| full_scaling.slurm | Full-size repeated strong scaling; current job 30691 was submitted from it. |
| profile_baseline.slurm | New small diagnostic cProfile job; not yet cluster-verified. |
| normal_comparison.slurm | New full normal-model financial comparison; not yet cluster-verified. |
| calibrate.py / produce.py / prepare_full.slurm | Earlier size-calibration helpers; not needed to repeat current verified size. |

## 5. Get the project and run small checks

Sign in to GitHub and accept the repository invitation first. Open your own
university JupyterLab account and a terminal. If Git authentication is configured:

```bash
cd ~
git clone https://github.com/dmainardieu2024/ospc_project.git
cd ospc_project
export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python check.py
python check_parallel.py
python simulate.py --scenarios 1000 --batch-size 4096 --output results/my-demo
```

If the repository is already cloned, enter that folder and use `git pull` first;
do not clone over existing work. Git may ask for credentials; finish its prompts
before entering more commands. Your normal GitHub password is not a Git token.
Do not share passwords/tokens. If authentication is blocked, TEAM_TASKS.md gives
a browser-download route without putting credentials into a shell command.

These are small development checks intended to finish well under five minutes,
subject to the environment. They do not submit another full-size experiment.
Record any missing files/dependencies rather than reporting a failed check as passed.
Existing output folders are protected; choose a new name if a demo already exists.

The course environment provides NumPy and Matplotlib. Historical verified cluster
environment: Python 3.12.15 / NumPy 2.5.4. Record your actual versions; the full
environment has not yet been pinned or audited with a fresh clone.

## 6. Results and how to regenerate graphs

| Directory | Contents |
|---|---|
| results/scaling-30338/ | Preliminary raw timings, metadata, table and plots. |
| results/full-baseline-30375/ | Full-size one-core resource report and financial summaries. |
| results/full-scaling-30691/ | Current repeated full-size experiment, if it has started. |

When job 30691 completes successfully, it automatically calls the plotting script.
Once its files have been shared through GitHub, anyone can redraw the graph:

```bash
python plot_scaling.py results/full-scaling-30691
```

That reads the saved measurements; it does NOT rerun the simulations. The script
refuses incomplete/failed experiments. Output: strong_scaling.png, strong_scaling.pdf
and scaling_summary.csv. Runtime error bars show minimum-to-maximum across repeats.

Commit source, job scripts, raw timing CSVs, metadata, small summaries and graphs.
Keep the reproducible large .npy scenario arrays out of Git. An ordinary teammate
does not automatically see Diego's private cluster home: results must be pushed
before teammates can get them. Downloading a ZIP is a snapshot, not a live sync.

## 7. Important remaining work

- Inspect/retain the full-size scaling results; diagnose the slowdown honestly.
- cProfile and profiling-based/inferred serial-fraction comparison.
- Independent analytical normal-case check requested by the professor.
- Full-size normal/crisis financial comparison.
- For the final project: direct overhead measurements, shared memory, weak scaling,
  statistical uncertainty/sensitivity, final report and presentation, fresh-clone
  reproducibility and syllabus-format AI acknowledgement.

Do not change simulate.py, parallel.py or benchmark.py in the account running
job 30691 while it is executing: spawned workers import those files. Other
members should use their own account/copy and create separate task files.

Each member must understand their work and commit their own contributions.
See TEAM_TASKS.md for concrete tasks and completion conditions.
