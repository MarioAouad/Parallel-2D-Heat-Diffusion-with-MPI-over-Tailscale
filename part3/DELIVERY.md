# Part 3 delivery checklist

This maps assignment section 7 to the code and evidence. **Complete:** every row's
evidence points at the reviewed [cluster study](results/2026-11-19-cluster/) of 19 November 2026
(90/90 byte-identical across 2–3 VMs). Checkpoint C3 also includes the Part 4
performance runs, which are not part of this checklist.

| Requirement (assignment section 7) | Where it is implemented | Evidence |
| --- | --- | --- |
| Arrange P processes in a Px×Py grid; each owns a rectangular block of interior nodes with ghost layers on all four sides | Local (rows+2)×(cols+2) storage in [heat_blocks.cpp](heat_blocks.cpp) | Grid/size test ([console/check-blocks.txt](results/2026-11-19-cluster/console/check-blocks.txt)); [decomposition.png](results/2026-11-19-cluster/decomposition.png) |
| Choose the grid with `MPI_Dims_create`; build it with `MPI_Cart_create` (non-periodic); neighbours with `MPI_Cart_shift`; plate edges are `MPI_PROC_NULL` | Process-grid block in `run()` | Grid/neighbour test; [debug_halo.txt](results/2026-11-19-cluster/debug_halo.txt) lists coords and `down/up/left/right` (`none` at plate edges) for 2×2 and 3×2; `Py`/`Px` in every row of [compare.csv](results/2026-11-19-cluster/compare.csv) |
| Split rows and columns as evenly as possible, as in Part 2 | `split()` applied to y and x | Size test; 48 uneven rows in `compare.csv`; 3×2 transcript shows rows 3/2/2 and columns 4/3 for N = 8 |
| Rows sent contiguously; **columns with an `MPI_Type_vector` derived datatype**, not by copying into a buffer by hand | `exchange` lambda, `column` type | Code; ghost-column test (P = 4, 6) OK; every ghost column in `debug_halo.txt` equals the neighbour's owned column |
| Output identical to serial, as in Part 2 | Unchanged stencil, data and time-step code; subarray gather | **90/90 byte-identical** for P = 1, 2, 3, 4, 6 (grids up to 3×2), Cases 1, 2, V, six N; P ≥ 2 on 2–3 VMs ([ANALYSIS](ANALYSIS.md#correctness-results)); [cases.png](results/2026-11-19-cluster/cases.png) |
| Report: why corner ghosts are not needed, and which stencil would need them | — | [ANALYSIS, question 1](ANALYSIS.md#question-1-why-are-corner-ghosts-not-needed); corners print as `-` in `debug_halo.txt` and results still match serial |
| Report: predict strips vs blocks for P = 4, 8 and N = 512, 2048, 8192 from Task 8.2 with the measured t<sub>s</sub>, t<sub>w</sub>, then check | Model in ANALYSIS; timing stage of `run_experiments.py` | [Prediction table](ANALYSIS.md#question-2-strips-or-blocks-prediction-from-task-82-with-the-measured-ts-tw) and [measured check](ANALYSIS.md#then-check-measured-strips-vs-blocks) for P = 4, 6 ([timing_summary.csv](results/2026-11-19-cluster/timing_summary.csv), [timing.png](results/2026-11-19-cluster/timing.png)): blocks win at N = 8192, strips at N ≤ 2048, explained. P = 8 is model-only (6 slots) |
| Optional: overlap communication with computation (`MPI_Isend`/`MPI_Irecv`) | Not attempted | — |

## Single-machine pre-check (not evidence)

Before the cluster run, the code was built and run on one machine (WSL Ubuntu 26.04,
GCC with Open MPI, 12 logical CPUs, 19 November 2026):

- `make serial strips blocks` compiled with no warnings under `-Wall -Wextra -Wpedantic`;
- `make check-blocks` passed all six groups;
- `python3 part3/run_experiments.py --timing` gave 90/90 byte-identical comparisons
  (P = 1, 2, 3, 4, 6; grids 1×1, 2×1, 3×1, 2×2, 3×2) and complete transcripts and figures;
- `python3 part3/verify_results.py --allow-local` passed.

This shows that the code and scripts work. It is **not** the C3 evidence: all ranks
shared one machine, so no message crossed the network and its timings say nothing about
the strips-vs-blocks question. That run was not archived.

## How to produce the evidence (Ubuntu, repository root)

All three VMs need the same commit, built at the same path:

```bash
cd ~/heat-project-repo && git pull --ff-only origin main && make serial strips blocks
```

Then, on one VM:

```bash
make check-blocks                                   # 1. six correctness groups (this VM)
python3 part3/run_experiments.py --cluster          # 2. comparisons + debug + figures + timing across the VMs
python3 part3/verify_results.py --data part3/results/runs/<stamp>   # 3. offline check of that folder
```

Before step 2, make every VM pair `direct` in `tailscale ping`, and keep all three VMs free
of other work during the timing stage (assignment section 8.1).

## Scripts

| Script | Purpose | Part 2 counterpart |
| --- | --- | --- |
| [verify_blocks.py](verify_blocks.py) | Six correctness groups against the built executables | `verify_strips.py` |
| [run_experiments.py](run_experiments.py) | Comparisons, halo-debug transcripts, figures, strips-vs-blocks timing, manifest | `run_experiments.py` |
| [verify_results.py](verify_results.py) | Offline verification of an archived study | `verify_results.py` |

## Not in Part 3

The full performance study (single-node baseline, strong and weak scaling for both
placements, communication share against the model) is Part 4.
