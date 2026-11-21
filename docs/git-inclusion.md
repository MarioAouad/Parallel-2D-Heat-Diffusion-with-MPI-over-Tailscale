# What belongs in the pending commit

File count alone is not a reason to ignore evidence. The reviewed new Part 2/3
archives contain **239 small original field files** (109 strips-study and 130
blocks-study files). Keep those: they close the missing-field gap and let the
strict verifier repeat byte comparisons. Their original manifests/hashes remain
unchanged. The existing specific .bin exceptions for reviewed cluster archives
are intentional; do not replace them with a blanket exclusion of all fields.

## Include

- Reviewed Part 2/3 dated study folders, original fields, CSV/JSON, plots/PDFs,
  manifests, public-safe console evidence and review notes.
- Part 4 Python sources/tests, Bash helpers, Makefile targets and documentation.
- .gitignore/.gitattributes and the append-only public interaction log.
- Later, a reviewed Part 4 archive's public measurements, calibration, raw JSONL,
  metadata, placement evidence, analysis tables, plots and generated report.

## Exclude

- Build products and platform-specific executables/objects.
- `output/` transfers, extracted review copies, temporary renderings and tarballs.
- `part4/results/runs/`, including long-running campaign logs and return bundles.
- `part4/results/analysis-local/` scratch analysis.
- Every `part4/results/**/private/` directory, including unredacted raw commands.
- Private cluster addresses/configuration, SSH keys and complete private chat exports.
- Python caches, environments and incomplete `.partial` writes.

The new ignore entries cover unreviewed Part 4 data and private records. They do
not hide CSVs, figures, PDFs or reviewed evidence globally. Measured Part 4 files
are promoted to a dated public archive only after review, as in Parts 2/3.
The complete original bundle stays in the private course submission.

## Review before committing

```bash
git status --short
git diff --check
git diff --stat
git ls-files --others --exclude-standard
git check-ignore part4/results/runs/example/raw_runs.jsonl
git check-ignore part4/results/example-cluster/private/raw_runs.jsonl
```

The last two should print the ignored paths. In contrast, a reviewed Part 2/3
`*-cluster/fields/*.bin` and a reviewed Part 4 `measurements.csv` must remain
eligible for Git. `make test-part4` tests this distinction.

Stage the reviewed paths, inspect `git diff --cached --stat` and
`git diff --cached --check`, and include the corresponding interaction log.
Do not force-add the full original private bundle or an in-progress campaign.
