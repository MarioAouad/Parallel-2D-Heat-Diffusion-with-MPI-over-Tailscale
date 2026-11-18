#!/usr/bin/env bash
# New reproducible helper for the checks previously entered manually.
# Run from EACH VM, as mpi. This is not a timing benchmark.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_root/part0/config/cluster.sh"
[[ $(id -un) == "$MPI_USER" ]] || { echo "Run as $MPI_USER" >&2; exit 2; }
local_ip=$(tailscale ip -4)
printf 'source_host=%s source_ip=%s\n' "$(hostname)" "$local_ip"

failed=0
for peer in "$HEAT1_IP" "$HEAT2_IP" "$HEAT3_IP"; do
    # A local SSH login would not prove that a different VM is reachable.
    [[ $peer == "$local_ip" ]] && continue
    printf '\nChecking peer=%s\n' "$peer"
    # Tailscale may return nonzero after successful relay replies because a
    # DIRECT path was not established. Preserve output; test SSH separately.
    if ! timeout -s INT -k 3s 35s tailscale ping --c 3 --timeout=5s "$peer"; then
        echo "Read the ping output: relay replies differ from no replies."
    fi
    # BatchMode disallows password prompts; StrictHostKeyChecking refuses an
    # unknown key. Verify host fingerprints manually before this automated test.
    # The outer timeout bounds the entire SSH command, not just connecting.
    if ! timeout 25s ssh -o BatchMode=yes -o StrictHostKeyChecking=yes \
        -o ConnectTimeout=15 "$MPI_USER@$peer" 'hostname; whoami'; then
        failed=1
        echo "Noninteractive SSH failed for $peer" >&2
    fi
done
exit "$failed"
