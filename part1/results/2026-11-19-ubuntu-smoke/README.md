# First Ubuntu serial verification

This is the user's first N=16 verification run on heat-1 after a successful
fast-forward pull to commit `8acc213` and native compilation with the documented
C++17/O2/ffp-contract=off flags. The full pasted transcript is retained privately;
the source hash of that transcript and exact solver output are recorded here.
The run's precise UTC timestamp was not supplied; the record was received on
19 November 2026.

The command was:

```bash
./build/heat --decomp serial --case V --N 16 --r 0.2 --T 0.05
```

It reports 64 steps, err_inf=0.0016633705032857438 and
err_l2=0.00083168525164289075, matching the expected discretization errors.
The original output is in `stdout.txt`, with parsed string fields and provenance
in `metadata.json`. This single successful point is a smoke verification, not
the full Ubuntu correctness suite or five-grid convergence study. Those were
subsequently completed; use the [primary Ubuntu study](../2026-11-19-ubuntu/)
and [results index](../README.md). Loop timing here is incidental, not a Part 4
performance result.
