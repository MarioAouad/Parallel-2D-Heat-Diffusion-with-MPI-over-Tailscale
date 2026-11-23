# Assignment deliverables and final status

**24 November 2026: Parts 0-4 technical evidence passes. Optional GPU/CUDA work
is deliberately omitted.** These statements refer to reviewed saved evidence,
not to synthetic tests or an assumed live demonstration.

| Requirement | Current delivery |
| --- | --- |
| Part 0 | Three-guest setup, all six directed SSH checks, six-rank hello, six full ping-pong sweeps / 132 measurements |
| Part 1 | Serial solver, five-grid second-order convergence, isolated instability experiment, Cases 1/2 and offline verification |
| Part 2 | 84/84 exact serial/strips comparisons, 109 retained fields, strict verifier passes |
| Part 3 | 108/108 exact serial/blocks comparisons, 130 retained fields, P=4,8 timing matrix on real eight-slot allocation |
| Part 4 | [Full reviewed study](../part4/results/2026-11-24-cluster/): 429 measurements, 18 calibration sweeps, 16 placement probes, all P=1..8, three repeats/configuration |
| Final report | [Ten main pages plus three plot appendices](final-report/final-report.pdf); actual cluster/results/model and shared contribution statements |
| Background-task solutions | [Separate PDF and editable source](background-solutions/README.md), all required tasks included |
| Reproducible evidence check | `make verify-delivery` checks Parts 0-4 offline; no MPI rerun |
| Live-demo materials | Existing Cases 1/2 images/three-guest field records, plus [new explicit-run helper](../scripts/run-demo.py) |
| Full private AI histories | Existing records plus newly recovered local visible snapshots; all-member historical completeness still needs team confirmation |

## What remains for the team

1. Present the required ten-minute live demo to the instructor if it has not
   already been delivered. Existing plots and raw runs prove technical execution,
   not that a live presentation occurred. Run Cases 1 and 2 across all three VMs,
   show the heat map, be ready to change N/P and explain the code. See the
   [demo/report guide](final-report/README.md). No repeat of the full performance
   campaign is required for this.
2. Include every member's complete visible project AI conversations and actual
   member/tool/model/date metadata in the private course hand-in. Missing earlier
   chats on other computers/tools cannot be reconstructed from timing archives.
   See [the record-status index](../llm_log/README.md). This cannot honestly be
   marked complete from one machine's exports.
3. Read the final report as a team, check the shared contribution statement, and
   submit the repository snapshot, separate background PDF, report and private
   records through the instructor's channel. Instructor acceptance remains external.

All three members (Mario Aouad, Mohamad Farchoukh and Bassem Haddad) reported joint
work across all project stages. The report reflects that statement without
inventing exclusive ownership. GPU and optional nonblocking overlap are not required.

## Final evidence qualifications

The performance campaign contains 143 configurations with exactly three retained
measurements each (45 serial, 288 strong, 96 weak). All 509 raw invocations remain:
499 checkpoint references, nine rejected warning-only attempts and one failed
MPI invocation when a peer VM became unavailable. The final strict verifier passes.
All original data remains private; only account identifiers in public network
stdout were additionally redacted, with a new manifest and [hash provenance](../part4/review.json).

Best tested strong speed-ups are 2.68/2.92/2.86 on four ranks within heat1. No tested
cross-guest configuration beats serial heat1. Wide spread and route/VM changes
are disclosed; they are observed limitations, not grounds for fabricating timings
or claiming a stable network. No new correctness/performance runs are required
solely because recovery helpers, documentation and report files were added.

## Solver contract: serial, strips and blocks implemented

The professor requires a C++17-or-later executable `heat` with documented equivalents of:

| Option | Required meaning |
| --- | --- |
| `--case 1`, `2`, or `V` | Four hot edges, hot top/bottom, or analytic verification |
| `--N` | Intervals per direction; the full grid has (N+1)^2 nodes |
| `--r` | Dimensionless alpha*dt/h^2; reject unstable values with an explanation |
| `--T` or `--steps` | Final time or fixed steps; for T adjust dt so an integer number of steps reaches T without exceeding requested r |
| `--out` | Optional full-grid raw little-endian double file, row-major, no header |
| `--decomp serial`, `strips`, `blocks` | Select reference or parallel decomposition |

The serial version needs contiguous arrays, a single indexing function, two time levels swapped rather than copied, loop-only timing and error norms for V. Part 1 also requires the convergence study and deliberate unstable example. Preserve the serial reference throughout later parts.

These serial requirements are implemented in `part1/heat_serial.cpp`; the exact
options and results are in `part1/README.md`. Ordinary unstable runs are refused.
A separate explicit demonstration option permits only the deliberate Case 1
fixed-step experiment. Do not treat local Windows timings as cluster performance.
The [Part 0 closeout](part0-closeout.md) records the completed repairs and preserves
both the failed and successful captures. The technical checklist is complete.

The same-architecture parallel fields must match the serial output bit for bit for identical inputs. Merely producing similar plots or no MPI error is insufficient. `--decomp strips` is `build/heat_mpi` ([Part 2](../part2/README.md)) and `--decomp blocks` is `build/heat_blocks` ([Part 3](../part3/README.md)); `heat_blocks` rejects `serial` and `strips` with a pointer to the right executable. `heat_mpi` still prints "--decomp blocks is Part 3 and is not implemented yet": its source is left unchanged so that the archived Part 2 evidence hash stays valid. Their byte-for-byte file comparisons against serial are archived in the Part 2 and Part 3 cluster studies.

## Performance and resource constraints to keep visible

The later study needs fixed comparable step counts, at least three independent runs per configuration with median/spread, strong/weak scaling and computation/communication timing. Our three timed trips for a large ping-pong size are not three independent full experiments.

The original example hostfile has six slots. The reviewed current configuration has eight actual allocated vCPUs and slots (4+2+2), and P=8 has been measured. Increasing slots without allocating real CPUs would not be valid. `cluster.sh` now takes optional per-VM slot counts, and `part3/run_experiments.py --cluster` checks each against the VM's `nproc` before running P = 8. The archived P=8 evidence is complete in the 21 November Part 3 and full Part 4 studies. This does not invalidate the present six-process hello or two-process benchmark.

## Section 12: AI use

All interactions at setup, code, debugging, analysis and reporting stages must be submitted in full, with actual team member, tool/model and dates. The professor asks for logging from the start. The instructions in this project were added later during the audit: they do not prove a pipeline existed before then or recover missing history.

Full earlier conversations containing credentials remain private. The public repository can include a safe copy and explain its limits, while the private course hand-in must contain the required complete records. A summary README or index is not a substitute for prompts and responses.

## Historical audit: 20 November 2026 (superseded by final status above)

The pulled retention and CPU-slot checks are preserved and the same CPU preflight
is now shared by both parallel runners (Part 2 no longer assumes six slots). Local evidence tests and
CLI documentation now use the same CSV field/hash format and CPU configuration.
The offline checkers compare raw output with tables, check numerical/debug values,
and recompute timing medians and spread. Existing dated measurements and C++
solvers are unchanged. These changes include Python behavior, not only Markdown.

Parts 0/1 archived checks pass; the serial solver also passes a fresh local build
and six correctness groups. Part 2/3 record-only archives pass stronger checks.
Part 2's nine and Part 3's sixteen evidence tests use real serial execution with
mocked MPI in temporary fixtures, not new Ubuntu/Open MPI or cluster measurements.
No fresh three-VM run was performed during this reconciliation.

Before declaring Parts 0–3 closed, synchronize/build the tested revision on each
VM, run the MPI correctness groups, archive a new retained-field study for each
parallel solver, and collect the required P=8 timing evidence on eight real CPUs
(or obtain an instructor-approved substitution). Refresh inventories if allocations
change. Earlier complete AI records still need the actual owners' missing exports.
Part 4 implementation can proceed while these external evidence tasks are completed.

For Part 4, keep transport and mapping settings explicit. The old same-VM ping-pong
used shared-memory transport, while the solver cluster launchers force `tcp,self`.
Calibrate communication with the transport the performance runs actually use;
do not apply the same-VM shared-memory fit as if it measured local TCP. Preserve
the old measurements and save fresh calibration separately. Part 4 still requires
per-VM serial baselines, both decompositions, both node/slot placements, strong and
weak scaling, fixed step counts, at least three repetitions, median/spread, and
model-versus-measurement comparisons.

## Evidence closure, 21 November 2026

The uploaded parts23-20261120T231427Z checked bundle passes strict Part 2
`--require-fields` and Part 3 `--require-fields --require-p8` checks. The earlier
missing-field/P=8 items described above are now closed by the new archives.
All 280 recorded solver commands succeeded with empty stderr. Six strips and six
blocks correctness groups passed on the launching VM. Inventories/capacity records
confirm 4+2+2 guest vCPUs; all three VMs have identical hashes for the three binaries.
The launcher's checkout was clean at revision 60fc802. Raw inventories/endpoints
remain private; the reviewed study files and manifests retain their original bytes.

Connectivity probes included DERP relay use. This is valid observed cluster data,
but does not establish a controlled, always-direct performance environment. Part 4
still needs a fixed documented configuration and matching communication calibration,
serial baselines, both placements, strong/weak scaling, communication share and
repeated measurements/model comparisons. Final report, live demo and complete
missing private AI histories remain open. No further Part 2/3 correctness rerun is
needed merely because the laptop restarted after these data were collected.

## Historical implementation checkpoint, 21 November 2026

The [Part 4 runner](../part4/README.md) now scripts all required baselines,
strong/weak scaling, placements, per-run communication fractions, repeated
statistics, a measured per-host/pairwise Task 8.2 model and a 1us-latency scenario.
The default eight-slot plan is 429 heat invocations plus calibration/probes.
Checkpoint/resume and private raw originals are included. Synthetic pipeline tests
are validation of the tools, not actual Part 4 results. C3 is not marked complete
until the real full campaign is collected, verified and interpreted.

The reviewed Part 2/3 field files remain intended versioned correctness evidence.
Temporary Part 4 runs/scratch and private originals are ignored. See the
[Git inclusion policy](git-inclusion.md) before staging the pending files.


## Final closure, 24 November 2026

The full Part 4 study and report above supersede earlier pending-campaign statements
in dated audit entries. All saved Parts 0-4 checks pass. Live presentation and
all-member private history completeness are the remaining external obligations.
