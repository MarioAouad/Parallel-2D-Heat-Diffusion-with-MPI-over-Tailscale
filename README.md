# Parallel 2D Heat Diffusion with MPI over Tailscale

A three-student project connecting Ubuntu virtual machines on three Windows computers in different homes. **This repository contains Part 0 setup/network measurements and the Part 1 serial heat solver.**

**Status on 19 November: Part 0 technical work is complete.** The successful recheck closes both earlier issues: all six SSH directions pass and MPI hello shows ranks 0-5, size=6, rank_sum=15, with two ranks on each VM. All three inventories, hostname placement and the original six ping-pong sweeps are verified. [Closeout details and evidence](docs/part0-closeout.md) preserve the earlier failures as well. [Part 1](part1/README.md) is implemented and verified locally on Windows; the next step is its Ubuntu verification. Complete earlier AI histories remain a private course-submission item.

The purpose of this first stage is to understand how programs start on different machines, how MPI processes exchange data, and how expensive that communication is. Slow Internet communication is a result to explain, not automatically a failed program.

## Start here, slowly

Read one folder at a time. You do not need to rerun every experiment while reading.

| Order | Folder | Question it answers |
| --- | --- | --- |
| 0 | [Cluster setup](part0/00-cluster-setup/README.md) | What are VirtualBox, Ubuntu, Tailscale and SSH doing? |
| 1 | [Connectivity](part0/01-connectivity/README.md) | Can the VMs reach each other and log in without a prompt? |
| 2 | [Hostname launch](part0/02-hostname/README.md) | Can one coordinator start processes on all three VMs? |
| 3 | [MPI hello](part0/03-mpi-hello/README.md) | Can the processes actually exchange MPI data? |
| 4 | [Ping-pong benchmark](part0/04-pingpong/README.md) | How much time does a message and its reply take? |
| 5 | [Offline analysis](part0/05-analysis/README.md) | How do we turn recorded times into plots and model parameters? |
| 6 | [Our measured results](part0/results/README.md) | What happened in the six completed runs, and what are their limits? |

[Part 0 overview](part0/README.md) ties these steps together. The code is heavily commented: read the explanation beside the relevant statements, then use each folder's README to see the whole execution sequence.

## The machines and the processes

| Short label | Public node alias | Private configuration field | Linux project user |
| --- | --- | --- | --- |
| heat1 | heat-1 | HEAT1_IP (local only) | mpi |
| heat2 | heat-2 | HEAT2_IP (local only) | mpi |
| heat3 | heat-3 | HEAT3_IP (local only) | mpi |

Node names in this public copy are generic aliases. Actual hostnames/addresses remain in the private originals. Each Windows computer hosts one Ubuntu VM. Tailscale runs **inside Ubuntu** and joins the VMs into the same private network. SSH lets the coordinator start remote programs. MPI lets the running processes communicate. A rank identifies a process; it does not identify a physical computer.

The initial six-rank test uses two processes per VM. A ping-pong measurement always uses exactly **two ranks**: either both in one VM or one at each endpoint of a VM pair. The third VM keeps its existing real hostname; the public alias does not require renaming it.

## Repository layout

```text
Makefile                         one command builds MPI programs and serial heat
AGENTS.md                        prospective course logging instructions
part0/
  00-cluster-setup/               setup explanation and troubleshooting
  01-connectivity/                SSH/Tailscale checks and inventory helper
  02-hostname/                    launch-only test
  03-mpi-hello/                   annotated C++ program and cluster launcher
  04-pingpong/                    annotated C++ benchmark and case launcher
  05-analysis/                    plotting, verification and numerical tests
  config/                        local-configuration loader and example hostfile
  results/
    2026-11-17/<case>/            six archived runs, five files per run
    analysis/                    reproducible summary and six plots
    README.md                    measured findings, units and limitations
part1/                           serial solver, correctness checks and required studies
  results/2026-11-19-windows/     reviewed local convergence and instability evidence
docs/
  assignment/                    the two supplied professor PDFs
  deliverables.md                requirement-by-requirement status and next work
  cluster-inventory.md            known configuration and missing evidence
  validation.md                  what was checked during organization
  history/                       source provenance and old/new path mapping
  reports/                       public-guide index; the detailed PDF remains private
llm_log/                         this organization session and logging status
```

## Build on Ubuntu

The three VMs use Ubuntu Server 24.04 LTS. The archived coordinator metadata records Open MPI 4.1.6. Check the same release and MPI version on **every VM**; the coordinator's version alone does not prove that.

Packages used during setup:

```bash
sudo apt update
sudo apt install -y build-essential cmake git openmpi-bin libopenmpi-dev python3-numpy python3-matplotlib openssh-server curl
```

For a fresh checkout, run the following **on every VM as `mpi`**. The common path matters because SSH-based MPI starts the remote executable at that path.

```bash
git clone https://github.com/MarioAouad/Parallel-2D-Heat-Diffusion-with-MPI-over-Tailscale.git ~/heat-project-repo
cd ~/heat-project-repo
make
```

Before running the launchers, follow [private configuration](part0/config/README.md) to enter your real addresses in the ignored local file. The loader renders the local hostfile from those values.

This checkout is separate from the existing `~/heat-project` used for the original runs. Keep that original directory and its measurements. `make` creates `build/mpi_hello`, `build/mpi_pingpong` and `build/heat` locally on each VM after receiving the corresponding source updates; Git does not distribute a compiled binary automatically. Use the [commit, push and pull workflow](docs/git-and-part1.md) to transfer your source changes to Ubuntu after publishing them. The source bundle is an alternative for changes not yet published.

The build uses C++17, `-O2`, `-ffp-contract=off` and compiler warnings. `OMPI_SKIP_MPICXX` skips unused legacy MPI C++ wrapper classes; we use the MPI C API from C++. [Build and run validation limits](docs/validation.md) are recorded honestly.

## Run one step at a time

From the repository root on Ubuntu, use the relevant command only after reading its folder:

```bash
# Run on each VM; checks both directions when every member runs it.
bash part0/01-connectivity/check_cluster.sh

# Run on ONE coordinator. Do not launch concurrently from all three VMs.
bash part0/02-hostname/run_hostname.sh
bash part0/03-mpi-hello/run_hello.sh

# Two quick functional tests before deciding to collect new measurements.
bash part0/04-pingpong/run_pingpong.sh heat1-local smoke
bash part0/04-pingpong/run_pingpong.sh heat1-heat2 smoke
```

You can inspect the existing results without any cluster access or new MPI run:

```bash
make verify-results
make analyze
make test-analysis
```

On Windows with Python, call the Python scripts directly; `make` and the shell launchers target Ubuntu. NumPy and Matplotlib are required for analysis; the archive verifier uses only Python's standard library.

All benchmark command-line options, cases, profiles, MCA flags, communication counts and timer boundaries are documented in [the benchmark README](part0/04-pingpong/README.md). The [serial solver guide](part1/README.md) documents its options and verification. From this updated source tree:

```bash
make serial
make check-serial
make verify-part1
./build/heat --decomp serial --case V --N 64 --r 0.2 --T 0.05
```

## What we have measured

Six complete sweeps contain 22 sizes each, from 8 bytes through 16 MiB: **132 measurement rows**. All match the earlier pasted terminal records. Same-VM cases use shared memory; cross-VM cases use TCP over Tailscale. The startup/transfer estimates and route observations are in [the results README](part0/results/README.md).

The full archive does not contain every earlier SSH, hostname, hello or smoke-test terminal transcript. Those were earlier functional checks, not additional full sweeps. Its route snapshots observe before/after conditions and cannot establish an unchanged path throughout a long run.

## What the professor ultimately requires

The [complete deliverable map](docs/deliverables.md) covers assignment sections 10 and 12: repository, background-task solutions, correctness evidence, final report, complete LLM logs, and live demo. Current Part 0 success does **not** complete checkpoint C1: C1 also needs the serial convergence study and background tasks.

The next step is to run and understand the Part 1 serial reference on Ubuntu. Strip decomposition, block decomposition and the performance study remain future work. The existing [study guide](docs/reports/README.md) is a learning document, not the final course report limited to ten pages plus appendices.

## Public copy and original evidence

All 132 numeric measurement records are unchanged. Public evidence copies anonymize node identities and remove actual overlay/public addresses and account handles. CSV host fields use generic aliases; their sizes, counts and timing/throughput fields are unchanged. Metadata and routes are marked as public copies. A [manifest](part0/results/file-manifest.json) records both original and published hashes. Original files remain in the local Windows project/private archive. No passwords, login links or SSH keys are part of this repository.

`llm_log/` records this organization interaction and explicitly identifies the incomplete earlier transcript archive. Full earlier conversations containing credentials belong in a private course hand-in; a public redacted copy or this README does not satisfy the professor's complete-log requirement by itself.

## References

The two [supplied course PDFs](docs/assignment/README.md) define requirements. The MPI programs were prepared in the team's recorded AI-assisted project workflow; see `llm_log/`. External API references: [Open MPI 4.1](https://www.open-mpi.org/doc/v4.1/), [Tailscale CLI](https://tailscale.com/docs/reference/tailscale-cli), [VirtualBox networking](https://www.virtualbox.org/manual/ch06.html), and [Ubuntu OpenSSH](https://ubuntu.com/server/docs/how-to/security/openssh-server/).
