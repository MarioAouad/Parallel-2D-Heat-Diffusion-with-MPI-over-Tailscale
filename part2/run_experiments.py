"""Part 2 study (checkpoint C2): strips must equal the serial reference bit for bit.

For every case, grid size N and process count P this runs the Part 1 serial
executable and the Part 2 strips executable with identical inputs, compares the
field files byte by byte (the `cmp` test) and compares the summary values. Every
field file is kept under fields/ and listed with its SHA-256 in compare.csv and
manifest.json, so the byte comparison can be repeated offline (verify_results.py). It
also records the halo-debugging transcripts of assignment section 6 and draws the
decomposition and Case 1/2 figures for the report.

Local mode (one VM) oversubscribes the CPU: fine for correctness, never for timing.
Cluster mode uses the team hostfile with --map-by node, so every P >= 2 run spans
at least two VMs; the solver's nodes= field records how many machines took part.
Each invocation writes a new timestamped folder; existing folders are refused.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shlex
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
PUBLISHED = ['compare.csv', 'debug_halo.txt', 'decomposition.png', 'decomposition.pdf',
             'cases.png', 'raw_runs.json', 'metadata.json']


def ints(text):
    return [int(v) for v in text.split(',') if v]


def strip_of(rank, P, N):
    """Same formula as heat_mpi.cpp: first interior row and row count of a rank."""
    base, extra = divmod(N-1, P)
    return 1 + rank*base + min(rank, extra), base + (1 if rank < extra else 0)


def decomposition_figure(out):
    """Report figure: which rank owns which rows, and the ghost rows of one rank."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), constrained_layout=True)
    colours = plt.cm.tab10.colors
    for ax, (N, P) in zip(axes, [(9, 3), (10, 4)]):
        for j in range(N+1):
            for i in range(N+1):
                if j in (0, N) or i in (0, N):
                    ax.plot(i, j, 's', color='0.55', ms=7)
        for p in range(P):
            first, rows = strip_of(p, P, N)
            for j in range(first, first+rows):
                ax.plot(range(1, N), [j]*(N-1), 'o', color=colours[p], ms=7)
            ax.axhspan(first-.5, first+rows-.5, color=colours[p], alpha=.12)
            ax.text(N+.7, first+(rows-1)/2, f'rank {p}\nrows {first}–{first+rows-1}',
                    va='center', fontsize=8, color=colours[p])
        # ghost rows of rank 1: copies of its neighbours' edge rows
        first, rows = strip_of(1, P, N)
        for j in (first-1, first+rows):
            ax.plot([-.4, N+.4], [j, j], '--', color=colours[1], lw=1.2)
        ax.set(title=f'N={N}, P={P}: {N-1} interior rows, (N-1) mod P = {(N-1) % P}',
               xlabel='i (contiguous in memory)', ylabel='j (row)', xlim=(-.8, N+3.2), ylim=(-.8, N+.8))
        ax.set_aspect('equal')
        ax.set_yticks(range(N+1))
    fig.suptitle('Strip decomposition: grey = fixed boundary; dashed = ghost rows held by rank 1', fontsize=10)
    fig.savefig(out/'decomposition.png', dpi=170)
    fig.savefig(out/'decomposition.pdf')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--serial', type=Path, default=ROOT/'build'/'heat')
    parser.add_argument('--mpi', type=Path, default=ROOT/'build'/'heat_mpi')
    parser.add_argument('--np', type=ints, default=[1, 2, 3, 4], help='process counts, e.g. 1,2,3,4')
    parser.add_argument('--N', type=ints, default=[8, 9, 10, 16, 17, 64, 101],
                        help='grid sizes; include N-1 not divisible by P')
    parser.add_argument('--cases', default='1,2,V')
    parser.add_argument('--steps', type=int, default=20, help='fixed steps for Cases 1 and 2')
    parser.add_argument('--T', type=float, default=0.002, help='final time for case V')
    parser.add_argument('--r', type=float, default=0.2)
    parser.add_argument('--figure-N', type=int, default=64)
    parser.add_argument('--figure-steps', type=int, default=500)
    parser.add_argument('--cluster', action='store_true',
                        help='use part0/config/hosts across the VMs (run from ONE VM)')
    parser.add_argument('--mpirun-args', default=None,
                        help='extra mpirun arguments (default local: --oversubscribe)')
    parser.add_argument('--out', type=Path, help='new output directory (must not exist)')
    args = parser.parse_args()

    for exe in (args.serial, args.mpi):
        if not exe.is_file():
            parser.error(f'Missing {exe}. Build first: make serial strips')
    serial_exe, mpi_exe = str(args.serial.resolve()), str(args.mpi.resolve())
    if args.cluster:
        # Render the ignored hostfile from the private configuration (as Part 0 does).
        subprocess.run(['bash', '-c', f'source {shlex.quote(str(ROOT/"part0/config/cluster.sh"))}'],
                       check=True)
        extra = CLUSTER_ARGS
        if max(args.np) > 6:
            parser.error('The team hostfile has 6 slots; P must be <= 6 in cluster mode.')
    else:
        extra = shlex.split(args.mpirun_args if args.mpirun_args is not None else '--oversubscribe')

    stamp = datetime.now(timezone.utc)
    out = args.out or ROOT/'part2'/'results'/'runs'/stamp.strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=False)
    fields = out/'fields'
    fields.mkdir()
    calls, rows = [], []

    def run(command, summary=True):
        p = subprocess.run(command, capture_output=True, text=True, timeout=1800)
        portable = [Path(a).name if a in (serial_exe, mpi_exe) else
                    (Path(a).relative_to(out).as_posix() if a.startswith(str(out)) else a)
                    for a in command]
        calls.append(dict(command=portable, returncode=p.returncode,
                          stdout=p.stdout.strip(), stderr=p.stderr.strip()))
        if p.returncode:
            raise RuntimeError(f'{" ".join(portable)} failed:\n{p.stderr.strip()}')
        if not summary:
            return p.stdout
        last = p.stdout.strip().splitlines()[-1]
        return dict(token.split('=', 1) for token in last.split())

    def mpirun(P, *options):
        return ['mpirun', '-np', str(P), *extra, mpi_exe, '--decomp', 'strips', *options]

    failures = 0
    try:
        # 1. Bit-for-bit comparisons (the C2 requirement).
        for case in args.cases.split(','):
            time_args = ['--T', str(args.T)] if case == 'V' else ['--steps', str(args.steps)]
            for N in args.N:
                common = ['--case', case, '--N', str(N), '--r', str(args.r), *time_args]
                ref_path = fields/f'serial_case{case}_N{N}.bin'
                ref = run([serial_exe, '--decomp', 'serial', *common, '--out', str(ref_path)])
                ref_bytes = ref_path.read_bytes()
                for P in args.np:
                    if P > N-1:
                        continue   # each rank needs at least one interior row
                    path = fields/f'strips_case{case}_N{N}_P{P}.bin'
                    got = run(mpirun(P, *common, '--out', str(path)))
                    if not path.is_file():
                        raise RuntimeError(f'{path.name} missing: rank 0 must run on the launching VM.')
                    got_bytes = path.read_bytes()
                    identical = got_bytes == ref_bytes
                    mismatched = [k for k in SAME if ref.get(k) != got.get(k)]
                    ok = identical and not mismatched
                    failures += not ok
                    uneven = (N-1) % P != 0
                    rows.append(dict(case=case, N=N, P=P, nodes=int(got['nodes']),
                                     uneven_strips=uneven, bytes=len(ref_bytes),
                                     identical=identical,
                                     serial_field=ref_path.name,
                                     serial_sha256=hashlib.sha256(ref_bytes).hexdigest(),
                                     strips_field=path.name,
                                     strips_sha256=hashlib.sha256(got_bytes).hexdigest(), summary_mismatch=' '.join(mismatched),
                                     steps=got['steps'], t_total=got['t_total'],
                                     t_comp=got['t_comp'], t_comm=got['t_comm'],
                                     result='PASS' if ok else 'FAIL'))
                    print(f"{'PASS' if ok else 'FAIL'}  case={case} N={N:<4} P={P} "
                          f"nodes={got['nodes']} uneven={'yes' if uneven else 'no '} "
                          f"identical={identical}" + (f" mismatch={mismatched}" if mismatched else ''),
                          flush=True)

        # 2. Halo-debugging transcripts (assignment section 6: N=8, P=2 then uneven P=3).
        with (out/'debug_halo.txt').open('w', encoding='utf-8') as f:
            for P in (2, 3):
                text = run(mpirun(P, '--case', '2', '--N', '8', '--r', str(args.r), '--steps', '1',
                                  '--debug-print'), summary=False)
                f.write(f'$ mpirun -np {P} heat_mpi --decomp strips --case 2 --N 8 --r {args.r} '
                        f'--steps 1 --debug-print\n{text}\n')

        # 3. Report figures: decomposition layout and strips-computed Case 1/2 fields.
        decomposition_figure(out)
        Nf, Pf = args.figure_N, min(max(args.np), args.figure_N-1)
        fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.9), constrained_layout=True)
        for ax, case in zip(axes, ['1', '2']):
            common = ['--case', case, '--N', str(Nf), '--r', str(args.r), '--steps', str(args.figure_steps)]
            ref_path, path = fields/f'figure_serial_case{case}.bin', fields/f'figure_strips_case{case}.bin'
            run([serial_exe, '--decomp', 'serial', *common, '--out', str(ref_path)])
            run(mpirun(Pf, *common, '--out', str(path)))
            if path.read_bytes() != ref_path.read_bytes():
                failures += 1
                print(f'FAIL  figure run case={case} differs from serial')
            u = np.fromfile(path, dtype='<f8').reshape(Nf+1, Nf+1)
            if not np.isfinite(u).all() or u.min() < 0 or u.max() > 1:
                raise ValueError('Stable strips field violates [0,1]')
            im = ax.imshow(u, origin='lower', extent=[0, 1, 0, 1], vmin=0, vmax=1, cmap='inferno')
            for p in range(1, Pf):
                first, _ = strip_of(p, Pf, Nf)
                ax.axhline((first-.5)/Nf, color='cyan', lw=.8, ls='--')
            ax.set(title=f'Case {case}: strips P={Pf}, {args.figure_steps} steps', xlabel='x', ylabel='y')
            fig.colorbar(im, ax=ax, shrink=.75)
        fig.suptitle('Dashed lines: strip boundaries. Each field is byte-identical to the serial reference.',
                     fontsize=9)
        fig.savefig(out/'cases.png', dpi=170)
        plt.close(fig)
    finally:
        (out/'raw_runs.json').write_text(json.dumps(calls, indent=2)+'\n', encoding='utf-8')
        if rows:
            with (out/'compare.csv').open('w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        version = subprocess.run(['mpirun', '--version'], capture_output=True, text=True).stdout
        meta = dict(utc=stamp.isoformat(), mode='cluster' if args.cluster else 'local',
                    mpirun_args=extra, platform=platform.system(), architecture=platform.machine(),
                    mpirun_version=version.strip().splitlines()[0] if version else None,
                    serial_source_sha256=hashlib.sha256((ROOT/'part1/heat_serial.cpp').read_bytes()).hexdigest(),
                    strips_source_sha256=hashlib.sha256((ROOT/'part2/heat_mpi.cpp').read_bytes()).hexdigest(),
                    parameters=dict(np=args.np, N=args.N, cases=args.cases, steps=args.steps, T=args.T,
                                    r=args.r, figure_N=args.figure_N, figure_steps=args.figure_steps),
                    scope='Correctness comparison; timings are incidental, not Part 4 measurements')
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
    print(f'Results: {out}')
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
