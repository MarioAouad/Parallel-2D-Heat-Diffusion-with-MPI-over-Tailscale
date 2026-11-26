#!/bin/sh
# Installed as ./heat by make. Keep the same MPI process when selecting a solver.
set -eu

select_solver() {
    solver=heat
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --decomp)
                if [ "$#" -lt 2 ]; then
                    printf '%s\n' 'Error: --decomp requires serial, strips or blocks.' >&2
                    return 2
                fi
                case "$2" in
                    serial) solver=heat ;;
                    strips) solver=heat_mpi ;;
                    blocks) solver=heat_blocks ;;
                    *)
                        printf 'Error: unknown decomposition %s. Choose serial, strips or blocks.\n' "$2" >&2
                        return 2 ;;
                esac
                shift
                ;;
            --case|--N|--r|--T|--steps|--out)
                if [ "$#" -gt 1 ]; then
                    shift
                fi
                ;;
        esac
        shift
    done
    printf '%s\n' "$solver"
}

if [ "$#" -eq 1 ] && [ "$1" = '--help' ]; then
    cat <<'EOF'
Usage: ./heat [--decomp serial|strips|blocks] [--case 1|2|V] [--N N]
              [--r R] (--T T | --steps M) [--out FILE]
Serial is the default. Use mpirun -np P ./heat --decomp strips|blocks for MPI.
MPI layouts accept --debug-print for N <= 16. All layouts accept
--allow-unstable-demo for the isolated Case 1 fixed-step experiment.
EOF
    exit 0
fi

solver=$(select_solver "$@")
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$root/build/$solver" "$@"
