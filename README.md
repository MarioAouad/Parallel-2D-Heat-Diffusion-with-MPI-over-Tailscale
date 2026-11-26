# Parallel 2D Heat Diffusion with MPI over Tailscale

The project solves the 2D heat equation with a C++17 serial reference and two MPI
decompositions. Three Ubuntu 24.04.5 VMs use Open MPI 4.1.6 over Tailscale.
The final study found that four ranks on one VM were fastest at every tested
grid size. No tested configuration spanning multiple VMs beat the serial
reference on heat1.

## Build and run

On each Ubuntu VM, use the same absolute checkout path and run as `mpi`:

```bash
sudo apt install build-essential openmpi-bin libopenmpi-dev python3-numpy python3-matplotlib
make

./heat --case V --N 64 --r 0.2 --T 0.05
mpirun -np 2 ./heat --decomp strips --case 2 --N 64 --r 0.24 --steps 40
mpirun -np 4 ./heat --decomp blocks --case 1 --N 64 --r 0.24 --steps 40 --out case1.bin
```

`./heat --help` lists the options. The default layout is serial. The launcher
starts the matching binary from `build/` in the same process, so MPI sets
placement and rank count in the usual way. `make serial` builds the serial
version and launcher without requiring Open MPI. The [serial guide](part1/README.md)
covers the native Windows build and the output field format.

To run across the VMs, first follow the [Part 0 setup](part0/README.md) and
[private configuration guide](part0/config/README.md). From the launching VM:

```bash
source part0/config/cluster.sh
mpirun --hostfile "$PWD/part0/config/hosts" --map-by node --nooversubscribe \
  --mca oob_tcp_if_include tailscale0 --mca btl_tcp_if_include tailscale0 \
  --mca btl tcp,self -np 3 ./heat --decomp blocks --case 1 --N 32 --r 0.24 --steps 40
```

## Verify and explore

Run `make verify-delivery` to check the archived data without MPI or network
access. Run `make check-serial check-strips check-blocks` to exercise the
solvers on one Ubuntu VM.

| Part | Guide | Reviewed evidence |
| --- | --- | --- |
| 0 | [Cluster, SSH and ping-pong](part0/README.md) | [Six sweeps and route observations](part0/results/README.md) |
| 1 | [Serial solver](part1/README.md) | [Convergence and instability](part1/results/2026-11-19-ubuntu/) |
| 2 | [MPI strips](part2/README.md) | [84 exact field comparisons](part2/results/2026-11-21-retained-cluster/) |
| 3 | [MPI blocks](part3/README.md) | [108 exact field comparisons and P=8 timings](part3/results/2026-11-21-retained-cluster/) |
| 4 | [Performance and modelling](part4/README.md) | [429 measurements](part4/results/2026-11-24-cluster/) |

## Course hand-in

- [Final report](docs/final-report/final-report.pdf) and [rebuild instructions](docs/final-report/README.md)
- [Separate numerical-method solutions](docs/background-solutions/README.md)
- [Assignment, submission checklist, live demo and maintenance](docs/deliverables.md)
- [Optional explanation PDFs](docs/project_explanation/README.md)
- [AI record status and private export instructions](llm_log/README.md)

The saved CPU/MPI evidence covers Parts 0–4. The team must confirm completion
of the live demonstration and the private AI records for every member. Parts
0–4 have their own code, run scripts and results. `docs/` contains the course
documents and `scripts/` contains shared build, demo and packaging helpers.
