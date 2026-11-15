"""Synthetic monthly paths, generated in reproducible, memory-bounded batches."""

import argparse
import csv
import json
import os
import platform
import socket
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Settings:
    # Illustrative assumptions, not estimates fitted to historical data.
    days: int = 20
    assets: int = 50
    initial_value: float = 100_000.0
    normal_log_mean: float = 0.0002
    crisis_log_mean: float = -0.005
    normal_log_vol: float = 0.012
    crisis_log_vol: float = 0.035
    normal_correlation: float = 0.25
    crisis_correlation: float = 0.80
    enter_crisis_probability: float = 0.01
    leave_crisis_probability: float = 0.20


def maximum_drawdown(values):
    """One row per scenario; include the starting value in column zero."""
    peaks = np.maximum.accumulate(values, axis=1)
    return np.max(1.0 - values / peaks, axis=1)


def simulate_batch(settings, count, seed, model):
    """Buy and hold equal initial allocations; do not rebalance each day."""
    rng = np.random.default_rng(seed)
    positions = np.full((count, settings.assets),
                        settings.initial_value / settings.assets)
    values = np.empty((count, settings.days + 1))
    values[:, 0] = settings.initial_value
    crisis = np.zeros(count, dtype=bool)  # Today starts in normal mode.
    crisis_days = np.zeros(count, dtype=int)
    # Fixed heterogeneity: some assets fluctuate more than others.
    asset_volatility = np.linspace(0.8, 1.2, settings.assets)

    for day in range(settings.days):
        # Both models draw the same random inputs for a given batch seed.
        transition = rng.random(count)
        market_shock = rng.standard_normal((count, 1))
        individual_shock = rng.standard_normal((count, settings.assets))
        if model == "crisis":
            crisis = np.where(crisis,
                              transition >= settings.leave_crisis_probability,
                              transition < settings.enter_crisis_probability)
        crisis_days += crisis
        mean = np.where(crisis, settings.crisis_log_mean,
                        settings.normal_log_mean)[:, None]
        volatility = np.where(crisis, settings.crisis_log_vol,
                              settings.normal_log_vol)[:, None]
        correlation = np.where(crisis, settings.crisis_correlation,
                               settings.normal_correlation)[:, None]
        shock = (np.sqrt(correlation) * market_shock
                 + np.sqrt(1.0 - correlation) * individual_shock)
        log_return = mean + volatility * asset_volatility * shock
        positions *= np.exp(log_return)  # Positive prices, compounded daily.
        values[:, day + 1] = positions.sum(axis=1)

    return values, maximum_drawdown(values), crisis_days


def generate(settings, scenarios, batch_size, seed, model):
    # Streams belong to fixed batch IDs, never to worker IDs. Future parallel
    # implementations must use these same batches, seeds, and output ordering.
    batches = (scenarios + batch_size - 1) // batch_size
    batch_seeds = np.random.SeedSequence(seed).spawn(batches)
    for batch_id, batch_seed in enumerate(batch_seeds):
        start = batch_id * batch_size
        count = min(batch_size, scenarios - start)
        yield start, simulate_batch(settings, count, batch_seed, model)


def compute(settings, scenarios, batch_size, seed, model):
    start_time = time.perf_counter()
    drawdowns = np.empty(scenarios)
    final_values = np.empty(scenarios)
    crisis_days = np.empty(scenarios, dtype=np.int32)
    example_paths = []
    for start, (values, batch_drawdowns, batch_crisis_days) in generate(
            settings, scenarios, batch_size, seed, model):
        stop = start + len(values)
        drawdowns[start:stop] = batch_drawdowns
        final_values[start:stop] = values[:, -1]
        crisis_days[start:stop] = batch_crisis_days
        if start == 0:
            example_paths = values[:5].copy()
    compute_seconds = time.perf_counter() - start_time
    return drawdowns, final_values, crisis_days, example_paths, compute_seconds


def run(settings, scenarios, batch_size, seed, model, output, output_format="binary"):
    if (output / f"{model}_summary.json").exists():
        raise FileExistsError(f"Results already exist in {output}; choose a new --output folder.")
    drawdowns, final_values, crisis_days, example_paths, compute_seconds = compute(
        settings, scenarios, batch_size, seed, model)

    analysis_start = time.perf_counter()
    # Use exactly ceil(1% * N) observations for the empirical worst-tail mean.
    tail_count = max(1, int(np.ceil(0.01 * scenarios)))
    percentile = float(np.quantile(drawdowns, 0.99))
    # Partition selects the worst tail without sorting all N observations.
    partitioned = np.partition(drawdowns, scenarios - tail_count)
    summary = {
        "model": model,
        "scenarios": scenarios,
        "seed": seed,
        "batch_size": batch_size,
        "settings": asdict(settings),
        "drawdown_99th_percentile": percentile,
        "mean_drawdown_worst_one_percent": float(partitioned[-tail_count:].mean()),
        "worst_tail_sample_count": tail_count,
        "probability_drawdown_above_20_percent": float(np.mean(drawdowns > 0.20)),
        "fraction_months_with_crisis_days": float(np.mean(crisis_days > 0)),
        "path_generation_and_drawdown_seconds": compute_seconds,
        "risk_summary_seconds": time.perf_counter() - analysis_start,
        "numpy_version": np.__version__,
        "python_version": platform.python_version(),
        "date_utc": datetime.now(timezone.utc).isoformat(),
        "node": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "slurm_cpus_per_task": os.environ.get("SLURM_CPUS_PER_TASK"),
        "node_load_at_summary": list(os.getloadavg()),
        "output_format": output_format,
        "asset_day_updates": scenarios * settings.days * settings.assets,
        "hypothetical_full_asset_path_bytes": scenarios * (settings.days + 1) * settings.assets * 8,
        "saved_scenario_array_bytes": scenarios * 20,
        "one_core_10_minute_compute_requirement_met": compute_seconds >= 600,
        "warning": "Synthetic assumptions, not calibrated market risk. Runtime qualifies only with a verified one-core cluster allocation.",
    }

    del partitioned
    output.mkdir(parents=True, exist_ok=True)
    write_start = time.perf_counter()
    if output_format == "binary":
        np.save(output / f"{model}_drawdowns.npy", drawdowns, allow_pickle=False)
        np.save(output / f"{model}_final_values.npy", final_values, allow_pickle=False)
        np.save(output / f"{model}_crisis_days.npy", crisis_days, allow_pickle=False)
    else:
        with (output / f"{model}_scenarios.csv").open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["scenario_id", "final_value_eur", "final_loss_eur",
                             "maximum_drawdown_fraction", "crisis_days"])
            for i in range(scenarios):
                writer.writerow([i, final_values[i], settings.initial_value - final_values[i],
                                 drawdowns[i], crisis_days[i]])
    with (output / f"{model}_example_paths.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["scenario_id"] + [f"day_{d}" for d in range(settings.days + 1)])
        for i, path in enumerate(example_paths):
            writer.writerow([i] + path.tolist())
    summary["data_writing_seconds"] = time.perf_counter() - write_start
    (output / f"{model}_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", type=int, default=1000)
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--assets", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20261115)
    parser.add_argument("--model", choices=["normal", "crisis", "both"], default="both")
    parser.add_argument("--output", type=Path, default=Path("results/demo"))
    parser.add_argument("--output-format", choices=["binary", "csv"], default="binary")
    args = parser.parse_args()
    if min(args.scenarios, args.days, args.assets, args.batch_size) < 1:
        parser.error("Scenario count, days, assets, and batch size must be positive.")
    settings = Settings(days=args.days, assets=args.assets)
    models = ["normal", "crisis"] if args.model == "both" else [args.model]
    for model in models:
        run(settings, args.scenarios, args.batch_size, args.seed, model, args.output,
            args.output_format)
