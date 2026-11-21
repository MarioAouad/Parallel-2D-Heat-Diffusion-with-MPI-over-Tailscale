#!/usr/bin/env bash
# Reproduce the first launch/placement test. hostname itself is NOT an MPI
# application: this test verifies remote process launch, not MPI message exchange.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_root/part0/config/cluster.sh"
[[ $(id -un) == "$MPI_USER" ]] || { echo "Run as $MPI_USER" >&2; exit 2; }

# Six processes spread round-robin: two on each of the three VMs, including
# the later 4+2+2 allocation. Filling by slot could skip the third VM.
# oob_tcp is Open MPI 4's runtime control channel; btl_tcp is its TCP data path.
# Include tailscale0 so remote processes do not advertise unreachable NAT IPs.
exec mpirun --hostfile "$repo_root/part0/config/hosts" -np 6 --map-by node --rank-by node \
    --mca plm_rsh_args "-o BatchMode=yes -o ConnectTimeout=15" \
    --mca oob_tcp_if_include tailscale0 \
    --mca btl_tcp_if_include tailscale0 \
    --mca btl tcp,self \
    hostname
