# Part 2 results index

| Record | Role | Contents |
| --- | --- | --- |
| [19 November cluster study](2026-11-19-cluster/) | **Primary Part 2 delivery (checkpoint C2)** | 84/84 byte-identical serial-vs-strips comparisons across 2–3 VMs, halo-debug transcripts, decomposition and Case 1/2 figures, raw commands, console transcripts, manifest and review |

Use the [analysis](../ANALYSIS.md) for interpretation and the
[delivery checklist](../DELIVERY.md) for requirement links.

`make verify-part2-results` checks the newest archived study offline.
`python3 part2/run_experiments.py [--cluster]` writes a new timestamped folder under the
ignored `runs/` directory. Before publishing a new run:

1. `python3 part2/verify_results.py --data part2/results/runs/<stamp>` passes;
2. the figures have been inspected;
3. every P ≥ 2 row has `nodes` ≥ 2.

Then copy the folder unchanged to `part2/results/<date>-cluster/` and add a row above.
Keep the dated original and its manifest unchanged afterwards.

Binary fields (`fields/*.bin`) stay ignored. The experiment script regenerates them, and the
byte comparison results are recorded in `compare.csv`. Timings in these runs are incidental
correctness-run measurements, not Part 4 data.
