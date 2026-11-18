"""One-at-a-time crisis sensitivity with paired random streams and small outputs."""
import argparse
import csv
import hashlib
import json
import os
import platform
import socket
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from calculations.simulate import Settings, compute
from calculations.sampling_variation import METRICS, summarise

PARAMETERS = ['crisis_log_vol', 'crisis_correlation', 'enter_crisis_probability']


def cases():
    baseline = Settings()
    yield 'baseline', '', 1.0, baseline
    for parameter in PARAMETERS:
        for factor, suffix in [(0.8, 'low'), (1.2, 'high')]:
            value = getattr(baseline, parameter) * factor
            yield parameter + '_' + suffix, parameter, factor, replace(baseline, **{parameter: value})


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', type=int, default=262144)
    parser.add_argument('--batch-size', type=int, default=4096)
    parser.add_argument('--seeds', type=int, nargs='+', default=[101,202,303,404,505])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if min(args.scenarios, args.batch_size) < 1 or min(args.seeds) < 0:
        parser.error('Positive counts and non-negative seeds required')
    if len(args.seeds) < 3 or len(set(args.seeds)) != len(args.seeds):
        parser.error('Use at least three distinct seeds')
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
        if os.environ.get(name) != '1':
            parser.error(f'Set {name}=1 before starting Python')
    if args.output.exists():
        parser.error('Output already exists; use a fresh directory')
    args.output.mkdir(parents=True)
    design = list(cases())
    sources = ['calculations/simulate.py', 'calculations/sampling_variation.py',
               'calculations/parameter_sensitivity.py', 'calculations/jobs/parameter_sensitivity.slurm']
    metadata = dict(experiment='one_at_a_time_parameter_sensitivity', status='running',
        date_utc=datetime.now(timezone.utc).isoformat(), model='crisis', scenarios=args.scenarios,
        batch_size=args.batch_size, seeds=args.seeds,
        cases={name: asdict(settings) for name, _, _, settings in design},
        source_sha256={name: hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in sources},
        python_version=platform.python_version(), numpy_version=np.__version__,
        node=socket.gethostname(), slurm_job_id=os.environ.get('SLURM_JOB_ID'),
        interpretation='Paired changes conditional on synthetic assumptions; no confidence intervals or causal market claims.')
    meta_path = args.output/'metadata.json'
    meta_path.write_text(json.dumps(metadata, indent=2)+'\n')
    rows = []
    for name, parameter, factor, settings in design:
        for seed in args.seeds:
            dd, fv, days, paths, seconds = compute(settings, args.scenarios, args.batch_size, seed, 'crisis')
            rows.append(dict(case=name, changed_parameter=parameter, factor=factor,
                parameter_value=getattr(settings, parameter) if parameter else '', seed=seed,
                scenarios=args.scenarios, batch_size=args.batch_size,
                **summarise(dd, days), compute_seconds=seconds))
            # Keep partial evidence if the job is interrupted; status remains running.
            write_csv(args.output/'seed_estimates.csv', rows)
            print(f'{name} seed={seed}: drawdown99={rows[-1][METRICS[0]]:.6f}', flush=True)
            del dd, fv, days, paths
    baseline = {r['seed']: r for r in rows if r['case']=='baseline'}
    paired = []
    summary = []
    for name, parameter, factor, settings in design:
        current = [r for r in rows if r['case']==name]
        for metric in METRICS:
            values = np.array([r[metric] for r in current])*100
            changes = np.array([(r[metric]-baseline[r['seed']][metric])*100 for r in current])
            summary.append(dict(case=name, metric=metric, seed_count=len(current),
                mean_percent=values.mean(), mean_paired_change_pp=changes.mean(),
                sample_sd_paired_change_pp=changes.std(ddof=1),
                min_paired_change_pp=changes.min(), max_paired_change_pp=changes.max()))
            if name != 'baseline':
                for r, change in zip(current, changes):
                    paired.append(dict(case=name, metric=metric, seed=r['seed'],
                        baseline_percent=baseline[r['seed']][metric]*100,
                        variant_percent=r[metric]*100, paired_change_pp=change))
    write_csv(args.output/'paired_changes.csv', paired)
    write_csv(args.output/'sensitivity_summary.csv', summary)
    metadata['status']='completed'
    meta_path.write_text(json.dumps(metadata, indent=2)+'\n')


if __name__ == '__main__':
    main()
