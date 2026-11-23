# Part 4 results

The [reviewed full campaign](2026-11-24-cluster/) was measured on 23 November UTC
and reviewed on 24 November 2026 local time. It passes the strict full-profile
verifier: 429 heat measurements, 18 calibration sweeps and 16 placement probes.
There are 143 configurations with exactly three repetitions each. The guests use
4+2+2 actual vCPUs/slots; all P=1..8 are measured.

```bash
python3 part4/verify_results.py --data part4/results/2026-11-24-cluster
```

No CSV, heat summary, command, warning, figure, metadata or checkpoint was changed
after measurement. The original return archive remains private. The reviewed
public copy additionally replaces 108 account identifiers in 36 network-status
stdout records and has a new manifest. The derived/original hashes and exact
policy are in [the review](../review.json). `private/` and original terminal logs
stay in the private course hand-in, not the public study.

Of 509 raw invocations, 499 are referenced by successful checkpoints. Nine
warning-only rejected attempts and one genuine MPI disconnection (exit 205) remain
in raw history. `failed_attempts_retained=1` counts nonzero process exits only;
it must not be described as the total number of rejected warning attempts.

Best tested results use four ranks on heat1 with slot placement: speed-ups 2.68,
2.92 and 2.86 at N=512,2048,8192. None of the 66 cross-guest strong configurations
beats serial heat1. Retained spread and route/VM interruptions limit stationary
performance claims; see [the report](../../docs/final-report/final-report.pdf).

New runs, session logs and return archives go under the ignored `runs/` directory.
Analysis scratch goes under ignored `analysis-local/`. Do not force-add these
folders or confuse a smoke fixture with official evidence.

After a full run:

1. Verify with `python3 part4/verify_results.py --data /run/folder`.
2. Inspect all plots, raw warnings, failed attempts, conditions and model fits.
3. Keep the complete original return bundle, especially `private/`, in the private
   course hand-in.
4. Copy the public study files unchanged into a new dated `*-cluster/` folder,
   excluding `private/` (also protected by .gitignore). Public raw commands already
   use generic guest aliases; inspect them and operator notes before publishing.
5. Re-run strict verification on the copied archive and add a review/index entry.

Do not edit recorded measurements or existing dated archives. Reviewed CSVs,
JSON/JSONL, plots, PDFs, report and manifests belong in Git. No full-grid `.bin`
files are required for this no-output timing campaign. The existing reviewed
Part 2/3 `.bin` fields remain committed correctness evidence.
