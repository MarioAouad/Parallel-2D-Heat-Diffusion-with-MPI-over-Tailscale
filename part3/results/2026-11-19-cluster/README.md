# Reviewed cluster Part 3 study, 19 November 2026

Primary source: run folder `20261119T200747311497Z`, launched from heat-3 at
2026-11-19 20:07:47 UTC with `python3 part3/run_experiments.py --cluster`
(Linux x86_64, Open MPI 4.1.6, commit 7a8f45f or its merge into main as PR #3, which have identical sources). All three VMs
had built the same commit at `~/heat-project-repo`. The folder was copied to Windows with
`scp` and archived here. Two things changed:

- the regenerable `fields/*.bin` reference fields were left out;
- the launching VM's device hostname was replaced by `heat3` in two stderr lines of
  `raw_runs.json` (see Review).

| File | Content |
| --- | --- |
| `compare.csv` | 90 serial-vs-blocks comparisons: case, N, P, grid, machines used, uneven blocks, byte equality, incidental timers |
| `debug_halo.txt` | Halo debugging: Case 1, N=8, one step, 2×2 and 3×2 grids; every rank's coordinates, neighbours, owned rows, ghost rows and columns |
| `decomposition.png/.pdf` | Report figure: N=9 on 2×2 and N=10 on 3×2, one block's ghost layer and its four unexchanged corners |
| `cases.png` | Case 1 and 2 computed by 3×2 blocks (N=64, 500 steps), block boundaries marked; both byte-identical to serial |
| `timing.csv` | 36 strips-vs-blocks timing runs: P = 4, 6; N = 512, 2048, 8192; 10 steps; 3 interleaved repetitions |
| `timing_summary.csv` | Median, min and max exchange time per step, and median computation and total time per step |
| `timing.png/.pdf` | Exchange time (with min–max) and total time per step, log scale |
| `raw_runs.json` | All 150 commands with stdout, stderr and return codes (all zero) |
| `metadata.json` | Mode, mpirun arguments, MPI version, parameters, SHA-256 of the serial, strips and blocks sources |
| `manifest.json` | Sizes and SHA-256 of the eleven published run files |
| `console/` | Terminal transcripts: `make check-blocks`, the cluster run, `verify_results.py` |
| `review.json` | Review record: checks, summary numbers, the redaction and console-file hashes |

## Review

- **Correctness suite:** six groups, `OK` (`console/check-blocks.txt`).
- **Comparisons:** 90/90 byte-identical, with matching summary values (steps, r, dt, T,
  minimum, maximum and V error norms). They cover Cases 1, 2 and V, N = 8, 9, 10, 17, 64,
  101, and P = 1, 2, 3, 4, 6, i.e. grids 1×1, 2×1, 3×1, 2×2 and 3×2. 48 rows have uneven blocks.
- **Machines:** every P=2 run used 2 VMs; every P=3, 4 or 6 run used all 3 (72 multi-machine
  runs). Every timing run used all 3.
- **Provenance:** the source hashes in `metadata.json` equal the committed `heat_serial.cpp`,
  `heat_mpi.cpp` and `heat_blocks.cpp`. Manifest hashes were re-verified after transfer.
- **Halo debugging:** in `debug_halo.txt`, every ghost row and ghost column equals the
  neighbour's owned values, plate-edge ghosts hold 1.0, and the corners print as `-`.
  The 3×2 grid splits N=8 into rows 3/2/2 and columns 4/3.
- **Figures:** all three were inspected. The fields are symmetric, lie within [0,1] and
  show no seam at block edges.
- **stderr:** 148 runs have empty stderr. Two contain only Open MPI's harmless launcher
  warning `plm:rsh: Warning: setpgid(...) failed ... Permission denied`. Both returned 0,
  and their fields match serial.
- **Privacy:** that warning included the launching VM's device hostname. It was replaced by
  `heat3`, and the `raw_runs.json` entry of `manifest.json` was updated to match. The
  original hash and size are recorded in `review.json`. No network addresses or account
  identifiers remain.

The timing check answers the Part 3 strips-vs-blocks question. It is not the Part 4 study.
It is analysed in [ANALYSIS.md](../../ANALYSIS.md#then-check-measured-strips-vs-blocks).
Blocks win at N = 8192 (6/6 paired repetitions). Strips win at N ≤ 2048 (10/12).
Communication is at least 98.1 % of every run.
From the repository root, run `make verify-part3-results` to re-check this archive.
