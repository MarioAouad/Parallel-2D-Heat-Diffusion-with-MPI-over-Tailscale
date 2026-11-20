#!/usr/bin/env bash
set -euo pipefail
cd /home/mpi/heat-project-repo
source part0/config/cluster.sh
local_ip=$(tailscale ip -4)
expected=$(git rev-parse HEAD)
bundle="$PWD/output/parts23-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$bundle"
echo "Bundle: $bundle"
git rev-parse HEAD > "$bundle/revision.txt"
git status --short > "$bundle/git-status.txt"
cp part0/config/hosts "$bundle/hosts.txt"
for item in "heat1:$HEAT1_IP" "heat2:$HEAT2_IP" "heat3:$HEAT3_IP"; do
    label=${item%%:*}
    peer=${item#*:}
    if [[ "$peer" == "$local_ip" ]]; then
        bash part0/01-connectivity/collect_inventory.sh > "$bundle/$label-inventory.txt" 2>&1
        bash part0/01-connectivity/check_cluster.sh 2>&1 | tee "$bundle/$label-connectivity.txt"
        sha256sum build/heat build/heat_mpi build/heat_blocks > "$bundle/$label-binaries.txt"
    else
        ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
            "$MPI_USER@$peer" "cd /home/mpi/heat-project-repo && test \"\$(git rev-parse HEAD)\" = '$expected' && bash part0/01-connectivity/collect_inventory.sh" \
            > "$bundle/$label-inventory.txt" 2>&1
        ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
            "$MPI_USER@$peer" 'cd /home/mpi/heat-project-repo && bash part0/01-connectivity/check_cluster.sh' \
            2>&1 | tee "$bundle/$label-connectivity.txt"
        ssh -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15 \
            "$MPI_USER@$peer" 'cd /home/mpi/heat-project-repo && sha256sum build/heat build/heat_mpi build/heat_blocks' \
            > "$bundle/$label-binaries.txt"
    fi
done
python3 - <<'PY' 2>&1 | tee "$bundle/checked-slots.txt"
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('slots', 'part0/config/check_slots.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
hosts = module.check_slots(Path('part0/config/hosts'))
print(hosts)
if sum(h['slots'] for h in hosts) < 8:
    raise SystemExit('STOP: P=8 requires eight checked real guest CPU slots.')
PY
make check-strips 2>&1 | tee "$bundle/check-strips.txt"
make check-blocks 2>&1 | tee "$bundle/check-blocks.txt"
python3 part2/run_experiments.py --cluster --out "$bundle/part2" \
    2>&1 | tee "$bundle/part2-run.txt"
python3 part2/verify_results.py --data "$bundle/part2" --require-fields \
    2>&1 | tee "$bundle/part2-verify.txt"
python3 part3/run_experiments.py --cluster --np 1,2,3,4,6,8 --timing-np 4,8 \
    --out "$bundle/part3" 2>&1 | tee "$bundle/part3-run.txt"
python3 part3/verify_results.py --data "$bundle/part3" --require-fields --require-p8 \
    2>&1 | tee "$bundle/part3-verify.txt"
tar -czf "$bundle.tar.gz" -C "$(dirname "$bundle")" "$(basename "$bundle")"
echo "Return bundle: $bundle.tar.gz"
