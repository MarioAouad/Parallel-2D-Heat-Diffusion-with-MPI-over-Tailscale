# Assignment deliverables and our current status

This maps the supplied `heat_mpi_project.pdf` to actual repository contents. A document describing a future requirement is not evidence that the requirement has been implemented.

## Parts and checkpoints

| Assignment section | Requirement | Current state |
| --- | --- | --- |
| 4.1-4.3 | One Ubuntu VM per host; common user/software; record CPU/RAM | Three VMs used successfully. Complete all-machine inventory/version evidence remains pending |
| 4.4 | Tailscale inside VMs; reachability and pair routes | Connectivity observed; original full-run before/after route observations preserved in public copies |
| 4.5 | Every VM can SSH to every other without prompts | Reported successful during setup; preserve all six directed check outputs for the hand-in |
| 4.6 | Cluster hostname and MPI hello | Earlier six-process outputs demonstrated two per VM and hello sum 15 |
| 4.7 | Same-VM and every-pair ping-pong, 8 B to 16 MiB; model | Six complete sweeps / 132 measured rows; analysis, plots, route qualifications included |
| C1 | Part 0 plus serial convergence and background tasks | Not complete from this Part 0 repository alone |
| 5 / Part 1 | Serial heat solver and verification | Future work |
| 6 / Part 2 | 1D strips, correct halos, identical final output | Future work |
| 7 / Part 3 | 2D Cartesian blocks and column communication | Future work |
| 8 / Part 4 | Repeated performance study, model and scaling | Future work |
| 9 / Part 5 | Optional GPU extension | Not attempted here; optional |

## Section 10: final hand-in checklist

| Deliverable | Included now | Remaining work |
| --- | --- | --- |
| 1. Code repository | Current sources, one-command Part 0 build, option documentation, hostfile, launchers, raw/public evidence and plotting scripts | Implement and document the final solver and its build target |
| 2. Background-task solutions PDF | Background notes are supplied as assignment reference | Submit all nonoptional written task solutions; existing separate local drafts were not audited or published by this Part 0 organization |
| 3. Correctness evidence | MPI functional checks and benchmark consistency checks | Serial convergence table/plot; comparison script and output for serial, strips and blocks over several N and P |
| 4. Report, at most 10 pages plus appendices | Detailed Part 0 learning guide, results explanation and figures | Prepare the final concise course report covering all required items below |
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

## Future solver contract: not implemented yet

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

The later same-architecture parallel fields must match the serial output bit for bit for identical inputs. Merely producing similar plots or no MPI error is insufficient. File comparisons and error/convergence evidence are future tests, separate from ping-pong.

## Performance and resource constraints to keep visible

The later study needs fixed comparable step counts, at least three independent runs per configuration with median/spread, strong/weak scaling and computation/communication timing. Our three timed trips for a large ping-pong size are not three independent full experiments.

The example hostfile has six slots. Later comparisons at P=8 require eight actual allocated vCPU slots or discussion of a resource-limited case with the professor. Increasing hostfile numbers without allocating real vCPUs is not a valid fix. This does not invalidate the present six-process hello or two-process benchmark.

## Section 12: AI use

All interactions at setup, code, debugging, analysis and reporting stages must be submitted in full, with actual team member, tool/model and dates. The professor asks for logging from the start. The instructions in this project were added later during the audit: they do not prove a pipeline existed before then or recover missing history.

Full earlier conversations containing credentials remain private. The public repository can include a safe copy and explain its limits, while the private course hand-in must contain the required complete records. A summary README or index is not a substitute for prompts and responses.
