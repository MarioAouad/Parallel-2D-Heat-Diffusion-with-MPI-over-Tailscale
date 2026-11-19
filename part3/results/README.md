# Part 3 results index

| Record | Role | Contents |
| --- | --- | --- |
| *(none yet)* | Primary Part 3 delivery: the cluster study | Pending: `compare.csv`, `debug_halo.txt`, `decomposition.png/.pdf`, `cases.png`, `timing.csv`, `timing_summary.csv`, `timing.png/.pdf`, `raw_runs.json`, `metadata.json`, `manifest.json` |

`python3 part3/run_experiments.py --cluster` writes a new timestamped folder under the
ignored `runs/` directory. Review it before publishing:

1. `python3 part3/verify_results.py --data part3/results/runs/<stamp>` passes;
2. the figures have been inspected;
3. every P ≥ 2 row has `nodes` ≥ 2.

Then copy the folder unchanged, except for `fields/`, to `part3/results/<date>-cluster/`,
and add a row above. `make verify-part3-results` checks the newest archived study.

The timing stage is a small, repeated check of the Part 3 strips-vs-blocks question.
The full scaling study belongs to Part 4.
