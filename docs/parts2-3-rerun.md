# Reproduce the Parts 2 and 3 cluster studies

The [reviewed strips](../part2/results/2026-11-21-retained-cluster/) and
[reviewed blocks](../part3/results/2026-11-21-retained-cluster/) studies already
contain the original fields and pass strict checks. Run the instructions below
only when collecting a separate dataset.

1. Bring all three VMs to the same Git revision at the same absolute path
   using the [update guide](local-update.md). Build on each VM with `make`.
2. Confirm the actual guest vCPUs with `nproc`, check connectivity from the
   launcher and set the corresponding slot counts in the ignored
   `part0/config/cluster.local.sh`. The eight-rank study used
   `HEAT1_SLOTS=4`, `HEAT2_SLOTS=2` and `HEAT3_SLOTS=2`. The runners validate
   slots against the guest counts and refuse oversubscription. Record route
   probes and keep other workloads off the guests during timing.
3. Run the checked study once on the launching VM as `mpi`:

   ```bash
   bash scripts/rerun-parts23.sh
   ```

The helper runs local correctness groups and the cluster comparisons, then
prints the location of a private transfer bundle. It records the revision, VM
inventories, slot checks, binary hashes, fields, timing records and verifier
output. Keep the complete bundle internally. For public review, remove private
endpoint and account details while preserving raw measurements.

New studies retain every binary field, and the manifests record each file’s
size and SHA-256. Review the entire study before placing it under a new
`part2/results/<label>-cluster/` or `part3/results/<label>-cluster/` directory.
Keep older studies, including the 19 November record-only archives, intact.
For manual runner commands see the [Part 2 guide](../part2/README.md) and
the [rerun script](../scripts/rerun-parts23.sh).
