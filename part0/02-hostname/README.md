# 2. Launching processes on three VMs

## The question

Can `mpirun` on one VM start programs on all three VMs with the requested process placement?

```bash
bash part0/02-hostname/run_hostname.sh
```

Run this on one coordinator after the connectivity step. It reads `part0/config/hosts`: three addresses, each allowing two slots. `-np 6` requests six processes. `--map-by slot` fills two slots on the first VM, then the next, then the third. A slot is an allowed process resource, not a newly created CPU.

Expected output, in any order:

```text
heat-1
heat-1
heat-2
heat-2
heat-3
heat-3
```

The historical screenshot showed exactly this distribution. An order change is normal: independent processes produce output at different times.

## Why the network options?

`--mca oob_tcp_if_include tailscale0` selects the Open MPI 4 runtime control interface. `--mca btl_tcp_if_include tailscale0` selects its TCP payload interface when that transport is used. `--mca btl tcp,self` chooses TCP plus same-process communication. These options keep MPI from advertising an unreachable VirtualBox NAT address. They target Open MPI 4.x; do not silently assume later major versions use identical runtime flags.

`--mca plm_rsh_args "-o BatchMode=yes -o ConnectTimeout=15"` makes the SSH launcher refuse password prompts and limits connection setup. It is not a timeout for a long benchmark.

`hostname` is an ordinary system utility: it does not call `MPI_Init`, `MPI_Send` or `MPI_Allreduce`. This test checks launching and placement, not the later application's MPI message protocol. The runtime may communicate internally; that is different from testing our own MPI code.

If it hangs, check unattended SSH in **both directions**, accepted host keys, awake VMs, interfaces and matching software. Earlier heat-2 trouble was resolved after diagnostic checks, but the available transcript did not isolate one certain root cause. Do not turn a plausible cause into an established historical fact.

Next: [MPI hello](../03-mpi-hello/README.md).
