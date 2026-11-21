# Reviewed retained-field part2 cluster study

Primary evidence reviewed on 21 November 2026 from the user's original bundle.
The run began on 20 November UTC / 21 November Beirut. Code revision: `60fc802`.
The VM allocation was heat1=4, heat2=2, heat3=2 guest vCPUs, eight total.
All VMs used matching Open MPI 4.1.6 and identical hashes for all three executables.

All comparison and figure fields are retained under `fields/`. Original study
files and `manifest.json` are copied byte for byte. The older dated archive is
unchanged. Supplemental console files and `review.json` document this review.
Private inventories, endpoint addresses and the original full outer bundle are
kept outside this public-ready study directory.

Strict verification passed with `--require-fields`.
Serial-versus-MPI comparisons are exact byte comparisons. Independent Python
Case V recomputation on Windows used the documented C-library tolerance for a
few fields; this does not relax the exact serial/MPI comparison.

Network prechecks included relay use. Timing describes that observed run, not
a guarantee of direct routes or a completed Part 4 performance campaign.
