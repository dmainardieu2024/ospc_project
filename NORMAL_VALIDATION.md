# Independent normal reference validation

Prepared for Leo Ayyashi Guillén, 16 November 2026. Status: university cluster validation completed successfully; team review and Git commit pending. The professor's original feedback was not supplied; this implementation follows Task C's specification. Repository snapshot: 2efa319a64b30d797c1ce7d0e8868e7d4206be9a. simulate.py is unchanged.

## Model and analytical answer

This separate ONE-DAY arithmetic-return model has portfolio value €100,000, five equal weights of 0.2, zero means, volatilities [0.010, 0.012, 0.015, 0.018, 0.020], and off-diagonal correlation 0.25 (diagonal 1).

Let Σ = diag(vol) R diag(vol), and loss L = −100000 wᵀr. Then L is normal with mean zero and σ_L = 100000 sqrt(wᵀΣw).

For z = Φ⁻¹(0.99), VaR99 = z σ_L and ES99 = σ_L φ(z)/0.01. Here φ(z) = exp(−z²/2)/sqrt(2π). These are positive upper-tail losses. Reference: https://www.mathworks.com/help/risk/estimate-expected-shortfall-with-the-expectedShortfall-function.html (normal VaR/ES formulas; adapted to the loss sign convention).

Calculated σ_L = €959.3747964; VaR99 = €2231.8395181; ES99 = €2556.9393501.

## Simulation and verified cluster results

Each seed generates 1,000,000 return vectors in batches of 4,096, including a partial final batch. SeedSequence.spawn assigns a child stream to each batch. With Σ = CCᵀ from Cholesky, standard-normal row vectors Z are transformed as ZCᵀ. Losses are assembled globally before calculating the linear-interpolated 99th percentile and the mean of the largest ceil(0.01N) losses. No batch-level quantiles are averaged. All losses take about 8 MB; return-vector memory is bounded by batch size.

The script checks the Cholesky reconstruction and verifies portfolio variance independently using 0.75 Σ_i(w_i vol_i)² + 0.25(Σ_i w_i vol_i)².

| Seed | Estimated VaR (€) | VaR error | Estimated ES (€) | ES error |
|---|---:|---:|---:|---:|
| 11 | 2227.9499 | 0.174% | 2551.7356 | 0.204% |
| 22 | 2229.1549 | 0.120% | 2557.0895 | 0.006% |
| 33 | 2228.3845 | 0.155% | 2555.2615 | 0.066% |

Cluster job **30985**, submitted from account pc17, completed on 16 November 2026 with State COMPLETED and ExitCode 0:0. Python 3.12.15; NumPy 2.5.4. All three seeds and both metrics passed the unchanged 1% tolerance. Library thread limits were fixed to 1 in the submitted script. The uploaded cluster script matches the locally tested script byte for byte.

Evidence: results/normal-validation-30985/validation.csv (full precision and versions), job_status.txt (Slurm completion), resources.txt (process resource usage), and normal-validation-30985.out (printed outcomes). The process took 0.57 seconds wall time and maximum resident memory was 58,088 KB; Slurm reported an elapsed time of one second. This small diagnostic run is not the project's full-size performance baseline.

The table above is verified against the cluster CSV; the local test produced the same estimates. Raw cluster evidence is preserved unchanged.

## Tolerance and interpretation

A 1% relative-error threshold is fixed for each metric for every seed. It is a practical regression threshold for this million-scenario example, not a derived confidence interval. Both metrics pass for all three seeds; the tolerance was not adjusted after testing. A future failure should be investigated and reported rather than silently changing tolerance. Three successful seeds do not establish a failure probability for all possible seeds.

Sampling error means finite simulated samples differ from population answers; it changes with the seed. Arithmetic roundoff comes from finite floating-point precision and is distinct from this Monte Carlo variation. Model uncertainty concerns whether Gaussian one-day returns describe actual markets; agreement with the analytic answer does not establish that assumption.

Agreement between parallel implementations checks consistency, but both may share the same mistake. Comparison against a separately derived financial answer tests something different. Existing check.py includes hand-path drawdown checks and controlled-model cases; check_parallel.py addresses execution equivalence. Neither substitutes for this normal reference case.

This validation does not prove that the crisis model is realistic and does not analytically validate monthly compounded maximum drawdown. The normal reference models one-day terminal arithmetic loss; the main simulation models a different quantity over multiple days.

## Reproduce locally

From the repository root, with NumPy installed:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python validate_normal.py --scenarios 1000000 --seed 11 22 33 --batch-size 4096 --output results/normal-validation-local/validation.csv
```

A non-zero exit code indicates at least one tolerance failure (or an execution error). Existing output paths are rejected to preserve evidence. Reproducibility requires retaining seed, batch size, scenario count, code and numerical-library versions; changing batch size changes the random stream assignment.

## Required university cluster run

Upload validate_normal.py and normal_validation.slurm to your own project folder in JupyterLab, open its terminal, change to that folder, then:

```bash
sbatch normal_validation.slurm
squeue -u "$USER"
```

Record the returned job ID. Submit once. After it leaves the queue, replace ID below with the actual number:

```bash
sacct -j ID -o JobID,State,Elapsed,ExitCode
cat normal-validation-ID.out
cat results/normal-validation-ID/validation.csv
```

Confirm COMPLETED and exit code 0:0; inspect every CSV pass flag. Preserve the job output, resources.txt and CSV. This procedure was completed successfully for job 30985; no repeat submission is needed. The Slurm script uses the cpu partition and course environment path from the existing repository jobs.

Commit only the new script, Slurm script, report and small evidence files after reviewing them. No .npy files are produced.

## Explain it to the group

“We chose a simple portfolio whose loss distribution has a known mathematical answer. We calculated that answer, simulated a million possible days for each of three seeds, and compared the simulated VaR and ES with it. Differences arise because the sample is finite. This checks the simple normal model; it does not prove our crisis assumptions or monthly drawdown model are correct.”
