# Run Parts 2 and 3 again and return the complete evidence

Run as `mpi`, with the repository at `/home/mpi/heat-project-repo` on all three
VMs. All VMs must stay awake and connected. A study is launched once from one VM;
do not launch the same study independently on all three. Keep the launching
terminal open, or use an existing persistent terminal session.

## 1. Real CPU allocation for P=8

The archived allocation was 2+2+2 guest vCPUs. P=8 needs at least eight allocated
guest vCPUs, for example 2+2+4. The owner of the VM being changed must shut it
down, change its VirtualBox CPU allocation, restart it and confirm `nproc`.
SSH cannot change a Windows host's VirtualBox settings from inside the guest.
Record the changed hypervisor allocation as well as the new guest inventory.

On the launching VM, edit the existing private configuration:

```bash
cd /home/mpi/heat-project-repo
nano part0/config/cluster.local.sh
```

For actual allocations of heat-1=2, heat-2=2, heat-3=4, set these entries while
retaining the existing real endpoints:

```bash
HEAT1_SLOTS=2
HEAT2_SLOTS=2
HEAT3_SLOTS=4
```

Match the entries to your actual allocation if a different VM gets the extra
CPUs. Each guest's private configuration can retain its endpoints; synchronize
slot entries on any VM you intend to use as a launcher. Never claim extra slots
without allocating the guest CPUs. With six real slots you can still produce
retained-field studies, but P=8 remains open unless the instructor accepts a
substitution. The strict sequence below requires eight.

## 2. Update and build all VMs from one terminal

Yes: SSH from your VM can run `git pull` and `make` on your friends' VMs. Their
VMs must already allow the configured `mpi` user's SSH key and have working
GitHub access. The block checks for local tracked/untracked work and stops
instead of discarding it. Ignored private configuration and run folders are kept.

After pulling the published version on the launching VM, run the
[update helper](../scripts/update-vms.sh) from its repository root:

```bash
bash scripts/update-vms.sh
```

If any pull, SSH login, revision check or build fails, stop and send its output.
Do not reset or force-pull over your friends' changes. Re-run the whole update
block after resolving the issue. If the branch changes during the updates, the
revision check stops the sequence; update again to synchronize.

## 3. Collect checks, retained fields and required P=8 timings

The [rerun helper](../scripts/rerun-parts23.sh) creates a new ignored `output/parts23-<timestamp>/` folder. It
records revision/inventory and directed connectivity checks from each VM, runs
the local MPI correctness groups, checks eight real slots, and runs the two
studies sequentially. No old archive is overwritten. The Part 3 command selects
P=4,8 for timing, avoiding a redundant P=6 timing stage; its correctness stage
still includes P=6. Default timing uses three repetitions and ten steps.

```bash
bash scripts/rerun-parts23.sh
```

The command block stops on a failed check. If it stops before creating the
archive, retain the partial folder and send the failing output first. Do not
launch another study while any MPI run is still active. Before timing, inspect
the connectivity output: relay versus direct paths affect performance; a
successful SSH connection alone does not establish a direct route. Keep the
VMs/host PCs free of other heavy work during the studies. Connectivity probes
are observations, not proof of the route throughout a run.

The inventories/hostfile contain private machine and endpoint information. Send
the bundle privately for review; it is not automatically ready for public Git.
Do not add credentials, private configuration scripts or SSH keys to it.

## 4. What to send back

Return the complete `.tar.gz` printed at the end, the update log from step 2,
and a screenshot/record of any changed VirtualBox CPU allocation. The bundle
contains `fields/`, comparison CSVs, raw command JSON, metadata, manifests,
debug transcripts, plots, timing repetitions/summaries, verifier outputs,
inventories, capacity checks, binary hashes and connectivity observations.

If you cannot transfer the archive immediately, first send the two verifier
outputs, `checked-slots.txt`, `revision.txt`, and any error. Console PASS text
alone cannot close the retained-field evidence gap. Keep all original folders.

After review, archive new studies under new labels, preserve the older archives,
and update the deliverable status. Part 4 implementation/measurement planning can
then use the frozen configuration; Part 4 is a separate performance campaign,
not completed by these correctness runs. Missing earlier AI histories remain a
separate course-submission obligation.

## Estimated time

The old Part 2 raw outputs sum to about 6.1 minutes of solver-loop time. The old
Part 3 P=4,6 study sums to about 39.8 minutes, including approximately 20 minutes
of timing runs. These sums exclude MPI launch/SSH/plotting overhead and do not
measure P=8. The new P=4,8 timing matrix has the same number of timing invocations
as the older P=4,6 matrix, plus an extra P=8 correctness group.

Allow roughly 5–15 minutes for updating/building/prechecks, 10–20 minutes for
Part 2, and 45–90 minutes for Part 3 with P=8. Budget about 1–2 hours overall,
and longer if Wi-Fi/Tailscale/relay conditions are worse. This is a planning
estimate, not a measured P=8 runtime; allocating/restarting a VM adds time.
