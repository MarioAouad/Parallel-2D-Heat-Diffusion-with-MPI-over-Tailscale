# Part 2 results index

| Record | Role | Contents |
| --- | --- | --- |
| *(none yet)* | Primary Part 2 delivery: the C2 cluster study | Pending: `compare.csv`, `debug_halo.txt`, `decomposition.png/.pdf`, `cases.png`, `raw_runs.json`, `metadata.json`, `manifest.json` |

`python3 part2/run_experiments.py --cluster` writes a new timestamped folder under the
ignored `runs/` directory. Review it before publishing:

1. `python3 part2/verify_results.py --data part2/results/runs/<stamp>` passes;
2. the figures have been inspected;
3. every P ≥ 2 row has `nodes` ≥ 2.

Then copy the folder unchanged to `part2/results/<date>-cluster/` and add a row above.
Keep the dated original and its manifest unchanged afterwards.
`make verify-part2-results` checks the newest archived study.

Binary fields (`fields/*.bin`) stay ignored. The experiment script regenerates them, and the
byte comparison results are recorded in `compare.csv`. Timings in these runs are incidental
correctness-run measurements, not Part 4 data.
