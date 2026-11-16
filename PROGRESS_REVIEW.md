# Progress review, Tuesday 17 November: four-slide outline

Group 3: Diego Alfaro, Markel Artamendi, Leo Ayyashi, Diego Mainardi, Mia Marcelli

## Slide 1. The question, and how we responded to the feedback

- **New question:** for EUR 100,000 split equally across 50 stocks and held for one month (20 trading days),
  how bad is the maximum drawdown in the worst 1% of months, under normal markets and under markets that
  can switch into a crisis?
- **Why we changed it:** the professor pointed out that one-day VaR with normal returns has a closed form.
  Our new question needs simulation:
  - the drawdown depends on the whole path of the month, not just the final value;
  - crises start and end at random (on any day there is a 1% chance a crisis starts; once in a crisis,
    a 20% chance each day that it ends);
  - in a crisis, volatility rises from 1.2% to 3.5% a day, the average return turns negative and the
    correlation between stocks rises from 0.25 to 0.80.
- This also makes our project clearly different from the other Monte Carlo VaR team.
- The one-day normal VaR stays as our **known-answer test** (package C, in progress).
- **Ask the professor:** do you approve the revised question?

## Slide 2. What the program does, and how we know it is correct

- One scenario is one possible month. The size parameter is the number of months (64 million at full size).
- The months are generated in fixed batches of 4,096. **Each batch has its own random stream from
  `SeedSequence.spawn`**, so the results do not depend on the number of workers or on the order in which
  they finish.
- `check.py`: hand-calculated drawdowns, a flat market, crises switched off and forced on, batch order, output
  files: all pass.
- `check_parallel.py`: threads and processes give byte-identical results to the sequential version. The
  benchmark also checks every timed run against the reference.
- Reproduced independently in a second account (pc75) with identical results (REPRODUCTION.md).
- BLAS threads are set to 1 in every version (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`).

## Slide 3. Baseline and first scaling plot

- **Full baseline (job 30375):** 64 million months on one pinned CPU, 800 s of computation (meets the
  10-minute rule). `/usr/bin/time -v`: 99% CPU, peak memory 1.8 GB, no swapping: the workload is
  CPU-bound, not limited by I/O.
- **First strong-scaling plot (job 30338):** strong_scaling.png, labelled **2,097,152 months** (a preliminary
  size, not the full workload). 1–32 workers, 5 repeats, median with min–max bars.
  - Threads scale almost ideally up to 8 workers and are fastest at 16 workers: 1.91 s, a 13.2× speedup.
  - Processes reach 10.3× at 16 workers.
  - Both get slightly **slower** from 16 to 32 workers.
  - Threads beat processes because NumPy releases the GIL in our heavy operations, and threads avoid
    starting processes and copying results.
- **Full-size scaling (job 30691):** [replace with the 64-million-month plot if it has finished; otherwise
  say it is pending].

## Slide 4. Problems, next steps and questions

- **Open problem:** why does going from 16 to 32 workers make it slower? Hypotheses to test, not conclusions:
  - pool start-up and gathering overhead (at 2 million months each worker has only 16 batches);
  - memory bandwidth;
  - page faults: the baseline had 97 million minor page faults and 42 s of system time, because new arrays
    are allocated every simulated day;
  - workers placed on the two hardware threads of one core.
- **Next steps:**
  - profiling with cProfile and the Amdahl serial fraction (package B);
  - the known-answer normal case (package C);
  - the full-size normal vs crisis comparison (package D);
  - `multiprocessing.shared_memory`, to measure how much data movement it saves;
  - weak scaling, direct overhead measurements, and statistical uncertainty across independent seeds.
- **Blocker:** three job scripts (`profile_baseline.slurm`, `normal_comparison.slurm`, `prepare_full.slurm`)
  still have to be pushed to GitHub.
- **Questions for the professor:**
  1. Is the revised drawdown question approved?
  2. Is the one-day normal VaR an acceptable known-answer test for it?
