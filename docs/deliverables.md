# Assignment deliverables and our current status

This maps the supplied `heat_mpi_project.pdf` to actual repository contents. A document describing a future requirement is not evidence that the requirement has been implemented.

## Parts and checkpoints

| Assignment section | Requirement | Current state |
| --- | --- | --- |
| 4.1-4.3 | One Ubuntu VM per host; common user/software; record CPU/RAM | Three timestamped inventories confirm matching Ubuntu/MPI; host CPUs, VM 4096 MB / 2 vCPU and physical Wi-Fi records collected |
| 4.4 | Tailscale inside VMs; reachability and pair routes | Connectivity observed; original full-run before/after route observations preserved in public copies |
| 4.5 | Every VM can SSH to every other without prompts | COMPLETE: all six directions verified across original captures and the successful heat-2 recheck at 15:30:12 UTC |
| 4.6 | Cluster hostname and MPI hello | COMPLETE: hostname placement passes; fresh six-rank hello at 15:34:24 UTC shows size=6 and rank_sum=15, two ranks per VM |
| 4.7 | Same-VM and every-pair ping-pong, 8 B to 16 MiB; model | Six complete sweeps / 132 measured rows; analysis, plots, route qualifications included |
| C1 | Part 0 plus serial convergence and background tasks | Technical materials ready: verified cluster, reviewed Ubuntu convergence evidence, and written-task PDF/source. Team explanation and private course-record obligations remain |
| 5 / Part 1 | Serial heat solver and verification | COMPLETE: actual Ubuntu results archived, numerically cross-checked and visually reviewed; six correctness groups pass; analysis and delivery checklist included |
| 6 / Part 2 | 1D strips, correct halos, identical final output | Implemented: [part2/](../part2/DELIVERY.md); C2 supported by 84/84 recorded byte comparisons across 2–3 VMs; retained-field evidence remains [open](../part2/RECOVERY.md) ([study](../part2/results/2026-11-19-cluster/)) |
| 7 / Part 3 | 2D Cartesian blocks and column communication | Solver implemented: [part3/](../part3/DELIVERY.md); 90/90 recorded matches across 2–3 VMs; timing checked at P=4,6. Required P=8 measurements and retained-field evidence remain [open](../part3/RECOVERY.md) ([study](../part3/results/2026-11-19-cluster/)) |
| 8 / Part 4 | Repeated performance study, model and scaling | Future work |
| 9 / Part 5 | Optional GPU extension | Not attempted here; optional |

## Section 10: final hand-in checklist

| Deliverable | Included now | Remaining work |
| --- | --- | --- |
| 1. Code repository | Parts 0–3 sources (serial, strips, blocks), one-command build, option documentation, hostfile, launchers, verified evidence and plotting/offline-check scripts | Part 4 performance scripts |
| 2. Background-task solutions PDF | PDF covering 25 required tasks plus optional 6.5, editable LaTeX, figures/tables and reproduction files under docs/background-solutions | Add actual team identification where required and include complete private AI records in the course hand-in |
| 3. Correctness evidence | Reviewed Ubuntu serial table/plots, raw output, source/archive hashes, instability and stable-case checks; serial-vs-strips (84/84) and serial-vs-blocks (90/90) recorded byte comparisons over several N and P across the VMs | New reviewed studies should retain the original binary fields with the updated Part 2/3 runners |
| 4. Report, at most 10 pages plus appendices | Part 0 learning guide and report-ready Part 1–3 analyses with figures | Integrate the completed numerical/decomposition material, Part 4 performance results and actual team contributions into the final concise report |
| 5. Complete llm_log folder and instructions | Root AGENTS rules, this session record and honest missing-history status | Preserve every earlier full interaction, actual member/model/tool/date metadata, and full private exports in the course hand-in |
| 6. Ten-minute live demo | Cluster can launch programs and communicate | Run heat Cases 1 and 2 across at least three VMs with heat map/animation; change N or P and explain any code |

## What the final report must explain

1. Machines, host CPU models, VM vCPU/RAM allocations, network access and direct/DERP observations, with the latency/bandwidth table.
2. Numerical method, stability condition and convergence study.
3. Both decomposition designs, a figure and correctness checks.
4. Performance curves, model and answers to the Part 3/4 questions, including cases where extra machines slow down the computation.
5. GPU details only if the optional extension is attempted.
6. A short paragraph describing each team member's contribution; do not invent assignments or authorship.

The 39-page Part 0 guide is intentionally explanatory. It is **not** the required final ten-page report.

The delivery indexes for [Part 1](../part1/DELIVERY.md), [Part 2](../part2/DELIVERY.md)
and [Part 3](../part3/DELIVERY.md) identify the completed technical work. The full
project hand-in still requires Part 4, the live heat-solver demo, the final report
and complete private interaction records. Part 2 has an explicit [evidence recovery
item](../part2/RECOVERY.md): the older archive omitted the binary fields, whereas
new runs retain them for independent byte comparison. [Part 3](../part3/RECOVERY.md)
has the same legacy-field limitation and still needs the required P=8 measurement.

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

The example hostfile has six slots. Comparisons at P=8 require eight actual allocated vCPU slots or discussion of a resource-limited case with the professor. Increasing hostfile numbers without allocating real vCPUs is not a valid fix. `cluster.sh` now takes optional per-VM slot counts, and `part3/run_experiments.py --cluster` checks each against the VM's `nproc` before running P = 8. The P = 8 measurement stays open until it has actually been run on eight real vCPUs. This does not invalidate the present six-process hello or two-process benchmark.

## Section 12: AI use

All interactions at setup, code, debugging, analysis and reporting stages must be submitted in full, with actual team member, tool/model and dates. The professor asks for logging from the start. The instructions in this project were added later during the audit: they do not prove a pipeline existed before then or recover missing history.

Full earlier conversations containing credentials remain private. The public repository can include a safe copy and explain its limits, while the private course hand-in must contain the required complete records. A summary README or index is not a substitute for prompts and responses.

## Reconciled local handoff, 20 November 2026

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
