# Cluster inventory

**Current, reviewed 24 November 2026:** the Part 4 inventories confirm heat1=4,
heat2=2,heat3=2 actual guest vCPUs and matching slots, about 4 GB RAM per VM,
Ubuntu 24.04.5 and Open MPI 4.1.6. See
[the immutable campaign metadata](../part4/results/2026-11-24-cluster/metadata.json).
The original 19 November records below describe the earlier 2+2+2 allocation.


These records describe configurations collected on **19 November 2026**.
They do not independently establish the exact settings during the archived
17 November ping-pong sweeps. Public node names are generic aliases.

## Ubuntu guests

| Node | Inventory UTC | Ubuntu | Open MPI | Tailscale | Guest CPUs | Guest-visible RAM |
| --- | --- | --- | --- | --- | --- | --- |
| heat-1 | 14:45:54 | 24.04.5 LTS | 4.1.6 | 1.104.7 | 2 | 3.8 GiB |
| heat-2 | 14:45:37 | 24.04.5 LTS | 4.1.6 | 1.104.7 | 2 | 3.8 GiB |
| heat-3 | 14:51:47 | 24.04.5 LTS | 4.1.6 | 1.104.7 | 2 | 3.8 GiB |

All three report x86_64, little-endian. Public inventory captures and hashes are in
[the setup archive](../part0/results/setup/2026-11-19/). These later captures
supply the timestamp missing from the first heat-2 text record. Earlier supplied
guest records agree on software versions and guest resources.

## Windows hosts and VirtualBox allocations

| Node | Host CPU | Host RAM | VM RAM / vCPUs | VM network | Physical connection at collection |
| --- | --- | --- | --- | --- | --- |
| heat-1 | Intel Core i9-14900HX; 24 cores / 32 logical processors | 31.63 GiB Windows-visible | 4096 MB / 2 | NAT | Intel Wi-Fi 6E AX211 160MHz; link 130 Mbps; IPv4 default route uses Wi-Fi |
| heat-2 | Intel Core i7-1255U | Not supplied | 4096 MB / 2 | NAT | Intel Wi-Fi 6 AX201 160MHz; link 390 Mbps; active physical adapter |
| heat-3 | Intel Core i7-1255U; 10 cores / 12 logical processors | Reported 16 GB installed, 15.7 GB usable | 4096 MB / 2 | NAT | Realtek RTL8852BE WiFi 6; link 144.4 Mbps; owner reports Wi-Fi default route |

Heat-1 was inspected read-only using Windows CIM, network routes and VirtualBox
at 14:36:31 UTC. Heat-2/3 values are user-supplied records; precise heat-2 host
collection time was not supplied. All VMs were reported running. The corrected
heat-2 VirtualBox query confirmed the RAM/vCPU/NAT values after an earlier query
used a placeholder VM name.

Guest-visible 3.8 GiB and configured 4096 MB describe different views of memory.
The VM's virtual Ethernet interface does not identify its host's physical link.
Wi-Fi link rates are adapter reports, not measured Internet or MPI bandwidth.
Heat-2's active adapter establishes Wi-Fi availability; no separate Windows
default-route capture was supplied for that host. Host RAM for heat-2 remains
unreported rather than inferred.

That original allocation supported six ranks. The later allocation supports eight
ranks (4+2+2), and the reviewed Part 3/4 studies include actual P=8 execution.

## Setup evidence and provenance

The [Part 0 closeout](part0-closeout.md) links the successful final recheck:
all six directed SSH logins, hostname placement and six-rank MPI hello pass.
The initial failed checks remain alongside later successes.

Full original captures, real addresses and hostnames stay in the private course
archive. Initial text attachments were read, but their Downloads paths were no
longer available for a later byte-for-byte backup; retain those originals
separately. Later exported captures are preserved with original/public hashes.

For new inventories, run
`bash part0/01-connectivity/collect_inventory.sh` on each VM and record Windows
host information separately. Add a dated capture rather than changing archived
records. Complete earlier AI history is a separate private submission item.
