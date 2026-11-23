# Part 4 measured analysis

Revision: `1355492f732af771446a243ddd79ba9acaf262c7`. Profile: **full**. Mode: **cluster**.
Conditions supplied by operator: All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2
All session notes: ['All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2', 'Resuming after Open MPI parent setpgid warning; all laptops on AC; heavy applications closed; all three guests use Wi-Fi; allocation 4+2+2', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2; supervised recovery after reviewed launcher warnings', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2; supervised recovery after reviewed launcher warnings', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2; supervised recovery after reviewed launcher warnings', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2; supervised recovery after reviewed launcher warnings', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2; supervised recovery after reviewed launcher warnings', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2; supervised recovery after reviewed launcher warnings', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. Resuming after peer VM interruption and recovery; all laptops on AC; heavy applications closed; Wi-Fi unchanged; allocation 4+2+2', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. Resuming after peer VM interruption and recovery; all laptops on AC; heavy applications closed; Wi-Fi unchanged; allocation 4+2+2', 'Exact Open MPI parent setpgid Permission denied(13) warning-only heat attempts are retried at most 3 times per task and 32 times in this supervised session; all attempts retained. Resuming after peer VM interruption and recovery; all laptops on AC; heavy applications closed; Wi-Fi unchanged; allocation 4+2+2']
Failed invocation attempts retained in raw history: 1.
Network snapshot counters (mentions, not route-continuity proof): {'snapshots': 36, 'relay_mentions': 2, 'direct_mentions': 61}

This file summarizes recorded data; it is not the final ten-page course report.

## Does spreading work across VMs pay off?

Measured cross-VM speed-up over serial heat1 occurs at tested N: none.
The busiest-rank model predicts cross-VM speed-up at tested N: none.
These are tested sizes, not an interpolated crossover or proof about untested N.

## Model and discrepancies

Compute uses each guest's measured serial seconds per interior node, log-interpolated in global N. Strips use owned rows and N-1 columns; blocks use the actual uneven Cartesian split. Each neighbor contributes ts + doubles*tw; prediction is max over ranks of compute + summed neighbor exchanges. ts is the median half-RTT at 8..64 bytes; tw is eight times the anchored seconds/byte slope at the largest three sizes. All six same/cross-VM calibrations use the same TCP/self transport as the solvers. Half-RTT assumes directional symmetry. Pairwise estimates are not simultaneous contention measurements.

The model omits blocking-phase critical paths, cache changes, datatype packing, shared memory-bandwidth contention and interference on home links. Check raw network observations before attributing a mismatch to DERP or Wi-Fi; those observations do not prove route continuity. Per-host compute rates represent isolated serial execution, not simultaneous execution on every guest core.

## A one-microsecond interconnect

predictions.csv and the dotted strong-time curves replace every link startup with 1 microsecond, retaining measured bandwidth and compute rates. This isolates latency: a real cluster also changes bandwidth, hardware and contention, so it is not a forecast of a particular supercomputer.

## Advice for Tailscale

Select P/layout/placement from the measured configuration at the N you need, rather than assuming more processes are faster. A tested crossing is listed above. Keep power/load/allocation/transport fixed, prefer stable routes and retain spread, including slow results. Do not compare different N as a speed-up.

## Interpretation and scope

Strong speed-up uses the serial baseline on heat1 at the same N; therefore MPI P=1 need not have speed-up exactly 1. Efficiency divides that speed-up by P. Weak efficiency uses the same layout/placement's P=1 weak run. Weak N=round(base*sqrt(P))+1 fixes interior work approximately; the exact cells per rank and min/max owned cells are recorded. Raw per-run communication fraction is max-rank t_comm/max-rank t_total: the maxima can occur on different ranks, and t_comp+t_comm need not equal t_total.

summary.csv includes median and min-max spread for every configuration. measurements.csv preserves every repetition and per-step/per-grid-node/per-interior-node quantities. predictions.csv preserves model error for each strong/weak group. Original raw output and placement probes are retained. A smoke/synthetic fixture is never official performance evidence.

The final report must still add actual team contributions, hardware/network discussion, selected curves, and explanation of the specific discrepancies observed. The live demo and full AI-history hand-in remain separate.

## Best tested parallel configuration at each strong-scaling N

| N | Layout | Placement | P | Median seconds/step | Speed-up vs serial heat1 |
| ---: | --- | --- | ---: | ---: | ---: |
| 512 | blocks | slot | 4 | 0.000118199 | 2.67689 |
| 2048 | blocks | slot | 4 | 0.00305356 | 2.9155 |
| 8192 | strips | slot | 4 | 0.0508819 | 2.86186 |

If the best tested speed-up is at most 1, serial heat1 was faster than every tested parallel configuration at that N.
