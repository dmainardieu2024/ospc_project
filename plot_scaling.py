"""Rebuild the first scaling figure and summary from the raw timing CSV."""

import argparse
import csv
import json
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="Directory containing timings.csv and metadata.json")
    args = parser.parse_args()
    from pathlib import Path
    directory = Path(args.directory)
    metadata = json.loads((directory / "metadata.json").read_text())
    if metadata.get("status") != "completed":
        raise ValueError("Benchmark did not complete; do not plot partial data as a complete experiment")
    with (directory / "timings.csv").open() as file:
        rows = list(csv.DictReader(file))
    groups = defaultdict(list)
    for row in rows:
        if row["correct"] != "True":
            raise ValueError("Incorrect results cannot be used for performance plots")
        groups[(row["version"], int(row["workers"]))].append(float(row["elapsed_seconds"]))
    expected = {(method, workers) for method in metadata["methods"] for workers in metadata["workers"]}
    expected.add(("sequential", 1))
    if set(groups) != expected:
        raise ValueError("Missing or unexpected configurations")
    if any(len(times) != metadata["repeats"] or len(times) < 5 for times in groups.values()):
        raise ValueError("Every configuration must have the expected number of repeats (>=5)")
    baseline = statistics.median(groups[("sequential", 1)])
    summary = []
    for (method, workers), times in sorted(groups.items()):
        median = statistics.median(times)
        summary.append({"version": method, "workers": workers, "repeats": len(times),
                        "median_seconds": median, "min_seconds": min(times),
                        "max_seconds": max(times), "speedup_vs_sequential": baseline / median,
                        "efficiency_vs_sequential": baseline / median / workers})
    with (directory / "scaling_summary.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.7))
    colors = {"threads": "#2878B5", "processes": "#D46A28"}
    for method in dict.fromkeys(metadata["methods"]):
        selected = sorted((row for row in summary if row["version"] == method),
                          key=lambda row: row["workers"])
        x = [row["workers"] for row in selected]
        y = [row["median_seconds"] for row in selected]
        error = [[row["median_seconds"] - row["min_seconds"] for row in selected],
                 [row["max_seconds"] - row["median_seconds"] for row in selected]]
        axes[0].errorbar(x, y, yerr=error, fmt="o-", capsize=4,
                         color=colors[method], label=method.title())
        axes[1].plot(x, [row["speedup_vs_sequential"] for row in selected],
                     "o-", color=colors[method], label=method.title())
    workers = sorted(set(metadata["workers"]))
    axes[0].plot(workers, [baseline / n for n in workers], "--", color="0.5", label="Ideal")
    axes[0].axhline(baseline, color="0.3", linestyle=":", label="Sequential median")
    axes[1].plot(workers, workers, "--", color="0.5", label="Ideal")
    axes[0].set_ylabel("Computation time (seconds)")
    axes[1].set_ylabel("Speedup vs sequential median")
    for axis in axes:
        axis.set_xscale("log", base=2)
        axis.set_xticks(workers, [str(n) for n in workers])
        axis.set_xlabel("Workers")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=8)
    label = "LOCAL DEVELOPMENT TEST" if metadata["context"] == "local_preview" else "First cluster strong-scaling experiment"
    fig.suptitle(f"{label}\n{metadata['scenarios']:,} months · {metadata['settings']['assets']} stocks · {metadata['settings']['days']} days")
    note = (f"{metadata['repeats']} repeats; runtime bars show min–max. Pool startup and gathering included. "
            f"Node: {metadata['node']}; job: {metadata['slurm_job_id']}.")
    if metadata.get("resume_attempts"):
        jobs = list(dict.fromkeys([str(metadata['slurm_job_id'])] +
                    [str(attempt['job_id']) for attempt in metadata['resume_attempts']]))
        note = (f"{metadata['repeats']} repeats; runtime bars show min–max. Pool startup and gathering included. "
                f"Node: {metadata['node']}; jobs: {', '.join(jobs)}."
                "\nResumed after preemption; measurements span allocations.")
    if not metadata["sequential_median_at_least_10_minutes"]:
        note += "\nPreliminary size: the final 10-minute sequential-workload requirement is not met."
    fig.text(0.5, 0.015, note, ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.105, 1, 0.90))
    fig.savefig(directory / "strong_scaling.png", dpi=180)
    fig.savefig(directory / "strong_scaling.pdf")
    plt.close(fig)
    print(f"Saved strong_scaling.png, strong_scaling.pdf, and scaling_summary.csv in {directory}")


if __name__ == "__main__":
    main()
