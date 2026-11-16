# Project decisions and experiment log

This log distinguishes completed work from plans. Update it after each meaningful
change or experiment; commit the log with the relevant source and evidence.

## 15 November 2026 — agreed question and scope

The original proposal estimated 99% one-day VaR and Expected Shortfall for a
linear portfolio with correlated normal returns. The professor approved the
general Monte Carlo direction but pointed out that this case has a direct
mathematical answer, and requested a more justified simulation workload, clear
differentiation, reproducible batch streams, explicit profiling/measurement tools,
controlled numerical-library threads, and multiprocessing.shared_memory.

The group approved the revised direction in discussion: simulate a buy-and-hold
portfolio over 20 trading days and compare its maximum drawdown under constant
normal conditions versus persistent normal/crisis conditions. The revised
question has not yet received specific professor approval. Keep the original
arithmetic-normal one-day case as a future independent analytical benchmark.

One scenario is one complete possible month. The portfolio starts with EUR
100,000 equally invested across 50 fictional assets. It is not rebalanced daily.
Inputs are synthetic model assumptions, not historical estimates or real crash
predictions. The main outputs are the 99th percentile of maximum drawdown, the
mean of the largest 1% of drawdowns, and the frequency of drawdown above 20%.
These are drawdown measures, not the original one-day VaR/ES.

Normal/crisis mean daily log returns are 0.0002/-0.005; base standard deviations
are 0.012/0.035; asset shock correlations are 0.25/0.80. Fixed asset volatility
multipliers range from 0.8 to 1.2. A normal state enters crisis with daily
probability 0.01; crisis exits with daily probability 0.20. Changing these
assumptions requires documenting the change and assessing sensitivity.

The full-workload size is 64 million months per model. A one-core qualification
run completed as job 30375, with 799.935084 seconds of computation (see below).
This size follows the computing requirement, not an established statistical
accuracy requirement. Repeated full-size scaling remains to run.

## Correctness and first financial demonstration — completed

User: pc47; node: haskell. The reported cluster environment was Python 3.12.15
and NumPy 2.5.4. Small tests ran in the interactive Jupyter allocation, not as
formal performance experiments. Checks passed for hand-calculated drawdowns,
flat markets, disabled/forced crises, repeatability, batch order, output arrays,
tail summaries, output protection and production-size selection.

With 1,000 months, 50 assets, 20 days, batch size 4,096 and seed 20261115:

| Statistic | Normal | Crisis |
|---|---:|---:|
| 99th percentile of maximum drawdown | 6.5199% | 15.7697% |
| Mean maximum drawdown in worst 1% | 7.2408% | 18.5853% |
| Fraction of months with drawdown above 20% | 0% | 0.2% |
| Fraction of months with crisis days | 0% | 19% |

Each worst-tail mean uses only 10 observations, so these are demonstration
results, not precise final estimates. Saved files are in results/first_run on
the cluster. They are not the first scaling experiment.

Parallel equivalence checks also passed on the cluster for normal/crisis
models, threads/processes and 1/2 workers: all eight comparisons were
byte-identical to the sequential output. These are small-input checks; the
benchmark below additionally checks every timed full-workload result.

## Preliminary strong scaling — completed, job 30338

Date: 15 November 2026. Node: haskell. Account: pc2026; user: pc47.
64 logical CPUs requested (32 physical cores under the course's allocation
scheme); 16 GB requested. Library thread settings: OMP_NUM_THREADS=1,
OPENBLAS_NUM_THREADS=1, MKL_NUM_THREADS=1. Process pools explicitly use spawn.

Workload: crisis model, 2,097,152 months, 50 assets, 20 days, batch size 4,096,
seed 20261115. Five repetitions of each execution configuration, with randomized
configuration order in each repetition. The same scenarios are reused across
versions/repetitions. Every timed output digest matched the sequential reference.

The whole Slurm job completed in 00:11:47, State=COMPLETED, ExitCode=0:0.
That total is not the sequential baseline duration. The sequential median was
25.211230 seconds, so this workload does NOT meet the final 10-minute criterion.

| Workers | Threads median (s) | Thread speedup | Processes median (s) | Process speedup |
|---:|---:|---:|---:|---:|
| 1 | 25.581814 | 0.9855 | 27.454939 | 0.9183 |
| 2 | 12.826952 | 1.9655 | 13.776326 | 1.8300 |
| 4 | 6.406833 | 3.9351 | 7.002373 | 3.6004 |
| 8 | 3.296088 | 7.6488 | 3.836658 | 6.5711 |
| 16 | 1.908452 | 13.2103 | 2.454583 | 10.2711 |
| 32 | 2.223529 | 11.3384 | 2.547949 | 9.8947 |

Speedup uses the independently measured sequential median, not each pool's
one-worker time. Runtime includes output allocation, seed preparation, pool
start/stop, simulation, transfers and gathering; excludes output validation,
financial summary calculations and disk writing. Inputs are generated within
the timed computation. No full scenario arrays are written by this benchmark.

Evidence to preserve in Git under results/scaling-30338/:

- timings.csv: every raw timing, validation result, node, job ID, date and node load.
- metadata.json: settings, environment, affinity list, source fingerprints and CPU topology.
- scaling_summary.csv: medians, minimum/maximum, speedup and efficiency.
- strong_scaling.png and strong_scaling.pdf: figures rebuilt from the CSV.

These files are on the cluster. This log summarizes the user's reported output;
the original CSVs/metadata must be retained as the authoritative evidence.

Initial interpretation: 16 threads are the fastest tested configuration for this
size and allocation; threads scale almost ideally through 8 workers. Both pools
stop improving beyond 16. The causes are NOT yet established. Pool startup,
serialization/copying, shared memory bandwidth/cache limits, physical-core
placement and contention are hypotheses to measure, not proven explanations.

## Scheduling issue and resolution

Job 30327 was pending and cancelled; replacement job 30338 was explicitly
requested on haskell. Early queue output showed Reservation. A later job report
showed QOSMaxCpuPerUserLimit, and the student QoS confirmed cpu=64 per user.
The 2-CPU Jupyter allocation plus a 64-CPU batch request exceeded that allowance.
The Jupyter server was stopped to release the interactive allocation; job 30338
subsequently completed. Do not diagnose future waits solely from one stale
pending reason. Check job details and per-user usage before resubmitting.

## Full-size baseline — completed, job 30375

Date: 15 November 2026. Node: haskell. Requested 2 logical CPUs, 16 GB; Python
execution pinned to the single logical CPU 65. Library thread limits were all 1.
Crisis model, 64,000,000 months, 50 assets, 20 days, batch size 4,096, seed 20261115.

- Job State=COMPLETED, ExitCode=0:0; total job elapsed 00:13:25.
- Actual computation: 799.935084 seconds (13 minutes 19.935 seconds).
- Risk-summary calculation: 0.758458 seconds; result writing: 2.378131 seconds.
- ten_minute_workload_verified=true and array_bounds_and_shapes_passed=true.
- Output arrays: 1,280,000,000 bytes before file headers, not full stock paths.
- Raw result digest: 94a2c858b5df667aab580e85c656a80082fb084d8f8c0de443f4463aa22973b1.
- simulate.py SHA256: a3e60ca0a4c342526311578b0749aad72c7aae21907a49185b6c9f194b86ccec.
- full_baseline.py SHA256: 7fdc1291bd3329692626ac8585e5b575c0d6da2f3d7d4d2a9732e2a259bbf7a6.

Job 30376 was an accidental duplicate and was cancelled while 30375 was running.
It briefly overlapped the baseline, so this single qualification timing should
not be treated as the final repeated performance estimate. Retain node-load
records and use repeated full-size experiments for scaling results.

Evidence lives on the cluster in results/full-baseline-30375/:
resource_usage.txt, data/crisis_summary.json, data/baseline_verification.json,
data/crisis_example_paths.csv, and the three large .npy result arrays. Preserve
small evidence files in Git; exclude large arrays.

The resource report and complete financial summary were subsequently reviewed:

| Resource measurement | Reported result |
|---|---:|
| User CPU time | 758.76 s |
| System CPU time | 42.41 s |
| Total command wall time | 804.92 s |
| Reported CPU utilization | 99% |
| Peak resident memory | 1,853,996 KiB (about 1.768 GiB) |
| Major page faults | 2 |
| Minor page faults | 97,040,659 |
| Swaps | 0 |
| Voluntary / involuntary context switches | 5,049 / 9,767 |

The single CPU stayed busy and the footprint was well below the 16 GB request.
This supports a computation/allocation-heavy workload rather than substantial
blocking on disk or swapping. It does NOT distinguish arithmetic from memory
bandwidth/cache limits; CPU utilization alone cannot establish that distinction.
The large minor-fault count warrants investigating allocation/page-management
costs with profiling rather than attributing the parallel slowdown to one cause.
The resource report covers the whole command, including summaries, disk output
and saved-array checks; the separate 799.935084 s figure times computation only.

Full-size crisis-model financial results, conditional on the synthetic settings:

| Statistic | Result |
|---|---:|
| 99th percentile of maximum monthly drawdown | 15.4045455% |
| Mean maximum drawdown in the worst 1% | 19.1946177% |
| Months in the empirical worst-tail mean | 640,000 |
| Fraction with maximum drawdown above 20% | 0.3094765625% |
| Count with maximum drawdown above 20% | 198,065 of 64,000,000 |
| Fraction of months with crisis days | 18.2039671875% |

This is the crisis model only; the full-size normal-model comparison is still
pending. More scenarios alone do not establish model realism or quantified
statistical precision. Independent-seed uncertainty and sensitivity checks remain.

This verifies the full workload's >=600-second runtime on one core. It does not
establish repeated full-size scaling, statistical precision, or complete model
validation. The independent analytical normal-case benchmark is still needed.

## Remaining work

- Repeat strong scaling at the verified 64-million-month size.
- Profile the baseline and estimate its parallelizable/serial fraction.
- Measure at least one overhead directly; implement/compare shared memory.
- Weak scaling and Amdahl comparison; investigate the 16-to-32-worker slowdown.
- Independent-seed statistical uncertainty/convergence and parameter sensitivity.
- Independent analytical normal-case benchmark.
- Final normal/crisis financial comparison at a justified scenario count.
- Reproducible README/fresh-clone test, report, teaching section and presentation.
- Group members' own commits and the syllabus-required AI acknowledgement.

Five timing repetitions measure execution-time variability on fixed scenarios.
They do not create extra independent Monte Carlo samples. Statistical uncertainty
requires a separate design. AI-assisted code/explanations have been used in this
work; the full acknowledgement must follow the syllabus format, which has not
been checked in this workspace yet.
