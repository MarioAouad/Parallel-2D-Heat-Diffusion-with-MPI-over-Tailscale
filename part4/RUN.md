# Run Part 4 on the three VMs

The code must be committed/pushed before the VMs can pull it. The implementation
alone is not a measured Part 4 result. Keep the allocation fixed at heat1=4,
heat2=2, heat3=2 unless you deliberately start a separately documented campaign.

## 1. Update and build

As `mpi` on heat-1, after publication:

```bash
cd /home/mpi/heat-project-repo
git status --short
# If that prints changes, preserve/reconcile them before continuing.
git pull --ff-only origin main
bash scripts/update-vms.sh
```

The updater now builds all targets, including the Part 0 ping-pong executable
reused for calibration. The runner refuses dirty or differing checkouts, missing
executables, changed capacity or still-running heat/ping-pong processes. Sources
must remain at the same absolute path on all guests. No compiled binary is pushed
or copied between architectures.

## 2. Preview

```bash
python3 part4/run_experiments.py --plan --slots 4,2,2
make test-part4
```

The preview prints the complete matrix without touching the cluster. Local tests
use synthetic data and do not measure the VMs. The live allocation is checked
over SSH/local nproc before a real run; preview slot arguments cannot bypass it.

## 3. Do a real smoke run first

Plug the laptops in, keep Windows and the VMs awake, close heavy applications and
record which hosts use Wi-Fi. Use actual conditions, editing this example if needed:

```bash
bash scripts/run-part4.sh smoke "All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2"
```

This uses small grids, fewer repetitions and P=1,2 to test the actual execution
path. It is **not** official performance evidence. It still checks all three
guests, both placement policies and same/cross-guest calibration.

If it stops, send the failing output and the printed run folder. Do not launch a
second campaign over one still running. If a physical calibration slope is not
positive, retain it: do not edit the fitted parameter to make the model work.

## 4. Full campaign

Use a persistent terminal if you already have one, or use the VM console and keep
it open. With tmux installed, `tmux new -s heat-part4` keeps a session alive after
an SSH disconnect; `tmux attach -t heat-part4` reconnects. This does not survive
a physical laptop/VM reboot: use checkpoint/resume after that.

```bash
bash scripts/run-part4.sh full "All laptops on AC; heavy applications closed; heat1/heat2/heat3 use Wi-Fi; allocation 4+2+2"
```

Launch this **once on one VM**. The default is 429 heat invocations plus 18
communication sweeps, 16 probes and network snapshots. Budget several hours,
possibly overnight on slow or relayed links. The smaller Part 3 campaign's
duration is not a promise for this much larger matrix. Keep all hosts awake.
Every heat invocation uses twenty steps/r=0.24, no full-field output and the
same compiler/transport policy. An invocation exceeding one hour stops with
partial output preserved rather than silently skipping it.

The script prints the run folder immediately and progress after every result.
On successful verification it packages the complete original study and session
logs and prints `Return bundle:`. The bundle includes private raw endpoints;
send it privately for review rather than force-adding it to public Git.

## 5. Disconnect, reboot or failure

First inspect whether an experiment remains active, using the VM console:

```bash
pgrep -af 'run_experiments.py|heat_mpi|heat_blocks|mpi_pingpong'
ls -dt part4/results/runs/*/
```

If it is still active, reconnect to its terminal rather than starting a duplicate.
After a reboot, start all three VMs and use the actual folder printed earlier:

```bash
bash scripts/run-part4.sh resume /home/mpi/heat-project-repo/part4/results/runs/ACTUAL_FOLDER "Same allocation/power/Wi-Fi; describe any interruption or changed conditions"
```

Resume skips completed measurements. Raw failed/partial attempts remain recorded.
It refuses changed code, binaries, MPI or CPU allocation; do not pull new code
halfway through a campaign. Only ignored `part4/results/runs/` folders can be
resumed. A verified complete folder does not repeat measurements; an interrupted
final manifest publication is rebuilt from the retained checkpoints and raw data.
Reviewed dated archives cannot be resumed/overwritten.

If model generation stopped because calibration was nonphysical, preserve the
first measurements and explicitly redo all calibration sweeps with wider coverage:

```bash
python3 part4/run_experiments.py --run --resume /home/mpi/heat-project-repo/part4/results/runs/ACTUAL_FOLDER --recalibrate --calibration-max-bytes 1048576 --calibration-iterations 5 --notes "Recalibration after nonphysical fit; same hardware and heat plan; describe current network conditions"
```

The original sweeps remain in raw history; metadata records this replacement.
This does not repeat completed heat tasks. If conditions changed materially,
report that limitation or collect a new controlled campaign instead of mixing
unlabelled configurations.

## 6. Offline verification and packaging

After a complete full campaign, no other VM is needed to check saved evidence:

```bash
python3 part4/verify_results.py --data /path/to/full/run
bash scripts/run-part4.sh package /path/to/full/run
```

The package command creates a new timestamped archive after verification, useful
if a laptop restarted after measurement but before the first archive finished.
It also supports smoke folders, which remain explicitly labelled as smoke.

To copy the printed archive to Windows Downloads using the already configured
heat-1 local SSH forward, run this in **Windows PowerShell**, replacing the path:

```powershell
scp -P 2222 "mpi@127.0.0.1:/home/mpi/heat-project-repo/part4/results/runs/ACTUAL_BUNDLE.tar.gz" "$env:USERPROFILE\Downloads"
```

No Windows Tailscale installation is needed for that localhost transfer. Keep
heat-1 running until it reaches 100%. Return the full bundle, including plots,
raw output, metadata and private originals, for review. Only the reviewed public
study files should later be committed; `.gitignore` excludes unreviewed runs,
private originals, return archives and scratch analysis.
