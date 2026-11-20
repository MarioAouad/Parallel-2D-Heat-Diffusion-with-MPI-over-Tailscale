"""Check advertised MPI slots against the three guests before a cluster study.

Only generic aliases and counts are returned for portable metadata.
"""
import subprocess


def check_slots(hostfile):
    """Slots per VM from the rendered hostfile, checked against the VM's real vCPUs.

    Returns a list of dict(host=heatN, slots, vcpus). Hosts are recorded by alias only,
    never by address. Raises if any VM has more slots than vCPUs.
    """
    hosts, addresses = [], set()
    lines = [line.strip() for line in hostfile.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    if len(lines) != 3:
        raise SystemExit('The cluster hostfile must contain three distinct VMs.')
    for k, line in enumerate(lines):
        address, *options = line.split()
        rest = ' '.join(options)
        if address in addresses:
            raise SystemExit('Duplicate VM in cluster hostfile.')
        addresses.add(address)
        slots = int(rest.split('slots=')[1].split()[0]) if 'slots=' in rest else 1
        p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', address, 'nproc'],
                           capture_output=True, text=True, timeout=60)
        if p.returncode or not p.stdout.strip().isdigit():
            raise SystemExit(f'Cannot read the vCPU count of heat{k+1} over SSH: {p.stderr.strip()}')
        vcpus = int(p.stdout.strip())
        if not 0 < slots <= vcpus:
            raise SystemExit(f'heat{k+1} has slots={slots} but only {vcpus} vCPUs (nproc). Allocate the vCPUs '
                             f'in VirtualBox first, or lower HEAT{k+1}_SLOTS in cluster.local.sh.')
        hosts.append(dict(host=f'heat{k+1}', slots=slots, vcpus=vcpus))
    return hosts
