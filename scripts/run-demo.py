#!/usr/bin/env python3
"""Plan, or explicitly run, the two required live-demo cases on three guests."""
import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'part4'))
import common as C
import run_experiments as R


def plot(folder, N, layout):
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(9, 4), constrained_layout=True)
    for case, ax in zip((1, 2), axes):
        field = np.fromfile(folder/f'case{case}-{layout}.bin', dtype='<f8').reshape(N+1, N+1)
        image = ax.imshow(field, origin='lower', extent=[0, 1, 0, 1], cmap='inferno', vmin=0, vmax=1)
        ax.set(title=f'Case {case}, {layout}, N={N}', xlabel='x', ylabel='y')
    fig.colorbar(image, ax=axes, label='Temperature u')
    fig.savefig(folder/'cases.png', dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='Actually launch MPI; default prints a plan')
    parser.add_argument('--N', type=int, default=32)
    parser.add_argument('--P', type=int, default=3)
    parser.add_argument('--steps', type=int, default=40)
    parser.add_argument('--decomp', choices=['strips', 'blocks'], default='blocks')
    args = parser.parse_args()
    C.require(args.N >= 4 and args.P >= 3 and args.N-1 >= args.P and args.steps > 0,
              'Use N>=4, P>=3, N-1>=P and positive steps')
    if not args.run:
        print(f'PLAN ONLY: Cases 1 and 2, N={args.N}, P={args.P}, {args.steps} steps, '
              f'r=0.24, {args.decomp}, map-by node. Serial byte comparisons and heat maps. Add --run.')
        return
    C.require(os.name == 'posix' and getpass.getuser() == 'mpi',
              'Launch the live demo as mpi inside Ubuntu; preview works offline')
    hosts = R.prepare_hosts()
    C.require(args.P <= sum(h['slots'] for h in hosts), 'P exceeds real slots')
    C.require(len(set(C.placement([h['slots'] for h in hosts], args.P, 'node'))) == 3,
              'Demo must use all three VMs')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = ROOT/'output'/('demo-'+stamp)
    folder.mkdir(parents=True, exist_ok=False)
    records = []
    def run(command):
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        records.append(dict(command=command, returncode=result.returncode,
                            stdout=result.stdout, stderr=result.stderr))
        C.write_json(folder/'raw_runs-private.json', records)
        print(result.stdout, end='', flush=True)
        if result.stderr:
            print(result.stderr, file=sys.stderr, end='', flush=True)
        C.require(result.returncode == 0, 'Demo invocation failed; original output retained')
        return result.stdout
    binary = 'heat_mpi' if args.decomp == 'strips' else 'heat_blocks'
    for case in (1, 2):
        common = ['--case', str(case), '--N', str(args.N), '--steps', str(args.steps), '--r', '0.24']
        serial = folder/f'case{case}-serial.bin'
        parallel = folder/f'case{case}-{args.decomp}.bin'
        run([str(ROOT/'build/heat'), '--decomp', 'serial', *common, '--out', str(serial)])
        output = run(R.mpi(hosts, args.P, 'node', ROOT/'build'/binary,
                           ['--decomp', args.decomp, *common, '--out', str(parallel)]))
        summary = dict(token.split('=', 1) for token in output.strip().splitlines()[-1].split())
        C.require(int(summary['nodes']) == 3 and int(summary['P']) == args.P, 'Demo did not span all three guests')
        C.require(serial.read_bytes() == parallel.read_bytes(), 'Demo field differs from serial')
        print(f'PASS Case {case}: exact serial/{args.decomp} field on three VMs', flush=True)
    plot(folder, args.N, args.decomp)
    C.write_json(folder/'demo.json', dict(N=args.N, P=args.P, steps=args.steps, r=.24,
                 layout=args.decomp, cases=[1,2], nodes=3, byte_comparisons='PASS',
                 scope='Demonstration run, not a new performance campaign; raw MPI warnings retained for review'))
    print('Show heat map:', folder/'cases.png')
    print('Save this folder as demonstration evidence; live presentation itself is performed by the team.')


if __name__ == '__main__':
    main()
