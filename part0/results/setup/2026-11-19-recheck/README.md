# Successful Part 0 recheck

Four supplied text records are preserved here as public copies. The exact
original archive is retained privately. The manifest records its SHA-256 plus
source/public hashes and byte counts for every capture. Actual addresses and
the third node's real hostname are replaced with aliases.

| Capture (UTC) | Result |
| --- | --- |
| Heat-2 connectivity, 14:45:37 | Historical failure on unknown SSH host keys, retained |
| Heat-2 connectivity, 15:30:12 | PASS: both destination hostnames and mpi returned; no SSH failures |
| MPI hello, 14:46:55 | Historical failure on third-node working directory, retained |
| MPI hello, 15:34:24 | PASS: ranks 0-5, size=6, rank_sum=15, two ranks per node |

Combined with the original inventory, other four SSH directions, hostname
placement and network study, the latest captures complete Part 0 technical work.
New direct-route observations are specific to these probes and do not alter the
17 November benchmark-route record.

From the repository root, `python3 part0/05-analysis/verify_setup.py` verifies all
12 archived text records and selects eight latest current checks, returning 0.
The `--initial-only` option retains the original failure assessment (exit 1).
