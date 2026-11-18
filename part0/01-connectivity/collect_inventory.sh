#!/usr/bin/env bash
# New read-only inventory helper. Run on EACH Ubuntu VM and save its output.
# It records the guest's view, not a complete Windows host hardware inventory.
set -euo pipefail
printf 'utc=%s\nhostname=%s\nuser=%s\n' "$(date -u +%FT%TZ)" "$(hostname)" "$(id -un)"
cat /etc/os-release
printf '\n--- VM CPU ---\n'
lscpu
printf '\n--- VM RAM ---\n'
free -h
printf '\n--- MPI ---\n'
mpirun --version
printf '\n--- Tailscale version and own address ---\n'
tailscale version
tailscale ip -4
