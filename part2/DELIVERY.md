# Part 2 delivery checklist

This maps assignment section 6 and checkpoint C2 to the code and evidence. **Code is
complete. Compilation on Ubuntu and the cluster C2 study are still pending.** A
requirement counts as delivered only once its evidence column points at a reviewed result.

| Requirement (assignment section 6) | Where it is implemented | Evidence |
| --- | --- | --- |
| Split the N−1 interior rows into contiguous strips; the first (N−1) mod P ranks get one extra row; rank 0 is the bottom strip | `strip_of()` in [heat_mpi.cpp](heat_mpi.cpp) | `verify_strips.py` row-size test; `decomposition.png` — pending |
| Local array of n<sub>local</sub>+2 rows of N+1 values; plate boundary acts as the edge ranks' ghost row | `old`/`next` allocation and `initial_value()` | debug test: boundary rows stay hot (Case 2) — pending |
| Halo exchange with `MPI_Sendrecv`; `MPI_PROC_NULL` at the outer edges; no special cases | `exchange` lambda | debug test: every ghost row equals the neighbour's row after 1, 2, 5 steps, P = 2, 3, 4 — pending |
| Each row sent as one message of N+1 doubles, directly from the array | `exchange` (`count = N+1`, pointer to the row) | code inspection |
| Exchange and computation timed separately; maximum over ranks with `MPI_Reduce(MPI_MAX)` | `t_comm`, `t_comp`, `t_total` | summary-field test — pending |
| Explain the blocking-Send deadlock and why `MPI_Sendrecv` avoids it | [README](README.md#why-a-blocking-send-then-recv-exchange-can-deadlock-report-question), [ANALYSIS](ANALYSIS.md#halo-exchange-and-deadlock) | written |
| Rank 0 assembles the full field (`MPI_Gatherv`) and writes the Part 1 file format | gather block and `write_field()` | byte-identical comparisons — pending |
| Field file bit-for-bit identical to serial for the same N, r and steps (`cmp`) | unchanged stencil, data and time-step code | `verify_strips.py` (one VM) and `run_experiments.py --cluster` — pending |
| Debugging aid: N=8, P=2 and P=3, one step, print arrays including ghost rows | `--debug-print` | `debug_halo.txt` in the study — pending |
| **C2:** identical output for P = 1, 2, 3, 4 and several N, including N−1 not divisible by P, **across at least two VMs** | `run_experiments.py --cluster` (`--map-by node`) | `compare.csv`, with a `nodes` column ≥ 2 for every P ≥ 2 — pending |

## How to produce the evidence (Ubuntu, repository root)

All three VMs need the same commit, built at the same path:

```bash
cd ~/heat-project-repo && git pull --ff-only origin main && make serial strips
```

Then, on one VM only:

```bash
make check-strips                                   # 1. correctness groups on this VM (oversubscribed)
python3 part2/run_experiments.py --cluster          # 2. C2 study across the VMs (new runs/ folder)
python3 part2/verify_results.py --data part2/results/runs/<stamp>   # 3. offline check of that folder
```

Before step 2, check that every VM pair is `direct` in `tailscale ping`; Part 0 showed
that the first packets often go through a relay. After review, copy the run folder to
`part2/results/<date>-cluster/`, update the [results index](results/README.md) and the
Results section of [ANALYSIS.md](ANALYSIS.md), then commit. `make verify-part2-results`
then checks the archived study.

## Scripts

| Script | Purpose | Part 1 counterpart |
| --- | --- | --- |
| [verify_strips.py](verify_strips.py) | Six correctness groups against the built executables | `verify_serial.py` |
| [run_experiments.py](run_experiments.py) | C2 comparisons, halo-debug transcripts, figures, manifest | `run_experiments.py` |
| [verify_results.py](verify_results.py) | Offline verification of an archived study | `verify_results.py` |

## Not in Part 2

The 2D block decomposition (Part 3) is not started. Speed-up and scaling are not measured
here: timings in C2 runs are incidental, and controlled repeated runs belong to Part 4.
The complete AI-interaction record still needs the full session export (see `llm_log/`).
