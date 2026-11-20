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
import re
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
        require(all(Path(n).name == n and n not in ('.','..') for n in (ref_name,got_name)), 'Unsafe field filename')
        require(ref_name == f"serial_case{r['case']}_N{N}.bin" and
                got_name == f"{decomp}_case{r['case']}_N{N}_P{r['P']}.bin", 'Field name/configuration mismatch')
        for name, digest in ((ref_name, r['serial_sha256']), (got_name, r[decomp+'_sha256'])):
            require('fields/'+name in names, f'{name} is not in the manifest')
            require(hashlib.sha256((folder/'fields'/name).read_bytes()).hexdigest() == digest,
                    f'{name}: SHA-256 differs from compare.csv')
        require((folder/'fields'/got_name).read_bytes() == (folder/'fields'/ref_name).read_bytes(),
                f'Retained field bytes differ: {got_name} is not byte-identical to {ref_name}')
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
        check_boundary(values, N, r['case'], ref_name)
        again = recompute(r['case'], N, float(run['r']), int(run['steps']))
        if again != values:
            require(V and max(abs(a-b) for a, b in zip(again, values)) <= 1e-12,
                    f'{ref_name} differs from an independent recomputation of the serial scheme')
            approximate.add(ref_name)
        checked.add(ref_name)
    require({Path(n).name for n in names if n.startswith('fields/figure_serial_case')} ==
            {'figure_serial_case1.bin','figure_serial_case2.bin'}, 'Missing retained figure fields')
    figures = sorted(n for n in names if n.startswith('fields/figure_serial_case'))
    for name in figures:
        other = name.replace('figure_serial_', 'figure_'+decomp+'_')
        require(other in names and (folder/other).read_bytes() == (folder/name).read_bytes(),
                f'Retained field bytes differ: {other} is missing or differs from {name}')
        run = printed.get(Path(name).name)
        require(run is not None, f'No serial run wrote {name}')
        N, case = int(run['N']), run['case']
        values = read_field(folder/name, N)
        check_boundary(values, N, case, name)
        require(values == recompute(case, N, float(run['r']), int(run['steps'])),
                f'{name} differs from independent figure recomputation')
    return len(checked), len(figures), len(approximate)


def rows_of(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def check_boundary(values, N, case, name):
    require(all(math.isfinite(v) and -1e-14 <= v <= 1+1e-14 for v in values),
            f'{name}: non-finite or out-of-range stable field')
    for j in range(N+1):
        for i in range(N+1):
            if i not in (0, N) and j not in (0, N):
                continue
            expected = 0.0 if case == 'V' else float(case == '1' or j in (0, N))
            require(values[j*(N+1)+i] == expected, f'Retained boundary value is wrong: {name} ({j},{i})')


def summary(run):
    return dict(t.split('=', 1) for t in run['stdout'].splitlines()[-1].split())


def option(command, flag):
    return command[command.index(flag)+1] if flag in command else None


def dims(P):
    return min(((P//a, a) for a in range(1, P+1) if P%a == 0 and P//a >= a), key=lambda d:d[0]-d[1])


def split(part, parts, N):
    base, extra = divmod(N-1, parts)
    return 1+part*base+min(part, extra), base+(part < extra)


def load_study(folder, decomp, allow_local):
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    names = set()
    for item in manifest['published_files']:
        name = item['file']
        require(name not in names and not Path(name).is_absolute() and '..' not in Path(name).parts
                and (folder/name).resolve().is_relative_to(folder.resolve()), 'Unsafe/duplicate manifest entry: '+name)
        names.add(name)
        data = (folder/name).read_bytes()
        require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                'Result hash/size mismatch: '+name)
    require({'compare.csv','raw_runs.json','metadata.json','debug_halo.txt','cases.png',
             'decomposition.png','decomposition.pdf'} <= names, 'Manifest is missing required evidence files')
    meta = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    for key, path in [('serial','part1/heat_serial.cpp'), ('strips','part2/heat_mpi.cpp')]+(
            [('blocks','part3/heat_blocks.cpp')] if decomp == 'blocks' else []):
        require(meta[key+'_source_sha256'] == hashlib.sha256((HERE.parent/path).read_bytes()).hexdigest(),
                path+' changed since this study; rerun it')
    if meta.get('evidence_schema',1) >= 2:
        binaries = meta.get('launcher_executables',{})
        require({'serial',decomp} <= set(binaries) and all(re.fullmatch(r'[0-9a-f]{64}',v.get('sha256','')) for v in binaries.values()),
                'New study missing launcher executable hashes')
    require(meta['mode'] in ('cluster','local'), 'Invalid study mode')
    require(meta['mode'] == 'cluster' or allow_local, 'Study is local; cluster evidence is required')
    runs = json.loads((folder/'raw_runs.json').read_text(encoding='utf-8'))
    require(runs and all(r['returncode'] == 0 for r in runs), 'A recorded solver run failed')
    warnings = 0
    for run in runs:
        if run.get('stderr', '').strip():
            require(all(re.fullmatch(r'\[heat[123]:\d+\] plm:rsh: Warning: setpgid\(\d+,\d+\) failed in parent with errno=Permission denied\(13\)', line)
                        for line in run['stderr'].strip().splitlines()), 'Unexpected stderr in a recorded run')
            warnings += 1
        c, s = run['command'], summary(run)
        N, steps, r, dt, T = int(s['N']), int(s['steps']), float(s['r']), float(s['dt']), float(s['T'])
        require(N >= 2 and steps > 0 and all(math.isfinite(x) for x in (r,dt,T)) and 0 < r <= .25
                and dt > 0 and T > 0, 'Invalid numerical parameters')
        require(s['case'] == option(c,'--case') and N == int(option(c,'--N'))
                and s['decomp'] == option(c,'--decomp'), 'Command/raw parameter mismatch')
        if '--steps' in c:
            require(steps == int(option(c,'--steps')) and r == float(option(c,'--r')), 'Command/raw steps or r mismatch')
        else:
            require(T == float(option(c,'--T')) and r <= float(option(c,'--r')), 'Command/raw final-time mismatch')
        require(math.isclose(dt, r*(1.0/N)**2, rel_tol=2e-14)
                and math.isclose(T, steps*dt, rel_tol=2e-14), 'Inconsistent r, dt, steps and T')
        for key in ('t_total','t_comp','t_comm','minimum','maximum'):
            require(math.isfinite(float(s[key])), 'Non-finite summary value')
        require(all(float(s[k]) >= 0 for k in ('t_total','t_comp','t_comm'))
                and 0 <= float(s['minimum']) <= float(s['maximum']) <= 1+1e-14, 'Invalid timers/extrema')
        P = int(s['P'])
        if meta.get('evidence_schema',1) >= 2 and meta['mode'] == 'cluster':
            hosts = meta.get('cluster_slots')
            require(hosts and len(hosts) == 3 and len({h['host'] for h in hosts}) == 3, 'Missing/duplicate checked VM slot record')
            require(all(isinstance(h['slots'],int) and isinstance(h['vcpus'],int) and 0 < h['slots'] <= h['vcpus'] for h in hosts)
                    and sum(h['slots'] for h in hosts) >= P, 'P exceeds checked real CPU slots')
        require(P == (int(option(c,'-np')) if '-np' in c else 1), 'Command/raw P mismatch')
        if s['decomp'] != 'serial':
            require(1 <= int(s['nodes']) <= min(P,3), 'Invalid machine count')
            if meta['mode'] == 'cluster' and P >= 2:
                require(int(s['nodes']) >= 2, 'A P>=2 cluster run used only one machine')
        if s['case'] == 'V':
            # Exact discrete sine eigenmode: verifies the reported error without stored fields.
            eigen = (1-8*r*math.sin(math.pi/(2*N))**2)**steps
            error = abs(eigen-math.exp(-2*math.pi**2*T))
            expected_inf = error*math.sin(math.pi*(N//2)/N)**2
            for key, expected in [('err_inf',expected_inf),('err_l2',error/2)]:
                require(math.isclose(float(s[key]), expected, rel_tol=1e-7, abs_tol=5e-13), 'V error norm disagrees with discrete sine solution')
    figure_runs = {Path(option(run['command'],'--out')).name:summary(run) for run in runs
                   if '--out' in run['command'] and 'figure_' in option(run['command'],'--out')}
    for case in ('1','2'):
        reference,parallel = (figure_runs.get(f'figure_{d}_case{case}.bin') for d in ('serial',decomp))
        require(reference and parallel and all(reference.get(k) == parallel.get(k) for k in
                ('case','N','steps','r','dt','T','minimum','maximum')), 'Figure serial/parallel summary mismatch')
    return names, meta, runs, warnings


def check_comparisons(folder, names, meta, runs, decomp, require_fields):
    rows = rows_of(folder/'compare.csv')
    p = meta['parameters']
    cases = p['cases'].split(',') if isinstance(p['cases'],str) else p['cases']
    expected = {(case,N,P) for case in cases for N in p['N'] for P in p['np']
                if N-1 >= (P if decomp == 'strips' else dims(P)[0])}
    keys = [(r['case'],int(r['N']),int(r['P'])) for r in rows]
    require(set(keys) == expected and len(keys) == len(expected), 'Missing, duplicate or extra comparison configurations')
    require({'1','2','V'} <= set(cases) and {1,2,3,4} <= set(p['np']) and len(set(p['N'])) >= 3,
            'Cases 1,2,V, P=1..4 and several N are required')
    raw = {(s['case'],int(s['N']),int(s['P'])): s for run in runs
           if (s:=summary(run))['decomp'] == decomp and '--out' in run['command']
           and 'figure_' not in option(run['command'],'--out')}
    serial = {(s['case'],int(s['N'])):s for run in runs
              if (s:=summary(run))['decomp'] == 'serial' and '--out' in run['command']
              and 'figure_' not in option(run['command'],'--out')}
    for row,key in zip(rows,keys):
        case,N,P = key
        s, ref = raw.get(key), serial.get((case,N))
        require(s is not None and ref is not None, 'CSV row without matching raw run')
        prefix = 'Comparison CSV/raw mismatch' if decomp == 'blocks' else 'CSV/raw mismatch'
        for column in ('steps','nodes','t_total','t_comp','t_comm')+ (('Py','Px') if decomp == 'blocks' else ()):
            require(float(row[column]) == float(s[column]), prefix+': '+column)
        require(all(ref.get(k) == s.get(k) for k in ('steps','r','dt','T','minimum','maximum','err_inf','err_l2')),
                'Serial/parallel raw summary mismatch')
        require(row['result'] == 'PASS' and row['identical'] == 'True' and not row['summary_mismatch']
                and int(row['bytes']) == 8*(N+1)**2, 'Invalid comparison result/field size')
        py,px = (P,1) if decomp == 'strips' else dims(P)
        if decomp == 'blocks':
            require((int(row['Py']),int(row['Px'])) == (py,px), 'Wrong Cartesian grid')
        uneven = (N-1)%py != 0 or (N-1)%px != 0
        require(row['uneven_'+decomp] == str(uneven), 'Incorrect uneven decomposition flag')
    if decomp == 'strips':
        for P in (2,3,4):
            require(any(k[2] == P and (k[1]-1)%P for k in keys), 'Missing uneven strips')
    else:
        require(any(int(r['Px']) >= 2 and r['uneven_blocks'] == 'True' for r in rows), 'Missing uneven 2D blocks')
    fields = bool(rows) and all(k in rows[0] for k in ('serial_field','serial_sha256',decomp+'_field',decomp+'_sha256'))
    require(meta.get('evidence_schema',1) < 2 or fields, 'New study missing retained field records')
    require(not require_fields or fields, 'Original binary fields unavailable: record-only legacy archive; run a new retained-field study')
    references, figures, approximate = check_fields(folder,rows,runs,names,decomp) if fields else (0,0,0)
    return dict(comparisons=len(rows), fields=fields, pairs=len(rows)+figures if fields else 0,
                references=references, approximate=approximate)


def check_debug(folder, runs, decomp, required):
    text = (folder/'debug_halo.txt').read_text(encoding='utf-8')
    found = set()
    for run in runs:
        if '--debug-print' not in run['command']:
            continue
        s = summary(run)
        N,P = int(s['N']),int(s['P'])
        found.add(P)
        require(run['stdout'].strip() in text, 'Debug transcript differs from raw output')
        values = recompute(s['case'],N,float(s['r']),int(s['steps']))
        py,px = (P,1) if decomp == 'strips' else dims(P)
        rank = None
        seen = set()
        seen_rows = {}
        for line in run['stdout'].splitlines():
            if line.startswith('rank '):
                rank = int(re.match(r'rank (\d+):',line)[1])
                require(rank not in seen and 0 <= rank < P, 'Duplicate/invalid debug rank')
                seen.add(rank)
                cy,cx = divmod(rank,px)
                fy,nr = split(cy,py,N)
                fx,nc = (1,N-1) if decomp == 'strips' else split(cx,px,N)
                if decomp == 'blocks':
                    require(f'coords ({cy},{cx}) of {py}x{px} grid, rows {fy}..{fy+nr-1}, cols {fx}..{fx+nc-1}' in line,
                            'Debug rank coordinates/ranges disagree')
                else:
                    require(f'owns global rows {fy}..{fy+nr-1} ({nr} rows)' in line, 'Debug strip range disagrees')
                neighbors = dict(down='none' if cy == 0 else str(rank-px), up='none' if cy == py-1 else str(rank+px))
                if decomp == 'blocks':
                    neighbors.update(left='none' if cx == 0 else str(rank-1),right='none' if cx == px-1 else str(rank+1))
                require(all(f'{k}={v}' in line for k,v in neighbors.items()), 'Debug neighbor disagrees')
                seen_rows[rank] = set()
            elif (m:=re.match(r'  (ghost|owned|boundary)\s+j=\s*(\d+):\s*(.*)',line)):
                require(rank is not None, 'Debug row without rank')
                j, tokens = int(m[2]),m[3].split()
                require(j not in seen_rows[rank] and fy-1 <= j <= fy+nr, 'Missing/duplicate debug row')
                seen_rows[rank].add(j)
                kind = 'owned' if fy <= j < fy+nr else ('boundary' if j in (0,N) else 'ghost')
                require(m[1] == kind and len(tokens) == nc+2, 'Debug row shape/kind disagrees')
                for q,token in enumerate(tokens):
                    corner = decomp == 'blocks' and j in (fy-1,fy+nr) and q in (0,nc+1)
                    require((token == '-') == corner, 'Debug corner ghost disagrees')
                    if not corner:
                        require(abs(float(token)-values[j*(N+1)+fx-1+q]) <= 5.1e-7, 'Debug value disagrees with independent FTCS solution')
        require(seen == set(range(P)) and all(len(v) == split(k//px,py,N)[1]+2 for k,v in seen_rows.items()), 'Incomplete debug ranks/rows')
    require(set(required) <= found, 'Required halo debug transcripts are missing')


def verify_study(folder, allow_local=False, require_fields=False):
    folder = Path(folder).resolve()
    names,meta,runs,warnings = load_study(folder,'strips',allow_local)
    result = check_comparisons(folder,names,meta,runs,'strips',require_fields)
    check_debug(folder,runs,'strips',(2,3))
    return dict(result, published=len(names), warnings=warnings)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path)
    parser.add_argument('--allow-local',action='store_true')
    parser.add_argument('--require-fields',action='store_true', help='reject record-only studies without original binaries')
    args = parser.parse_args()
    result = verify_study(args.data or default_study(),args.allow_local,args.require_fields)
    print('PASS hashes, source provenance, complete comparisons, CSV/raw summaries, V norms and halo values:',result)
    if not result['fields']:
        print('NOTE record-only archive: original binary fields unavailable; byte equality cannot be repeated offline')
    elif result['approximate']:
        print('NOTE Case V independent recomputation used the documented C-library tolerance:',result['approximate'])
    if result['warnings']:
        print('NOTE retained Open MPI setpgid warnings:',result['warnings'])


if __name__ == '__main__':
    main()
