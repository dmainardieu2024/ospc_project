# Sampling variation across random seeds

## Purpose and status

This addition measures how the financial estimates change when the simulated sample changes. The existing timing repetitions reuse the same seed: they measure runtime variation, not sampling variation.

Leo Ayyashi Guillén — 17 November 2026.

I completed this experiment on the university cluster as job 32103. All ten simulations completed successfully. This is additional work after my completed normal reference validation.

## Experiment

I use the existing, unchanged monthly simulation with 50 assets and 20 days. I run both normal and crisis models for seeds 101, 202, 303, 404 and 505, with 262,144 scenarios per seed/model and a batch size of 4,096. That is ten simulations and 2,621,440 scenario-months in total. This modest diagnostic workload avoids repeating the full 64-million-scenario comparison.

For each run I calculate the global 99th-percentile maximum drawdown, mean of the largest ceil(1% × N) drawdowns, fraction exceeding 20% drawdown, and fraction containing crisis days. Quantiles are calculated across the complete run, never averaged across batches.

For each model and metric, the summary reports the mean, sample standard deviation (ddof=1), minimum, maximum and range across five seeds. Values are percentages; standard deviations and ranges are percentage points. For example, a move from 15% to 16% is one percentage point.

Different seeds supply different pseudorandom samples. Reusing each seed for both models pairs the input streams, so the ten runs should not be described as ten independent model comparisons. Each model's across-seed spread is descriptive. It is not a confidence interval, a calibrated error guarantee, an assessment of model realism or proof of convergence. Five seeds give only a rough view. The smaller scenario count does not establish uncertainty at 64 million scenarios. A larger-count experiment would be a separate follow-up.

## Files

- calculations/sampling_variation.py: calculation and descriptive summaries.
- calculations/jobs/sampling_variation.slurm: small cluster job; two logical CPUs requested, numerical library threads fixed to one.
- results/sampling_variation/job-ID/measurements/seed_estimates.csv: one row per model/seed, including elapsed compute time.
- results/sampling_variation/job-ID/measurements/sampling_spread.csv: one row per model/metric.
- results/sampling_variation/job-ID/measurements/metadata.json: inputs, versions, host, source commit when available, job ID and status.
- results/sampling_variation/job-ID/run_details/resources.txt: command resources.

Only small CSV/JSON/text evidence is saved. No .npy arrays are written. Existing output directories are rejected; partial runs retain metadata status 'running', and a failed job must not be labelled complete.

## Submit once on the cluster

Use a fresh copy of the updated repository in your own account. Run from the repository root:

```bash
sbatch calculations/jobs/sampling_variation.slurm
squeue -u "$USER"
```

Record the returned ID and, after completion, inspect:

```bash
sacct -j ID -o JobID,State,Elapsed,ExitCode
cat sampling-variation-ID.out
cat results/sampling_variation/job-ID/measurements/sampling_spread.csv
```

Confirm COMPLETED, exit code 0:0, metadata status completed and ten seed-estimate rows. The Slurm script runs the existing correctness check first. Preserve the output and sacct status with the experiment evidence. Do not submit a duplicate if the first job is already pending or running.

## Local verification completed

A smoke run with 257 scenarios, batches of 64, three seeds and both models completed. It exercises a partial final batch and produces six estimates and eight summary rows. I checked global tail averaging against independently sorted values, the percentile calculation, zero crisis-day fraction, same-seed repeatability for both models, CSV structure and shell syntax. Small smoke-run values are development checks, not financial findings. Actual cluster results and interpretation will be added after execution.



## Verified cluster results

I ran the experiment from account pc17 on node julia. Job 32103 completed in 35 seconds with ExitCode 0:0. The measured Python command took 34.50 seconds and peak resident memory was 55,292 KB. Python was 3.12.15 and NumPy was 2.5.4. Both the ten-row seed table and eight-row spread table are present, and metadata status is completed. I recalculated all summary values from the per-seed CSV and confirmed that they match.

| Model | Metric | Across-seed mean (%) | Sample SD (percentage points) | Minimum (%) | Maximum (%) |
|---|---|---:|---:|---:|---:|
| normal | 99th-percentile drawdown | 6.5031 | 0.0196 | 6.4781 | 6.5327 |
| normal | Average drawdown in worst 1% | 7.2542 | 0.0203 | 7.2325 | 7.2858 |
| normal | Frequency above 20% drawdown | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| normal | Months containing crisis days | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| crisis | 99th-percentile drawdown | 15.3990 | 0.0515 | 15.3376 | 15.4786 |
| crisis | Average drawdown in worst 1% | 19.1304 | 0.0843 | 19.0457 | 19.2693 |
| crisis | Frequency above 20% drawdown | 0.3020 | 0.0067 | 0.2953 | 0.3094 |
| crisis | Months containing crisis days | 18.2133 | 0.0900 | 18.1343 | 18.3353 |

The 99th-percentile estimate ranged from 6.4781% to 6.5327% in the normal model, a spread of 0.0546 percentage points. In the crisis model it ranged from 15.3376% to 15.4786%, a spread of 0.1409 percentage points. In these five samples the crisis tail measures varied more in absolute percentage points, particularly the average of the worst 1% of drawdowns. This is an observation about this experiment, not proof of convergence or a general statistical ordering of the models.

No normal-model scenario exceeded 20% drawdown in any sample. The recorded zero and zero across-seed spread do not mean that this event has zero probability. Crisis-model exceedance frequency averaged 0.3020%. Model assumptions change together; this comparison does not isolate the effect of any one assumption.

These five runs describe sampling variation at 262,144 scenarios per model/seed. They do not quantify precision at 64 million scenarios or replace the full-size normal/crisis comparison. Further convergence work would repeat the design at additional scenario counts; parameter sensitivity would change model assumptions and remains separate work.

## Evidence and execution record

Raw cluster evidence is preserved under results/sampling_variation/job-32103. The Slurm output is run_details/sampling-variation-32103.out; job_status.txt records completion. The uploaded experiment script matches the locally tested version byte for byte.

The cluster used a ZIP copy, so metadata source_commit is null. The starting snapshot was supplied as git archive commit 09de9931c7289c9fe70d25fd0def0f94eb312fbe, with the new sampling script and job added. A complete Git provenance record is unavailable on that cluster copy; commit the addition together with its evidence.

The first submission, job 32102, failed before simulations because the uploaded package omitted archive/calibrate.py, which the existing correctness check imports. I added the required archive folder, reran the check successfully and submitted replacement job 32103. No simulation results from the failed submission are used. Future ZIP packages must include both calculations and archive.

## Explanation for the group

“I checked whether our monthly risk estimates change much when we generate different random samples. I ran each model five times with 262,144 possible months each time. The estimates were similar across these samples, but the crisis tail results varied more. This measures sampling variation at this workload size; it does not prove that the assumptions describe real markets.”
