"""Verify preserved setup evidence and assess the latest capture of each check."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'part0/results/setup'
HOSTS = {'HEAT1_TAILSCALE_IP': 'heat-1', 'HEAT2_TAILSCALE_IP': 'heat-2',
         'HEAT3_TAILSCALE_IP': 'heat-3'}


def load_snapshot(folder):
    manifest = json.loads((folder/'manifest.json').read_text())
    records = {}
    for item in manifest['files']:
        path = (folder/item['file']).resolve()
        if not path.is_relative_to(folder.resolve()) or path in records:
            raise ValueError('Invalid manifest path')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != item['published_sha256'] or len(raw) != item['published_bytes']:
            raise ValueError('Setup evidence hash mismatch: ' + item['file'])
        records[path] = raw.decode('utf-8')
    actual = {p.resolve() for p in folder.rglob('*.txt') if p.is_file()}
    if not records or set(records) != actual:
        raise ValueError('Manifest and archived text files differ')
    return records


def latest_captures(records):
    selected = {}
    for path, text in records.items():
        kind = path.name.split('-', 1)[0]
        stamp = re.search(r'-(\d{8}T\d{6}Z)\.txt$', path.name)
        if kind not in ('inventory', 'connectivity', 'hostname', 'hello') or not stamp:
            raise ValueError('Unknown capture filename: ' + path.name)
        captured = datetime.strptime(stamp.group(1), '%Y%m%dT%H%M%SZ')
        host = None
        if kind in ('inventory', 'connectivity'):
            pattern = r'^hostname=(\S+)' if kind == 'inventory' else r'^source_host=(\S+)'
            match = re.search(pattern, text, re.M)
            if not match or match.group(1) not in HOSTS.values():
                raise ValueError('Missing or unknown capture host')
            host = match.group(1)
        key = (kind, host)
        previous = selected.get(key)
        if previous and captured == previous[0] and text != previous[2]:
            raise ValueError('Conflicting copies of the same timestamped capture')
        if previous is None or captured > previous[0]:
            selected[key] = (captured, path, text)
    return {item[1]: item[2] for item in selected.values()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial-only', action='store_true',
                        help='Assess only the initial failed eight-file snapshot')
    args = parser.parse_args()
    initial = DATA/'2026-11-19'
    records = load_snapshot(initial)
    if len(records) != 8:
        raise ValueError('Expected eight initial setup files')
    if not args.initial_only:
        for folder in sorted(DATA.iterdir()):
            if folder != initial and (folder/'manifest.json').is_file():
                records.update(load_snapshot(folder))
    archived_count = len(records)
    records = latest_captures(records)
    if len(records) != 8:
        raise ValueError('Expected eight distinct current checks')
    print('Scope: ' + ('initial snapshot only' if args.initial_only else 'latest timestamped captures'))
    print(f'Verified {archived_count} archived text records; selected {len(records)} current checks')
    inventories = [text for path, text in records.items() if path.name.startswith('inventory-')]
    if len(inventories) != 3:
        raise ValueError('Need three inventories')
    seen = set()
    for text in inventories:
        host = re.search(r'^hostname=(.+)$', text, re.M).group(1)
        if host in seen or host not in HOSTS.values():
            raise ValueError('Duplicate or unexpected inventory host')
        seen.add(host)
        for expected in ['user=mpi', 'PRETTY_NAME="Ubuntu 24.04.5 LTS"', 'Open MPI) 4.1.6']:
            if expected not in text:
                raise ValueError('Inventory mismatch for ' + host)
        if not re.search(r'^CPU\(s\):\s+2$', text, re.M):
            raise ValueError('Unexpected vCPU count')
    print('PASS three timestamped inventories: same Ubuntu/MPI release and 2 vCPUs')
    directions = {}
    for path, text in records.items():
        if not path.name.startswith('connectivity-'):
            continue
        source = re.search(r'^source_host=(\S+)', text, re.M).group(1)
        for match in re.finditer(r'^Checking peer=(\S+)\n(.*?)(?=^Checking peer=|\Z)', text, re.M | re.S):
            peer, body = match.groups()
            if peer not in HOSTS or source == HOSTS[peer]:
                raise ValueError('Unexpected connectivity peer')
            key = (source, HOSTS[peer])
            if key in directions:
                raise ValueError('Duplicate SSH direction')
            directions[key] = ('Noninteractive SSH failed' not in body and
                               re.search(r'^'+re.escape(HOSTS[peer])+r'\nmpi\s*$', body.strip(), re.M) is not None)
    if len(directions) != 6:
        raise ValueError('Need six SSH directions')
    for (source, peer), passed in sorted(directions.items()):
        print(('PASS' if passed else 'FAIL') + f' SSH {source} -> {peer}')
    names = next(text.splitlines() for path, text in records.items() if path.name.startswith('hostname-'))
    hostname_ok = len(names) == 6 and all(names.count(host) == 2 for host in HOSTS.values())
    print(('PASS' if hostname_ok else 'FAIL') + ' six-process hostname placement')
    hello = next(text for path, text in records.items() if path.name.startswith('hello-'))
    matches = re.findall(r'rank=(\d+) size=(\d+) host=(\S+) rank_sum=(\d+)', hello)
    hello_ok = (len(matches) == 6 and {int(m[0]) for m in matches} == set(range(6)) and
                all(m[1] == '6' and m[3] == '15' for m in matches) and
                all(sum(m[2] == host for m in matches) == 2 for host in HOSTS.values()))
    print(('PASS' if hello_ok else 'FAIL') + ' six-rank MPI hello')
    ready = hostname_ok and hello_ok and all(directions.values())
    print('Archive integrity: PASS. Part 0 setup closeout: ' + ('READY' if ready else 'NOT READY'))
    return 0 if ready else 1


if __name__ == '__main__':
    sys.exit(main())
