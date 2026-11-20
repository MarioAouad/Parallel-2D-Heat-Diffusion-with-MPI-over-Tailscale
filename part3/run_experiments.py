"""Part 3 study: 2D blocks must equal the serial reference bit for bit; strips vs blocks timing.

Stage 1 runs the Part 1 serial executable and the Part 3 blocks executable with
identical inputs for every case, N and P, and compares field files byte by byte
(the `cmp` test) and summary values. Stage 2 records halo-debugging transcripts and
draws the decomposition and Case 1/2 figures. Stage 3 (cluster mode, or --timing)
answers the report question "predict whether strips or blocks are faster, then
check": repeated strips (Part 2) and blocks runs at large N, no output file, median
and spread over repetitions, interleaved so that network drift affects both alike.

Local mode (one VM) oversubscribes the CPU: fine for correctness, never for timing.
Cluster mode uses the team hostfile with --map-by node (every P >= 2 run spans at
least two VMs). Each invocation writes a new timestamped folder.

Slots. In cluster mode the hostfile's slots (part0/config/cluster.sh, HEATn_SLOTS) are
checked against each VM's real vCPU count (`nproc` over SSH) before anything runs: a
slot without a vCPU is refused, as the assignment forbids more processes than
allocated vCPUs. P = 8 (a 4x2 grid) is added to every stage only when the checked slots
total at least 8. The slots, vCPU counts and this decision go into metadata.json.

Fields. Every serial and blocks field is kept under fields/ and listed with its SHA-256
in compare.csv and manifest.json, so verify_results.py can repeat the comparison offline.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shlex
import statistics
import subprocess
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
HOSTFILE = ROOT/'part0'/'config'/'hosts'
CLUSTER_ARGS = ['--hostfile', str(HOSTFILE), '--map-by', 'node',
                '--mca', 'plm_rsh_args', '-o BatchMode=yes -o ConnectTimeout=15',
                '--mca', 'oob_tcp_if_include', 'tailscale0',
                '--mca', 'btl_tcp_if_include', 'tailscale0',
                '--mca', 'btl', 'tcp,self']
SAME = ['steps', 'r', 'dt', 'T', 'minimum', 'maximum', 'err_inf', 'err_l2']
PUBLISHED = ['compare.csv', 'debug_halo.txt', 'decomposition.png', 'decomposition.pdf', 'cases.png',
             'timing.csv', 'timing_summary.csv', 'timing.png', 'timing.pdf', 'raw_runs.json', 'metadata.json']


def ints(text):
    return [int(v) for v in text.split(',') if v]


def cluster_slots():
    """Slots per VM from the rendered hostfile, checked against the VM's real vCPUs.

    Returns a list of dict(host=heatN, slots, vcpus). Hosts are recorded by alias only,
    never by address. Raises if any VM has more slots than vCPUs.
    """
    hosts = []
    for k, line in enumerate(l for l in HOSTFILE.read_text().splitlines() if l.strip() and not l.startswith('#')):
        address, _, rest = line.partition(' ')
        slots = int(rest.split('slots=')[1].split()[0]) if 'slots=' in rest else 1
        p = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', address, 'nproc'],
                           capture_output=True, text=True, timeout=60)
        if p.returncode or not p.stdout.strip().isdigit():
            raise SystemExit(f'Cannot read the vCPU count of heat{k+1} over SSH: {p.stderr.strip()}')
        vcpus = int(p.stdout.strip())
        if slots > vcpus:
            raise SystemExit(f'heat{k+1} has slots={slots} but only {vcpus} vCPUs (nproc). Allocate the vCPUs '
                             f'in VirtualBox first, or lower HEAT{k+1}_SLOTS in cluster.local.sh.')
        hosts.append(dict(host=f'heat{k+1}', slots=slots, vcpus=vcpus))
    return hosts


def dims_create(P):
    """Same result as MPI_Dims_create(P, 2): most balanced Py >= Px with Py*Px = P."""
    return min(((P//a, a) for a in range(1, P+1) if P % a == 0 and P//a >= a), key=lambda d: d[0]-d[1])


def split(part, parts, N):
    base, extra = divmod(N-1, parts)
    return 1 + part*base + min(part, extra), base + (1 if part < extra else 0)


def decomposition_figure(out):
    """Report figure: owner of every interior node, and one block's ghost layer and corners."""
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 5.0), constrained_layout=True)
    colours = plt.cm.tab10.colors
    for ax, (N, P) in zip(axes, [(9, 4), (10, 6)]):
        Py, Px = dims_create(P)
        for j in range(N+1):
            for i in range(N+1):
                if j in (0, N) or i in (0, N):
                    ax.plot(i, j, 's', color='0.6', ms=7)
        for cy in range(Py):
            for cx in range(Px):
                p = cy*Px + cx
                fy, rows = split(cy, Py, N)
                fx, cols = split(cx, Px, N)
                for j in range(fy, fy+rows):
                    ax.plot(range(fx, fx+cols), [j]*cols, 'o', color=colours[p], ms=7)
                ax.add_patch(plt.Rectangle((fx-.5, fy-.5), cols, rows, color=colours[p], alpha=.12, lw=0))
                ax.text(fx+(cols-1)/2, fy+(rows-1)/2, f'rank {p}', ha='center', va='center', fontsize=9,
                        fontweight='bold', color=colours[p], zorder=5,
                        bbox=dict(boxstyle='round,pad=0.25', fc='white', ec=colours[p]))
        # Ghost layer of the rank in the middle of the top block row (or rank 0 for 2x2).
        target = (Py-1)//2*Px if Py > 2 else 0
        cy, cx = divmod(target, Px)
        fy, rows = split(cy, Py, N)
        fx, cols = split(cx, Px, N)
        c = colours[target]
        ax.plot([fx-1.4, fx+cols+.4], [fy-1, fy-1], '--', color=c, lw=1.3)
        ax.plot([fx-1.4, fx+cols+.4], [fy+rows, fy+rows], '--', color=c, lw=1.3)
        ax.plot([fx-1, fx-1], [fy-1.4, fy+rows+.4], '--', color=c, lw=1.3)
        ax.plot([fx+cols, fx+cols], [fy-1.4, fy+rows+.4], '--', color=c, lw=1.3)
        for cxn, cyn in [(fx-1, fy-1), (fx+cols, fy-1), (fx-1, fy+rows), (fx+cols, fy+rows)]:
            ax.plot(cxn, cyn, 'x', color='k', ms=11, mew=2)
        ax.set(title=f'N={N}, P={P}: MPI_Dims_create gives {Py}x{Px} (rows x columns)',
               xlabel='i (columns; rows are contiguous)', ylabel='j (rows)',
               xlim=(-.8, N+.8), ylim=(-.8, N+.8))
        ax.set_aspect('equal')
        ax.set_xticks(range(N+1))
        ax.set_yticks(range(N+1))
    fig.suptitle(f'Block decomposition: grey = fixed boundary; dashed = ghost layer of one block; '
                 f'x = corner ghosts, never exchanged (5-point stencil does not read them)', fontsize=9)
    fig.savefig(out/'decomposition.png', dpi=170)
    fig.savefig(out/'decomposition.pdf')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--serial', type=Path, default=ROOT/'build'/'heat')
    parser.add_argument('--strips', type=Path, default=ROOT/'build'/'heat_mpi')
    parser.add_argument('--blocks', type=Path, default=ROOT/'build'/'heat_blocks')
    parser.add_argument('--np', type=ints, default=None,
                        help='process counts (default 1,2,3,4,6, plus 8 when 8 real slots exist)')
    parser.add_argument('--N', type=ints, default=[8, 9, 10, 17, 64, 101])
    parser.add_argument('--cases', default='1,2,V')
    parser.add_argument('--steps', type=int, default=20, help='fixed steps for Cases 1 and 2')
    parser.add_argument('--T', type=float, default=0.002, help='final time for case V')
    parser.add_argument('--r', type=float, default=0.2)
    parser.add_argument('--figure-N', type=int, default=64)
    parser.add_argument('--figure-steps', type=int, default=500)
    parser.add_argument('--timing', action='store_true', help='run stage 3 (default: on in cluster mode)')
    parser.add_argument('--no-timing', action='store_true')
    parser.add_argument('--timing-np', type=ints, default=None,
                        help='default 4,6, plus 8 when 8 real slots exist')
    parser.add_argument('--timing-N', type=ints, default=[512, 2048, 8192])
    parser.add_argument('--timing-steps', type=int, default=10)
    parser.add_argument('--timing-reps', type=int, default=3)
    parser.add_argument('--cluster', action='store_true',
                        help='use part0/config/hosts across the VMs (run from ONE VM)')
    parser.add_argument('--mpirun-args', default=None,
                        help='extra mpirun arguments (default local: --oversubscribe)')
    parser.add_argument('--out', type=Path, help='new output directory (must not exist)')
    args = parser.parse_args()
    timing = (args.cluster or args.timing) and not args.no_timing

    for exe in (args.serial, args.blocks) + ((args.strips,) if timing else ()):
        if not exe.is_file():
            parser.error(f'Missing {exe}. Build first: make serial strips blocks')
    serial_exe, strips_exe, blocks_exe = (str(p.resolve()) for p in (args.serial, args.strips, args.blocks))
    hosts = None
    if args.cluster:
        subprocess.run(['bash', '-c', f'source {shlex.quote(str(ROOT/"part0/config/cluster.sh"))}'],
                       check=True)
        extra = CLUSTER_ARGS
        hosts = cluster_slots()
        total = sum(h['slots'] for h in hosts)
        print('Slots checked against nproc: ' + ', '.join(
            f"{h['host']} {h['slots']}/{h['vcpus']}" for h in hosts) + f' -> {total} slots', flush=True)
    else:
        extra = shlex.split(args.mpirun_args if args.mpirun_args is not None else '--oversubscribe')
        total = None   # local: oversubscribed, correctness only
    with_eight = total is None or total >= 8
    if args.np is None:
        args.np = [1, 2, 3, 4, 6] + ([8] if with_eight else [])
    if args.timing_np is None:
        args.timing_np = [4, 6] + ([8] if with_eight else [])
    if total is not None and max(args.np + (args.timing_np if timing else [])) > total:
        parser.error(f'The checked hostfile has {total} slots; P must be <= {total} in cluster mode.')
    if not with_eight:
        print('P = 8 skipped: fewer than 8 real slots (see part0/config/cluster.local.sh.example).',
              flush=True)

    stamp = datetime.now(timezone.utc)
    out = args.out or ROOT/'part3'/'results'/'runs'/stamp.strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=False)
    fields = out/'fields'
    fields.mkdir()
    calls, rows, timings = [], [], []

    def run(command, summary=True):
        p = subprocess.run(command, capture_output=True, text=True, timeout=3600)
        portable = [Path(a).name if a in (serial_exe, strips_exe, blocks_exe) else
                    (Path(a).relative_to(out).as_posix() if a.startswith(str(out)) else a)
                    for a in command]
        calls.append(dict(command=portable, returncode=p.returncode,
                          stdout=p.stdout.strip(), stderr=p.stderr.strip()))
        if p.returncode:
            raise RuntimeError(f'{" ".join(portable)} failed:\n{p.stderr.strip()}')
        if not summary:
            return p.stdout
        return dict(token.split('=', 1) for token in p.stdout.strip().splitlines()[-1].split())

    def mpirun(exe, decomp, P, *options):
        return ['mpirun', '-np', str(P), *extra, exe, '--decomp', decomp, *options]

    failures = 0
    try:
        # Stage 1: bit-for-bit comparisons against the serial reference.
        for case in args.cases.split(','):
            time_args = ['--T', str(args.T)] if case == 'V' else ['--steps', str(args.steps)]
            for N in args.N:
                common = ['--case', case, '--N', str(N), '--r', str(args.r), *time_args]
                ref_path = fields/f'serial_case{case}_N{N}.bin'
                ref = run([serial_exe, '--decomp', 'serial', *common, '--out', str(ref_path)])
                ref_bytes = ref_path.read_bytes()
                for P in args.np:
                    Py, Px = dims_create(P)
                    if N-1 < Py:
                        continue   # each block needs at least one interior row and column
                    path = fields/f'blocks_case{case}_N{N}_P{P}.bin'
                    got = run(mpirun(blocks_exe, 'blocks', P, *common, '--out', str(path)))
                    if not path.is_file():
                        raise RuntimeError(f'{path.name} missing: rank 0 must run on the launching VM.')
                    got_bytes = path.read_bytes()
                    identical = got_bytes == ref_bytes
                    mismatched = [k for k in SAME if ref.get(k) != got.get(k)]
                    ok = identical and not mismatched and (int(got['Py']), int(got['Px'])) == (Py, Px)
                    failures += not ok
                    uneven = (N-1) % Py != 0 or (N-1) % Px != 0
                    rows.append(dict(case=case, N=N, P=P, Py=got['Py'], Px=got['Px'], nodes=int(got['nodes']),
                                     uneven_blocks=uneven, bytes=len(ref_bytes), identical=identical,
                                     serial_field=ref_path.name,
                                     serial_sha256=hashlib.sha256(ref_bytes).hexdigest(),
                                     blocks_field=path.name,
                                     blocks_sha256=hashlib.sha256(got_bytes).hexdigest(),
                                     summary_mismatch=' '.join(mismatched), steps=got['steps'],
                                     t_total=got['t_total'], t_comp=got['t_comp'], t_comm=got['t_comm'],
                                     result='PASS' if ok else 'FAIL'))
                    print(f"{'PASS' if ok else 'FAIL'}  case={case} N={N:<4} P={P} grid={got['Py']}x{got['Px']} "
                          f"nodes={got['nodes']} uneven={'yes' if uneven else 'no '} identical={identical}"
                          + (f" mismatch={mismatched}" if mismatched else ''), flush=True)

        # Stage 2a: halo-debugging transcripts (2x2 and 3x2 grids, N=8, one step, Case 1).
        with (out/'debug_halo.txt').open('w', encoding='utf-8') as f:
            for P in [p for p in (4, 6, 8) if p <= max(args.np)]:
                text = run(mpirun(blocks_exe, 'blocks', P, '--case', '1', '--N', '8', '--r', str(args.r),
                                  '--steps', '1', '--debug-print'), summary=False)
                f.write(f'$ mpirun -np {P} heat_blocks --decomp blocks --case 1 --N 8 --r {args.r} '
                        f'--steps 1 --debug-print\n{text}\n')

        # Stage 2b: report figures.
        decomposition_figure(out)
        Nf, Pf = args.figure_N, max(args.np)
        Py, Px = dims_create(Pf)
        fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.9), constrained_layout=True)
        for ax, case in zip(axes, ['1', '2']):
            common = ['--case', case, '--N', str(Nf), '--r', str(args.r), '--steps', str(args.figure_steps)]
            ref_path, path = fields/f'figure_serial_case{case}.bin', fields/f'figure_blocks_case{case}.bin'
            run([serial_exe, '--decomp', 'serial', *common, '--out', str(ref_path)])
            run(mpirun(blocks_exe, 'blocks', Pf, *common, '--out', str(path)))
            if path.read_bytes() != ref_path.read_bytes():
                failures += 1
                print(f'FAIL  figure run case={case} differs from serial')
            u = np.fromfile(path, dtype='<f8').reshape(Nf+1, Nf+1)
            if not np.isfinite(u).all() or u.min() < 0 or u.max() > 1:
                raise ValueError('Stable blocks field violates [0,1]')
            im = ax.imshow(u, origin='lower', extent=[0, 1, 0, 1], vmin=0, vmax=1, cmap='inferno')
            for cy in range(1, Py):
                ax.axhline((split(cy, Py, Nf)[0]-.5)/Nf, color='cyan', lw=.8, ls='--')
            for cx in range(1, Px):
                ax.axvline((split(cx, Px, Nf)[0]-.5)/Nf, color='cyan', lw=.8, ls='--')
            ax.set(title=f'Case {case}: blocks {Py}x{Px} (P={Pf}), {args.figure_steps} steps',
                   xlabel='x', ylabel='y')
            fig.colorbar(im, ax=ax, shrink=.75)
        fig.suptitle('Dashed lines: block boundaries. Each field is byte-identical to the serial reference.',
                     fontsize=9)
        fig.savefig(out/'cases.png', dpi=170)
        plt.close(fig)

        # Stage 3: strips vs blocks timing (the "then check" of the Part 3 report question).
        if timing:
            for rep in range(1, args.timing_reps+1):
                for N in args.timing_N:
                    for P in args.timing_np:
                        for decomp, exe in (('strips', strips_exe), ('blocks', blocks_exe)):
                            s = run(mpirun(exe, decomp, P, '--case', '1', '--N', str(N), '--r', str(args.r),
                                           '--steps', str(args.timing_steps)))
                            steps = int(s['steps'])
                            timings.append(dict(rep=rep, decomp=decomp, P=P, N=N, nodes=int(s['nodes']),
                                                grid=f"{s.get('Py', P)}x{s.get('Px', 1)}", steps=steps,
                                                t_total=s['t_total'], t_comp=s['t_comp'], t_comm=s['t_comm']))
                            print(f"TIME  rep={rep} {decomp:<6} P={P} N={N:<5} "
                                  f"comm/step={float(s['t_comm'])/steps*1e3:9.2f} ms "
                                  f"comp/step={float(s['t_comp'])/steps*1e3:8.3f} ms", flush=True)
    finally:
        (out/'raw_runs.json').write_text(json.dumps(calls, indent=2)+'\n', encoding='utf-8')

        def write(name, data):
            with (out/name).open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)
        if rows:
            write('compare.csv', rows)
        if timings:
            write('timing.csv', timings)
            summary = []
            for N in args.timing_N:
                for P in args.timing_np:
                    for decomp in ('strips', 'blocks'):
                        sel = [t for t in timings if t['N'] == N and t['P'] == P and t['decomp'] == decomp]
                        if not sel:
                            continue
                        per = lambda k: [float(t[k])/t['steps'] for t in sel]
                        summary.append(dict(decomp=decomp, P=P, N=N, grid=sel[0]['grid'], reps=len(sel),
                                            nodes=sel[0]['nodes'],
                                            median_total_ms_per_step=statistics.median(per('t_total'))*1e3,
                                            median_comm_ms_per_step=statistics.median(per('t_comm'))*1e3,
                                            min_comm_ms_per_step=min(per('t_comm'))*1e3,
                                            max_comm_ms_per_step=max(per('t_comm'))*1e3,
                                            median_comp_ms_per_step=statistics.median(per('t_comp'))*1e3))
            write('timing_summary.csv', summary)
            # Row 1: halo exchange per step (the quantity the Task 8.2 model predicts), with
            # the min-max spread of the repetitions. Row 2: total per step. Log scale, so
            # N = 512 stays visible next to N = 8192.
            fig, axes = plt.subplots(2, len(args.timing_np), figsize=(5*len(args.timing_np), 7.0),
                                     constrained_layout=True, squeeze=False)
            for col, P in enumerate(args.timing_np):
                for row, (key, what) in enumerate((('median_comm_ms_per_step', 'halo exchange'),
                                                   ('median_total_ms_per_step', 'total'))):
                    ax = axes[row][col]
                    for k, decomp in enumerate(('strips', 'blocks')):
                        sel = {s['N']: s for s in summary if s['P'] == P and s['decomp'] == decomp}
                        Ns = [n for n in args.timing_N if n in sel]
                        xs = np.array([args.timing_N.index(n) for n in Ns], dtype=float)+(k-.5)*.38
                        med = np.array([sel[n][key] for n in Ns])
                        err = None
                        if row == 0:
                            err = np.array([med-[sel[n]['min_comm_ms_per_step'] for n in Ns],
                                            np.array([sel[n]['max_comm_ms_per_step'] for n in Ns])-med])
                        grid = sel[Ns[0]]['grid'] if Ns else ''
                        ax.bar(xs, med, .38, yerr=err, capsize=3, label=f'{decomp} ({grid})')
                    ax.set_yscale('log')
                    ax.set_xticks(np.arange(len(args.timing_N)), [str(n) for n in args.timing_N])
                    ax.set(title=f'P={P}: {what} per step (median of {args.timing_reps})', xlabel='N',
                           ylabel='ms per step (log scale)')
                    ax.legend()
            fig.savefig(out/'timing.png', dpi=170)
            fig.savefig(out/'timing.pdf')
            plt.close(fig)
        version = subprocess.run(['mpirun', '--version'], capture_output=True, text=True).stdout
        sha = lambda p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
        meta = dict(utc=stamp.isoformat(), mode='cluster' if args.cluster else 'local',
                    mpirun_args=extra, platform=platform.system(), architecture=platform.machine(),
                    mpirun_version=version.strip().splitlines()[0] if version else None,
                    serial_source_sha256=sha('part1/heat_serial.cpp'),
                    strips_source_sha256=sha('part2/heat_mpi.cpp'),
                    blocks_source_sha256=sha('part3/heat_blocks.cpp'),
                    parameters=dict(np=args.np, N=args.N, cases=args.cases, steps=args.steps, T=args.T,
                                    r=args.r, figure_N=args.figure_N, figure_steps=args.figure_steps,
                                    timing=timing, timing_np=args.timing_np, timing_N=args.timing_N,
                                    timing_steps=args.timing_steps, timing_reps=args.timing_reps),
                    cluster_slots=hosts,
                    scope='Correctness comparison plus a small strips-vs-blocks timing check; '
                          'full scaling study belongs to Part 4')
        (out/'metadata.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')
        # Every field file is evidence too: hash it so the archive can be re-checked offline.
        names = [n for n in PUBLISHED if (out/n).is_file()]
        names += sorted(p.relative_to(out).as_posix() for p in fields.glob('*.bin'))
        manifest = [dict(file=name, bytes=(out/name).stat().st_size,
                         sha256=hashlib.sha256((out/name).read_bytes()).hexdigest())
                    for name in names]
        (out/'manifest.json').write_text(json.dumps(dict(published_files=manifest), indent=2)+'\n',
                                         encoding='utf-8')

    total = len(rows)
    spread = sum(1 for r in rows if r['P'] > 1 and r['nodes'] > 1)
    print(f'\n{total-failures}/{total} comparisons bit-for-bit identical; '
          f'{spread} multi-process runs spanned more than one machine.')
    if timings:
        print(f'{len(timings)} timing runs recorded (timing_summary.csv).')
    print(f'Results: {out}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
