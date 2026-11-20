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
import math
import statistics
from collections import Counter
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


def verify_timing(folder,names,meta,runs):
    p = meta['parameters']
    if not p.get('timing'):
        return 0, False
    require({'timing.csv','timing_summary.csv','timing.png','timing.pdf'} <= names, 'Missing timing evidence')
    timing, aggregate = rows_of(folder/'timing.csv'), rows_of(folder/'timing_summary.csv')
    expected = {(d,P,N) for d in ('strips','blocks') for P in p['timing_np'] for N in p['timing_N']}
    keys = [(r['decomp'],int(r['P']),int(r['N']),int(r['rep'])) for r in timing]
    require(set(keys) == {(*k,rep) for k in expected for rep in range(1,p['timing_reps']+1)}
            and len(keys) == len(set(keys)), 'Missing/duplicate timing repetition')
    raw = [part2_verify.summary(run) for run in runs if '--out' not in run['command'] and '--debug-print' not in run['command']]
    def signature(row):
        return (row['decomp'],int(row['P']),int(row['N']),int(row['nodes']),int(row['steps']),
                *(float(row[k]) for k in ('t_total','t_comp','t_comm')))
    require(Counter(map(signature,timing)) == Counter(map(signature,raw)), 'Timing CSV/raw mismatch')
    for row in timing:
        P,N = int(row['P']),int(row['N'])
        grid = (P,1) if row['decomp'] == 'strips' else part2_verify.dims(P)
        require(row['grid'] == f'{grid[0]}x{grid[1]}' and int(row['steps']) == p['timing_steps'], 'Timing grid/steps mismatch')
    skeys = [(r['decomp'],int(r['P']),int(r['N'])) for r in aggregate]
    require(set(skeys) == expected and len(skeys) == len(expected), 'Missing/duplicate timing summary')
    for row,key in zip(aggregate,skeys):
        selected = [r for r in timing if (r['decomp'],int(r['P']),int(r['N'])) == key]
        require(int(row['reps']) == len(selected) and all(row['nodes'] == r['nodes'] and row['grid'] == r['grid'] for r in selected), 'Timing summary group differs')
        def per(k):
            return [float(r[k])/int(r['steps']) for r in selected]
        expected_values = {f'median_{name}_ms_per_step': statistics.median(per('t_'+name))*1000 for name in ('total','comp','comm')}
        expected_values.update(min_comm_ms_per_step=min(per('t_comm'))*1000,max_comm_ms_per_step=max(per('t_comm'))*1000)
        for column,value in expected_values.items():
            require(math.isclose(float(row[column]),value,rel_tol=1e-12,abs_tol=1e-12), column+' does not recompute from timing.csv')
    # Coverage alone is not a CPU-capacity check; verify_study enforces that separately.
    p8 = meta['mode'] == 'cluster' and p['timing_reps'] >= 3 and {
        (d,P,N) for d in ('strips','blocks') for P in (4,8) for N in (512,2048,8192)} <= expected
    return len(timing),p8


def verify_study(folder,allow_local=False,require_fields=False,require_p8=False):
    folder = Path(folder).resolve()
    names,meta,runs,warnings = part2_verify.load_study(folder,'blocks',allow_local)
    result = part2_verify.check_comparisons(folder,names,meta,runs,'blocks',require_fields)
    largest = max([int(part2_verify.summary(run)['P']) for run in runs])
    hosts = meta.get('cluster_slots')
    if meta['mode'] == 'cluster' and (largest > 6 or meta.get('evidence_schema',1) >= 2):
        require(hosts and len(hosts) == 3 and len({h['host'] for h in hosts}) == 3, 'Missing/duplicate checked VM slot record')
        require(all(isinstance(h['slots'],int) and isinstance(h['vcpus'],int) and 0 < h['slots'] <= h['vcpus'] for h in hosts), 'A VM has invalid slots or more slots than vCPUs')
        require(sum(h['slots'] for h in hosts) >= largest, 'P exceeds checked real CPU slots')
    part2_verify.check_debug(folder,runs,'blocks',(4,6,8) if largest >= 8 else (4,6))
    timing,p8 = verify_timing(folder,names,meta,runs)
    require(not require_p8 or p8, 'P=4,8 timing at N=512,2048,8192 with at least three cluster repetitions is required')
    return dict(result,published=len(names),warnings=warnings,timing=timing,p8=p8)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path)
    parser.add_argument('--allow-local',action='store_true')
    parser.add_argument('--require-fields',action='store_true')
    parser.add_argument('--require-p8',action='store_true',help='require the assignment P=4,8 timing matrix and checked real CPUs')
    args = parser.parse_args()
    result = verify_study(args.data or default_study(),args.allow_local,args.require_fields,args.require_p8)
    print('PASS hashes, source provenance, comparisons, raw summaries, V norms, halo values and recomputed timing aggregates:',result)
    if not result['fields']:
        print('NOTE record-only archive: original binary fields unavailable; byte equality cannot be repeated offline')
    if not result['p8']:
        print('NOTE required P=4,8 timing matrix remains incomplete')
    if result['approximate']:
        print('NOTE Case V independent recomputation used the documented C-library tolerance:',result['approximate'])
    if result['warnings']:
        print('NOTE retained Open MPI setpgid warnings:',result['warnings'])


if __name__ == '__main__':
    main()
