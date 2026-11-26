# Course hand-in

| Deliverable | Where to find it |
| --- | --- |
| Source, build, solver options and cluster setup | [Project README](../README.md) and [example hostfile](../part0/config/hosts.example) |
| Original assignment and numerical notes | [Course PDFs](assignment/README.md) |
| Written background tasks | [Solutions PDF and reproduction files](background-solutions/README.md) |
| Final report | [Ten main pages plus three appendices](final-report/final-report.pdf) |
| Setup evidence | [Three inventories and six directed SSH checks](part0-closeout.md) and [six ping-pong sweeps](../part0/results/README.md) |
| Serial correctness | [Five-grid convergence and deliberate instability](../part1/ANALYSIS.md) |
| Parallel correctness | [Strips, 84 exact comparisons](../part2/results/README.md) and [blocks, 108 exact comparisons](../part3/results/README.md) |
| Performance study | [429 timings in 143 configurations, 18 calibration sweeps and 16 placement probes](../part4/results/README.md) |
| AI records | [Logging instructions](../AGENTS.md) and [private export status](../llm_log/README.md) |

Part 3 includes both layouts at P=4 and P=8 for N=512, 2048 and 8192. The
[layout table](../part4/layout-comparison.csv) adds both placement policies from
the full Part 4 study. The measured P=8 runs used eight real guest vCPUs
allocated 4+2+2. Part 0 used a historical 2+2+2 allocation. CUDA and
nonblocking overlap are optional extensions.

Run `make verify-delivery` from the repository root to check hashes, coverage,
field equality and the performance tables. The check reads the saved evidence.
The dated raw measurements include route changes, warning-only attempts and
an MPI failure caused by a lost peer. Preserve these records and their manifests.

## Live demonstration

If the ten-minute presentation is pending, use the three VMs on the measurement
network. Build the same revision on each VM, then run from heat-1 as `mpi`:

```bash
python3 scripts/run-demo.py --N 32 --P 3 --steps 40 --decomp blocks
python3 scripts/run-demo.py --run --N 32 --P 3 --steps 40 --decomp blocks
```

The first command previews the run. The second runs both cases, confirms
three-VM participation, compares the fields against serial and writes a heat
map. Change N or P if requested during the presentation. The [demo and report
guide](final-report/README.md) has display and rehearsal details.

## Package and submit

1. Confirm the shared contribution statement in the report and verify every
   team member’s complete visible AI conversations, dates, tools and model
   metadata. Include these in the private submission. Earlier missing
   conversations and instructor acceptance remain unverified.
2. Generate the source snapshot and private supplement from a Git checkout
   with `python3 scripts/package-submission.py`. The script writes both ZIPs
   to `output/submission/`. It can recover the original Parts 2/3 and 4
   archives from an existing verified private ZIP or the original downloads.
3. Hand in the repository or its source snapshot, the report, the separate
   solutions PDF and the private course material. Use a Git checkout when
   running scripts that verify revision metadata. Keep the private ZIP,
   private configuration and original transcripts off public Git.

Archive new experimental data in separate directories. Keep reviewed CSVs,
plots, raw output, manifests and retained MPI fields together. Build products,
temporary runs, local review copies and private exports are ignored.

## Maintenance and history

- [VM update workflow](local-update.md)
- [Cluster inventory](cluster-inventory.md)
- [Parts 2 and 3 rerun instructions](parts2-3-rerun.md)
- [Original sources and provenance](history/README.md)
