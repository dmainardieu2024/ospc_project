# Progress review — Tuesday 17 November 2026

Group 3: Diego Alfaro, Markel Artamendi, Leo Ayyashi, Diego Mainardi, Mia Marcelli.

This is a four-part meeting guide. Use the [full-size graph](../results/strong_scaling/figures/strong_scaling.png) as the main figure. The final project remains in progress.

## 1. Question and response to feedback

**Say:** We simulate EUR 100,000 initially divided equally across 50 fictional stocks, held for 20 trading days. Each scenario is one possible month. We measure maximum drawdown: the largest fall from an earlier portfolio high. We examine the 99th-percentile drawdown threshold and the mean of the largest 1% of drawdowns.

The original one-day normal VaR problem has a mathematical solution. Our revised calculation depends on the daily path and on random switches into persistent crisis conditions. The crisis model changes mean log returns, volatility and stock correlations. The comparison is synthetic; it does not predict actual crashes.

The simple one-day arithmetic-normal model remains a separate known-answer test, now completed by Leo. Specific professor feedback on the revised monthly drawdown question is still needed.

**Ask:** Is this revised question sufficiently justified and differentiated from the other Monte Carlo VaR project?

## 2. Calculation and correctness

**Say:** Months are generated in fixed batches of 4,096. Each batch has its own SeedSequence.spawn stream. Workers calculate different batches; they do not divide the model into different financial tasks. Sequential, thread and process versions use the same simulation kernel and fixed batch streams.

- check.py covers hand-calculated paths, flat markets, disabled/forced crises, repeatability, batch order and saved outputs.
- check_parallel.py passed all eight small comparisons: normal/crisis, threads/processes, 1/2 workers.
- Every one of the 65 full-size crisis timing measurements has the same output digest as its reference.
- Mia independently reproduced the checks, small demo and preliminary graph in account pc75. See [REPRODUCTION.md](REPRODUCTION.md). This used a GitHub ZIP, not a fresh git-clone/environment-pinning test.
- Leo's job 30985 compared simulated one-day normal VaR/ES against analytical answers for seeds 11, 22 and 33, one million scenarios each. All six comparisons passed a provisional 1% relative-error tolerance. See [NORMAL_VALIDATION.md](NORMAL_VALIDATION.md). This validates the separate reference case, not monthly drawdown or market realism.

**Distinction:** 64 million months are simulation scenarios. Five repetitions rerun a configuration on the same scenarios to measure timing variability; they do not measure financial sampling uncertainty.

## 3. Main graph and results

Open [strong_scaling.png](../results/strong_scaling/figures/strong_scaling.png). Evidence: [raw timings](../results/strong_scaling/measurements/timings.csv), [summary](../results/strong_scaling/measurements/scaling_summary.csv), [metadata](../results/strong_scaling/run_details/metadata.json).

**Say:** This is strong scaling: the total workload remains 64 million months, 50 stocks and 20 days while the worker count changes. Both coloured lines use the crisis financial model. Blue means threads within one process; orange means separate worker processes coordinated by a main process.

| Configuration | Median seconds | Speedup |
|---|---:|---:|
| Sequential | 810.94 | 1.00x |
| 8 threads | 104.47 | 7.76x |
| **16 threads** | **67.34** | **12.04x** |
| 32 threads | 76.55 | 10.59x |
| 16 processes | 99.97 | 8.11x |
| 32 processes | 87.16 | 9.30x |

The left panel shows runtime: lower is better. The right shows sequential time divided by parallel time: higher is better. Grey dashed lines represent ideal scaling. Dots are medians of five runs; runtime bars show minimum to maximum. There are 13 configurations and five repetitions: 65 timed calculations plus reference checks, explaining the multi-hour experiment.

**Finding:** 16 threads are fastest among tested configurations. Threads are faster than processes at every matching worker count. At full size, threads slow down from 16 to 32 workers; processes continue improving. The causes remain to be measured. Worker startup, result transfer, memory effects, placement and shared-node contention are hypotheses.

The separate one-CPU qualification, job 30375, took 799.94 s computation on one pinned logical CPU, meeting the 10-minute workload criterion. Its peak RSS was about 1.77 GiB, CPU usage 99%, with no swapping. This indicates a busy CPU and little blocking; it does not distinguish arithmetic from memory/allocation costs.

**Disclose:** Slurm preempted job 30691 after 25 measurements. Job 31181 completed the remaining 40 on haskell and finished successfully in 03:53:55. The figure and metadata identify both allocations. This is not an uninterrupted single-allocation experiment; CPU affinity changed between allocations. Ask whether a clean single-allocation rerun is required for final assessment.

Timing includes allocation, seed setup, pool startup/shutdown, simulation and gathering. Validation, financial summaries and writing are excluded. Numerical-library thread limits are 1. The preliminary 2,097,152-month graph is retained in archive/preliminary_scaling as earlier evidence.

## 4. Problems, next work and questions

Completed: the simulation/checks, Mia's reproduction, Leo's known-answer test, one-CPU qualification and resumed full-size strong scaling.

Completed evidence is still needed in GitHub for:

- **Package B:** cProfile report, expensive functions, qualified serial-fraction estimate and Amdahl comparison. profile_baseline.slurm is uploaded.
- **Package D:** matching full-size normal-model summary, financial comparison table/chart and interpretation. normal_comparison.slurm is uploaded.

The crisis-only full-size financial result is a 15.40% drawdown threshold and a 19.19% mean in the worst 1%. We cannot yet present a completed full-size normal/crisis comparison from the uploaded evidence.

For the final project: measure overhead, implement/compare multiprocessing.shared_memory, weak scaling, independent-seed uncertainty, sensitivity analysis, final report/presentation, fresh-clone reproduction and syllabus-format AI acknowledgement.

Weak scaling would increase months in proportion to workers while keeping work per worker constant; ideal runtime would stay flat. This has not yet been completed.

**Questions for the professor:**

1. Is the revised monthly drawdown question approved?
2. Is the separate one-day normal known-answer test an appropriate complement to hand-path and equivalence checks?
3. How should we handle the preempted/resumed experiment against the single-allocation requirement?
4. Which profiling and overhead comparisons should we prioritise next?

## Repository walkthrough

Start with [README.md](../README.md), show the main graph, and open its evidence folder only if asked. Calculation files, tests, job scripts and separate evidence folders have different roles; there is no need to open every file during the meeting.

Before presenting, each member should explain one scenario, one batch, the two colours, one graph point, one correctness check and one limitation in their own words. AI-assisted code/explanations have been used; retain the required acknowledgement in the final submission.
