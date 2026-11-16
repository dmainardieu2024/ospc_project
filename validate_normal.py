"""Independent one-day arithmetic-normal reference; does not import simulate.py.
Formula: https://www.mathworks.com/help/risk/estimate-expected-shortfall-with-the-expectedShortfall-function.html
"""
import argparse
import csv
import math
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from statistics import NormalDist

import numpy as np


def validate(scenarios, seed, batch_size, tolerance):
    weights = np.full(5, 0.2)
    vol = np.array([0.010, 0.012, 0.015, 0.018, 0.020])
    correlation = np.full((5, 5), 0.25)
    np.fill_diagonal(correlation, 1.0)
    covariance = np.outer(vol, vol) * correlation
    sigma = 100000 * math.sqrt(float(weights @ covariance @ weights))
    z = NormalDist().inv_cdf(0.99)
    known_var = z * sigma
    known_es = sigma * math.exp(-z*z/2) / (math.sqrt(2*math.pi)*0.01)
    # Independent algebraic check of the equicorrelation portfolio variance.
    exposures = weights * vol
    variance_check = 0.75 * np.sum(exposures**2) + 0.25 * np.sum(exposures)**2
    np.testing.assert_allclose(sigma**2, 100000**2 * variance_check, rtol=1e-12)
    factor = np.linalg.cholesky(covariance)
    np.testing.assert_allclose(factor @ factor.T, covariance, rtol=1e-12, atol=1e-18)
    losses = np.empty(scenarios)
    seeds = np.random.SeedSequence(seed).spawn((scenarios + batch_size - 1)//batch_size)
    for batch_id, child in enumerate(seeds):
        start = batch_id * batch_size
        stop = min(start + batch_size, scenarios)
        rng = np.random.default_rng(child)
        # Row-vector convention: Z @ L.T has covariance L @ L.T.
        returns = rng.standard_normal((stop-start, 5)) @ factor.T
        losses[start:stop] = -100000 * (returns @ weights)
    estimate_var = float(np.quantile(losses, 0.99, method='linear'))
    tail_count = max(1, math.ceil(0.01 * scenarios))
    estimate_es = float(np.partition(losses, scenarios-tail_count)[-tail_count:].mean())
    row = dict(seed=seed, scenarios=scenarios, batch_size=batch_size,
               sigma_loss_eur=sigma, tail_count=tail_count)
    for label, known, estimated in [('var99', known_var, estimate_var), ('es99', known_es, estimate_es)]:
        error = abs(estimated-known)
        row.update({f'{label}_known_eur': known, f'{label}_estimated_eur': estimated,
                    f'{label}_absolute_error_eur': error, f'{label}_relative_error': error/known})
    row.update(tolerance=tolerance, passed=all(row[f'{x}_relative_error'] <= tolerance for x in ['var99','es99']),
               python_version=platform.python_version(), numpy_version=np.__version__,
               slurm_job_id=os.environ.get('SLURM_JOB_ID', ''), date_utc=datetime.now(timezone.utc).isoformat())
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', type=int, default=1000000)
    parser.add_argument('--seed', type=int, nargs='+', default=[11,22,33])
    parser.add_argument('--batch-size', type=int, default=4096)
    parser.add_argument('--tolerance', type=float, default=0.01)
    parser.add_argument('--output', type=Path, default=Path('results/normal-validation/validation.csv'))
    args = parser.parse_args()
    if args.scenarios < 1 or args.batch_size < 1 or min(args.seed) < 0 or not 0 < args.tolerance < 1:
        parser.error('Positive counts, non-negative seeds and tolerance between zero and one required.')
    if args.output.exists():
        parser.error('Output exists; choose a fresh path to preserve evidence.')
    rows = [validate(args.scenarios, seed, args.batch_size, args.tolerance) for seed in args.seed]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"seed={row['seed']}: VaR={row['var99_estimated_eur']:.4f}, ES={row['es99_estimated_eur']:.4f}, passed={row['passed']}")
    print(f'Results: {args.output}')
    return 0 if all(row['passed'] for row in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
