# Part 3 results index

| Record | Role | Contents |
| --- | --- | --- |
| [2026-11-19-cluster](2026-11-19-cluster/) | Primary Part 3 delivery: the cluster study | 90/90 byte-identical (P = 1–6, grids up to 3×2, 2–3 VMs); halo transcripts; figures; 36-run strips-vs-blocks timing check. [Review](2026-11-19-cluster/README.md) |

`python3 part3/run_experiments.py --cluster` writes a new timestamped folder under the
ignored `runs/` directory. Review it before publishing:

1. `python3 part3/verify_results.py --data part3/results/runs/<stamp>` passes;
2. the figures have been inspected;
3. every P ≥ 2 row has `nodes` ≥ 2.

Then copy the folder unchanged, **including** `fields/` (Git accepts
`part3/results/*-cluster/fields/*.bin`), to `part3/results/<date>-cluster/`,
and add a row above. `make verify-part3-results` checks the newest archived study.

The timing stage is a small, repeated check of the Part 3 strips-vs-blocks question.
The full scaling study belongs to Part 4.
