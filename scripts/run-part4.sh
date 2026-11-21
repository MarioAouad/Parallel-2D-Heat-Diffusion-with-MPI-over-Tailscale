#!/usr/bin/env bash
# Run once on one Ubuntu VM. Every other VM must already have this committed revision built.
set -euo pipefail
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd "$repo_root"
mode=${1:-}
stamp=$(date -u +%Y%m%dT%H%M%S%NZ)
case "$mode" in
    full|smoke)
        notes=${2:-}
        [[ -n "$notes" ]] || { echo 'Supply actual power/load/Wi-Fi conditions as the second argument.' >&2; exit 2; }
        out="$repo_root/part4/results/runs/$stamp"
        mkdir -p "$(dirname "$out")"
        python3 -u part4/run_experiments.py --run --profile "$mode" --out "$out" --notes "$notes" \
            2>&1 | tee "$out-session-$stamp.log"
        ;;
    resume)
        out=${2:-}
        notes=${3:-}
        [[ -d "$out" && -n "$notes" ]] || { echo 'Usage: run-part4.sh resume /absolute/run/folder "current conditions"' >&2; exit 2; }
        out=$(cd "$out" && pwd)
        python3 -u part4/run_experiments.py --run --resume "$out" --notes "$notes" \
            2>&1 | tee "$out-session-$stamp.log"
        ;;
    package)
        out=${2:-}
        [[ -d "$out" ]] || { echo 'Supply a completed run folder.' >&2; exit 2; }
        out=$(cd "$out" && pwd)
        ;;
    *)
        echo 'Usage: run-part4.sh full|smoke "conditions" | resume /run/folder "conditions" | package /run/folder' >&2
        exit 2
        ;;
esac
profile=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["parameters"]["profile"])' "$out/metadata.json")
verify_args=()
[[ "$profile" == full ]] || verify_args+=(--allow-smoke)
python3 part4/verify_results.py --data "$out" "${verify_args[@]}"
items=("$(basename "$out")")
for logfile in "$out"-session-*.log; do
    [[ ! -f "$logfile" ]] || items+=("$(basename "$logfile")")
done
archive="$out-bundle-$stamp.tar.gz"
tar -czf "$archive" -C "$(dirname "$out")" "${items[@]}"
echo "Return bundle (contains private raw records; share privately): $archive"
