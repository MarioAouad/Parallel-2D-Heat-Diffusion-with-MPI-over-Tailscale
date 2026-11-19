# Parallel 2D Heat Diffusion with MPI over Tailscale

A C++17 heat-diffusion project using three Ubuntu VMs on Windows laptops in
different homes. Tailscale connects the VMs, SSH launches remote processes, and
MPI carries messages between them.

**Status, 19 November 2026:** Parts 0 and 1 technical work and evidence review
are complete. Part 2 strip decomposition is implemented; its compilation and the
C2 cluster comparison on the VMs are pending. Blocks and performance studies
follow. See the [assignment status](docs/deliverables.md) for the full hand-in.

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

`make` builds `build/mpi_hello`, `build/mpi_pingpong`, `build/heat` and `build/heat_mpi`.
`make strips` builds only the Part 2 strips solver.
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

# Part 2: strips correctness groups and a strips run on this VM.
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
  results/               C2 study index (cluster evidence pending)
docs/                    documentation index, assignment PDFs and solutions
llm_log/                 append-only interaction index and record status
AGENTS.md                course logging instructions
```

## Results and their scope

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

Part 2 has no measured results yet. Its [results index](part2/results/README.md)
explains how the cluster C2 study is produced, reviewed and archived.

## Submission and private records

Reviewed code, CSVs, figures, PDFs and provenance belong in Git. Build products,
new unreviewed runs, binary snapshots, private archives and local configuration
are ignored. Public cluster records use generic aliases; exact originals remain
private. Keep every measured dataset and its manifest intact.

The [deliverable map](docs/deliverables.md) tracks the later MPI solvers, final
report, live demo and actual team contributions. Complete earlier AI conversations
are still required in the private course hand-in; the public
[interaction index](llm_log/README.md) does not replace them.
