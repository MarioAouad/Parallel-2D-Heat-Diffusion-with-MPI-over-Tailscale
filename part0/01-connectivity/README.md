# 1. Connectivity and passwordless SSH

## Why this comes before MPI

Tailscale supplies reachability. SSH supplies remote process launch. MPI needs both in this setup. Passing one does not guarantee the other works.

Originally we entered these checks manually. `check_cluster.sh` is a newly organized helper for repeating the same kinds of checks. It has not been represented as the exact historical command transcript.

## The keys we configured

On each VM, once as `mpi`, we created an Ed25519 key pair with `ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519`. The private key stays on that VM; its `.pub` partner is the public key. `ssh-copy-id mpi@DESTINATION` installed the public key into the destination account's authorized keys after authentication.

Do not run key generation again if a key already exists: overwriting it can break current access. Do not commit either key file. Verify each destination's host fingerprint with its owner when accepting it for the first time. A host-key acceptance prompt can also block an unattended MPI launch.

There are **six directed inter-VM SSH relationships**:

| Source | Destinations |
| --- | --- |
| heat-1 | heat-2, heat-3 |
| heat-2 | heat-1, heat-3 |
| heat-3 | heat-1, heat-2 |

A successful heat-1 -> heat-2 login does not install heat-2's key on heat-1 or establish the reverse relationship.

The third VM initially used another Linux username. Trying `mpi@...` with that other account's password failed because SSH authenticates the named destination account. Creating `mpi` and using its own password/key authorization corrected this account mismatch.

## Read the helper before running it

From the repository root, as `mpi`, on **each VM**:

```bash
bash part0/01-connectivity/check_cluster.sh
```

It reads the team addresses from `part0/config/cluster.sh`, skips itself, then checks the other two VMs. `tailscale ping` reports direct/DERP observations. The separate SSH call uses `BatchMode=yes`, so success cannot rely on someone secretly entering a password; `StrictHostKeyChecking=yes` also refuses an unverified new host key. It prints each peer's hostname and username. A nonzero exit means an SSH check failed.

Tailscale can receive relay replies and still report that it failed to establish a direct route. Read that output separately from an SSH error. Do not disable host-key verification or replace IP addresses randomly to hide an authentication failure.

## Record configuration separately

```bash
bash part0/01-connectivity/collect_inventory.sh
```

This new read-only helper prints Ubuntu version, VM CPU/RAM, MPI version and own Tailscale address. It does not inventory the Windows host fully. Record that host's CPU model and access network in [the inventory document](../../docs/cluster-inventory.md). Copy verified values into the final report rather than assuming the launch VM's version proves all three versions.

Next: [launching hostname processes](../02-hostname/README.md).
