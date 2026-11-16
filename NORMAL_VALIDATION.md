# Independent normal reference validation

Leo Ayyashi Guillén — 16 November 2026

I ran the independent normal reference validation on the university cluster as job 30985. All three seeds passed the 1% relative-error tolerance for both VaR and ES. The scripts, report and cluster evidence have been committed to the repository.

## Purpose

I used a simple portfolio with a known analytical loss distribution to compare simulated results against mathematical answers.

Agreement between sequential and parallel implementations checks consistency, but both implementations could share an error. This reference case provides a separate check against known financial quantities.

I kept this validation separate from simulate.py and did not change the existing financial model.

## Model and analytical answer

I used a one-day arithmetic-normal return model with:

| Input | Value |
|---|---|
| Portfolio value | €100,000 |
| Assets | 5 |
| Weights | 0.2 per asset |
| Mean returns | Zero |
| Daily volatilities | 0.010, 0.012, 0.015, 0.018, 0.020 |
| Correlation between different assets | 0.25 |
| Confidence level | 99% |

I constructed the covariance matrix as:

Σ = diag(vol) R diag(vol)

The correlation matrix R has ones on its diagonal and 0.25 elsewhere.

For return vector r and weight vector w, portfolio loss is:

L = −100000 wᵀr

The loss distribution is normal, with mean zero and standard deviation:

σ_L = 100000 √(wᵀΣw)

Using z = Φ⁻¹(0.99), I calculated:

VaR99 = z σ_L

ES99 = σ_L φ(z) / 0.01

Here, Φ is the standard normal cumulative distribution function and φ(z) = exp(−z²/2)/√(2π). Positive values represent losses.

The analytical answers are:

| Quantity | Analytical value |
|---|---:|
| Loss standard deviation | €959.3747964 |
| VaR99 | €2,231.8395181 |
| ES99 | €2,556.9393501 |

Formula reference: [MathWorks — Estimate Expected Shortfall](https://www.mathworks.com/help/risk/estimate-expected-shortfall-with-the-expectedShortfall-function.html).

## Simulation method

For each seed, I simulated 1,000,000 correlated one-day return vectors in batches of 4,096, including a smaller final batch.

The script uses SeedSequence.spawn to assign a separate child random stream to each batch. It calculates a Cholesky factor C such that Σ = CCᵀ, then transforms independent standard-normal row vectors Z into correlated returns using ZCᵀ.

For each scenario, it calculates:

Loss = −100000 × (return vector @ weights)

The script collects all losses before estimating:

- VaR99: the linearly interpolated 99th percentile.
- ES99: the mean of the largest ceil(0.01N) losses.

It does not average batch-level quantiles. For 1,000,000 scenarios, the ES estimate uses the largest 10,000 losses.

The loss array occupies approximately 8 MB. Return-vector memory is bounded by the batch size.

The script also checks that the Cholesky factor reconstructs the covariance matrix and verifies portfolio variance using the separate equicorrelation expression:

wᵀΣw = 0.75 Σᵢ(wᵢ volᵢ)² + 0.25(Σᵢ wᵢ volᵢ)²

## Cluster results

I submitted normal_validation.slurm from my cluster account, pc17. Job 30985 completed on 16 November 2026 with State COMPLETED and ExitCode 0:0.

| Seed | Estimated VaR (€) | VaR relative error | Estimated ES (€) | ES relative error |
|---|---:|---:|---:|---:|
| 11 | 2227.9499 | 0.174% | 2551.7356 | 0.204% |
| 22 | 2229.1549 | 0.120% | 2557.0895 | 0.006% |
| 33 | 2228.3845 | 0.155% | 2555.2615 | 0.066% |

All six comparisons passed the 1% tolerance.

The cluster environment used Python 3.12.15 and NumPy 2.5.4. OMP_NUM_THREADS, OPENBLAS_NUM_THREADS and MKL_NUM_THREADS were fixed to 1.

The process resource report recorded 0.57 seconds of wall time and maximum resident memory of 58,088 KB. Slurm reported an elapsed time of one second. This small validation run is separate from the project's full-size performance baseline.

I saved the evidence in:

- results/normal-validation-30985/validation.csv
- results/normal-validation-30985/job_status.txt
- results/normal-validation-30985/resources.txt
- normal-validation-30985.out

The CSV contains full-precision estimates, analytical answers, absolute and relative errors, pass flags and execution metadata.

## Tolerance and interpretation

I used a provisional 1% relative-error tolerance for each metric and each seed. This is a practical acceptance threshold for the million-scenario reference case, not a derived confidence interval.

The tolerance remained unchanged after testing. All three seeds passed, but three successful seeds do not establish the probability of passing for every possible seed.

The differences between simulated estimates and analytical answers require three distinctions:

- Sampling error arises because a finite random sample differs from the full theoretical distribution. It changes with the seed.
- Arithmetic roundoff arises from finite floating-point precision. It is separate from Monte Carlo sampling variation.
- Model uncertainty concerns whether the assumed return distribution describes actual markets. Agreement with an analytical answer does not establish that the assumptions are realistic.

## What this validates

These results show that the simulated VaR and ES estimates are close to the analytical answers for the specified one-day arithmetic-normal portfolio.

This does not prove that the crisis model is realistic or analytically validate monthly compounded maximum drawdown. The reference case measures one-day terminal loss, while the main simulation measures drawdown over multiple days.

The existing check.py hand-path and controlled-model checks address other aspects of the calculation. check_parallel.py checks agreement between execution methods. These checks complement the independent normal reference case.

## Reproduction

From the repository root, with NumPy installed:

```bash
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

python validate_normal.py \
  --scenarios 1000000 \
  --seed 11 22 33 \
  --batch-size 4096 \
  --output results/normal-validation-local/validation.csv
```

The script rejects an existing output file to preserve previous evidence. It returns a non-zero exit code if a tolerance comparison fails or an execution error occurs.

Reproduction requires retaining the scenario count, seeds, batch size, code and numerical-library versions. Changing the batch size changes the assignment of random streams.

For a new university cluster run:

```bash
sbatch normal_validation.slurm
squeue -u "$USER"
```

After completion, replace ID with the new job number:

```bash
sacct -j ID -o JobID,State,Elapsed,ExitCode
cat normal-validation-ID.out
cat results/normal-validation-ID/validation.csv
```

My completed run is job 30985; it does not need to be submitted again. The saved scripts and small evidence files are included in the repository. No .npy arrays are produced.

## Conclusion

For all three seeds, the simulated VaR and ES were within 1% of their analytical values. This provides a reproducible known-answer check for the simple normal reference case, alongside the project's existing correctness and parallel-equivalence checks.
