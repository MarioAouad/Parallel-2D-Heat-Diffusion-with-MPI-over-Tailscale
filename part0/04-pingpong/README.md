# 4. Ping-pong: measure the cost of communication

## What this program does

Exactly two MPI ranks execute the same program. Rank 0 sends `m` bytes to rank 1. Rank 1 receives them and sends them back. Rank 0 receives the reply. That is **one complete round trip**, with two application messages. The reverse send/receive order avoids a deadlock that could occur if both ranks made blocking large sends first.

Tag 10 matches the outbound message and tag 11 matches the reply. These numbers are labels for matching, not ports or buffer sizes. `MPI_BYTE` makes the count a byte count. A vector supplies contiguous storage; the program allocates once rather than in the timed loop.

## Where the work runs

| Case argument | Rank 0 | Rank 1 | Payload transport |
| --- | --- | --- | --- |
| heat1-local | heat-1 | heat-1 | self,vader shared memory |
| heat2-local | heat-2 | heat-2 | self,vader shared memory |
| heat3-local | heat-3 | heat-3 | self,vader shared memory |
| heat1-heat2 | heat-1 | heat-2 | tcp,self over tailscale0 |
| heat1-heat3 | heat-1 | heat-3 | tcp,self over tailscale0 |
| heat2-heat3 | heat-2 | heat-3 | tcp,self over tailscale0 |

The usual coordinator is heat-1, even for the last row. It saves output, but the timed application payload for that row goes between heat-2 and the third VM. The launcher probes that route from heat-2 over SSH, not from heat-1.

The same-VM baseline includes shared-memory MPI behavior. The cross-VM measurement includes different MPI transports, TCP, Tailscale, Internet paths and VM scheduling. Their difference cannot be attributed solely to Internet propagation.

## Source walkthrough

The C++ file comments cover every phase. Read the functions in this order:

| Code | Why it exists |
| --- | --- |
| `Options`, `integer`, `power_of_two`, `parse` | Set defaults and reject malformed sizes, counts and labels before exchanging buffers |
| `exchange` | Perform one safe send/receive round trip with distinct direction tags |
| `automatic_iterations` | Choose a bounded repeat count from a calibration without pretending every payload is equally cheap |
| `MPI_Init`, rank/size checks | Establish the communicator and require exactly two ranks |
| hostname `MPI_Allgather` | Identify actual endpoint VMs before timing |
| buffer allocation | Allocate once and initialize a known return pattern |
| per-size warm-up/calibration | Prepare communication and choose a count outside the reported interval |
| timed exchange loop | Measure repeated complete round trips using rank 0's clock |
| payload check and CSV output | Check final echoed bytes and write one measured row per size outside timing |
| `MPI_Finalize` | Complete the MPI program cleanly |

`MPI_Init` does not create the two processes. `mpirun` does. Each process has its own buffer. Branching on rank selects who sends first; this is the first explicit division of application roles, not a partition of a temperature grid.

## Why these sizes and repetition counts?

The full sweep uses `2^3, 2^4, ..., 2^24` bytes: 22 sizes from 8 B through 16 MiB. Small sizes expose startup cost; large sizes expose transfer cost. These are application message sizes, not Ethernet/TCP packet sizes or a choice of one optimal packet for the heat solver.

For each size, automatic mode performs one warm-up and one calibration round trip outside the measured interval. Rank 0 chooses a repeat count aiming at about 0.2 seconds, capped at 10,000 repeats and a soft 64 MiB measured-payload budget, with at least three repeats. It broadcasts the count so the two ranks run the same number of exchanges.

These are documented engineering choices, not professor-mandated constants. Local messages may need many repeats to give a useful interval. Large Internet messages may take minutes even with three repeats. The minimum overrides the soft traffic budget: three 16 MiB round trips transfer 96 MiB before counting warm-up/calibration. Warm-up can help with first-use effects, but one warm-up cannot establish statistical stationarity.

**Communication accounting for one size:** if `n` is the measured iteration count, `w` warm-ups and `p` calibration trips (`p=1` automatic, `p=0` fixed), the payload protocol sends `2*(n+w+p)` logical messages and `2*m*(n+w+p)` payload bytes. The timer includes only `2*n` of those messages. This excludes packet headers/retransmissions and MPI control collectives.

In automatic mode there are three explicit barriers and one Bcast per size, plus one hostname Allgather at startup. Fixed-count mode has two barriers and no calibration Bcast per size. Their low-level message counts depend on MPI's implementation and are not part of the two-payload-message formula.

## The timer and units

```text
initialization, name gathering, allocation          excluded
per size:
  barrier; warm-up                                 excluded
  automatic only: barrier; calibration; Bcast      excluded
  barrier                                         excluded
  start = MPI_Wtime()
  repeat n times: outbound message + reply         INCLUDED
  elapsed = MPI_Wtime() - start
  final payload validation; printing               excluded
```

Only rank 0's elapsed interval is reported. No timestamp from another VM is subtracted, so clock synchronization is unnecessary for RTT. `oneway_s = roundtrip_s/2` estimates a symmetric one-way time; it does not separately measure each direction. The constant `0x5a` check validates the final echoed buffer, not a sequence number for every trip.

```text
roundtrip_s = elapsed_seconds / n
oneway_s = roundtrip_s / 2
effective_MiB_s = (m / 1048576) / oneway_s
```

One MiB is 1,048,576 bytes. MiB/s is not Mbit/s. Effective throughput includes latency and is different from the inverse slope of the large-message model.

## How to run the organized version

After `make` on every VM at the same checkout path, run **one command at a time on one coordinator**:

```bash
bash part0/04-pingpong/run_pingpong.sh heat1-local smoke
bash part0/04-pingpong/run_pingpong.sh heat1-heat2 smoke
```

Smoke uses 8 B..64 KiB (14 sizes), five timed trips and one warm-up; it skips automatic calibration. It checks operation before paying for a full run. Existing smoke runs were reported successful, but their original CSVs were not included in the supplied full-study export.

The six full commands, if collecting a **new** study:

```bash
bash part0/04-pingpong/run_pingpong.sh heat1-local full
bash part0/04-pingpong/run_pingpong.sh heat2-local full
bash part0/04-pingpong/run_pingpong.sh heat3-local full
bash part0/04-pingpong/run_pingpong.sh heat1-heat2 full
bash part0/04-pingpong/run_pingpong.sh heat1-heat3 full
bash part0/04-pingpong/run_pingpong.sh heat2-heat3 full
```

These full measurements already exist in the archive. Do not rerun them merely to read the code. Keep VMs awake and avoid overlapping benchmarks/downloads during deliberate new measurements. The archived study used one full sweep per case, not three independent sweeps.

## Every program option

| C++ option | Default | Meaning |
| --- | --- | --- |
| `--min-bytes N` | 8 | First payload; power of two, at least 8 |
| `--max-bytes N` | 16777216 | Last payload; power of two, at most 16 MiB and at least minimum |
| `--iterations N` | automatic when omitted | Explicit positive measured trip count; skips calibration |
| `--warmup N` | 1 | Nonnegative warm-up trips per size, outside timing |
| `--label NAME` | pingpong | CSV case label; letters, digits, underscore, dot or hyphen |
| `--help` | off | Print usage and exit without measuring |

The shell launcher takes `CASE [smoke|full]`, defaulting to smoke. Cases are the six table rows above. It intentionally has a small interface; advanced direct invocations must retain the same correct host placement and MCA settings shown in the script. Giving hello's `-np 6` to this two-rank program is an error.

## Launcher options and result files

`--host` selects case endpoints and slots; `-np 2` fixes the process count; `--map-by slot` fixes endpoint order. `--wdir` and the executable use the common absolute checkout path. `pml ob1` selects Open MPI's point-to-point layer. The `oob_tcp` and `btl_tcp` interface options select Tailscale for control and TCP payloads; `btl` selects shared memory or TCP. `plm_rsh_args` makes SSH noninteractive.

New runs go into `part0/results/runs/<profile>/` and are ignored by Git until deliberately reviewed. Each completed run creates:

| Suffix | Contents |
| --- | --- |
| `.csv` | Measured rows from stdout |
| `.log` | Progress and success/errors from stderr |
| `.meta.txt` | Case, UTC start, placement, transport and launch-VM versions/status |
| `.route-before.txt` | Actual pair's route observations before MPI |
| `.route-after.txt` | Route observations after MPI |

`tee` displays and saves output. `pipefail` notices MPI failure even when tee succeeds. Only a successful MPI command promotes `.csv.partial` to `.csv`; failed/stopped output remains partial for diagnosis. A nonzero route probe can simply mean relay replies without a direct path; inspect the saved file. Route snapshots are outside the C++ timer and are not continuous monitoring.

Next: [offline analysis](../05-analysis/README.md) and [the measured results](../results/README.md).
