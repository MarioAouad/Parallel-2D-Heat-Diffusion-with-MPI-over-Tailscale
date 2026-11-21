# Part 4 results

No reviewed real Part 4 campaign is archived yet.

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
