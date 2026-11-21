# Part 2 delivery checklist

**Current review, 21 November 2026:** The [new retained-field cluster study](results/2026-11-21-retained-cluster/) passes strict verification: 84/84 exact comparisons, 109 retained fields, all three VMs represented. The missing-original-fields gap is closed by this new run; old archives remain record-only. Earlier dates and open-gap descriptions below refer to the historical archive, not the current delivery.


Part 2 implementation and archived C2 records pass the technical checks.
**Retained-field evidence is now archived and verified; C2 technical evidence is complete.**
The historical evidence below is the reviewed [cluster study of 19 November 2026](results/2026-11-19-cluster/),
launched from heat-3 across all three VMs. This checklist is the Part 2 handoff. It does
not claim that Part 3 (blocks), Part 4 (performance) or the final report are complete.

Evidence links point to files in [`results/2026-11-19-cluster/`](results/2026-11-19-cluster/).

| Requirement (assignment section 6) | Where it is implemented | Evidence |
| --- | --- | --- |
| Split the N−1 interior rows into contiguous strips; the first (N−1) mod P ranks get one extra row; rank 0 is the bottom strip | `strip_of()` in [heat_mpi.cpp](heat_mpi.cpp) | Row-size test OK ([check-strips](results/2026-11-19-cluster/console/check-strips.txt)); [decomposition figure](results/2026-11-19-cluster/decomposition.png); [debug transcripts](results/2026-11-19-cluster/debug_halo.txt) show 4/3 and 3/2/2 rows |
| Local array of n<sub>local</sub>+2 rows of N+1 values; plate boundary acts as the edge ranks' ghost row | `old`/`next` allocation and `initial_value()` | [debug transcripts](results/2026-11-19-cluster/debug_halo.txt): hot `boundary` rows on ranks 0 and P−1 |
| Halo exchange with `MPI_Sendrecv`; `MPI_PROC_NULL` at the outer edges; no special cases | `exchange` lambda | Ghost-equals-neighbour test OK for P = 2, 3, 4 after 1, 2, 5 steps; [debug transcripts](results/2026-11-19-cluster/debug_halo.txt) |
| Each row sent as one message of N+1 doubles, directly from the array | `exchange` (`count = N+1`, pointer to the row) | Code; byte-identical results |
| Exchange and computation timed separately; maximum over ranks with `MPI_Reduce(MPI_MAX)` | `t_comm`, `t_comp`, `t_total` | Summary-field test OK; timers in [compare.csv](results/2026-11-19-cluster/compare.csv), interpreted in [ANALYSIS](ANALYSIS.md#incidental-timing-what-one-correctness-run-already-shows) |
| Explain the blocking-Send deadlock and why `MPI_Sendrecv` avoids it | — | [README](README.md#why-a-blocking-send-then-recv-exchange-can-deadlock-report-question), [ANALYSIS](ANALYSIS.md#halo-exchange-and-deadlock) |
| Rank 0 assembles the full field (`MPI_Gatherv`) and writes the Part 1 file format | Gather block and `write_field()` | 84 field files byte-identical to serial |
| Field file bit-for-bit identical to serial for the same N, r and steps (`cmp`) | Unchanged stencil, data and time-step code | **84/84 identical** in [compare.csv](results/2026-11-19-cluster/compare.csv); Case 1/2 [figure](results/2026-11-19-cluster/cases.png) also byte-identical |
| Debugging aid: N=8, P=2 and P=3, one step, print arrays including ghost rows | `--debug-print` | [debug_halo.txt](results/2026-11-19-cluster/debug_halo.txt) |
| **C2:** identical output for P = 1, 2, 3, 4 and several N, including N−1 not divisible by P, **across at least two VMs** | `run_experiments.py --cluster` (`--map-by node`) | P = 1–4; N = 8, 9, 10, 16, 17, 64, 101; 36 uneven rows; `nodes` = 2 for P=2 and 3 for P=3, 4 — [verified](results/2026-11-19-cluster/console/verify-results.txt) |

## Verified checks

- `make check-strips` on heat-3: six groups OK
  ([transcript](results/2026-11-19-cluster/console/check-strips.txt)).
- Cluster run: 111 commands, all return codes zero, all stderr empty; 84/84 comparisons PASS
  ([transcript](results/2026-11-19-cluster/console/run-cluster.txt), [raw runs](results/2026-11-19-cluster/raw_runs.json)).
- `verify_results.py`: manifest hashes, unchanged sources, coverage, multi-machine spread and
  raw/CSV consistency all PASS, on heat-3 and again on the archived copy.
- Both figures were visually inspected. Published files contain no addresses or hostnames
  ([review](results/2026-11-19-cluster/review.json)).

## Reproduce (Ubuntu, repository root)

All three VMs need the same commit, built at the same path:

```bash
cd ~/heat-project-repo && git pull --ff-only origin main && make serial strips
```

Then, on one VM:

```bash
make check-strips                                   # six correctness groups (this VM)
python3 part2/run_experiments.py --cluster          # new C2 study across the VMs (runs/ folder)
make verify-part2-results                           # offline check of the archived study
```

Before running across the VMs, check that every pair is `direct` in `tailscale ping`. Part 0
showed that the first packets often go through a relay. The Python scripts need
`python3-numpy` and `python3-matplotlib` on the launching VM.

## Scripts

| Script | Purpose | Part 1 counterpart |
| --- | --- | --- |
| [verify_strips.py](verify_strips.py) | Six correctness groups against the built executables | `verify_serial.py` |
| [run_experiments.py](run_experiments.py) | C2 comparisons, halo-debug transcripts, figures, manifest | `run_experiments.py` |
| [verify_results.py](verify_results.py) | Offline verification of an archived study | `verify_results.py` |

## Public repository and private hand-in

GitHub holds the reviewed CSV, figures, raw command JSON, metadata, manifest, console
transcripts and review. The original transfer folder stays outside the commit.

**Historical evidence gap, now closed by the new archive: field files.** The 19 November study deleted each strips field after
comparing it, so its archive has no `.bin` files. Its byte equality rests on the
`identical` column recorded during the run, and `verify_results.py` reports it as
*record-only*. Since 20 November the runner keeps every field with its SHA-256, and the
verifier repeats the comparison offline and recomputes each serial field independently.
A new cluster run, archived **with** `fields/`, closes the gap. That complete new study is now archived and verified as linked above.

The complete AI-interaction record for this work still needs the full session exports
(see `llm_log/`).

Part 3 blocks are implemented and use the same serial reference. Close the
[retained-field gap](RECOVERY.md), then continue with Part 4 performance measurements.
