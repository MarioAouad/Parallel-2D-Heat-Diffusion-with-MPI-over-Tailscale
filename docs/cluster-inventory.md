# Cluster inventory: distinguish known values from missing records

| Node | Ubuntu / MPI evidence | VM vCPU and RAM | Host CPU / access network |
| --- | --- | --- | --- |
| heat-1 | Earlier Ubuntu 24.04.5 screenshot; archived launch metadata Open MPI 4.1.6 | Screenshot: 2 vCPUs, 4096 MB; disk 30 GB | Record the host CPU and Wi-Fi/wired conditions used in the run |
| heat-2 | Ubuntu installation reported; independently save release and MPI version | Intended 2 vCPUs and at least 4 GB; verify and record | Pending |
| heat-3 | Ubuntu installation reported; independently save release and MPI version | Intended 2 vCPUs and at least 4 GB; verify and record | Pending |

All three participated as Linux hosts in successful runs. Metadata files saved on heat-1 record **heat-1's** version, even for a benchmark whose application ranks are entirely on the other two VMs. Those files do not independently certify every node's version or hardware.

Use `bash part0/01-connectivity/collect_inventory.sh` on each VM to capture guest information. Use Windows Task Manager/System information for the host CPU and RAM. Record the date, VM allocations, wired/Wi-Fi connection and any competing activity. Do not copy serial numbers, Windows product keys or unrelated personal hardware reports into the public repository.

Fill unknown cells only from actual records. Do not replace missing evidence with the default numbers in an example hostfile.

## Inventory records supplied on 19 November 2026

This dated update supplements the earlier status above. These are user-supplied
terminal records, not a new remote inspection by the assistant, and they do not
retroactively certify the configuration used for the 17 November benchmarks.

| Node | Record timestamp (UTC) | Ubuntu | Open MPI | Architecture / byte order | Guest CPUs | Guest-visible RAM | CPU model reported inside VM | Tailscale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| heat-1 | 2026-11-19 14:14:31 | 24.04.5 LTS | 4.1.6 | x86_64 / little-endian | 2 | 3.8 GiB | Intel Core i9-14900HX | 1.104.7 |
| heat-2 | Not included in supplied file | 24.04.5 LTS | 4.1.6 | x86_64 / little-endian | 2 | 3.8 GiB | Intel Core i7-1255U | 1.104.7 |
| heat-3 (third supplied VM record) | 2026-11-19 14:14:00 | 24.04.5 LTS | 4.1.6 | x86_64 / little-endian | 2 | 3.8 GiB | Intel Core i7-1255U | 1.104.7 |

All three supplied records agree on the Ubuntu, Open MPI and Tailscale versions.
The third supplied record is mapped to the existing heat-3 alias; the real VM
hostname need not be changed. Source filenames, hostnames and overlay addresses
are recorded in the ignored private follow-up record under
`llm_log/private/2026-11-19-inventory/`. The heat-1 record was supplied in the chat;
the other two were attached text files. Both attachments were read successfully,
but their Downloads paths were no longer accessible when a backup was attempted.
The private follow-up record is not a byte-for-byte backup of those attachments;
retain the original files separately for the course hand-in.

Still record or confirm:

- Exact configured RAM in the hypervisor for each VM. The reported 3.8 GiB is
  guest-visible memory and is consistent with a roughly 4 GB allocation; it is
  not a direct record of the configured allocation.
- CPU model on each Windows host (the table above reports the VM's view), and
  Wi-Fi or Ethernet on the Windows host. The VM's virtual Ethernet interface
  does not establish which physical connection the host uses.
- A timestamped heat-2 capture, all six directed noninteractive SSH checks, and
  hostname/hello output from the organized checkout.
- Earlier full AI conversation exports; these inventory files do not close
  the missing-history item.

The current two-vCPU records support two slots per VM, six slots total. They do
not support an eight-rank run without a real allocation change.

## Windows host and VirtualBox follow-up, 19 November 2026

The heat-1 host was inspected directly at 14:36:31 UTC (16:36:31 Asia/Beirut).
The other two host records below were supplied by the user. These records
supplement the guest captures above; they describe current configurations, not
independent evidence of the exact settings during the archived benchmarks.

| Node | Windows host CPU | Host RAM | Configured VM RAM / vCPUs | Physical connection | Provenance / remaining evidence |
| --- | --- | --- | --- | --- | --- |
| heat-1 | Intel Core i9-14900HX; 24 cores / 32 logical processors | 31.63 GiB Windows-visible physical memory | 4096 MB / 2; VM running; NAT | Intel Wi-Fi 6E AX211 160MHz; reported link 130 Mbps; only IPv4 default route uses Wi-Fi | Direct read-only Windows CIM, network-route and VirtualBox inspection; raw capture retained privately |
| heat-2 | Intel Core i7-1255U | Not supplied | 4096 MB / 2; VM running; NAT | Intel Wi-Fi 6 AX201 160MHz; reported link 390 Mbps; active physical adapter | User supplied the successful corrected VirtualBox output on 19 November 2026; collection time not included |
| heat-3 | Intel Core i7-1255U; 10 cores / 12 logical processors | User reports 16 GB installed, 15.7 GB usable | 4096 MB / 2; VM running; NAT | Realtek RTL8852BE WiFi 6; reported link 144.4 Mbps; user reports Wi-Fi default route | User-supplied host record dated 19 November 2026; VM name differs from the generic public node alias |

The heat-2 VM is registered as `heat-2`. Its owner ran the corrected command
below successfully; the user supplied `memory=4096`, `cpus=2`,
`VMState="running"`, and `nic1="nat"`. This closes the configured-RAM gap left
by the earlier placeholder-name query. Retain the original terminal output.

```powershell
$vbox = "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"
& $vbox showvminfo "heat-2" --machinereadable |
    Select-String '^(memory|cpus|VMState|nic1)='
```

The VirtualBox host-only adapter and the Tailscale tunnel are virtual adapters;
their displayed link speeds do not establish the physical Internet connection.
Wi-Fi link rates are current adapter reports, not measured Internet or MPI
bandwidth. The heat-1 physical connection is confirmed by the Windows IPv4
default route. For heat-2, a default-route capture would additionally confirm
routing; its supplied adapter listing shows Wi-Fi as the active physical link.

The earlier pending-list items for host CPU and connection type are now updated
by this table. All three VMs have confirmed configured RAM of 4096 MB and two
vCPUs in the supplied or directly inspected VirtualBox records. The earlier
requirements for SSH/hostname/hello evidence and complete private AI history
remain separate. No VM settings or network configuration were changed.

## Exported setup archive reviewed on 19 November 2026

The eight-file export provides timestamped guest captures at 14:45:54 UTC
(heat-1), 14:45:37 UTC (heat-2), and 14:51:47 UTC (heat-3). This supplies the
previously missing heat-2 timestamp. All three confirm the matching versions
and guest resource values above. Public copies and a source/public hash manifest
are in `part0/results/setup/2026-11-19/`; exact originals are retained privately.

The new captures prove four successful directed SSH logins. The two from heat-2
fail on unknown host keys. The six-process hostname output is correct, but MPI
hello fails because the third VM cannot use `/home/mpi/heat-project-repo` at the
time of the run. See [the repair checklist](part0-closeout.md). These items are
not complete until new successful captures are collected.

## Successful final recheck, 19 November 2026

The final recheck archive is preserved privately, with four public text copies
and a source/public hash manifest under `part0/results/setup/2026-11-19-recheck/`.
It includes the old failures and these later successful captures:

- Heat-2 connectivity at 15:30:12 UTC: both peers return the correct hostname
  and `mpi`, with no host-key/SSH failure. Direct endpoints are observed in
  these two probes; this does not establish continuous direct routing.
- MPI hello at 15:34:24 UTC: all ranks 0-5 report size=6 and rank_sum=15;
  ranks 0/1 run on heat-1, 2/3 on heat-2, and 4/5 on heat-3.

Together with the four earlier successful SSH directions, original hostname
placement, inventories and network study, this completes the Part 0 technical
checklist. No failed records or measured benchmark values were overwritten.
