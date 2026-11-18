#!/usr/bin/env bash
# Annotated repository-layout adaptation of the launcher used for the archive.
# It keeps the same two-rank cases, transports, profiles and timing program.
# Paths now refer to this checkout/build and new results/runs, not the old flat
# /home/mpi/heat-project directory. It never overwrites the committed archive.
set -euo pipefail
# -e stops on unhandled errors, -u rejects unset variables, pipefail notices
# mpirun failing even if tee successfully writes the stream at the pipe's end.
repo_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
source "$repo_root/part0/config/cluster.sh"
case_name=${1:-}
profile=${2:-smoke}

# Each case runs EXACTLY TWO processes: two slots on one VM, or one slot on
# each endpoint. The third VM is not part of a two-VM payload exchange.
# vader is Open MPI 4 shared memory. tcp,self uses TCP between ranks and the
# self transport if a process communicates with itself. Local tests therefore
# measure shared-memory behavior, not a forced loopback TCP baseline.
case "$case_name" in
    heat1-local) hosts="$HEAT1_IP:2"; transport="self,vader" ;;
    heat2-local) hosts="$HEAT2_IP:2"; transport="self,vader" ;;
    heat3-local) hosts="$HEAT3_IP:2"; transport="self,vader" ;;
    heat1-heat2) hosts="$HEAT1_IP:1,$HEAT2_IP:1"; transport="tcp,self" ;;
    heat1-heat3) hosts="$HEAT1_IP:1,$HEAT3_IP:1"; transport="tcp,self" ;;
    heat2-heat3) hosts="$HEAT2_IP:1,$HEAT3_IP:1"; transport="tcp,self" ;;
    *)
        echo "Usage: bash run_pingpong.sh CASE [smoke|full]" >&2
        echo "Cases: heat1-local heat2-local heat3-local heat1-heat2 heat1-heat3 heat2-heat3" >&2
        exit 2 ;;
esac
# Smoke: 14 sizes through 64 KiB, five measured trips per size, one warm-up.
# Full: program defaults give 22 sizes through 16 MiB and adaptive repetitions.
# An empty Bash array adds NO command-line arguments, unlike a quoted string.
case "$profile" in
    smoke) benchmark_options=(--max-bytes 65536 --iterations 5 --warmup 1) ;;
    full) benchmark_options=() ;;
    *) echo "Profile must be smoke or full" >&2; exit 2 ;;
esac
[[ $(id -un) == "$MPI_USER" ]] || { echo "Run as $MPI_USER" >&2; exit 2; }
binary="$repo_root/build/mpi_pingpong"
[[ -x $binary ]] || { echo "Run make on every VM first." >&2; exit 2; }
directory="$repo_root/part0/results/runs/$profile"
mkdir -p "$directory"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
stem="$directory/${case_name}_${timestamp}"
# Prevent accidental replacement if the same case is launched in the same second.
[[ ! -e $stem.meta.txt ]] || { echo "Result name already exists; wait a second." >&2; exit 2; }

record_route() {
    printf 'case=%s\n' "$case_name"
    date -u +utc=%Y-%m-%dT%H:%M:%SZ
    local source_ip destination_ip
    case "$case_name" in
        *-local) echo "Same-VM case: MPI uses shared memory; no inter-VM route."; return 0 ;;
        heat1-heat2) source_ip=$HEAT1_IP; destination_ip=$HEAT2_IP ;;
        heat1-heat3) source_ip=$HEAT1_IP; destination_ip=$HEAT3_IP ;;
        heat2-heat3) source_ip=$HEAT2_IP; destination_ip=$HEAT3_IP ;;
    esac
    printf 'source=%s\ndestination=%s\n' "$source_ip" "$destination_ip"
    # Probe from the actual rank-zero VM. A heat-1 -> heat-3 ping cannot
    # characterize the heat-2 -> heat-3 path when heat-1 only coordinates.
    if [[ $(tailscale ip -4) == "$source_ip" ]]; then
        timeout -s INT -k 3s 45s tailscale ping --c 10 --timeout=3s "$destination_ip"
    else
        timeout -s INT -k 3s 60s ssh -o BatchMode=yes -o ConnectTimeout=15 \
            "$MPI_USER@$source_ip" \
            "timeout -s INT -k 3s 45s tailscale ping --c 10 --timeout=3s $destination_ip"
    fi
}

save_route() {
    local output=$1
    # Successful DERP replies can still end with a nonzero ping status if no
    # DIRECT path is established. Keep the evidence without rejecting MPI.
    # Inspect the file: an SSH error and a relay-only result are different.
    if record_route > "$output" 2>&1; then
        :
    else
        echo "Route probe returned nonzero; inspect $output for relay replies or errors." >&2
    fi
}

{
    printf 'case=%s\nprofile=%s\nutc=%s\nhosts=%s\ntransport=%s\n' \
        "$case_name" "$profile" "$timestamp" "$hosts" "$transport"
    echo "MPI version on launch VM:"
    mpirun --version
    echo "Tailscale status on launch VM (record pair-specific direct/DERP separately):"
    tailscale status
} > "$stem.meta.txt"
# Metadata includes version/placement context, but this is the launching VM's
# version only. Record versions independently on all three VMs as well.
echo "Running $case_name ($profile). Exactly two processes; keep selected VMs awake." >&2
echo "Recording the pair's route before the measurement..." >&2
save_route "$stem.route-before.txt"

# The coordinator may be absent from the two application endpoints. mpirun
# still launches/collects output there, while the payload travels endpoint to
# endpoint. ob1 selects the Open MPI point-to-point layer using the named BTLs.
# BatchMode disallows hidden password prompts. The control and TCP payload
# interfaces both use tailscale0, avoiding unreachable VirtualBox NAT addresses.
# stdout -> tee -> .csv.partial; stderr -> tee -> .log and the terminal.
# This does not put progress text into the CSV.
if mpirun --host "$hosts" -np 2 --map-by slot \
    --wdir "$repo_root" \
    --mca pml ob1 \
    --mca plm_rsh_args "-o BatchMode=yes -o ConnectTimeout=15" \
    --mca oob_tcp_if_include tailscale0 \
    --mca btl_tcp_if_include tailscale0 \
    --mca btl "$transport" \
    "$binary" --label "$case_name" "${benchmark_options[@]}" \
    2> >(tee "$stem.log" >&2) | tee "$stem.csv.partial"; then
    save_route "$stem.route-after.txt"
    # Only a normal mpirun completion promotes this file to a completed CSV.
    mv "$stem.csv.partial" "$stem.csv"
    echo "Saved $stem.csv" >&2
else
    save_route "$stem.route-after.txt"
    echo "Benchmark incomplete; retain $stem.log and $stem.csv.partial." >&2
    exit 1
fi
# Route probes lie OUTSIDE the C++ timer. Before/after do not continuously
# observe the route; describe transitions honestly when the two differ.
