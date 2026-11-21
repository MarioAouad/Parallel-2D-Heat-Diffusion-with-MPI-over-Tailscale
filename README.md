# Parallel 2D Heat Diffusion with MPI over Tailscale

A C++17 heat-diffusion project using three Ubuntu VMs on Windows laptops in
different homes. Tailscale connects the VMs, SSH launches remote processes, and
MPI carries messages between them.

**Status, 21 November 2026:** Parts 0/1 technical evidence passes. The new reviewed
[Part 2](part2/results/2026-11-21-retained-cluster/) and [Part 3](part3/results/2026-11-21-retained-cluster/)
cluster studies contain 84/84 and 108/108 exact serial/MPI matches, all original
comparison/figure fields, and the required Part 3 P=4,8 timing matrix. Strict
retained-field/P=8 verification passes. Three VMs used 4+2+2 guest vCPUs and
matching executable hashes. The previous field-retention and P=8 gaps are closed.
Part 4 campaign/model/analysis tools are implemented; its real VM campaign remains pending; final report, demonstration and
complete private AI records remain course-submission requirements.

## Start here

| Goal | Guide |
| --- | --- |
| Understand the cluster and communication measurements | [Part 0 overview](part0/README.md) |
| Build and use the serial heat solver | [Part 1 guide](part1/README.md) |
| Read the convergence and instability analysis | [Part 1 analysis](part1/ANALYSIS.md) |
| Find completed Part 1 deliverables | [Delivery checklist](part1/DELIVERY.md) |
| Build and run the strip-decomposed MPI solver | [Part 2 guide](part2/README.md) |
| Read the strips correctness argument and cost model | [Part 2 analysis](part2/ANALYSIS.md) |
| Track Part 2 deliverables and C2 evidence | [Part 2 delivery checklist](part2/DELIVERY.md) |
| Build and run the 2D block-decomposed solver | [Part 3 guide](part3/README.md) |
| Read the corner-ghost and strips-vs-blocks answers | [Part 3 analysis](part3/ANALYSIS.md) |
| Track Part 3 deliverables | [Part 3 delivery checklist](part3/DELIVERY.md) |
| Plan and run the full performance study | [Part 4 guide](part4/README.md) and [VM instructions](part4/RUN.md) |
| See Part 4 requirements versus implementation | [Part 4 delivery checklist](part4/DELIVERY.md) |
| Read the written numerical-method solutions | [PDF and editable source](docs/background-solutions/README.md) |
| Receive GitHub updates on the VMs | [Git and VM workflow](docs/local-update.md) |
| Find hardware, requirements and verification details | [Documentation index](docs/README.md) |

## Build and check on Ubuntu

For a fresh checkout, run as `mpi` on each VM. Use the same path on all three
because MPI starts remote programs at that path.

```bash
git clone https://github.com/MarioAouad/Parallel-2D-Heat-Diffusion-with-MPI-over-Tailscale.git ~/heat-project-repo
cd ~/heat-project-repo
make
```

The VMs use Ubuntu 24.04.5 LTS and Open MPI 4.1.6. Build dependencies are
`build-essential`, `openmpi-bin` and `libopenmpi-dev`; the studies use Python 3,
NumPy and Matplotlib. SSH, Tailscale and local addresses are covered in
[cluster setup](part0/00-cluster-setup/README.md) and
[private configuration](part0/config/README.md).
For an existing checkout, use the [update instructions](docs/local-update.md).

`make` builds `build/mpi_hello`, `build/mpi_pingpong`, `build/heat`, `build/heat_mpi` and `build/heat_blocks`.
`make strips` and `make blocks` build only the Part 2 and Part 3 MPI solvers.
`make serial` builds only the serial solver with an ordinary C++ compiler.
All use C++17, optimization, warnings and `-ffp-contract=off`.

```bash
# Check the archived evidence; no cluster access or new experiment required.
make verify-setup
make verify-results
make verify-part1-results

# Run the serial correctness checks and an example simulation.
make check-serial
./build/heat --decomp serial --case V --N 64 --r 0.2 --T 0.05

# Parts 2 and 3: correctness groups for strips and blocks on this VM.
make check-blocks
make check-strips
mpirun -np 2 ./build/heat_mpi --decomp strips --case V --N 64 --r 0.2 --T 0.05
```

`make verify-part1` creates a new timestamped convergence/instability study.
It does not overwrite the reviewed archive. Windows build instructions are in
the [Part 1 guide](part1/README.md).

## Repository layout

```text
Makefile                 builds and verification commands
part0/
  00-cluster-setup/      VM, Tailscale and SSH explanation
  01-connectivity/       inventory and directed connectivity checks
  02-hostname/           six-process launch test
  03-mpi-hello/          MPI rank/host/collective test
  04-pingpong/           two-rank communication benchmark
  05-analysis/           analysis, evidence checks and tests
  config/                examples and ignored local configuration
  results/               measured runs, setup evidence and analysis
part1/                   serial solver, checks and experiment scripts
  ANALYSIS.md            numerical method and reviewed findings
  DELIVERY.md            requirement-by-requirement evidence
  results/               primary Ubuntu study and supporting records
part2/                   strip-decomposed MPI solver, checks and C2 study script
  ANALYSIS.md            correctness argument and communication cost model
  DELIVERY.md            section 6 / C2 requirement-by-requirement evidence
  results/               reviewed C2 cluster study and index
part3/                   2D block-decomposed MPI solver, checks, study and timing script
  ANALYSIS.md            corner ghosts, strips-vs-blocks prediction and check
  DELIVERY.md            section 7 requirement-by-requirement evidence
  results/               reviewed cluster study and index
part4/                   restartable performance campaign, calibration, models and plots
scripts/                 VM update and experiment/package helpers
docs/                    documentation index, assignment PDFs and solutions
llm_log/                 append-only interaction index and record status
AGENTS.md                course logging instructions
```

## Results and their scope

The current primary studies are the 21 November retained-field archives linked
above. The following numerical/performance observations explicitly describe the
older 19 November studies. The new Part 3 timing outcomes differ; see its updated
analysis before using these older conclusions in a report.

Part 0 has six complete ping-pong sweeps, 22 payload sizes each:
**132 measurement rows**. The [results guide](part0/results/README.md) explains
latency, bandwidth and route observations. Before/after probes do not establish
the route throughout a measurement. Six SSH directions, three inventories and
the six-rank hello are verified in the [Part 0 closeout](docs/part0-closeout.md).

The [primary Ubuntu Part 1 study](part1/results/2026-11-19-ubuntu/) recovers
second-order convergence, demonstrates the isolated unstable case, and verifies
stable Cases 1 and 2. The [results index](part1/results/README.md) distinguishes
it from the earlier Windows study and Ubuntu smoke test. Timings in these serial
records are incidental; controlled scaling measurements belong to Part 4.

The [Part 2 cluster study](part2/results/2026-11-19-cluster/) shows the strips output
byte-identical to serial in 84/84 comparisons (P = 1–4, seven N, uneven strips, two to
three VMs). Its incidental timers attribute at least 99.98 % of
cross-VM loop time to the halo-exchange region, including waits. This is not an
isolated network-latency measurement. The [results index](part2/results/README.md) explains how studies are
reviewed and archived.

The [Part 3 cluster study](part3/results/2026-11-19-cluster/) shows the blocks output
byte-identical to serial in 90/90 comparisons (P = 1, 2, 3, 4, 6; grids up to 3×2; two to
three VMs). Its available P=4,6 timing check partially answers the strips-vs-blocks
question. Blocks win all six paired runs at N = 8192, by 1.5–2.3× in the medians;
strips win 10/12 paired runs at N ≤ 2048. Extra exchange phases are a plausible
contributor; these measurements do not isolate the cause. P=8 remains open.
The [analysis](part3/ANALYSIS.md#then-check-measured-strips-vs-blocks) compares
this with the Task 8.2 prediction.

## Data exchanged during a simulation

Each MPI process initializes and stores its own strip or block plus a thin ghost
layer. Every time step updates all its owned interior grid points. It exchanges
only neighboring edge values: two rows for strips, or up to two rows and two
columns for blocks. The five-point stencil does not require diagonal corners.
A process boundary can be inside one VM or cross to another VM.

The full matrix is assembled on rank zero when `--out` is requested or Case V
needs the deterministic serial-order error calculation. The Case 1 performance
runs omit output, so they do not collect a full matrix each step. Timers/extrema
use small reductions; debug printing gathers text separately.

## Submission and private records

Reviewed code, CSVs, figures, PDFs and provenance belong in Git. Build products,
new unreviewed runs, private archives and local configuration are ignored.
Reviewed Part 2/3 cluster archives retain `fields/*.bin` using the explicit ignore-rule exception. Public cluster records use generic aliases; exact originals remain
private. Keep every measured dataset and its manifest intact.

The [deliverable map](docs/deliverables.md) tracks the later MPI solvers, final
report, live demo and actual team contributions. Complete earlier AI conversations
are still required in the private course hand-in; the public
[interaction index](llm_log/README.md) does not replace them.
