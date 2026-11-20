"""Verify an archived Part 3 study without rerunning MPI.

Checks: manifest hashes, source provenance (serial, strips and blocks unchanged since
the run), every comparison PASS and byte-identical, true 2D grids (Px >= 2) covered,
uneven blocks present, several N, raw runs successful and consistent with the CSV,
for a cluster study every P >= 2 run on at least two machines, and the strips-vs-blocks
timing summary complete (both decompositions, every P and N, all repetitions).

Fields: if the study kept its field files (written by run_experiments.py since
20 November 2026), the byte comparison is repeated offline with the Part 2 checker:
hashes and sizes, every blocks field byte-identical to its serial field, each serial
field tied to the min/max (and Case V error norms) its run printed, and each serial
field recomputed independently in Python. Older studies are reported as record-only.

Eight processes: a cluster run with P > 6 must record, in metadata.json, the slots of
every VM checked against its real vCPU count (nproc), with slots <= vCPUs everywhere
and enough slots in total. A P = 8 study must also contain the 4x2 halo transcript.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('part2_verify', HERE.parent/'part2'/'verify_results.py')
part2_verify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(part2_verify)


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

    has_fields = 'blocks_sha256' in rows[0]
    if has_fields:
        references, figures, approximate = part2_verify.check_fields(folder, rows, runs, names, 'blocks')

    largest = max([int(r['P']) for r in rows] +
                  [int(P) for P in meta['parameters'].get('timing_np', [])
                   if meta['parameters'].get('timing')])
    slots_note = ''
    if cluster and largest > 6:
        hosts = meta.get('cluster_slots')
        require(hosts, f'P = {largest} was run, but metadata.json has no checked slot record')
        require(all(h['slots'] <= h['vcpus'] for h in hosts), 'A VM had more slots than vCPUs')
        total = sum(h['slots'] for h in hosts)
        require(total >= largest, f'P = {largest} exceeds the {total} checked slots')
        slots_note = ', '.join(f"{h['host']} {h['slots']}/{h['vcpus']}" for h in hosts)
    if largest >= 8:
        require('of 4x2 grid' in text, 'P = 8 was run, but the 4x2 halo transcript is missing')

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
    if slots_note:
        print(f'PASS P up to {largest} on checked real slots (slots/vCPUs: {slots_note})')
    if has_fields:
        exact = ('exactly' if not approximate else
                 f'({approximate} Case V fields within tolerance: the sin() of this C library differs in the '
                 'last bit from the one on the VMs; run on Ubuntu for an exact check)')
        print(f'PASS {len(rows)} blocks fields re-compared byte for byte offline against {references} serial '
              'fields; hashes, sizes, min/max and V error norms match their runs')
        print(f'PASS all {references} serial fields equal an independent Python recomputation of the scheme '
              f'{exact}; {figures} figure field pairs byte-identical')
    else:
        print('NOTE record-only study: fields were not retained, so byte equality comes from '
              'compare.csv and was not re-checked offline')


if __name__ == '__main__':
    main()
