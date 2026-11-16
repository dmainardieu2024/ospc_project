# Work packages for the 17 November progress review

Assign one owner to A, B, C and D. Diego owns job 30691, collecting its results,
integration, and the shared review explanation. These are four real work packages,
not a requirement to duplicate experiments. Agree the owners before starting.

## Everyone: get oriented first (about 15 minutes)

1. Sign into your own GitHub account, accept Diego's collaborator invitation,
   and open https://github.com/dmainardieu2024/ospc_project.
2. Read README.md sections 1-4, then the completed-experiment sections of
   PROJECT_LOG.md. A month has 20 days; the full workload has 64 million months.
3. Say back the difference between the normal/crisis financial models and
   sequential/thread/process execution. They are two separate comparisons.
4. For technical tasks, open your own cluster account at
   https://jupyter.iesci.tech:8085 and choose File > New > Terminal.
5. Get a working copy. If your course Git authentication already works, use
   the clone instructions in README.md. If it does not, use the simple ZIP route:
   - On GitHub, choose Code > Download ZIP while signed in.
   - Upload ospc_project-main.zip into your own JupyterLab home with its upload button.
   - In the cluster terminal run the following (the ZIP is expected to contain
     the default main-branch folder; inspect its actual name if yours differs):

```bash
cd ~
unzip -q ospc_project-main.zip
cd ospc_project-main
export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
python check.py
python check_parallel.py
```

Use a fresh destination if that ZIP folder already exists; do not overwrite
someone's working files. A ZIP copy has no Git history or automatic sync.
For ZIP-based work, download your new small deliverables from JupyterLab, then
upload them through the signed-in GitHub website under their intended paths.
Use your own account and a meaningful commit message. With a Git clone, commit
and push your named task files normally. Do not commit large .npy arrays, caches,
tokens, or other people's unreviewed files. Never share the pc47 login.

If a required script is missing from GitHub, report its exact filename to Diego.
Files existing only in Diego's JupyterLab are not available to the team.

## A — Independently reproduce and explain the project

**Goal:** establish that a teammate can run the project from GitHub, and create
the short explanation the whole group will rehearse. This is not just proofreading.

1. Obtain a fresh copy from GitHub in YOUR account, following the setup above.
2. Run the two check scripts. Save their terminal output to new text files:

```bash
mkdir -p results/reproduction
python check.py > results/reproduction/check.txt 2>&1
python check_parallel.py > results/reproduction/check_parallel.txt 2>&1
python simulate.py --scenarios 1000 --batch-size 4096 --output results/reproduction/demo
```

3. Inspect both check reports; successful file creation does not itself prove
   the tests passed. Inspect the normal/crisis JSON summaries and an example-path CSV.
4. Rebuild the already completed preliminary graph (no simulations needed):

```bash
python plot_scaling.py results/scaling-30338
```

   If the CSV/metadata are absent, identify the missing evidence instead of
   inventing data or submitting a new scaling experiment.
5. Create REPRODUCTION.md: your name, date, Python/NumPy versions, source commit
   (or ZIP download date), exact commands, actual pass/fail output, missing files,
   and any README corrections. Do not write 'fully reproducible' until tested.
6. Create PROGRESS_REVIEW.md containing four recommended slide outlines:
   (1) question and feedback response; (2) what the program does and correctness;
   (3) scaling graph plus the full-size baseline evidence; (4) current problems,
   limitations, remaining tasks and questions for the professor.
   Label the preliminary graph as 2,097,152 months. Replace/supplement it with
   the 64-million graph only after job 30691 finishes successfully.
7. Commit your report and small reproduction evidence. Fix documentation based
   on your actual experience; do not silently edit the financial model.

**Done when:** another person can follow your corrected instructions, your check
outputs are saved, and every group member can follow the four-slide story.

## B — Profile runtime and prepare the Amdahl explanation

**Goal:** replace guesses about the bottleneck with measurements.

1. Get your own copy and pass the checks. Read simulate.py functions
   simulate_batch, generate and compute; identify what is independent per batch.
2. Confirm profile_baseline.slurm exists, then submit it ONCE:

```bash
sbatch profile_baseline.slurm
squeue -u "$USER"
```

3. Note YOUR new job ID. When it leaves the queue, check it with
   `sacct -j ID -o JobID,State,Elapsed,ExitCode`, replacing ID with your actual number.
4. Open results/profile-ID/top25.txt, profile_summary.json, resources.txt and
   data/crisis_summary.json. The job uses 1,048,576 months for diagnosis, not
   the final full-size timing. It saves both cumulative-time and exclusive-time
   rankings. Cumulative parent/child times overlap: do not add every row.
5. Create PROFILING.md. Identify the three most expensive useful functions/calls,
   their reported times, and whether they are per-batch simulation, setup,
   summary, or writing. Explain which work could be distributed among workers.
6. Use profile_summary.json's rough_non_batch_fraction as an INITIAL serial-fraction
   estimate. Explain its limits: profiler overhead, timer boundaries, native calls,
   and the fact that starting/copying work in a pool adds costs not present here.
   Do not force a negative/noisy diagnostic estimate into a precise physical claim.
7. Read the shared scaling_summary.csv. For each method and n>1, calculate the
   effective serial fraction `e = (1/S - 1/n) / (1 - 1/n)`, where S is the saved
   speedup_vs_sequential. Save a small amdahl_estimates.csv (method, workers, S, e).
   Use preliminary results first; update with full results once shared.
8. Compare the profile estimate with e as n grows. Explain that this inferred
   fraction also absorbs overhead/contention; it is not a direct measurement of
   a fixed serial section. State what remains unproven about the slowdown.
9. Commit the .slurm file, profile reports, PROFILING.md and the Amdahl table;
   exclude generated .npy arrays. Raw .pstats can be kept if small.

**Done when:** the group has a measured bottleneck, a qualified initial serial
estimate and an explanation of what Amdahl does/does not account for.

## C — Build the professor's independent known-answer case

**Goal:** implement the separate simple case for which the financial answer is
known. This is NEW work; validate_normal.py does not exist yet.

1. Read the professor's feedback and the existing check.py. Understand why
   parallel versions agreeing is different from agreeing with a known answer.
2. Create validate_normal.py WITHOUT changing simulate.py. Define this deliberately
   simple ONE-DAY arithmetic-normal portfolio (not monthly compounded drawdown):
   portfolio EUR 100,000; 5 assets with weights 0.2 each; mean returns all zero;
   daily volatilities [0.010, 0.012, 0.015, 0.018, 0.020]; correlation 0.25 between
   distinct assets. Covariance[i,j] = vol[i]*vol[j]*correlation[i,j], with a unit diagonal.
3. Independently calculate the portfolio loss standard deviation:
   sigma_L = 100000 * sqrt(w.T @ covariance @ w). With zero means, loss mean is zero.
4. Compute z = statistics.NormalDist().inv_cdf(0.99). Calculate known answers:
   VaR99 = z*sigma_L; ES99 = sigma_L*exp(-z*z/2)/(sqrt(2*pi)*0.01).
   Expected check values: sigma_L about EUR 959.3748, VaR about EUR 2231.8395,
   ES about EUR 2556.9394. Derive these in your own code and cite the formula source.
5. Simulate 1,000,000 correlated one-day arithmetic return vectors in batches
   (use SeedSequence.spawn and a Cholesky factor or a correctly constructed common
   factor). Loss = -100000*(return_vector @ weights). Estimate the 99th percentile
   and mean of the largest 1% of losses. Do NOT average worker-level quantiles.
6. Run this with seeds 11, 22 and 33 in a small Slurm batch job with library
   threads fixed to 1. Give --scenarios and --seed CLI arguments. Save one CSV row
   per seed with known answer, estimated answer, absolute and relative errors.
   Exact equality is not expected: these errors include sampling variation.
7. Choose and justify a sampling tolerance. A provisional 1% relative tolerance
   can be checked across these seeds; do not present it as a derived confidence
   interval or loosen it silently until tests pass.
8. Create NORMAL_VALIDATION.md: formulas, model inputs, the result table,
   interpretation, and limits. Explain explicitly: this is the professor's simple
   normal reference case; it does not prove the crisis model is realistic or
   analytically validate the monthly drawdown distribution. Existing hand-path
   checks and equivalence tests address other aspects of our current calculation.
9. Commit your new script, Slurm script, report and small CSV. Explain the code
   to the group rather than submitting code you cannot describe.

Formula reference: https://www.mathworks.com/help/risk/estimate-expected-shortfall-with-the-expectedShortfall-function.html

**Done when:** the group has reproducible known-answer comparisons and can
distinguish sampling error, arithmetic roundoff and model uncertainty.

## D — Complete the full normal/crisis financial comparison

**Goal:** compare BOTH market models at the same full scenario count. So far only
the crisis model has completed a 64-million-month financial run.

1. Get your own copy and pass the checks. Read the Settings table in simulate.py
   and the full crisis JSON already in results/full-baseline-30375/data/.
2. Submit the provided normal-model job ONCE in YOUR account:

```bash
sbatch normal_comparison.slurm
squeue -u "$USER"
```

3. Record your job ID. After completion inspect its sacct status, Slurm output,
   results/normal-ID/resources.txt and data/normal_summary.json. It runs the same
   64 million months, 50 assets, 20 days, seed and 4,096 batch size, with crisis
   switching disabled. It requests only two CPUs; estimated compute time is
   around the measured baseline magnitude, but queue/runtime are not guaranteed.
4. Compare your normal summary with the saved crisis_summary.json. Verify the
   settings match apart from model choice; note NumPy versions if they differ.
   Same seeded inputs do not imply identical price paths because model rules differ.
5. Create financial_comparison.csv with one row per model: scenario count,
   drawdown_99th_percentile, mean_drawdown_worst_one_percent,
   probability_drawdown_above_20_percent, fraction_months_with_crisis_days.
6. Write a short script that reads these JSONs and creates one labelled bar
   chart of the threshold and tail average in PERCENT, not raw fractions. Save
   the comparison script so the chart is reproducible.
7. Create FINANCIAL_RESULTS.md: explain the numbers and assumptions, distinguish
   drawdown from final loss, and state that the settings change together. We
   have not isolated which assumption caused how much change, and the chart
   does not measure real market risk or statistical confidence.
8. Commit the comparison script, small JSON/CSV evidence, report, chart and job
   script. Keep the approximately 1.28 GB .npy output arrays out of Git.

**Done when:** we can show a fair full-size financial comparison, separately
from the graph comparing execution speed.

## WHEN READY (64 Million run) — integrate and prepare the group for tomorrow

1. Do not submit a duplicate of job 30691. A teammate can inspect its state with
   `squeue -u pc47`. It needs the pc47 Jupyter server stopped to use the 64-CPU cap.
2. When it has ended, restart your server and inspect:

```bash
sacct -j 30691 -o JobID,State,Elapsed,ExitCode
tail -n 30 ~/ospc_project/full-scaling-30691.out
```

3. If completed successfully, open results/full-scaling-30691/strong_scaling.png
   and scaling_summary.csv. They should already exist. If plotting needs to be
   repeated after a display/file problem, run only:

```bash
/data/software/envs/ospc/bin/python plot_scaling.py results/full-scaling-30691
```

   If the script reports incomplete/failed data, inspect the job; do not label a
   partial run as complete or rerun all simulations without diagnosing the issue.
4. Commit and push the small full-scaling result directory so teammates can get
   it. Update PROJECT_LOG.md with the actual outcome; submitted is not completed.
5. Integrate teammates' reports. Hold a walkthrough: each member explains one
   scenario, one batch, a correctness check, and one graph point in their own words.
6. Assemble the four-slide outline from task A using actual results. Keep the
   first graph as a labelled fallback if the new job fails or is still pending.
7. Explain the revised model and unresolved questions to the professor through
   the group Blackboard conversation or in tomorrow's review. The final report
   and shared-memory/weak-scaling work are not all due tomorrow.

## A practical 'ready for tomorrow' checklist

- Everyone can explain the question and why simulation is useful for it.
- Show one honest, labelled scaling plot, repeats/spread and correctness evidence.
- Show the verified >=10-minute full-size baseline.
- Explain the initial resource diagnosis and profiling results if available.
- Describe what remains unproven; identify who is doing the next tasks.
- Explain how the revised approach addresses each professor comment.
- Know the next steps: overhead/shared memory, weak scaling, uncertainty/sensitivity,
  final presentation/report and reproducibility. They are not all finished tomorrow.
