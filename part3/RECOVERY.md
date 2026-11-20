# Part 3 evidence recovery and open requirements

The block solver has no known numerical or halo-exchange defect from the audit.
Its C++ source and the original dated measurements remain unchanged. The fixes
concern evidence retention, verification, report wording and reproducible runs.

## Original archive

The 19 November study records 90 serial/block byte matches and 36 timing runs
across two/three VMs. Its original binary fields were omitted. The old runner also
deleted comparison block files immediately after comparing them, so even a full
transfer folder may contain only serial references and the four figure fields.
Do not regenerate data and put it in the old archive as though it were original.

The updated verifier checks the manifest and unchanged solver sources, full
case/N/P coverage, raw/CSV numerical agreement, V error norms, debug splits,
neighbours and every printed non-corner halo value. It also checks each timing
repetition and recomputes every median/min/max. Only the specifically documented
Open MPI `setpgid` warning is accepted; unexpected stderr fails.

Legacy verification explicitly reports missing fields and missing P=8 measurements.
It does not claim to repeat byte comparisons from unavailable files.

## New complete field evidence

Synchronize this updated checkout onto all three VMs and build on **each** VM:

```bash
cd ~/heat-project-repo
make serial strips blocks
```

On **one** launching VM, with the existing private cluster configuration:

```bash
cd ~/heat-project-repo
make check-blocks
python3 part3/run_experiments.py --cluster
# Replace <timestamp> with the folder printed by the runner:
python3 part3/verify_results.py --data part3/results/runs/<timestamp> --require-fields
```

With six checked slots, the default study retains 112 original binary files
(18 comparison references, 90 block results and four figure fields), covering 92
field pairs. With eight checked slots it adds P=8: 130 fields and 110 pairs.
Comparison filenames and hashes are stored in `compare.csv`; metadata uses schema 2. Every field
has a byte count and SHA-256 hash in the manifest. Strict verification reads and
compares the original bytes and checks boundaries, extrema and V norms. Missing,
changed or inconsistent files fail. Launcher executable hashes are captured;
they do not independently attest the binary installed on every remote VM. Each VM
must build the same synchronized source with the documented compiler flags.

Review the figures, then copy the **whole** folder, including `fields/`, to a new
`part3/results/<new-date-or-label>-cluster/` directory. The ignore policy permits
fields in reviewed cluster archives while keeping temporary run folders ignored.
Do not overwrite `2026-11-19-cluster` or change its manifest.

## Required eight-process timing check

P=6 is useful additional evidence, but is not an automatic replacement for the
assignment's P=8 check. Either measure P=8 or obtain the instructor's acceptance
of the resource-limited substitution. Full checkpoint C3 also needs Part 4.

To measure P=8, first allocate at least eight **real guest vCPUs** across the VMs.
Record each guest's actual allocation (`nproc`, plus the hypervisor settings) and
make the private hostfile's slots match them. Increasing only hostfile numbers is
not sufficient. For example, **after** actual allocations of 4, 2 and 2 vCPUs, a
private hostfile could contain the real Tailscale endpoints with those slot counts.
The example does not change any VM allocation.

Use the pulled configuration mechanism: set `HEAT1_SLOTS`, `HEAT2_SLOTS` and
`HEAT3_SLOTS` in the ignored `part0/config/cluster.local.sh`, matching the actual
guest allocations. For example, **after** allocating 4,2,2 actual vCPUs:

```bash
# Add these to the existing private cluster.local.sh (keep its real endpoints):
HEAT1_SLOTS=4
HEAT2_SLOTS=2
HEAT3_SLOTS=2
```

The runner sources `cluster.sh` to render `part0/config/hosts`, checks each guest's
`nproc` over SSH, records alias/slots/vCPUs in metadata, and launches with
`--nooversubscribe`. There is no separate runner `--hostfile` option. Refresh the
inventory after changing the VM allocation. With eight verified slots, on one VM:

```bash
cd ~/heat-project-repo
python3 part3/run_experiments.py --cluster --np 1,2,3,4,6,8 --timing-np 4,8
python3 part3/verify_results.py --data part3/results/runs/<timestamp> --require-fields --require-p8
```

`--require-p8` requires both layouts at P=4 and P=8 for N=512,2048,8192, with at
least three unique repetitions on the cluster. It fails on the existing P=4,6
archive. These commands prepare the missing experiment; no P=8 measurements have
been performed or fabricated during the fixes.

New timing runs alternate which layout goes first across repetitions. This reduces
one ordering bias; it does not prove identical network conditions or establish
why a layout wins. More controlled measurements belong to Part 4.

## Local verification tests

```bash
make test-part3-evidence
```

These tests use the actual serial solver and mocked MPI records in temporary
fixtures. They exercise capture, byte comparisons, corruption detection, timing
recomputation and P=8 coverage enforcement. Synthetic records are not VM-run or
performance evidence. Complete earlier AI logs remain a separate private course
submission item; see [the logging guide](../llm_log/README.md).
