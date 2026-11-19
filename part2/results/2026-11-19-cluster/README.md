# Reviewed cluster C2 study, 19 November 2026

Primary source: run folder `20261119T184915639127Z`, launched from heat-3 at
2026-11-19 18:49:15 UTC with `python3 part2/run_experiments.py --cluster`
(Linux x86_64, Open MPI 4.1.6, commit 1c2b5e6). All three VMs had built the same
commit at `~/heat-project-repo`. The folder was copied to Windows with `scp`
and archived here unchanged, except that the regenerable `fields/*.bin` serial
reference fields were left out.

| File | Content |
| --- | --- |
| `compare.csv` | 84 serial-vs-strips comparisons: case, N, P, machines used, uneven strips, byte equality, incidental timers |
| `debug_halo.txt` | Section 6 debugging runs: Case 2, N=8, one step, P=2 and P=3, every rank's rows and ghost rows |
| `decomposition.png/.pdf` | Report figure of the row split (N=9, P=3 and N=10, P=4) and ghost rows |
| `cases.png` | Case 1 and 2 computed by strips (P=4, N=64, 500 steps), strip boundaries marked; both byte-identical to serial |
| `raw_runs.json` | All 111 commands with stdout, stderr (all empty) and return codes (all zero) |
| `metadata.json` | Mode, mpirun arguments, MPI version, parameters, SHA-256 of both solver sources |
| `manifest.json` | Sizes and SHA-256 of the seven published run files, written by the run itself |
| `console/` | Terminal transcripts: `make check-strips`, the cluster run, `verify_results.py`, executed commit |
| `review.json` | Review record: checks performed, summary numbers, console-file hashes |

## Review

- **Correctness suite:** six groups, `OK` (`console/check-strips.txt`).
- **Comparisons:** 84/84 byte-identical, with matching summary values (steps, r, dt, T,
  minimum, maximum and V error norms). They cover Cases 1, 2 and V, N = 8, 9, 10, 16, 17, 64, 101,
  and P = 1, 2, 3, 4. Uneven strips appear in 36 rows, 12 for each P ≥ 2.
- **Machines:** every P=2 run used 2 VMs and every P=3 or P=4 run used all 3.
- **Provenance:** the source hashes in `metadata.json` equal the committed `heat_mpi.cpp`
  and `heat_serial.cpp`. Manifest hashes were re-verified after transfer.
- **Halo debugging:** in `debug_halo.txt` every ghost row equals the neighbour's owned
  row, the plate rows are the fixed boundary values, and P=3 gives the uneven split 3, 2, 2.
- **Figures:** both were inspected. The fields are symmetric, lie within [0,1] and show no seam at strip boundaries.
- **Privacy:** published files contain no network addresses, hostnames or account identifiers.

Timers are incidental: each configuration was run once, for correctness. They are
summarised in [ANALYSIS.md](../../ANALYSIS.md#results) and are not Part 4 measurements.
From the repository root, run `make verify-part2-results` to re-check this archive.
