# Part 0 closeout

**Technical work complete, 19 November 2026.** The preserved setup captures and
six ping-pong sweeps cover the Part 0 requirements.

| Requirement | Current evidence |
| --- | --- |
| Matching guest software and resources | Three timestamped inventories: Ubuntu 24.04.5, Open MPI 4.1.6, two vCPUs each; configured VM RAM confirmed as 4096 MB |
| Every directed SSH connection | All six directions pass across the initial captures and later heat-2 recheck |
| Six-process hostname launch | Each VM appears twice |
| Six-rank MPI hello | Latest capture: ranks 0-5, size=6, rank_sum=15, two processes per VM |
| Same-VM and all-pair communication | Six full sweeps, 22 sizes each, 132 rows; analysis and qualified route observations preserved |

## Preserved failure and repair timeline

The [initial archive](../part0/results/setup/2026-11-19/) contains eight text
records. At 14:46:55 UTC, heat-2 rejected unknown SSH host keys and MPI hello
could not enter the third VM's checkout directory. Hostname placement and the
other four SSH directions succeeded.

The repair consisted of verifying/accepting destination SSH fingerprints on
heat-2 and ensuring the common checkout/build existed on the third VM.
The [recheck archive](../part0/results/setup/2026-11-19-recheck/) preserves both
old failures and later successes:

- **15:30:12 UTC:** heat-2 logs into both peers as mpi without a prompt.
- **15:34:24 UTC:** all six MPI hello ranks report the expected sum and placement.

No failed record or measurement was replaced. Exact archives remain private;
public copies and manifests disclose identity redaction and original/public
hashes. The [inventory](cluster-inventory.md) records host and VM details.

## Verify the completed record

```bash
make verify-setup
make verify-results
```

The setup verifier checks all 12 text records and uses the latest timestamped
capture for each check. Duplicate same-time copies must agree. Both commands
pass for the current archive.

For the original eight-record assessment, run:

```bash
python3 part0/05-analysis/verify_setup.py --initial-only
```

That historical mode intentionally exits 1. Its failures are expected and do
not describe the current setup.

## Route observations and next stage

A DERP reply can still accompany successful SSH; it does not explain an SSH
host-key error or a missing directory. Later direct probes do not establish the
route during the 17 November sweeps. Use the
[measured route qualifications](../part0/results/README.md) in the report.

[Part 1](../part1/DELIVERY.md) is also complete technically. The next stage is
Part 2 strip decomposition; the hours-long Part 0 sweeps need not be repeated
merely to continue. New setup/troubleshooting instructions remain in the
numbered [Part 0 guides](../part0/README.md), with the current Git workflow in
[local update](local-update.md).
