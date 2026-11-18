#!/usr/bin/env bash
# Run after "make" on every VM, with this checkout at the SAME absolute path.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_root/part0/config/cluster.sh"
[[ $(id -un) == "$MPI_USER" ]] || { echo "Run as $MPI_USER" >&2; exit 2; }
binary="$repo_root/build/mpi_hello"
[[ -x $binary ]] || { echo "Run make on every VM first." >&2; exit 2; }

# All six processes execute mpi_hello; the program's Allreduce exchanges data.
# This script chooses the processes/hosts. The C++ program chooses rank behavior.
exec mpirun --hostfile "$repo_root/part0/config/hosts" -np 6 --map-by slot \
    --wdir "$repo_root" \
    --mca pml ob1 \
    --mca plm_rsh_args "-o BatchMode=yes -o ConnectTimeout=15" \
    --mca oob_tcp_if_include tailscale0 \
    --mca btl_tcp_if_include tailscale0 \
    --mca btl tcp,self \
    "$binary"
