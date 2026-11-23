"""Experiment design and independently reusable numerical/evidence checks for Part 4."""
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
BASELINE_N = [512, 1024, 2048, 4096, 8192]
STRONG_N = [512, 2048, 8192]
SOURCES = ['part1/heat_serial.cpp', 'part2/heat_mpi.cpp', 'part3/heat_blocks.cpp',
           'part0/04-pingpong/mpi_pingpong.cpp', 'part4/common.py',
           'part4/run_experiments.py', 'part4/analyze.py', 'part4/verify_results.py']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def check_pingpong_diagnostics(stderr, rows):
    """Accept the unchanged Part 0 benchmark's exact progress protocol.

    Rank zero prints one progress line per CSV row to stderr, then the success
    marker. Extra warnings/errors are still rejected, not silently discarded.
    """
    expected=[f"Testing {r['bytes']} bytes: {r['host0']} <-> {r['host1']}" for r in rows]
    expected.append('Finished successfully. CSV contains measured results.')
    require(bool(rows) and stderr.strip().splitlines()==expected,
            'Unexpected ping-pong diagnostic: progress/hosts/success do not match CSV; inspect raw_runs.jsonl')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    path = Path(path)
    temporary = path.with_suffix(path.suffix+'.partial')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    temporary.replace(path)


def write_csv(path, rows):
    require(bool(rows), 'Cannot publish an empty result table')
    with Path(path).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    with Path(path).open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def dims(P):
    return min(((P//x, x) for x in range(1, math.isqrt(P)+1) if P % x == 0),
               key=lambda y: y[0]-y[1])


def split(index, parts, N):
    base, extra = divmod(N-1, parts)
    return base+(index < extra)


def weak_N(base, P):
    # Keep INTERIOR work per process close to base^2; report the rounding exactly.
    return math.floor(base*math.sqrt(P)+0.5)+1


def placement(slots, P, mapping):
    require(0 < P <= sum(slots), 'P exceeds real configured slots')
    require(mapping in ('node', 'slot'), 'Unknown placement')
    if mapping == 'slot':
        return [k for k, count in enumerate(slots) for _ in range(count)][:P]
    remaining, result = slots[:], []
    while len(result) < P:
        for k in range(len(slots)):
            if remaining[k] and len(result) < P:
                result.append(k)
                remaining[k] -= 1
    return result


def design(parameters, slots):
    """Pure complete plan: stable IDs support checkpoint/restart without lost runs."""
    p = parameters
    require(p['weak_base']>0 and all(isinstance(N,int) and N>=2 for N in p['baseline_N']+p['strong_N']), 'Invalid grid sizes')
    require(p['reps']>0 and p['steps']>0 and all(isinstance(P,int) and P>0 for P in p['P']), 'Invalid repetitions/steps/P')
    tasks = []
    for rep in range(1, p['reps']+1):
        for host in range(3):
            for N in p['baseline_N']:
                tasks.append(dict(id=f'baseline:{host}:{N}:{rep}', experiment='baseline',
                                  host=f'heat{host+1}', decomp='serial', mapping='serial',
                                  P=1, N=N, rep=rep))
        for experiment in ('strong', 'weak'):
            for mapping in ('node', 'slot'):
                for P in p['P']:
                    for N in (p['strong_N'] if experiment == 'strong' else [weak_N(p['weak_base'], P)]):
                        for decomp in (('strips', 'blocks') if rep % 2 else ('blocks', 'strips')):
                            require(N-1 >= P, 'N too small for nonempty strips at requested P')
                            tasks.append(dict(id=f'{experiment}:{mapping}:{P}:{N}:{decomp}:{rep}',
                                              experiment=experiment, host='cluster', decomp=decomp,
                                              mapping=mapping, P=P, N=N, rep=rep))
    require(len({t['id'] for t in tasks}) == len(tasks), 'Duplicate configurations in plan')
    require(all(0 < P <= sum(slots) for P in p['P']), 'P exceeds available slots')
    return tasks


def default_parameters(total=8, smoke=False):
    return dict(profile='smoke' if smoke else 'full', baseline_N=[8,16] if smoke else BASELINE_N[:],
                strong_N=[8,16] if smoke else STRONG_N[:], P=[1,2] if smoke else list(range(1,total+1)),
                reps=1 if smoke else 3, steps=2 if smoke else 20, r=.24,
                weak_base=8 if smoke else 1024, calibration_reps=1 if smoke else 3,
                calibration_iterations=1 if smoke else 3,
                calibration_max_bytes=32768 if smoke else 131072)


def official_parameters(p, total):
    return (p['profile'] == 'full' and set(p['baseline_N']) == set(BASELINE_N)
            and set(p['strong_N']) == set(STRONG_N) and set(p['P']) == set(range(1,total+1))
            and p['reps'] >= 3 and p['calibration_reps'] >= 3 and .20 <= p['r'] <= .25
            and p['calibration_max_bytes'] >= 8*(max(max(p['strong_N']),weak_N(p['weak_base'],max(p['P'])))+1))


def parse_summary(stdout, task, parameters, nodes):
    s = dict(word.split('=',1) for word in stdout.strip().splitlines()[-1].split())
    for key, value in [('decomp',task['decomp']),('case','1'),('N',str(task['N'])),
                       ('P',str(task['P'])),('steps',str(parameters['steps']))]:
        require(s.get(key) == value, 'Solver summary disagrees with plan: '+key)
    N = task['N']
    require(float(s['r']) == parameters['r'] and
            math.isclose(float(s['dt']),parameters['r']*(1/N)**2,rel_tol=1e-13) and
            math.isclose(float(s['T']),parameters['steps']*float(s['dt']),rel_tol=1e-13),
            'Solver time parameters disagree with fixed-step plan')
    for key in ('t_total','t_comp','t_comm','minimum','maximum'):
        require(math.isfinite(float(s[key])), 'Non-finite solver result')
    require(float(s['t_total']) > 0 and all(0 <= float(s[k]) <= float(s['t_total'])*(1+1e-10)
                                          for k in ('t_comp','t_comm')), 'Invalid timers')
    require(0 <= float(s['minimum']) <= float(s['maximum']) <= 1, 'Stable field violates [0,1]')
    if task['decomp'] == 'serial':
        require(float(s['t_comm']) == 0, 'Serial communication timer is nonzero')
    else:
        require(int(s['nodes']) == nodes, 'Solver machine count disagrees with placement probe')
    py, px = dims(task['P']) if task['decomp']=='blocks' else (task['P'],1)
    if task['decomp']=='blocks':
        require((int(s['Py']),int(s['Px'])) == (py,px), 'Incorrect Cartesian dimensions')
    cells = [split(y,py,N)*split(x,px,N) for y in range(py) for x in range(px)]
    steps = parameters['steps']
    return dict(task, steps=steps, r=parameters['r'], nodes=nodes, Py=py, Px=px,
                cells_per_rank=(N-1)**2/task['P'], min_rank_cells=min(cells),max_rank_cells=max(cells),
                total_s=float(s['t_total']), comp_s=float(s['t_comp']),comm_s=float(s['t_comm']),
                seconds_per_step=float(s['t_total'])/steps,
                seconds_per_grid_node=float(s['t_total'])/steps/(N+1)**2,
                seconds_per_interior_node=float(s['t_total'])/steps/(N-1)**2,
                communication_fraction=float(s['t_comm'])/float(s['t_total']))


def fit_link(samples, maximum):
    """Startup from small messages, anchored transfer slope over relevant large sizes."""
    by_size = {}
    for sample in samples:
        by_size.setdefault(int(sample['bytes']),[]).append(float(sample['oneway_s']))
    expected = {2**k for k in range(3,int(math.log2(maximum))+1)}
    require(set(by_size) == expected, 'Incomplete communication size sweep')
    med = {b:statistics.median(v) for b,v in by_size.items()}
    ts = statistics.median(med[b] for b in med if b <= 64)
    large = [b for b in med if b >= maximum//4]
    slope = sum(b*(med[b]-ts) for b in large)/sum(b*b for b in large)
    valid = math.isfinite(slope) and slope > 0 and ts > 0
    return dict(latency_s=ts, seconds_per_byte=slope, seconds_per_double=8*slope,
                valid=valid, max_bytes=maximum,
                rmse_s=math.sqrt(sum((med[b]-(ts+b*slope))**2 for b in med)/len(med)))


def predict(row, rank_hosts, compute_rates, links, latency_override=None):
    """Task 8.2 busiest-rank model, extended to uneven blocks and measured host speeds.

    Each existing neighbor contributes one send/receive exchange, not two RTTs.
    This omits phase critical paths, contention, datatype packing and cache changes.
    """
    N,P,py,px = int(row['N']),int(row['P']),int(row['Py']),int(row['Px'])
    totals, compute, communication = [], [], []
    for rank in range(P):
        y,x = divmod(rank,px)
        nr,nc = split(y,py,N),split(x,px,N)
        neighbors=[]
        for yy,xx,count in [(y-1,x,nc),(y+1,x,nc),(y,x-1,nr),(y,x+1,nr)]:
            if 0 <= yy < py and 0 <= xx < px:
                if row['decomp']=='strips':count=N+1
                neighbors.append((yy*px+xx,count))
        host=rank_hosts[rank]
        comp=nr*nc*compute_rates[host]
        comm=0.0
        for other,count in neighbors:
            key='|'.join(sorted([host,rank_hosts[other]]))
            link=links[key]
            require(link['valid'], 'Nonphysical calibration fit: '+key)
            comm+=(link['latency_s'] if latency_override is None else latency_override)+count*link['seconds_per_double']
        compute.append(comp);communication.append(comm);totals.append(comp+comm)
    return dict(model_total_s_per_step=max(totals),model_compute_s_per_step=max(compute),
                model_comm_s_per_step=max(communication))


def manifest(folder):
    files=[]
    for p in sorted(folder.rglob('*')):
        if p.is_file() and 'private' not in p.relative_to(folder).parts and p.name != 'manifest.json' and not p.name.endswith('.partial'):
            files.append(dict(file=p.relative_to(folder).as_posix(),bytes=p.stat().st_size,sha256=sha(p)))
    write_json(folder/'manifest.json',dict(published_files=files))
