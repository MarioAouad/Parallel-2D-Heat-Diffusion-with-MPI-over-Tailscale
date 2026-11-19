# Reviewed Ubuntu Part 1 study

Primary source: the user's run folder `20261119T161615613935Z` from heat-1,
Linux x86_64, generated at 2026-11-19 16:16:15.613935 UTC. The supplied tar.gz
and all fourteen original member files are retained privately. The nine
published original files here are byte-identical copies, including CSV line
endings. `.gitattributes` preserves result bytes across Git checkouts.

`manifest.json` records the source archive hash, nine public file hashes and
five private/reproducible binary snapshot hashes. `metadata.json` is the original
study metadata, including the solver source hash. `raw_runs.json` preserves
all ten commands, stdout, stderr and return statuses.

Review checked every convergence row against the raw run and discrete sine-mode
formula, all three unstable extrema against their binary fields, and both
stable cases for finite values, [0,1] bounds, fixed boundaries and reflection
symmetry. All five binary files have the required 33800-byte layout and match
the corresponding earlier Windows boundary-heated snapshots byte-for-byte.
All three PNG figures were visually inspected. This is serial evidence; no
parallel solver has been validated yet.

Read [the analysis](../../ANALYSIS.md) and [delivery checklist](../../DELIVERY.md).
From the repository root, run `make verify-part1-results` to verify the public
archive. New experiments go into a new run folder; this study is preserved.
Raw loop timings are incidental correctness-study measurements, not Part 4 data.
