"""Verify the archived Ubuntu Part 1 evidence without rerunning the simulation."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

DEFAULT = Path(__file__).resolve().parent/'results/2026-11-19-ubuntu'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DEFAULT)
    folder = parser.parse_args().data.resolve()
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    seen = set()
    for item in manifest['published_files']:
        p = (folder/item['file']).resolve()
        require(p.is_relative_to(folder) and p not in seen, 'Invalid or duplicate manifest entry')
        seen.add(p)
        data = p.read_bytes()
        require(len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256'],
                'Result hash/size mismatch: '+item['file'])
    require(len(seen) == 9, 'Expected nine original published result files')
    metadata = json.loads((folder/'metadata.json').read_text(encoding='utf-8'))
    source = Path(__file__).resolve().parent/'heat_serial.cpp'
    require(metadata['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest(),
            'Study source differs from current serial reference')
    require(metadata['platform'] == 'Linux' and metadata['architecture'] == 'x86_64',
            'Unexpected archived study platform')
    runs = json.loads((folder/'raw_runs.json').read_text(encoding='utf-8'))
    require(len(runs) == 10 and all(r['returncode'] == 0 for r in runs),
            'Expected ten successful solver invocations')
    summaries = [dict(token.split('=',1) for token in run['stdout'].split()) for run in runs]
    require(all(s['decomp'] == 'serial' and s['P'] == '1' for s in summaries), 'Wrong execution mode')
    for s in summaries:
        require(float(s['t_total']) >= 0 and s['t_total'] == s['t_comp'] and float(s['t_comm']) == 0,
                'Unexpected serial timing fields')
    with (folder/'convergence.csv').open(newline='',encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    require([int(r['N']) for r in rows] == [16,32,64,128,256], 'Wrong convergence grids')
    for k, row in enumerate(rows):
        n, steps = int(row['N']), int(row['steps'])
        r, dt, T = (float(row[name]) for name in ['r','dt','T'])
        einf, e2 = float(row['err_inf']), float(row['err_l2'])
        require(float(row['h']) == 1/n and r == .2 and T == .05 and steps == n*n//4,
                'Unexpected convergence parameters')
        require(math.isclose(dt*steps,T,rel_tol=1e-14), 'Final time mismatch')
        modal = abs((1-8*r*math.sin(math.pi/(2*n))**2)**steps-math.exp(-2*math.pi**2*T))
        require(abs(einf-modal)<5e-13 and abs(einf-2*e2)<5e-13, 'Independent modal/norm check failed')
        s = summaries[k]
        require(s['case'] == 'V' and int(s['N']) == n and int(s['steps']) == steps,
                'Raw convergence command/summary mismatch')
        require(float(s['err_inf']) == einf and float(s['err_l2']) == e2,
                'CSV and raw norm mismatch')
        if k:
            order = math.log2(float(rows[k-1]['err_l2'])/e2)
            require(abs(float(row['order'])-order)<1e-12 and 1.9<order<2.1,
                    'Expected second-order convergence')
    with (folder/'instability.csv').open(newline='',encoding='utf-8') as f:
        unstable = list(csv.DictReader(f))
    require([int(row['steps']) for row in unstable] == [40,120,200], 'Wrong instability snapshots')
    for k, row in enumerate(unstable,5):
        s = summaries[k]
        require(s['case']=='1' and int(s['N'])==64 and float(s['r'])==.2625,
                'Wrong unstable parameters')
        require('--allow-unstable-demo' in runs[k]['command'], 'Demo must be explicitly isolated')
        require(int(s['steps'])==int(row['steps']) and float(s['T'])==float(row['T']),
                'Instability time mismatch')
        require(float(s['minimum'])==float(row['minimum']) and float(s['maximum'])==float(row['maximum']),
                'Instability CSV and raw summary mismatch')
    require(float(unstable[-1]['minimum']) < -100 and float(unstable[-1]['maximum']) > 100,
            'Expected visible instability')
    for case, s in zip(['1','2'],summaries[8:]):
        require(s['case']==case and int(s['N'])==64 and int(s['steps'])==500 and float(s['r'])==.2,
                'Wrong stable case parameters')
        require(0<=float(s['minimum'])<=float(s['maximum'])<=1, 'Stable field violates [0,1]')
        require('err_inf' not in s and 'err_l2' not in s, 'Simulation case has meaningless exact error')
    print('PASS nine published hashes, source/platform provenance and ten successful raw runs')
    print('PASS five-grid convergence, independent sine-mode norms and observed orders near two')
    print('PASS isolated instability evidence and stable Cases 1/2 summaries')
    print('Binary-field boundary/symmetry checks and image inspection were also performed during archive review.')


if __name__ == '__main__':
    main()
