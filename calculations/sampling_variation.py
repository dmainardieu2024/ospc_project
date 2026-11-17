"""Repeat monthly risk estimates across seeds; save small evidence, not path arrays."""
import argparse
import csv
import json
import os
import platform
import socket
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from calculations.simulate import Settings, compute

METRICS = ['drawdown_99th_percentile', 'mean_drawdown_worst_one_percent',
           'probability_drawdown_above_20_percent', 'fraction_months_with_crisis_days']


def summarise(drawdowns, crisis_days):
    count = len(drawdowns)
    tail_count = max(1, int(np.ceil(0.01 * count)))
    return dict(zip(METRICS, [float(np.quantile(drawdowns, 0.99)),
        float(np.partition(drawdowns, count-tail_count)[-tail_count:].mean()),
        float(np.mean(drawdowns > 0.20)), float(np.mean(crisis_days > 0))]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenarios', type=int, default=262144)
    parser.add_argument('--batch-size', type=int, default=4096)
    parser.add_argument('--seeds', type=int, nargs='+', default=[101,202,303,404,505])
    parser.add_argument('--models', nargs='+', choices=['normal','crisis'], default=['normal','crisis'])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if min(args.scenarios, args.batch_size) < 1 or min(args.seeds) < 0:
        parser.error('Positive counts and non-negative seeds required')
    if len(set(args.seeds)) != len(args.seeds) or len(args.seeds) < 3:
        parser.error('Use at least three distinct seeds')
    if len(set(args.models)) != len(args.models):
        parser.error('Models must not repeat')
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
        if os.environ.get(name) != '1':
            parser.error(f'Set {name}=1 before starting Python')
    if args.output.exists():
        parser.error('Choose a new output directory; existing evidence is preserved')
    args.output.mkdir(parents=True)
    settings = Settings()
    try:
        commit = subprocess.check_output(['git','rev-parse','HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    metadata = dict(experiment='independent_seed_sampling_variation',
        date_utc=datetime.now(timezone.utc).isoformat(), scenarios=args.scenarios,
        batch_size=args.batch_size, seeds=args.seeds, models=args.models, settings=asdict(settings),
        python_version=platform.python_version(), numpy_version=np.__version__,
        node=socket.gethostname(), slurm_job_id=os.environ.get('SLURM_JOB_ID'),
        source_commit=commit, status='running',
        interpretation='Descriptive across-seed spread at this scenario count; not a confidence interval or model validation.')
    def save_metadata():
        (args.output/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
    save_metadata()
    rows=[]
    with (args.output/'seed_estimates.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['model','seed','scenarios','batch_size',*METRICS,'compute_seconds'])
        writer.writeheader()
        for model in args.models:
            for seed in args.seeds:
                drawdowns, final_values, days, paths, elapsed = compute(settings,args.scenarios,args.batch_size,seed,model)
                row=dict(model=model, seed=seed, scenarios=args.scenarios,batch_size=args.batch_size,
                         **summarise(drawdowns,days), compute_seconds=elapsed)
                writer.writerow(row)
                stream.flush()
                rows.append(row)
                print(f'{model} seed={seed}: drawdown99={row[METRICS[0]]:.6f}',flush=True)
                del drawdowns,final_values,days,paths
    with (args.output/'sampling_spread.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream, fieldnames=['model','metric','seed_count','mean_percent',
            'sample_sd_percentage_points','min_percent','max_percent','range_percentage_points'])
        writer.writeheader()
        for model in args.models:
            for metric in METRICS:
                values=np.array([r[metric] for r in rows if r['model']==model])*100
                writer.writerow(dict(model=model,metric=metric,seed_count=len(values),
                    mean_percent=values.mean(),sample_sd_percentage_points=values.std(ddof=1),
                    min_percent=values.min(),max_percent=values.max(),
                    range_percentage_points=np.ptp(values)))
    metadata['status']='completed'
    save_metadata()


if __name__ == '__main__':
    main()
