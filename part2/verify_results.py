"""Verify an archived Part 2 (C2) study without rerunning MPI.

Checks: manifest hashes, source provenance (both solvers unchanged since the run),
every comparison PASS and byte-identical, P = 1..4 covered, uneven strips present,
several N, raw runs successful and consistent with the CSV, and, for a cluster
study, every P >= 2 run spread over at least two machines.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def default_study():
    base = HERE/'results'
    studies = sorted(p for p in base.iterdir() if p.is_dir() and p.name != 'runs'
                     and (p/'manifest.json').is_file()) if base.is_dir() else []
    if not studies:
        raise SystemExit('No archived Part 2 study yet: run part2/run_experiments.py --cluster, review it, '
                         'then copy the run folder to part2/results/<date>-cluster/.')
    return studies[-1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, help='study folder (default: newest under part2/results/)')
    parser.add_argument('--allow-local', action='store_true', help='accept a one-VM study (not C2 evidence)')
    args = parser.parse_args()
    folder = (args.data or default_study()).resolve()

    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    for item in manifest['published_files']:
        data = (folder/item['file']).read_bytes()
        require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                'Result hash/size mismatch: '+item['file'])
    names = {item['file'] for item in manifest['published_files']}
    require({'compare.csv', 'raw_runs.json', 'metadata.json', 'debug_halo.txt'} <= names,
            'Manifest is missing required evidence files')

    meta = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    root = HERE.parent
    require(meta['strips_source_sha256'] == hashlib.sha256((HERE/'heat_mpi.cpp').read_bytes()).hexdigest(),
            'heat_mpi.cpp changed since this study; rerun it')
    require(meta['serial_source_sha256'] ==
            hashlib.sha256((root/'part1/heat_serial.cpp').read_bytes()).hexdigest(),
            'Serial reference changed since this study')
    cluster = meta['mode'] == 'cluster'
    require(cluster or args.allow_local, 'Study is local (one VM); C2 needs --cluster evidence')

    with (folder/'compare.csv').open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    require(rows and all(r['result'] == 'PASS' and r['identical'] == 'True' and not r['summary_mismatch']
                         for r in rows), 'Not every comparison is bit-for-bit identical')
    require({1, 2, 3, 4} <= {int(r['P']) for r in rows}, 'P = 1, 2, 3 and 4 must all be covered')
    require(len({int(r['N']) for r in rows}) >= 3, 'Several N are required')
    for P in (2, 3, 4):
        require(any(int(r['P']) == P and r['uneven_strips'] == 'True' for r in rows),
                f'No uneven-strip case (N-1 not divisible by P) for P={P}')
    if cluster:
        require(all(int(r['nodes']) >= 2 for r in rows if int(r['P']) >= 2),
                'A P>=2 cluster run used only one machine')

    runs = json.loads((folder/'raw_runs.json').read_text(encoding='utf-8'))
    require(all(r['returncode'] == 0 for r in runs), 'A recorded solver run failed')
    strips = [dict(t.split('=', 1) for t in r['stdout'].splitlines()[-1].split())
              for r in runs if 'heat_mpi' in r['command'] and '--debug-print' not in r['command']]
    by_key = {(s['case'], int(s['N']), int(s['P'])): s for s in strips}
    for r in rows:
        s = by_key.get((r['case'], int(r['N']), int(r['P'])))
        require(s is not None and s['decomp'] == 'strips' and int(s['nodes']) == int(r['nodes']),
                'CSV row without matching raw strips run: '+str(r))
    text = (folder/'debug_halo.txt').read_text(encoding='utf-8')
    require(text.count('rank ') >= 5, 'Halo debug transcripts for P=2 and P=3 are missing')

    print(f'PASS {len(names)} published hashes and unchanged serial/strips sources ({meta["mode"]} study)')
    print(f'PASS {len(rows)} comparisons bit-for-bit identical; P = '
          f'{sorted({int(r["P"]) for r in rows})}; N = {sorted({int(r["N"]) for r in rows})}')
    if cluster:
        print('PASS every P >= 2 run used at least two machines')
    print('PASS raw runs successful and consistent with compare.csv; halo debug transcripts present')


if __name__ == '__main__':
    main()
