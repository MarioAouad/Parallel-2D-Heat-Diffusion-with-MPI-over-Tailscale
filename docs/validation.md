# Validation status

**Parts 0 and 1 technical work and evidence review are complete
(19 November 2026).** This page records the current assessment. Earlier failures
remain in the original evidence and append-only interaction index.

## Evidence and completed checks

| Area | Verified outcome |
| --- | --- |
| Part 0 measurements | All 30 published files match the manifest; six sweeps, 22 sizes each, 132 rows; hosts, RTT/2, throughput and successful logs agree |
| Original measurement preservation | Numeric measurements match private originals; public records anonymize identifying fields and retain original/public hashes |
| Current cluster setup | Three inventories, all six directed SSH logins, correct six-process hostname placement, and six-rank hello with rank_sum=15; two ranks per VM |
| Repaired setup history | Default verifier checks all 12 preserved text records and assesses the latest capture for each check; the initial snapshot still fails as expected |
| Part 0 source organization | Original C++ executable tokens and analyzer Python AST were compared; added comments retained the original statements |
| Analysis | Six analysis tests passed; all six real-data fits and plots reproduced the reviewed model values |
| Shell/configuration | Bash syntax and four no-network configuration-loader cases passed during organization |
| Serial correctness | Six groups passed on Windows and in user-supplied Ubuntu console output: known steps, boundaries/buffers, symmetry/bounds, sine mode/norms, time rounding, input rejection and isolated instability |
| Primary Ubuntu archive | All ten invocations returned zero; source hash matches the serial solver; nine original public files retain exact bytes/hashes |
| Convergence | Five rows match raw outputs and independent discrete sine-mode predictions; weighted L2 norms and orders near two recompute correctly |
| Full fields | Five 33800-byte binary fields checked privately; stable fields preserve boundaries, corner precedence, bounds and reflection symmetry; unstable extrema match CSVs |
| Figures | All three Ubuntu PNGs and both vector PDF plots visually inspected |
| Written solutions | 32-page PDF, editable source, 25 required tasks plus optional 6.5; provenance checked and sample pages inspected |
| Publication | Relative links, public-file scans and archive hashes checked; private originals/configuration/conversations remain excluded |

The primary Ubuntu archive is
`part1/results/2026-11-19-ubuntu/`; its source archive SHA-256 is
`babe3d4f0730f4f017a4b69a0de87e43677642a2d6c06295a2b028626233269b`.
All 14 original members remain private, including five reproducible binary
snapshots. See its [manifest](../part1/results/2026-11-19-ubuntu/manifest.json)
and [review record](../part1/results/2026-11-19-ubuntu/review.json).

The earlier Windows study and first Ubuntu smoke output are supporting records.
The [results index](../part1/results/README.md) distinguishes them from the
primary study. Boundary-heated Windows/Ubuntu fields matched byte-for-byte;
this is a serial cross-platform observation, not MPI solver validation.

## Recheck without collecting new measurements

From the repository root on Ubuntu:

```bash
make verify-setup
make verify-results
make verify-part1-results
make test-analysis
```

The first three use Python's standard library; analysis tests require NumPy and
Matplotlib. On Windows, use `python` with the scripts named in the Makefile.
To reproduce the initial setup assessment:

```bash
python3 part0/05-analysis/verify_setup.py --initial-only
```

That historical mode intentionally exits 1 for the old SSH and hello failures.
Default verification uses the later successful captures and exits 0.

## Limits and remaining work

- The team collected the actual Ubuntu/cluster terminal evidence. The assistant
  reviewed the supplied files; no new remote cluster experiment is claimed.
- Inventory captures describe 19 November; they do not retroactively certify
  every setting during the 17 November measurements.
- Route snapshots are observations before/after a run, and serial loop timings
  are incidental values. Neither is a controlled Part 4 scaling experiment.
- The background PDF was preserved with source/provenance and sample-page
  inspection; no new full audit of every written proof is claimed.
- Part 2/3 decompositions and bit-for-bit comparisons, Part 4 repeated performance
  study, final report/demo, actual team contributions and complete earlier
  private AI histories remain in the [deliverable map](deliverables.md).
