# Main performance experiment

**Show:** [graph](figures/strong_scaling.png). **Read:** [summary](measurements/scaling_summary.csv). **Audit:** [65 timings](measurements/timings.csv), [metadata](run_details/metadata.json).

## What this proves

Same 64 million months, 50 stocks, 20 days. Sequential median 810.94 s; fastest 16 threads at 67.34 s (12.04x). Five repetitions of 13 configurations. Interrupted and resumed across allocations; disclose this limitation.

## Run identity

Job/account: 30691 and 31181. Original evidence bytes and metadata are preserved. See [path/provenance map](../../docs/REPOSITORY_MAP.md).

## File guide

- figures/: presentation graphs, where available.
- measurements/: numerical results.
- run_details/: settings, resource reports, logs and verification.
- check_outputs/: terminal reports for reproduction only.

Only sections with evidence are present.
