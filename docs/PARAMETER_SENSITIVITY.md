# Parameter sensitivity of monthly drawdown

Leo Ayyashi Guillén — 18 November 2026

## Purpose and status

I extend the completed sampling-variation experiment by changing model assumptions rather than only changing random samples. This addresses parameter sensitivity in the README's remaining work. I completed the university cluster experiment as job 32422. All 35 simulations finished successfully; the saved summaries were independently recalculated from the per-seed results.

## Design

I use the existing crisis model, without modifying simulate.py, with 50 assets, 20 days and an initial €100,000 portfolio. Each case uses 262,144 months, batches of 4,096 and seeds 101, 202, 303, 404 and 505.

| Setting | Low | Baseline | High |
|---|---:|---:|---:|
| Crisis daily log-return volatility | 0.028 | 0.035 | 0.042 |
| Crisis correlation | 0.64 | 0.80 | 0.96 |
| Daily probability of entering crisis when normal | 0.008 | 0.010 | 0.012 |

Each variant changes just one setting by −20% or +20% relative to its baseline; all other inputs are unchanged. There are seven cases (baseline plus six variants) and five seeds, for 35 simulations and 9,175,040 scenario-months. The ±20% range is an illustrative local stress range, not a calibrated estimate of parameter uncertainty.

The daily entry probability is conditional on currently being in the normal state; it is not the monthly probability of a crisis. Correlation describes how assets move together. Crisis log-return volatility scales daily fluctuations during crisis days, with the main model's asset heterogeneity retained.

I reuse the same seed and batch structure for every case. This pairs random inputs so that variant-minus-baseline differences can be calculated within each seed. Cases are therefore deliberately dependent. Changing the entry probability can change crisis states and subsequent paths; pairing does not imply identical paths or guarantee that noise disappears.

## Outputs and interpretation

The script records four metrics: the 99th-percentile monthly maximum drawdown, the average of the worst ceil(1% × N) drawdowns, the frequency exceeding 20% drawdown, and the fraction of months containing crisis days. It assembles complete losses/drawdowns before summarising, never averaging batch quantiles.

- seed_estimates.csv: 35 case/seed estimates, inputs and compute times.
- paired_changes.csv: 120 within-seed changes (six variants × five seeds × four metrics).
- sensitivity_summary.csv: 28 case/metric summaries. Means are percentages; changes and their sample standard deviations are percentage points. Baseline-minus-baseline is exactly zero by construction.
- metadata.json: complete settings for every case, seeds, versions, host/job ID, SHA-256 hashes of the relevant source files and status. Interrupted runs retain status running.

The across-seed mean paired change describes the effect of this specific input perturbation in the synthetic model. Sample SD uses ddof=1. Neither the observed range nor the SD is a confidence interval. Five seeds and one scenario count do not prove convergence. These are model responses, not causal effects in real markets or evidence that the assumptions are realistic. One-at-a-time changes do not measure interactions; results also depend on perturbation size. A ranking would apply only to these chosen perturbations and outputs, not universal parameter importance.

Maximum drawdown is the largest decline from an earlier portfolio high, not terminal loss. This experiment does not replace the full-size normal/crisis comparison, weak scaling or performance profiling.

## Cluster execution

The complete prepared cluster ZIP includes calculations and archive, both required by the correctness check. Extract into a fresh directory and run from its root:

```bash
sbatch calculations/jobs/parameter_sensitivity.slurm
squeue -u "$USER"
```

Submit once and record the ID. The job requests two logical CPUs and 2 GB RAM, with numerical-library threads fixed to one. The Python simulation itself is sequential; this is a financial sensitivity experiment, not a speed-up measurement. A 15-minute limit leaves margin over the prior sampling experiment; actual runtime and queue time are not guaranteed.

After completion, replace ID below with the actual number:

```bash
sacct -j ID -o JobID,State,Elapsed,ExitCode
cat parameter-sensitivity-ID.out
cat results/parameter_sensitivity/job-ID/measurements/sensitivity_summary.csv
```

Check COMPLETED and ExitCode 0:0, completed metadata and 35 seed rows. Save the job output, sacct status and resources.txt. Existing measurement directories are rejected to preserve evidence. No large .npy arrays are written.

## Verification completed

A small local run used 257 scenarios, batches of 64 and three seeds, exercising partial batches across all seven cases. It produced 21 estimates, 72 paired changes and 28 summaries. I checked that each variant changes exactly one setting, paired differences match the saved estimates, summary means and sample SDs match recalculations, baseline changes are zero and crisis occurrence is unchanged when only volatility or correlation changes. Slurm shell syntax passed. These smoke results are development checks, not the full experiment's financial findings.

Source snapshot: 8a224eb13e6f96a9980e4f277b9c7be152ec5b7e, with the sensitivity module, job and report added. Source file hashes are recorded at execution because the cluster ZIP has no Git history.

## Cluster results

I submitted job 32422 from account pc17 on haskell on 18 November 2026. Slurm recorded COMPLETED, 1 minute 58 seconds and ExitCode 0:0. Python and NumPy versions are recorded in metadata.json. The metadata status is completed; all 35 seed rows, 120 paired changes and 28 summaries are present. I checked each paired difference and recalculated the summary means, sample standard deviations and extrema from the seed table. The executed script and job match the prepared versions and their recorded SHA-256 hashes.

The following table reports means across five seeds. Changes are paired variant-minus-baseline differences in percentage points (pp).

| Case | 99th-percentile drawdown (%) | Change (pp) | Mean of worst 1% (%) | Change (pp) |
|---|---:|---:|---:|---:|

| Baseline | 15.399 | +0.000 | 19.130 | +0.000 |
| Crisis volatility −20% | 13.342 | -2.057 | 16.544 | -2.586 |
| Crisis volatility +20% | 17.417 | +2.018 | 21.663 | +2.532 |
| Crisis correlation −20% | 14.274 | -1.125 | 17.726 | -1.405 |
| Crisis correlation +20% | 16.403 | +1.004 | 20.396 | +1.265 |
| Crisis entry probability −20% | 14.470 | -0.929 | 18.267 | -0.863 |
| Crisis entry probability +20% | 16.167 | +0.768 | 19.837 | +0.706 |

For these chosen perturbations, crisis volatility produced the largest absolute changes in both tail measures. Raising it from 0.035 to 0.042 increased the 99th-percentile drawdown by about 2.018 percentage points and the worst-tail mean by 2.532 points. Correlation and entry probability also affected the outputs, with smaller changes for the specified ±20% perturbations. This is a comparison within this model and design, not a universal importance ranking.

All six variants changed both drawdown tail measures in the expected direction in every seed: higher settings increased them and lower settings decreased them. The sample SD of the paired 99th-percentile change ranged from about 0.010 to 0.048 percentage points across the six variants. This consistency is descriptive and is not a formal significance test.

Increasing crisis volatility raised the frequency of drawdown above 20% from a baseline mean of 0.3020% to 0.5605%. Changing only volatility or correlation left the fraction of months containing crisis days exactly unchanged, as expected: these settings affect returns, not crisis transitions. Changing entry probability moved that fraction from 18.2133% at baseline to 14.8422% (low) or 21.4552% (high).

The upward and downward responses were not perfectly symmetric. A 20% relative parameter change does not imply a 20% change in risk outputs. Results remain conditional on the other fixed assumptions, sample size and the chosen perturbation range.

## Evidence and completion

The original CSV, JSON and resource evidence is saved under results/parameter_sensitivity/job-32422. Slurm completion is recorded in run_details/job_status.txt; printed output is run_details/parameter-sensitivity-32422.out. The experiment produces no large .npy arrays. README status updates, wider convergence tests, model calibration and parameter interactions are separate follow-ups.

## Explanation for the group

“I changed one assumption at a time to see how much our risk estimates depend on it. I tested lower and higher crisis volatility, correlation and crisis-entry probability, using the same five random seeds for fair comparisons. For the changes I tested, volatility had the biggest effect on the tail drawdown measures. These results show how our model responds to its assumptions; they do not prove those assumptions describe actual markets.”
