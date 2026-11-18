#!/usr/bin/env bash
# Reproduce the first launch/placement test. hostname itself is NOT an MPI
# application: this test verifies remote process launch, not MPI message exchange.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_root/part0/config/cluster.sh"
[[ $(id -un) == "$MPI_USER" ]] || { echo "Run as $MPI_USER" >&2; exit 2; }

# Six processes = two allowed slots on each of three VMs. Mapping by slot fills
# the first host's two slots, then the next, then the third. Output can reorder.
# oob_tcp is Open MPI 4's runtime control channel; btl_tcp is its TCP data path.
# Include tailscale0 so remote processes do not advertise unreachable NAT IPs.
exec mpirun --hostfile "$repo_root/part0/config/hosts" -np 6 --map-by slot \
    --mca plm_rsh_args "-o BatchMode=yes -o ConnectTimeout=15" \
    --mca oob_tcp_if_include tailscale0 \
    --mca btl_tcp_if_include tailscale0 \
    --mca btl tcp,self \
    hostname
