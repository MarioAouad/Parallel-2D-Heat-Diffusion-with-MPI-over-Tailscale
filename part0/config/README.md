# Private team configuration and public examples

The public repository uses generic node labels heat-1, heat-2, heat-3. Actual hostnames and network addresses are retained in the team's private originals. Configure only when ready to run the organized checkout; reading results needs no configuration.

On each VM, from the repository root:

```bash
cp part0/config/cluster.local.sh.example part0/config/cluster.local.sh
nano part0/config/cluster.local.sh
```

Replace the three quoted placeholders with the real Tailscale IPv4 addresses, obtained with `tailscale ip -4` in each VM. Use the same VM order on every checkout. Save the actual configuration locally; `.gitignore` excludes it. No passwords or authentication keys belong in this file.

The launchers source `cluster.sh`, which validates local values and renders the ignored `hosts` file with two slots per VM, or `HEAT1_SLOTS`/`HEAT2_SLOTS`/`HEAT3_SLOTS` from `cluster.local.sh` when set (whole numbers; anything else is refused). `hosts.example` shows the required syntax with placeholders. You do not type the addresses twice. Missing or placeholder configuration produces an explanation instead of launching MPI with invalid endpoints.

Hostname/hello launch six ranks round-robin on the rendered hostfile, including
the later eight-slot allocation. Ping-pong chooses exactly two slots from the same
configuration: two on one VM or one on each pair endpoint. Changing slot numbers
does not allocate extra vCPUs: raise a VM's vCPUs in VirtualBox first, then its
slots. The Part 2/3/4 runners check every guest's slots against `nproc` with the
shared checker; it reads the launching guest locally and uses verified SSH only
for the other guests.

## Current Part 3/4 allocation: 4+2+2

After allocating heat-1 four actual guest vCPUs, the launching checkout's existing
private `cluster.local.sh` should contain these entries in addition to its real IPs:

```bash
HEAT1_SLOTS=4
HEAT2_SLOTS=2
HEAT3_SLOTS=2
```

Do not maintain `hosts` separately: sourcing `cluster.sh` regenerates it from this
configuration, and the experiment runners do that automatically. Both private
files are ignored, so pulling Git updates does not synchronize their contents
between VMs. Set the same allocation on any checkout you intend to launch from.
Never overwrite an existing private configuration by copying the example again.

To regenerate and check from heat-1 (all guests running):

```bash
cd /home/mpi/heat-project-repo
hostname
nproc
source part0/config/cluster.sh
awk 'NF { print "hostfile entry " ++n ": " $2 }' part0/config/hosts
python3 -c "from pathlib import Path; from part0.config.check_slots import check_slots; print(check_slots(Path('part0/config/hosts')))"
```

Expect heat-1's `nproc` to print 4; hostfile entries 1/2/3 should show
`slots=4`, `slots=2`, `slots=2`. The Python check must confirm matching guest
counts of 4,2,2. These are configuration checks, not new simulations. The verified
21 November Part 3 archive already records this allocation and P=8 on three VMs.

Keep local configuration and original private route/metadata files out of the public repository. Preserve archived public measurements; separately record every new run and its private configuration.
