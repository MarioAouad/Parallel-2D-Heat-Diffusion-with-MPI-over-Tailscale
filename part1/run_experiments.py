"""Run Tasks 7.2 and 6.7 using the final Part 1 executable; preserve each new run."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=ROOT/'build'/('heat.exe' if platform.system() == 'Windows' else 'heat'))
    parser.add_argument('--out', type=Path, help='A new output directory; existing directories are refused')
    args = parser.parse_args()
    exe = args.exe.resolve()
    if not exe.is_file():
        parser.error('Build the executable first: make serial')
    stamp = datetime.now(timezone.utc)
    out = args.out or ROOT/'part1/results/runs'/stamp.strftime('%Y%m%dT%H%M%S%fZ')
    out.mkdir(parents=True, exist_ok=False)
    calls = []

    def run(*options):
        command = [str(exe), '--decomp', 'serial', *map(str, options)]
        p = subprocess.run(command, capture_output=True, text=True, timeout=90)
        # Store portable commands without embedding usernames or absolute run paths.
        portable = [Path(arg).name if arg == str(exe) or str(out) in arg else arg for arg in command]
        calls.append(dict(command=portable, returncode=p.returncode,
                          stdout=p.stdout.strip(), stderr=p.stderr.strip()))
        if p.returncode:
            raise RuntimeError(p.stderr)
        return {k: v for k, v in (token.split('=', 1) for token in p.stdout.split())}

    def write_csv(name, rows):
        with (out/name).open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    try:
        convergence = []
        for N in [16, 32, 64, 128, 256]:
            v = run('--case', 'V', '--N', N, '--r', .2, '--T', .05)
            steps, r = int(v['steps']), float(v['r'])
            modal_error = abs((1-8*r*math.sin(math.pi/(2*N))**2)**steps -
                              math.exp(-2*math.pi**2*float(v['T'])))
            einf, e2 = float(v['err_inf']), float(v['err_l2'])
            if abs(einf-modal_error) > 5e-13 or abs(einf-2*e2) > 5e-13:
                raise ValueError('Discrete sine-mode check failed')
            order = math.log2(convergence[-1]['err_l2']/e2) if convergence else None
            if order is not None and not 1.9 < order < 2.1:
                raise ValueError('Expected second-order convergence')
            convergence.append(dict(N=N, h=1/N, steps=steps, r=r, dt=float(v['dt']),
                                    T=float(v['T']), err_inf=einf, err_l2=e2, order=order))
        write_csv('convergence.csv', convergence)
        fig, ax = plt.subplots(figsize=(6.4, 4.2), constrained_layout=True)
        hs = np.array([v['h'] for v in convergence])
        errors = np.array([v['err_l2'] for v in convergence])
        ax.loglog(hs, errors, 'o-', label='Computed discrete L2 error')
        ax.loglog(hs, errors[-1]*(hs/hs[-1])**2, '--', label='Slope 2')
        ax.set(xlabel='Grid spacing h', ylabel='Error at T=0.05', title='Verification V, r=0.2')
        ax.grid(True, which='both', alpha=.25)
        ax.legend()
        fig.savefig(out/'convergence.png', dpi=170)
        fig.savefig(out/'convergence.pdf')
        plt.close(fig)

        unstable = []
        fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), constrained_layout=True)
        for ax, steps in zip(axes, [40, 120, 200]):
            path = out/f'unstable_{steps}.bin'
            v = run('--case', 1, '--N', 64, '--r', .2625, '--steps', steps,
                    '--allow-unstable-demo', '--out', path)
            u = np.fromfile(path, dtype='<f8').reshape(65,65)
            unstable.append(dict(steps=steps, T=float(v['T']),
                                 minimum=float(u.min()), maximum=float(u.max())))
            im = ax.imshow(u, origin='lower', extent=[0,1,0,1], cmap='coolwarm')
            ax.set(title=f'Step {steps}', xlabel='x', ylabel='y')
            fig.colorbar(im, ax=ax, shrink=.7)
        if unstable[-1]['minimum'] > -100 or unstable[-1]['maximum'] < 100:
            raise ValueError('Expected visible instability')
        write_csv('instability.csv', unstable)
        fig.savefig(out/'instability.png', dpi=170)
        fig.savefig(out/'instability.pdf')
        plt.close(fig)

        fig, axes = plt.subplots(1, 2, figsize=(8, 3.8), constrained_layout=True)
        for ax, case in zip(axes, [1,2]):
            path = out/f'case{case}.bin'
            v = run('--case', case, '--N', 64, '--r', .2, '--steps', 500, '--out', path)
            u = np.fromfile(path, dtype='<f8').reshape(65,65)
            if not np.isfinite(u).all() or u.min() < 0 or u.max() > 1:
                raise ValueError('Stable simulation violates [0,1]')
            im = ax.imshow(u, origin='lower', extent=[0,1,0,1], vmin=0, vmax=1, cmap='inferno')
            ax.set(title=f'Case {case}: 500 steps', xlabel='x', ylabel='y')
            fig.colorbar(im, ax=ax, shrink=.75)
        fig.savefig(out/'cases.png', dpi=170)
        plt.close(fig)
        metadata = dict(utc=stamp.isoformat(), platform=platform.system(), architecture=platform.machine(),
                        scope='Local serial correctness study; timings are not cluster performance results',
                        source_sha256=hashlib.sha256((ROOT/'part1/heat_serial.cpp').read_bytes()).hexdigest())
        (out/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
        print('PASS five-grid convergence and modal cross-check; orders:',
              ', '.join(f"{v['order']:.5f}" for v in convergence[1:]))
        print('PASS isolated instability and stable Cases 1/2; outputs:', out)
    finally:
        (out/'raw_runs.json').write_text(json.dumps(calls, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
