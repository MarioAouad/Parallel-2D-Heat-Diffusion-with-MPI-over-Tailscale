# Part 3: 2D block decomposition

The [reviewed cluster study](results/2026-11-21-retained-cluster/) has 108 exact
serial comparisons and 130 retained fields. It includes P=8 correctness and
P=4,8 timings on eight checked guest vCPUs.

| File | Purpose |
| --- | --- |
| [heat_blocks.cpp](heat_blocks.cpp) | Block-decomposed solver, `--decomp blocks` |
| [verify_blocks.py](verify_blocks.py) | Six correctness groups (`make check-blocks`) |
| [run_experiments.py](run_experiments.py) | Byte-for-byte comparisons, halo-debug transcripts, figures, and the strips-vs-blocks timing check (`make verify-part3`, add `--cluster`) |
| [verify_results.py](verify_results.py) | Offline check of an archived study (`make verify-part3-results`) |
| [Analysis](ANALYSIS.md) and [results](results/README.md) | Model, measured comparison and evidence index |

The [project launcher](../README.md#build-and-run) selects this solver with
`--decomp blocks`. The underlying executable is `build/heat_blocks`.

## Build and run (Ubuntu, repository root, as `mpi`)

```bash
git pull --ff-only origin main
make serial strips blocks          # build/heat, build/heat_mpi, build/heat_blocks
mpirun -np 4 --oversubscribe ./build/heat_blocks --decomp blocks --case 2 --N 64 --r 0.2 --steps 500 --out blocks.bin
./build/heat --decomp serial --case 2 --N 64 --r 0.2 --steps 500 --out serial.bin
cmp serial.bin blocks.bin && echo IDENTICAL
```

Options are identical to Parts 1 and 2, plus `--debug-print` (N <= 16). The Py×Px process
grid comes from `MPI_Dims_create`, for example 2×2 for P=4 and 3×2 for P=6. N−1 must be at
least Py. Output is one key=value line, for example:

```text
decomp=blocks P=6 Py=3 Px=2 nodes=3 case=2 N=64 steps=500 r=0.2 dt=... T=... t_total=... t_comp=... t_comm=... minimum=0 maximum=1
```

## Design

**Process grid (section 7).** `MPI_Dims_create(P, 2, dims)` picks the most balanced
factorisation. `MPI_Cart_create` builds a non-periodic grid with `reorder = 0`, so rank 0
stays on the launching VM and writes the file there. `MPI_Cart_shift` returns the
neighbours, and the plate edges automatically get `MPI_PROC_NULL`. Dimension 0 is y
(rows j) and dimension 1 is x (columns i). Ranks are row-major: rank = cy·Px + cx.

**Split.** Rows and columns use the Part 2 rule independently. The N−1 interior indices
are split into contiguous ranges, and the first (N−1) mod Py block rows (or Px block
columns) get one extra. Example N=10, P=6: block rows of 3, 3, 3 rows and block columns
of 5 and 4 columns.

**Local storage.** (rows+2)×(cols+2) values, row-major, with one ghost layer on all four
sides. On a plate edge that layer is the Dirichlet boundary and is never overwritten.

**Halo exchange.** Four `MPI_Sendrecv` shifts per step:

1. up (top owned row → upper rank; bottom ghost row ← lower rank);
2. down;
3. right (rightmost owned column → right rank; left ghost column ← left rank);
4. left.

Rows are contiguous: `cols` doubles are sent straight from the array. Columns are strided
in memory, so they use a derived datatype,
`MPI_Type_vector(rows, 1, cols+2, MPI_DOUBLE)`: `rows` blocks of one double, `cols+2`
doubles apart. MPI reads the column directly from the array, with no hand-written
copy loop. **The four corner ghost cells are never exchanged**, because the five-point
stencil never reads them (see [ANALYSIS](ANALYSIS.md#question-1-why-are-corner-ghosts-not-needed)).

**Output.** The blocks are not contiguous in the global array. Each rank therefore sends
its owned block with an `MPI_Type_create_subarray` type (skipping its ghost layer), and
rank 0 receives each block straight into place with a subarray type of the global
(N+1)×(N+1) array. Again there is no manual packing. Rank 0 fills the boundary, computes
the V-case norms in the serial loop order, and writes the Part 1 file format.

**Timing.** `t_comm` covers the four Sendrecv calls and `t_comp` the stencil. Each is
reported as the maximum over ranks, as in Part 2.

## Debugging a halo exchange

```bash
mpirun -np 4 --oversubscribe ./build/heat_blocks --case 1 --N 8 --r 0.2 --steps 1 --debug-print   # 2x2
mpirun -np 6 --oversubscribe ./build/heat_blocks --case 1 --N 8 --r 0.2 --steps 1 --debug-print   # 3x2, uneven
```

Each block prints its rows top to bottom, including the ghost row and column values.
Corners print as `-` because they are never exchanged. Every ghost value must equal the
neighbouring block's owned value at the same (i, j).

## Verify or rerun

```bash
make check-blocks
python3 part3/verify_results.py --data part3/results/2026-11-21-retained-cluster --require-fields --require-p8
```

The first command runs six correctness groups on one VM. The second verifies
the saved cluster fields and timing matrix offline. For a new study, use the
[cluster rerun guide](../docs/parts2-3-rerun.md).
