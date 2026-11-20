#!/usr/bin/env bash
set -euo pipefail
cd /home/mpi/heat-project-repo
if [[ -n $(git status --porcelain) ]]; then
    echo 'Local changes exist. Preserve/reconcile them before pulling.' >&2
    exit 1
fi
git pull --ff-only origin main
source part0/config/cluster.sh
local_ip=$(tailscale ip -4)
expected=$(git rev-parse HEAD)
mkdir -p output
update_log="output/update-all-$(date -u +%Y%m%dT%H%M%SZ).log"
{
    echo "Expected revision: $expected"
    make serial strips blocks
    echo 'Local guest CPU count:'
    nproc
    for peer in "$HEAT1_IP" "$HEAT2_IP" "$HEAT3_IP"; do
        [[ "$peer" == "$local_ip" ]] && continue
        echo "Updating peer $peer"
        ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
            "$MPI_USER@$peer" bash -s -- "$expected" <<'REMOTE'
set -euo pipefail
cd /home/mpi/heat-project-repo
if [[ -n $(git status --porcelain) ]]; then
    echo 'Remote local changes exist. Preserve/reconcile them before pulling.' >&2
    exit 1
fi
git pull --ff-only origin main
test "$(git rev-parse HEAD)" = "$1"
make serial strips blocks
echo "Revision: $(git rev-parse HEAD)"
echo 'Guest CPU count:'
nproc
REMOTE
    done
    echo 'All three VMs updated and built successfully.'
} 2>&1 | tee "$update_log"
echo "Update log: $update_log"
