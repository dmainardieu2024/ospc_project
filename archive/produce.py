"""Produce both financial-model datasets using a cluster-calibrated plan."""

import argparse
import json
import os
from pathlib import Path

from simulate import Settings, run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    if plan["status"] != "cluster_calibrated_estimate":
        parser.error("A local preview cannot authorize a full production dataset. Calibrate on the cluster.")
    if not os.environ.get("SLURM_JOB_ID") or len(os.sched_getaffinity(0)) != 1:
        parser.error("Run production as a Slurm job pinned to one logical CPU for baseline verification.")
    for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        if os.environ.get(variable) != "1":
            parser.error(f"Set {variable}=1 before starting Python.")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Output directory must be empty to avoid replacing prior results.")
    settings = Settings(**plan["settings"])
    summaries = []
    # Same seed and batches couple the random inputs of the two financial models.
    for model in ["crisis", "normal"]:
        summaries.append(run(settings, plan["scenarios_per_model"], plan["batch_size"],
                             plan["seed"], model, args.output, "binary"))
    verified = summaries[0]["path_generation_and_drawdown_seconds"] >= 600
    args.output.joinpath("production_status.json").write_text(json.dumps({
        "crisis_workload_10_minute_baseline_verified": verified,
        "plan": plan,
        "next_step": ("Use this fixed workload for parallel equivalence/scaling experiments."
                      if verified else
                      "Do not finalize this size: increase scenario count and repeat the one-core run."),
    }, indent=2) + "\n")
    if not verified:
        raise SystemExit("Dataset saved, but crisis baseline was under 10 minutes. Increase N before finalizing size.")


if __name__ == "__main__":
    main()
