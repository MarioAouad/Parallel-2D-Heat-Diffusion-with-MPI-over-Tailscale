# Part 1: the serial reference

Run this on one VM as one ordinary process. MPI decomposition starts in Part 2.
The earlier task solver was adapted into this project interface. Its separate
[written-task reproduction code](../docs/background-solutions/README.md) is
retained with the background deliverable.

**Status: Part 1 technical work and Ubuntu evidence review complete.** Start with
the [delivery checklist](DELIVERY.md) and [numerical analysis](ANALYSIS.md). The
primary [Ubuntu result archive](results/2026-11-19-ubuntu/) includes the actual
CSV tables, figures, raw commands and source/provenance metadata.

## Build and run on Ubuntu

From the repository root:

```bash
make serial
./build/heat --decomp serial --case V --N 64 --r 0.2 --T 0.05
./build/heat --decomp serial --case 2 --N 64 --r 0.2 --steps 500 --out case2.bin
make check-serial
make verify-part1
make verify-part1-results
```

`make` builds the two Part 0 MPI programs and this solver. `make serial` needs
only the ordinary C++ compiler. The flags include C++17, `-O2`, warnings and
`-ffp-contract=off`; override `SERIAL_CXX` if necessary. Verification scripts
use Python; the experiment/plot script also needs NumPy and Matplotlib.

Windows PowerShell, from the repository root with the installed compiler:

```powershell
New-Item -ItemType Directory -Path build -Force | Out-Null
g++ -std=c++17 -O2 -ffp-contract=off -Wall -Wextra -Wpedantic part1/heat_serial.cpp -o build/heat.exe
python part1/verify_serial.py --exe build/heat.exe
python part1/run_experiments.py --exe build/heat.exe
```

## Options

| Option | Meaning / default |
| --- | --- |
| `--case 1`, `2`, `V` | Default 1: four hot edges. Case 2: hot top/bottom including corners, cold left/right interiors. V: sine-mode verification with exactly zero boundary entries |
| `--N N` | Intervals per direction; default 64; `(N+1)^2` stored nodes |
| `--r R` | Requested alpha*dt/h^2; default 0.2; ordinary runs require `0 < r <= 0.25` |
| `--T T` | Positive final time; choose an integer step count and reduce dt so effective r does not exceed the request |
| `--steps M` | Positive fixed step count; dt=r/N^2; supply exactly one of this option and `--T` |
| `--out FILE` | Optional full grid: raw little-endian IEEE-754 doubles, row-major, boundaries included, no header |
| `--decomp serial` | Default serial; strips/blocks explicitly rejected until implemented |
| `--allow-unstable-demo` | Explicit Task 6.7 experiment only; requires Case 1, fixed steps and r>0.25 |
| `--help` | Show usage |

Malformed numeric strings, nonfinite values, duplicate/unknown options, invalid
time selectors and unsupported decompositions fail with a nonzero exit status.

## Understand the calculation

For alpha=1, h=1/N and r=dt/h^2, each interior node is updated from its old centre
and four old neighbours. The precise addition order is preserved from the earlier
task solver. Two contiguous vectors hold the old and new fields; they swap after
every step. Fixed boundaries are initialized in both vectors before the timer.
Case 2 assigns the hot horizontal edges last, so all four corners are hot.

With `--T`, the step count begins at ceil(T/(r*h^2)), dt=T/steps. A rounding guard
ensures the effective r does not exceed the requested value. With `--steps`, dt
is r*h^2. Only the time-stepping loop and swaps are timed with steady_clock.
Initialization, norms, range inspection and file writing are excluded.

Each successful run prints one key=value line with case, decomposition, P=1,
N, steps, effective r, dt, final T, t_total, t_comp, t_comm=0, minimum and maximum.
Only V prints err_inf and err_l2. The latter is h*sqrt(sum(error^2)), not the
unscaled Euclidean norm. V uses sin(pi*x)*sin(pi*y)*exp(-2*pi^2*T).

## Required studies and correctness checks

`verify_serial.py` checks known one-step values, Case 2 corner precedence,
boundaries over odd/even swaps, symmetry, the maximum principle, Case 1 steady
state, exact output byte count, the full discrete sine eigenmode, error norms,
final-time rounding, invalid inputs and the isolated unstable example.

`run_experiments.py --exe PATH [--out NEW_DIRECTORY]` runs the required V study
at T=0.05, r=0.2 and N=16,32,64,128,256. It checks the grid-computed norms against
the discrete eigenmode and requires observed orders near two. It also records
the deliberate r=0.2625 example at steps 40,120,200 and stable Case 1/2 fields.
The default destination is a new UTC timestamped folder under `part1/results/runs/`.
Existing output directories are refused to preserve evidence. Every run stores
CSV tables, plots, raw command output, binary snapshots and source/platform metadata.

All three Python scripts belong in Git:

| Script | Purpose |
| --- | --- |
| `verify_serial.py` | Runs correctness checks against the executable |
| `run_experiments.py` | Reproduces convergence, instability and field studies |
| `verify_results.py` | Checks the primary archived Ubuntu results without running the solver |

The C++ file performs the simulation. These scripts support verification and
delivery. Reviewed CSVs, figures, source metadata and raw command JSON are
submission evidence. Binary fields and fresh unreviewed run folders stay ignored.

## Completed evidence and next stage

The [primary Ubuntu study](results/2026-11-19-ubuntu/) has been received,
numerically cross-checked and visually reviewed. Six correctness test groups
passed; the five-grid observed orders are 2.00577, 2.00144, 2.00036 and 2.00009.
All five binary snapshots passed format/boundary checks; stable fields passed
bounds/symmetry checks.

See [ANALYSIS.md](ANALYSIS.md) for interpretation and
[DELIVERY.md](DELIVERY.md) for the handoff. The
[results index](results/README.md) distinguishes the completed Ubuntu study from
earlier Windows and Ubuntu smoke evidence. Use `make verify-part1-results`
for an offline integrity/numerical check.

The serial reference is ready for Part 2 comparisons. Keep it and its arithmetic
order intact while implementing strips. Timings in the existing raw output are
incidental; controlled repeated measurements belong to Part 4.
