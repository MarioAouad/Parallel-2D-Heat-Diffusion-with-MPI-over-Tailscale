"""Verify an archived Part 2 (C2) study without rerunning MPI.

Checks: manifest hashes, source provenance (both solvers unchanged since the run),
every comparison PASS and byte-identical, P = 1..4 covered, uneven strips present,
several N, raw runs successful and consistent with the CSV, and, for a cluster
study, every P >= 2 run spread over at least two machines.

If the study kept its field files (fields/*.bin, written by run_experiments.py since
20 November 2026), the byte comparison itself is repeated offline:
  - every serial and strips field named in compare.csv exists, is in the manifest and
    has the SHA-256 recorded in the CSV;
  - each strips field is byte-identical to its serial field (the `cmp` test);
  - each serial field holds (N+1)^2 little-endian doubles whose minimum and maximum (and,
    for Case V, err_inf and err_l2) equal what the serial run printed in raw_runs.json;
  - each serial field is recomputed independently here, in Python, with the serial
    FTCS loop (same expression order, the r and step count the run printed) and must
    match byte for byte. A field that was edited and re-hashed therefore still fails.
    Cases 1 and 2 use no transcendental functions and must match exactly on any
    platform. Case V starts from sin() and its norms use sin()/exp(); a different C
    library (e.g. Windows instead of the VMs' glibc) can change the last bit, so if the
    exact match fails there, Case V is accepted with field values within 1e-12 and error
    norms within 1e-8 relative (a norm subtracts nearly equal numbers, which magnifies
    a last-bit difference), and the output says so.
  - the two figure fields (serial and strips) are byte-identical.
An older study without fields still verifies, but is reported as record-only.
"""
import argparse
import array
import csv
import hashlib
import json
import math
from pathlib import Path
import sys

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


def read_field(path, N):
    """Raw little-endian float64 field, (N+1)^2 values, row-major."""
    data = path.read_bytes()
    require(len(data) == 8*(N+1)**2, f'{path.name}: expected {(N+1)**2} doubles, found {len(data)} bytes')
    values = array.array('d')
    values.frombytes(data)
    if sys.byteorder != 'little':
        values.byteswap()
    return values


def recompute(case, N, r, steps):
    """Independent re-implementation of part1/heat_serial.cpp's loop (IEEE doubles, no FMA)."""
    w, h, pi = N+1, 1.0/N, math.acos(-1.0)
    old = [0.0]*(w*w)
    if case == 'V':
        for j in range(1, N):
            for i in range(1, N):
                old[j*w+i] = math.sin(pi*i*h)*math.sin(pi*j*h)
    else:
        if case == '1':
            for j in range(w):
                old[j*w] = old[j*w+N] = 1.0
        for i in range(w):
            old[i] = old[N*w+i] = 1.0
    new = old[:]
    for _ in range(steps):
        for j in range(1, N):
            k0 = j*w
            for k in range(k0+1, k0+N):
                c = old[k]
                new[k] = c+r*((((old[k-1]+old[k+1])+old[k-w])+old[k+w])-4.0*c)
        old, new = new, old
    return array.array('d', old)


def field_summary(values, N, case, T):
    """Recompute what the solver prints, with the serial loop order and expressions."""
    out = dict(minimum=min(values), maximum=max(values))
    if case == 'V':
        h, pi = 1.0/N, math.acos(-1.0)
        amplitude = math.exp(-2*pi*pi*T)
        einf = sumsq = 0.0
        for j in range(1, N):
            for i in range(1, N):
                error = values[j*(N+1)+i] - math.sin(pi*i*h)*math.sin(pi*j*h)*amplitude
                einf = max(einf, abs(error))
                sumsq += error*error
        out.update(err_inf=einf, err_l2=h*math.sqrt(sumsq))
    return out


def check_fields(folder, rows, runs, names, decomp='strips'):
    """Repeat the serial-vs-parallel byte comparison from the stored files (strips or blocks)."""
    printed = {}
    for r in runs:
        c = r['command']
        if c and c[0] == 'heat' and '--out' in c:
            printed[Path(c[c.index('--out')+1]).name] = dict(
                t.split('=', 1) for t in r['stdout'].splitlines()[-1].split())
    checked, approximate = set(), set()
    for r in rows:
        N, ref_name, got_name = int(r['N']), r['serial_field'], r[decomp+'_field']
        for name, digest in ((ref_name, r['serial_sha256']), (got_name, r[decomp+'_sha256'])):
            require('fields/'+name in names, f'{name} is not in the manifest')
            require(hashlib.sha256((folder/'fields'/name).read_bytes()).hexdigest() == digest,
                    f'{name}: SHA-256 differs from compare.csv')
        require((folder/'fields'/got_name).read_bytes() == (folder/'fields'/ref_name).read_bytes(),
                f'{got_name} is not byte-identical to {ref_name}')
        if ref_name in checked:
            continue
        run = printed.get(ref_name)
        require(run is not None, f'No serial run wrote {ref_name}')
        values = read_field(folder/'fields'/ref_name, N)
        require(all(math.isfinite(v) for v in values), f'{ref_name} contains non-finite values')
        V = r['case'] == 'V'
        for key, value in field_summary(values, N, r['case'], float(run['T'])).items():
            if float(run[key]) != value and V and key.startswith('err'):
                require(math.isclose(float(run[key]), value, rel_tol=1e-8, abs_tol=0.0),
                        f'{ref_name}: {key} recomputed as {value!r}, but the run printed {run[key]}')
                approximate.add(ref_name)
                continue
            require(float(run[key]) == value,
                    f'{ref_name}: {key} recomputed as {value!r}, but the run printed {run[key]}')
        again = recompute(r['case'], N, float(run['r']), int(run['steps']))
        if again != values:
            require(V and max(abs(a-b) for a, b in zip(again, values)) <= 1e-12,
                    f'{ref_name} differs from an independent recomputation of the serial scheme')
            approximate.add(ref_name)
        checked.add(ref_name)
    figures = sorted(n for n in names if n.startswith('fields/figure_serial_case'))
    for name in figures:
        other = name.replace('figure_serial_', 'figure_'+decomp+'_')
        require(other in names and (folder/other).read_bytes() == (folder/name).read_bytes(),
                f'{other} is missing or differs from {name}')
    return len(checked), len(figures), len(approximate)


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
    has_fields = 'strips_sha256' in rows[0]
    references, figures, approximate = check_fields(folder, rows, runs, names) if has_fields else (0, 0, 0)

    print(f'PASS {len(names)} published hashes and unchanged serial/strips sources ({meta["mode"]} study)')
    print(f'PASS {len(rows)} comparisons bit-for-bit identical; P = '
          f'{sorted({int(r["P"]) for r in rows})}; N = {sorted({int(r["N"]) for r in rows})}')
    if cluster:
        print('PASS every P >= 2 run used at least two machines')
    print('PASS raw runs successful and consistent with compare.csv; halo debug transcripts present')
    if has_fields:
        print(f'PASS {len(rows)} strips fields re-compared byte for byte offline against {references} serial '
              'fields; hashes, sizes, min/max and V error norms match their runs')
        exact = ('exactly' if not approximate else
                 f'({approximate} Case V fields within tolerance: the sin() of this C library differs in the '
                 'last bit from the one on the VMs; run on Ubuntu for an exact check)')
        print(f'PASS all {references} serial fields equal an independent Python recomputation of the scheme '
              f'{exact}; {figures} figure field pairs byte-identical')
    else:
        print('NOTE record-only study: fields were not retained, so byte equality comes from '
              'compare.csv and was not re-checked offline')


if __name__ == '__main__':
    main()
