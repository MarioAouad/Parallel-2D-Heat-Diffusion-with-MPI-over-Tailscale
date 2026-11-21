# Part 2 results index

| Record | Role | Contents |
| --- | --- | --- |
| [21 November retained-field study](2026-11-21-retained-cluster/) | **Current primary evidence** | 84/84 exact serial/MPI comparisons; 109 original fields retained; strict offline verification PASS; C2 coverage on 2–3 VMs |
| [19 November cluster study](2026-11-19-cluster/) | Historical C2 record; original fields absent | 84/84 byte-identical serial-vs-strips comparisons across 2–3 VMs, halo-debug transcripts, decomposition and Case 1/2 figures, raw commands, console transcripts, manifest and review |

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

Since 20 November 2026 the runner keeps every field (`fields/*.bin`, about 2 MB) and lists
each with its SHA-256 in `compare.csv` and `manifest.json`. Archive the folder **with**
`fields/`: Git accepts `part2/results/*-cluster/fields/*.bin`. For such a study,
`verify_results.py` repeats the byte comparison offline, ties each field to the run that
printed its min/max and error norms, and recomputes every serial field independently.
The 19 November study predates this change and has no fields, so it verifies as
*record-only*: its byte equality is the `identical` column written during the run.
Timings in these runs are incidental correctness-run measurements, not Part 4 data.
