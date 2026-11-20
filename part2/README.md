# Part 2: 1D strip decomposition

**Status: implemented; C2 is supported by the archived run records. Original binary-field evidence remains open.** Start with the [delivery checklist](DELIVERY.md)
and the [analysis](ANALYSIS.md). The [cluster study](results/2026-11-19-cluster/) shows
84/84 strips fields byte-identical to the serial reference for P = 1–4 across two and
three VMs, including uneven strips.

| File | Purpose |
| --- | --- |
| [heat_mpi.cpp](heat_mpi.cpp) | Strip-decomposed solver, `--decomp strips` |
| [verify_strips.py](verify_strips.py) | Six correctness groups (`make check-strips`) |
| [run_experiments.py](run_experiments.py) | C2 study: byte-for-byte comparisons, halo-debug transcripts, figures (`make verify-part2`, add `--cluster`) |
| [verify_results.py](verify_results.py) | Offline check of an archived study (`make verify-part2-results`) |
| [tests/test_evidence.py](tests/test_evidence.py) | Evidence-capture and tampering regression tests (`make test-part2-evidence`); MPI is mocked, so these are not cluster measurements |
| [DELIVERY.md](DELIVERY.md) · [ANALYSIS.md](ANALYSIS.md) · [results/](results/README.md) | Checklist, interpretation, evidence index |

The Part 1 reference [`heat_serial.cpp`](../part1/heat_serial.cpp) is unchanged and
stays the `--decomp serial` executable (`build/heat`). Part 3 (blocks) is now available in [part3/](../part3/README.md). The Part 2 solver source is retained unchanged to preserve the archived source hash.

## Build and run (Ubuntu, repository root, as `mpi`)

```bash
git pull --ff-only origin main
make serial strips                 # build/heat and build/heat_mpi
mpirun -np 2 --oversubscribe ./build/heat_mpi --decomp strips --case 2 --N 64 --r 0.2 --steps 500 --out strips.bin
./build/heat --decomp serial --case 2 --N 64 --r 0.2 --steps 500 --out serial.bin
cmp serial.bin strips.bin && echo IDENTICAL
```

Options are identical to Part 1 (`--case`, `--N`, `--r`, `--T`/`--steps`, `--out`,
`--allow-unstable-demo`), plus `--debug-print` (N <= 16) and the requirement N-1 >= P.
`--oversubscribe` lets one 2-vCPU VM run 3–4 ranks: acceptable for correctness, never
for timing (assignment section 8.1).

Output is one key=value line, for example:

```text
decomp=strips P=4 nodes=2 case=2 N=64 steps=500 r=0.2 dt=... T=... t_total=... t_comp=... t_comm=... minimum=0 maximum=1
```

`nodes` is the number of distinct machines that ran ranks. The three times are the
**maximum over ranks** (`MPI_Reduce` with `MPI_MAX`).

## Design

**Row split (section 6.1).** The N-1 interior rows j=1..N-1 are divided into contiguous
strips. With `base=(N-1)/P` and `extra=(N-1) mod P`, rank p owns
`base + (p < extra ? 1 : 0)` rows starting at `1 + p*base + min(p, extra)`. Rank 0 is the
bottom strip. Example N=9, P=3: rows 1–3, 4–6, 7–8.

**Local storage.** Each rank stores `rows+2` contiguous rows of N+1 doubles, using
the same row-major layout as the serial code:

```text
local row rows+1  top ghost     = copy of the upper neighbour's bottom row (rank P-1: plate row j=N)
local rows 1..rows owned rows   = updated by the unchanged serial stencil
local row 0       bottom ghost  = copy of the lower neighbour's top row (rank 0: plate row j=0)
```

**Halo exchange (section 6.2).** Before every step, two `MPI_Sendrecv` calls run on every rank:

1. *shift up*: send my top owned row to `up`; receive my bottom ghost from `down`;
2. *shift down*: send my bottom owned row to `down`; receive my top ghost from `up`.

`up`/`down` are `MPI_PROC_NULL` at the plate edges, so ranks 0 and P-1 run the same
code. Their boundary ghost rows are never overwritten. Every row is sent directly from the
array as one message of N+1 doubles; no packing is needed. Pairing the send with the
opposite-direction receive means all neighbour pairs communicate at once. Pairing
"send up / receive from up" instead would make the exchange ripple down the
ranks one pair at a time.

**Bit-for-bit equality.** The stencil line, the initial values and the time-step selection are
copied from the serial reference, and both files use the same compiler flags
(`-O2 -ffp-contract=off`). Every node is therefore computed from the same five values, with the same
operations in the same order. A rank boundary changes only where a value is stored,
never how it is computed. The V-case error norms are computed on rank 0 from the
gathered field in the serial loop order, so they also match exactly.

**Output (section 6.3).** Rank 0 assembles the full field with `MPI_Gatherv`: each rank's
owned rows land at offset `first*(N+1)`, and rank 0 fills the boundary rows j=0 and j=N.
It writes the same raw little-endian file as Part 1. Gathering, norms, min/max and file
output are all outside the timed loop.

**Timing.** `t_comm` covers the two Sendrecv calls and `t_comp` the stencil loop. `t_total` is the whole
loop after an `MPI_Barrier`. Each is reduced with `MPI_MAX`, because the slowest rank sets the pace.

## Why a blocking Send-then-Recv exchange can deadlock (report question)

A standard-mode `MPI_Send` is allowed to wait for a matching receive. Small
messages often succeed using internal eager buffers; larger messages may use a
rendezvous protocol. Correctness must not depend on buffer availability.

The exact order and matching neighbours matter. For this nonperiodic chain,
`Send(up); Recv(down)` does **not** by itself form a circular wait: the top rank's
send to `MPI_PROC_NULL` completes, allowing its receive from below to start a
wave of progress down the chain. It can serialize the exchange, but it is not
the deadlock example.

A genuinely unsafe two-sided halo exchange is:

```text
Send(top_row, up)
Send(bottom_row, down)
Recv(bottom_ghost, down)
Recv(top_ghost, up)
```

For P=2 and unbuffered/rendezvous sends, rank 0 waits sending upward to rank 1,
while rank 1 has completed its null upward send and waits sending downward to
rank 0. Neither reaches its receive. Eager buffering can hide this bug for small
rows. A periodic send-up/receive-down ring also has a circular dependency.

Our two `MPI_Sendrecv` calls combine matching sends and receives, so the library
can progress them together without relying on eager buffering. The send/receive
buffers are disjoint, and `MPI_PROC_NULL` preserves the physical boundary rows.
Do not predict a fixed grid-size threshold from assumed eager limits: transport,
configuration and MPI version affect when buffering is used.

Sources: [MPI null-process semantics](https://www.mpi-forum.org/docs/mpi-4.1/mpi41-report/node84.htm)
and [Open MPI `MPI_Sendrecv`](https://docs.open-mpi.org/en/main/man-openmpi/man3/MPI_Sendrecv.3.html).

## Debugging a halo exchange (section 6, yellow box)

```bash
mpirun -np 2 --oversubscribe ./build/heat_mpi --case 2 --N 8 --r 0.2 --steps 1 --debug-print
mpirun -np 3 --oversubscribe ./build/heat_mpi --case 2 --N 8 --r 0.2 --steps 1 --debug-print   # uneven: 3,2,2 rows
```

Each rank prints its owned rows and its ghost rows (labelled `boundary` at the plate edges).
Every ghost row must equal the neighbouring rank's owned row with the same j.

## Checkpoint C2 evidence

C2 requires output identical to serial for P = 1, 2, 3, 4 and several N, including
N-1 not divisible by P, **across at least two VMs**.

1. **One VM** (quick, oversubscribed):

   ```bash
   make check-strips      # six correctness groups
   make verify-part2      # local C2-style study (not C2 evidence: one machine)
   ```

2. **Cluster** (from ONE VM; all three VMs must have pulled and run `make` in
   `~/heat-project-repo`, with routes direct in `tailscale ping`):

   ```bash
   python3 part2/run_experiments.py --cluster
   python3 part2/verify_results.py --data part2/results/runs/<stamp>
   ```

   `--map-by node` spreads ranks round-robin, so every P >= 2 run uses at least two VMs.
   The `nodes` column of `compare.csv` records this. A cross-VM step costs roughly
   0.1–0.5 s (see [ANALYSIS](ANALYSIS.md#expected-cost-a-prediction-from-part-0-and-part-1-data)),
   so the defaults use few steps.

Each run writes `part2/results/runs/<UTC timestamp>/` containing:

- `compare.csv`;
- `debug_halo.txt`;
- `decomposition.png/.pdf` and `cases.png`;
- `raw_runs.json` (commands and outputs);
- `metadata.json` (mode, MPI version, source hashes);
- `manifest.json`;
- every original `fields/*.bin`, with byte counts and SHA-256 hashes in the manifest;
  `compare.csv` records the serial/strips filenames and hashes. Metadata schema 2
  prevents a new study from silently falling back to record-only verification.

For new runs, verify the retained fields explicitly:

```bash
python3 part2/verify_results.py --data part2/results/runs/<stamp> --require-fields
```

The 19 November legacy archive records byte equality but does not contain its binary
fields. The verifier labels that limitation; it never presents the old records as a
fresh byte comparison. See [evidence recovery](RECOVERY.md).

Run folders are git-ignored until reviewed. Copy the reviewed cluster run to
`part2/results/<date>-cluster/`, as was done for Part 1 (see the [results index](results/README.md)).

Timings printed during these checks are incidental. Controlled, repeated measurements
belong to Part 4.
