# Load trusted LOCAL configuration, excluded from this public repository.
# Copy cluster.local.sh.example to cluster.local.sh and enter the three real
# Tailscale IPv4 addresses there. Never put passwords or keys in either file.
config_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ ! -f "$config_directory/cluster.local.sh" ]]; then
    echo "Configure part0/config/cluster.local.sh first; see part0/config/README.md." >&2
    return 2
fi
source "$config_directory/cluster.local.sh"
MPI_USER="mpi"

# Validate values before passing them to SSH, MPI, or a remote shell command.
# Accept dotted decimal addresses, not shell metacharacters or placeholders.
for name in HEAT1_IP HEAT2_IP HEAT3_IP; do
    value=${!name:-}
    if [[ ! $value =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
        echo "Set $name to its real Tailscale IPv4 address in cluster.local.sh." >&2
        return 2
    fi
    IFS=. read -r -a octets <<< "$value"
    for octet in "${octets[@]}"; do
        if (( 10#$octet > 255 )); then
            echo "Invalid IPv4 octet in $name" >&2
            return 2
        fi
    done
done

# Slots per VM: optional HEATn_SLOTS in cluster.local.sh, default 2. A slot only
# PERMITS a process; it must not exceed the vCPUs really allocated to that VM
# Part 2/3/4 runners verify all counts using check_slots.py: local nproc for the
# launching guest, verified SSH for the others.
for name in HEAT1_SLOTS HEAT2_SLOTS HEAT3_SLOTS; do
    value=${!name:-2}
    if [[ ! $value =~ ^[1-9][0-9]?$ ]]; then
        echo "$name must be a whole number from 1 to 99 (got '$value')." >&2
        return 2
    fi
    printf -v "$name" '%s' "$value"
done

# Render the ignored hostfile from the same configuration. The hostname/hello
# tests and pair benchmark therefore use the same endpoints without duplication.
printf '%s slots=%s\n%s slots=%s\n%s slots=%s\n' \
    "$HEAT1_IP" "$HEAT1_SLOTS" "$HEAT2_IP" "$HEAT2_SLOTS" "$HEAT3_IP" "$HEAT3_SLOTS" \
    > "$config_directory/hosts"
