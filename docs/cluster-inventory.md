# Cluster inventory: distinguish known values from missing records

| Node | Ubuntu / MPI evidence | VM vCPU and RAM | Host CPU / access network |
| --- | --- | --- | --- |
| heat-1 | Earlier Ubuntu 24.04.5 screenshot; archived launch metadata Open MPI 4.1.6 | Screenshot: 2 vCPUs, 4096 MB; disk 30 GB | Record the host CPU and Wi-Fi/wired conditions used in the run |
| heat-2 | Ubuntu installation reported; independently save release and MPI version | Intended 2 vCPUs and at least 4 GB; verify and record | Pending |
| heat-3 | Ubuntu installation reported; independently save release and MPI version | Intended 2 vCPUs and at least 4 GB; verify and record | Pending |

All three participated as Linux hosts in successful runs. Metadata files saved on heat-1 record **heat-1's** version, even for a benchmark whose application ranks are entirely on the other two VMs. Those files do not independently certify every node's version or hardware.

Use `bash part0/01-connectivity/collect_inventory.sh` on each VM to capture guest information. Use Windows Task Manager/System information for the host CPU and RAM. Record the date, VM allocations, wired/Wi-Fi connection and any competing activity. Do not copy serial numbers, Windows product keys or unrelated personal hardware reports into the public repository.

Fill unknown cells only from actual records. Do not replace missing evidence with the default numbers in an example hostfile.
