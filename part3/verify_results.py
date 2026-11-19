"""Verify an archived Part 3 study without rerunning MPI.

Checks: manifest hashes, source provenance (serial, strips and blocks unchanged since
the run), every comparison PASS and byte-identical, true 2D grids (Px >= 2) covered,
uneven blocks present, several N, raw runs successful and consistent with the CSV,
for a cluster study every P >= 2 run on at least two machines, and the strips-vs-blocks
timing summary complete (both decompositions, every P and N, all repetitions).
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
        raise SystemExit('No archived Part 3 study yet: run part3/run_experiments.py --cluster, review it, '
                         'then copy the run folder to part3/results/<date>-cluster/.')
    return studies[-1]


def rows_of(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, help='study folder (default: newest under part3/results/)')
    parser.add_argument('--allow-local', action='store_true', help='accept a one-VM study')
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
    for key, path in [('serial_source_sha256', 'part1/heat_serial.cpp'),
                      ('strips_source_sha256', 'part2/heat_mpi.cpp'),
                      ('blocks_source_sha256', 'part3/heat_blocks.cpp')]:
        require(meta[key] == hashlib.sha256((root/path).read_bytes()).hexdigest(),
                f'{path} changed since this study; rerun it')
    cluster = meta['mode'] == 'cluster'
    require(cluster or args.allow_local, 'Study is local (one VM); cluster evidence is required')

    rows = rows_of(folder/'compare.csv')
    require(rows and all(r['result'] == 'PASS' and r['identical'] == 'True' and not r['summary_mismatch']
                         for r in rows), 'Not every comparison is bit-for-bit identical')
    require({1, 2, 3, 4} <= {int(r['P']) for r in rows}, 'P = 1, 2, 3 and 4 must all be covered')
    require(any(int(r['Px']) >= 2 for r in rows), 'No genuinely two-dimensional process grid (Px >= 2)')
    require(len({int(r['N']) for r in rows}) >= 3, 'Several N are required')
    require(any(r['uneven_blocks'] == 'True' and int(r['Px']) >= 2 for r in rows),
            'No uneven 2D block case (N-1 not divisible by Py or Px)')
    if cluster:
        require(all(int(r['nodes']) >= 2 for r in rows if int(r['P']) >= 2),
                'A P>=2 cluster run used only one machine')

    runs = json.loads((folder/'raw_runs.json').read_text(encoding='utf-8'))
    require(all(r['returncode'] == 0 for r in runs), 'A recorded solver run failed')
    blocks = {}
    for r in runs:
        if 'heat_blocks' in r['command'] and '--debug-print' not in r['command']:
            s = dict(t.split('=', 1) for t in r['stdout'].splitlines()[-1].split())
            blocks.setdefault((s['case'], int(s['N']), int(s['P'])), []).append(s)
    for r in rows:
        found = blocks.get((r['case'], int(r['N']), int(r['P'])), [])
        require(any(s['decomp'] == 'blocks' and s['Py'] == r['Py'] and s['Px'] == r['Px'] and
                    int(s['nodes']) == int(r['nodes']) for s in found),
                'CSV row without matching raw blocks run: '+str(r))
    text = (folder/'debug_halo.txt').read_text(encoding='utf-8')
    require('of 2x2 grid' in text and 'of 3x2 grid' in text, 'Halo debug transcripts for 2x2 and 3x2 are missing')

    timing_note = 'no timing stage'
    if meta['parameters'].get('timing'):
        p = meta['parameters']
        timing = rows_of(folder/'timing.csv')
        summary = rows_of(folder/'timing_summary.csv')
        expected = {(d, P, N) for d in ('strips', 'blocks') for P in p['timing_np'] for N in p['timing_N']}
        got = {(t['decomp'], int(t['P']), int(t['N'])) for t in timing}
        require(got == expected, 'Timing runs do not cover every decomposition, P and N')
        require(len(timing) == len(expected)*p['timing_reps'], 'Missing timing repetitions')
        require(all(float(t['t_comm']) >= 0 and float(t['t_comp']) >= 0 for t in timing), 'Invalid timers')
        require(len(summary) == len(expected), 'Timing summary incomplete')
        if cluster:
            require(all(int(t['nodes']) >= 2 for t in timing), 'A timing run used only one machine')
        timing_note = f'{len(timing)} timing runs, {len(summary)} medians'

    print(f'PASS {len(names)} published hashes and unchanged serial/strips/blocks sources ({meta["mode"]} study)')
    print(f'PASS {len(rows)} comparisons bit-for-bit identical; P = '
          f'{sorted({int(r["P"]) for r in rows})}; grids = {sorted({r["Py"]+"x"+r["Px"] for r in rows})}; '
          f'N = {sorted({int(r["N"]) for r in rows})}')
    if cluster:
        print('PASS every P >= 2 run used at least two machines')
    print(f'PASS raw runs consistent with compare.csv; 2x2 and 3x2 halo transcripts present; {timing_note}')


if __name__ == '__main__':
    main()
