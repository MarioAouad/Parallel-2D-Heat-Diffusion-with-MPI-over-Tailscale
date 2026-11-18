# Results: six full sweeps from 17 November 2026 UTC

## Are these the original measurements?

Yes. The supplied export contains six CSVs, six progress logs, six metadata files and twelve route snapshots: **30 files**. Every CSV has 22 powers-of-two sizes from 8 B through 16 MiB. All **132 rows** match the earlier pasted terminal records numerically. Every progress log reports all sizes and successful completion; actual endpoint hostnames agree with the intended cases.

All public evidence files use generic node labels. CSV sizes, iteration/warm-up counts, times and throughput are preserved exactly as recorded; only identifying host fields are anonymized. Public metadata/routes remove real overlay/public addresses and account handles. Their timing, route type, pair and timestamps are retained. [file-manifest.json](file-manifest.json) contains hashes for both original and published versions; the private originals remain intact locally. Hashes establish the supplied-file/public-copy relationship, not an independent check against the live VMs.

The folder was exported from heat-1 using the existing Windows-to-VM SSH forwarding rule and recursive SCP of `/home/mpi/heat-project/results/full`. This was correct even for heat2-heat3: the launcher on heat-1 collected remote stdout/stderr and saved all case files. Copying did not run the benchmark again.

## What each archived file means

Each [case folder](2026-11-17/) has a timestamped `.csv`, `.log`, `.meta.txt`, `.route-before.txt` and `.route-after.txt`. Filenames give run-start UTC timestamps, not measured durations. Metadata records placement and the launching VM's MPI version. Before/after pings are separate observations outside the C++ measured loop.

The full-study folder does not include the earlier standalone SSH/Tailscale checks, hostname output, hello output, source/executable files, or smoke CSVs. Those are distinct evidence. Their historical success is documented in the guide/chat observations; do not invent missing raw terminal transcripts.

## Measured and derived numbers

| Case | Startup reference us | Large-message model MiB/s | 16 MiB RTT s | 16 MiB effective MiB/s |
| --- | --- | --- | --- | --- |
| heat1-local | 0.258 | 5829.8801 | 0.005876 | 5446.3190 |
| heat2-local | 0.412 | 3592.1907 | 0.009016 | 3549.1718 |
| heat3-local | 0.310 | 3406.0070 | 0.009565 | 3345.6283 |
| heat1-heat2 | 17728.317 | 0.1440 | 223.586401 | 0.1431 |
| heat1-heat3 | 60033.336 | 0.0706 | 455.605666 | 0.0702 |
| heat2-heat3 | 77603.552 | 0.0924 | 317.011046 | 0.1009 |

Startup is the median of four small-message half-RTT averages, expressed in **microseconds**. For the cross-VM cases the same numbers are approximately 17.73, 60.03 and 77.60 **milliseconds**. The large-message bandwidth column is a fitted model parameter. The final column is measured effective throughput at 16 MiB and includes startup; the two bandwidth columns answer different questions.

The very small same-VM times use Open MPI shared memory. Cross-VM values include TCP, Tailscale, the network, MPI overhead and scheduling. Local times do not represent an Internet path.

For example, heat1-heat2's 16 MiB round trip averaged 223.5864 seconds, about 111.7932 seconds for the half-RTT estimate. Its effective rate was about 0.1431 MiB/s. With three timed trips, the measured loop alone costs about 670.76 seconds, plus an untimed warm-up and calibration at that size. A long-running benchmark can therefore be functioning correctly. The run's entire wall time is not one average RTT.

## Route observations for these exact runs

| Pair | Before snapshot UTC | After snapshot UTC | Supported conclusion |
| --- | --- | --- | --- |
| heat1-heat2 | 20:17:40 direct, 15 ms | 20:55:09 direct, 16 ms | Direct in both snapshots; route continuity between them was not recorded |
| heat1-heat3 | 21:57:00 three DERP(par) replies, then direct at 70 ms | 23:09:35 direct, 61 ms | Pre-probe transitioned to direct before the benchmark; cannot label the timed run as relay merely from its first probe replies |
| heat2-heat3 | 20:56:24 ten DERP(ams) replies; no direct path established | 21:53:23 direct, 74 ms | Before/after path differs; transition time is unknown and may include the later probe establishing a path |

These probe times are Tailscale RTTs, not MPI one-way estimates. The heat2-heat3 warning is explained by relay replies without a direct connection: it was not a failed MPI run. Do not label that entire sweep “DERP” or “direct” without qualification.

**DERP cannot explain all slow throughput:** heat1-heat2 was direct in both snapshots and still slow. The files do not establish one specific bottleneck such as upload capacity, packet loss or congestion. Record additional evidence before naming a cause. A high fitted R-squared also does not prove stable routing.

## What we corrected in analysis

The original all-size unconstrained fit can give negative startup intercepts. These remain visible as diagnostics. The reviewed estimator anchors startup using the small-message reference and fits transfer slope over 1..16 MiB. Raw measurements are unchanged. [Analysis README](../05-analysis/README.md) explains the equations, units, warnings and every summary field.

The [derived summary](analysis/summary.csv) and six plots are reproducible from these exact CSVs. Analysis is offline; it does not rerun MPI. Use `make verify-results` and `make analyze` from the repository root.

## What the results do and do not establish

- All required local configurations and VM pairs completed and exchanged the expected final payload bytes.
- We have **one complete sweep per case**, with adaptive repeated exchanges inside it. Large messages used three timed trips; those are not three independent full experiments.
- There are no per-exchange timing samples or independent-sweep confidence intervals. Small-message min/max in the summary describe four per-size averages, not packet jitter distributions.
- Route snapshots are not continuous traces. The changing heat2-heat3 condition limits a single-condition model; prioritize a separately recorded stable-route repeat if stronger claims are needed.
- Complete all-machine hardware/software inventories and earlier setup/logging evidence remain separate tasks.
- This communication benchmark does not compute a temperature field, validate a numerical scheme, or complete C1/Parts 1-4.

## Why this matters later

For a strip solver, a full halo row has `N+1` doubles, or `8*(N+1)` bytes on these VMs. At N=1024 it is 8200 bytes, between sampled sizes. The grid/decomposition determines that payload; we are not selecting an optimal Internet packet size. Blocks change both edge lengths and neighbor counts. The model estimates the communication cost for those sizes; measured computation rates and the actual solver are still needed to predict speed-up.

Keep all six runs. Additional controlled measurements should be new files with their own route/inventory records, not replacements for inconvenient values.
