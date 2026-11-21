"""Verify a recorded Part 4 campaign offline. No MPI or SSH is launched."""
import argparse
import collections
import csv
import io
import json
import math
from pathlib import Path
import shlex
import statistics
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as C
import analyze


def check_transport(command,expected):
    def options(tokens):
        return {tokens[i+1]:tokens[i+2] for i,t in enumerate(tokens) if t=='--mca'}
    actual=options(command)
    C.require(all(actual.get(k)==v for k,v in options(expected).items()),'MPI transport differs from recorded calibration')


def equal_tables(actual,expected,message):
    C.require(len(actual)==len(expected),message+' row count')
    for a,b in zip(actual,expected):
        C.require(set(a)==set(b),message+' columns')
        for key,value in b.items():
            if isinstance(value,(float,int)) and not isinstance(value,bool):
                C.require(math.isclose(float(a[key]),value,rel_tol=1e-12,abs_tol=1e-15),message+': '+key)
            else:C.require(str(a[key])==str(value),message+': '+key)


def verify_study(folder,require_full=True,allow_synthetic=False):
    folder=Path(folder).resolve()
    manifest=json.loads((folder/'manifest.json').read_text())
    names=set()
    for item in manifest['published_files']:
        name=item['file'];p=(folder/name).resolve()
        C.require(p.is_relative_to(folder) and not p.is_symlink() and name not in names and
                  'private' not in Path(name).parts,'Unsafe/duplicate manifest entry')
        names.add(name)
        C.require(p.stat().st_size==item['bytes'] and C.sha(p)==item['sha256'],'Hash/size mismatch: '+name)
    required={'metadata.json','state.json','measurements.csv','calibration.csv','raw_runs.jsonl',
              'analysis/summary.csv','analysis/predictions.csv','analysis/calibration_fit.json','analysis/REPORT.md'}
    for name in ('serial_baselines','strong_time','strong_speedup','strong_efficiency','weak_scaling','communication_share'):
        required.update({'analysis/'+name+'.png','analysis/'+name+'.pdf'})
    C.require(required<=names,'Manifest lacks required evidence/analysis')
    meta=json.loads((folder/'metadata.json').read_text());p=meta['parameters'];hosts=meta['hosts']
    C.require(meta['status']=='complete','Campaign incomplete; inspect/resume before submission')
    C.require(meta['mode']=='cluster' or (allow_synthetic and meta['mode']=='synthetic'),'Synthetic/local results are not cluster evidence')
    C.require(meta['mode']=='cluster' or not require_full,'Synthetic data cannot close Part 4')
    C.require(meta.get('notes','').strip(),'Missing operator measurement-condition notes')
    if meta['mode']=='cluster':C.require(meta.get('binding')=='core','Missing binding policy')
    C.require(len(hosts)==3 and [h['host'] for h in hosts]==['heat1','heat2','heat3'],'Invalid host record')
    slots=[h['slots'] for h in hosts]
    C.require(all(isinstance(h['vcpus'],int) and 2<=h['slots']<=h['vcpus'] for h in hosts),'Invalid real CPU capacity')
    C.require(p['steps']>0 and p['reps']>0 and 0<p['r']<=.25,'Invalid fixed-step parameters')
    if require_full:C.require(C.official_parameters(p,sum(slots)),'Missing full assignment matrix/repetitions/stable near-limit r')
    C.require(meta['sources']=={name:C.sha(C.ROOT/name) for name in C.SOURCES},'Source changed since campaign')
    for host in hosts:
        inv=host['inventory']
        if meta['mode']=='cluster':
            C.require(all(inv.get(k) for k in ('platform','cpu','ram','compiler','build_recipe')), 'Missing measured guest hardware/build inventory')
        C.require(inv['sources']==meta['sources'] and inv['revision']==meta['revision'] and not inv['dirty'],
                  'Guest source/revision does not match campaign')
        C.require(inv['vcpus']==host['vcpus'] and inv['mpi']==hosts[0]['inventory']['mpi'],'Guest CPU/MPI changed')
        C.require(set(inv['binaries'])=={'heat','heat_mpi','heat_blocks','mpi_pingpong'} and
                  all(len(v)==64 for v in inv['binaries'].values()),'Missing executable provenance')
    C.require(meta['transport']==['--mca','pml','ob1','--mca','btl','tcp,self','--mca','btl_tcp_if_include',
                                'tailscale0','--mca','oob_tcp_if_include','tailscale0'],'Calibration/solver transport changed')
    raw=[json.loads(line) for line in (folder/'raw_runs.jsonl').read_text().splitlines()]
    if meta['mode']=='cluster':
        C.require(meta.get('failed_attempts_retained')==sum(r['returncode']!=0 for r in raw),'Failed-attempt disclosure differs from raw history')
        observations=[r for r in raw if r['task_id'].startswith('network:')]
        expected_counts=dict(snapshots=len(observations),
            relay_mentions=sum(r['stdout'].lower().count('relay') for r in observations),
            direct_mentions=sum(r['stdout'].lower().count('direct') for r in observations))
        C.require(meta.get('network_snapshot_counts')==expected_counts,'Network snapshot disclosure differs from raw history')
    by_id={r['run_id']:r for r in raw}
    C.require(len(by_id)==len(raw) and set(by_id)==set(range(1,len(raw)+1)),'Duplicate/missing raw invocation ID')
    completed=json.loads((folder/'state.json').read_text())['completed']
    for key,value in completed.items():
        r=by_id.get(value['run_id'])
        C.require(r and r['task_id']==key and r['returncode']==0,'Checkpoint lacks successful raw output')
    tasks=C.design(p,slots)
    rows=C.read_csv(folder/'measurements.csv')
    C.require(len(rows)==len(tasks) and {r['id'] for r in rows}=={t['id'] for t in tasks},'Missing/duplicate measurement configuration')
    by_task={r['id']:r for r in rows}
    for mapping in ('node','slot'):
        for P in p['P']:
            key=f'placement:{mapping}:{P}';value=completed.get(key)
            C.require(value,'Missing rank placement probe')
            expected=[f'heat{i+1}' for i in C.placement(slots,P,mapping)]
            probe=by_id[value['run_id']]
            actual=sorted([json.loads(line) for line in probe['stdout'].splitlines()],key=lambda r:r['rank'])
            C.require([r['rank'] for r in actual]==list(range(P)) and [r['host'] for r in actual]==expected
                      and value['rank_hosts']==expected,'Recorded rank placement disagrees with actual probe')
            command=probe['command']
            for flag,setting in [('--map-by',mapping),('--rank-by',mapping),('-np',str(P)),('--bind-to','core')]:
                C.require(flag in command and command[command.index(flag)+1]==setting,'Placement command mismatch')
    for task in tasks:
        value=completed.get(task['id']);C.require(value,'Missing measurement checkpoint')
        r=by_id[value['run_id']]
        command=r['command']
        if task['experiment']=='baseline':
            if command[0]=='ssh':
                C.require('mpi@'+task['host'] in command,'Baseline executed on wrong guest')
                command=shlex.split(command[-1])
            else:C.require(next(h for h in hosts if h['host']==task['host'])['local'],'Baseline local guest differs')
            C.require(Path(command[0]).name=='heat','Baseline must use the serial executable')
            nodes=1
        else:
            C.require(command[0]=='mpirun' and '--nooversubscribe' in command,'Missing safe MPI launch')
            check_transport(command,meta['transport'])
            probe=by_id[completed[f"placement:{task['mapping']}:{task['P']}"]['run_id']]['command']
            C.require(command[command.index('--host')+1]==probe[probe.index('--host')+1],'Heat host allocation differs from placement probe')
            for flag,setting in [('--map-by',task['mapping']),('--rank-by',task['mapping']),('-np',str(task['P'])),('--bind-to','core')]:
                C.require(command[command.index(flag)+1]==setting,'Heat launch placement differs from probe')
            C.require(all('oversubscribe' not in token or token=='--nooversubscribe' for token in command),'Oversubscribed campaign')
            nodes=len(set(completed[f"placement:{task['mapping']}:{task['P']}"]['rank_hosts']))
        C.require('--out' not in command and '--T' not in command,'Performance run includes output/final-time stepping')
        for flag,setting in [('--case','1'),('--N',str(task['N'])),('--decomp',task['decomp']),
                             ('--steps',str(p['steps'])),('--r',str(p['r']))]:
            C.require(command[command.index(flag)+1]==setting,'Command disagrees with numerical plan')
        expected=dict(C.parse_summary(r['stdout'],task,p,nodes),run_id=r['run_id'])
        if meta['mode']=='cluster':
            C.require(math.isfinite(r['wall_seconds']) and r['wall_seconds'] >= expected['total_s']*(1-1e-8),'Solver loop exceeds captured invocation wall time')
        C.require(not r['stderr'].strip(),'Unexpected heat diagnostic')
        equal_tables([by_task[task['id']]],[expected],'Measurement CSV/raw mismatch')
        C.require(value==expected,'Checkpoint measurement differs from raw summary')
    cal=C.read_csv(folder/'calibration.csv');expected_cal=[]
    for rep in range(1,p['calibration_reps']+1):
        for a in range(3):
            for b in range(a,3):
                key=f'calibration:{a}:{b}:{rep}';value=completed.get(key)
                C.require(value,'Missing calibration repetition/link')
                r=by_id[value['run_id']];command=r['command']
                C.require(r['stderr'].strip()=='Finished successfully. CSV contains measured results.','Unexpected calibration diagnostic')
                for flag,setting in [('-np','2'),('--max-bytes',str(p['calibration_max_bytes'])),
                                     ('--iterations',str(p['calibration_iterations'])),('--map-by','node')]:
                    C.require(command[command.index(flag)+1]==setting,'Calibration command mismatch')
                C.require('--nooversubscribe' in command and all(token in command for token in meta['transport']),
                          'Calibration transport/capacity policy differs')
                check_transport(command,meta['transport'])
                measured=list(csv.DictReader(io.StringIO(r['stdout'])))
                C.require(len(measured)==int(math.log2(p['calibration_max_bytes']))-2,'Incomplete calibration sweep')
                for row in measured:
                    C.require((row['host0'],row['host1'])==(f'heat{a+1}',f'heat{b+1}'),'Calibration hosts differ')
                    C.require(int(row['iterations'])==p['calibration_iterations'] and int(row['warmup'])==1,'Calibration repetition count differs')
                    one,rt=float(row['oneway_s']),float(row['roundtrip_s'])
                    C.require(math.isfinite(one) and one>0 and math.isclose(rt,one*2,rel_tol=1e-10) and
                              math.isclose(float(row['effective_MiB_s']),int(row['bytes'])/2**20/one,rel_tol=1e-8),'Invalid ping-pong arithmetic')
                if meta['mode']=='cluster':
                    C.require(r['wall_seconds'] >= sum(float(t['roundtrip_s'])*int(t['iterations']) for t in measured)*(1-1e-8),'Calibration timings exceed invocation wall time')
                C.fit_link(measured,p['calibration_max_bytes'])
                C.require(value['rows']==measured and value['link']==f'heat{a+1}|heat{b+1}' and value['rep']==rep,'Calibration checkpoint/raw mismatch')
                expected_cal.extend(dict(row,link=value['link'],rep=rep,run_id=r['run_id']) for row in measured)
    equal_tables(cal,expected_cal,'Calibration CSV/raw mismatch')
    for host in hosts:
        C.require(any(k.startswith('network:before:') and k.endswith(':'+host['host']) for k in completed) and
                  any(k.startswith('network:after:') and k.endswith(':'+host['host']) for k in completed),
                  'Missing before/after network observations')
    _,_,summary,links,predictions=analyze.derive(folder)
    equal_tables(C.read_csv(folder/'analysis/summary.csv'),summary,'Summary does not recompute')
    equal_tables(C.read_csv(folder/'analysis/predictions.csv'),predictions,'Prediction does not recompute')
    stored_links=json.loads((folder/'analysis/calibration_fit.json').read_text())
    C.require(set(stored_links)==set(links),'Calibration fit links differ')
    for key,value in links.items():
        equal_tables([stored_links[key]],[value],'Calibration fit does not recompute')
    C.require((folder/'analysis/REPORT.md').read_text(encoding='utf-8')==analyze.report(meta,summary,links,predictions),'Report does not recompute')
    # A second direct calculation checks statistics independently of the grouping output.
    for group in C.read_csv(folder/'analysis/summary.csv'):
        selected=[r for r in rows if all(r[k]==group[k] for k in analyze.GROUP)]
        for field in ('seconds_per_step','communication_fraction','seconds_per_grid_node','seconds_per_interior_node'):
            values=[float(r[field]) for r in selected]
            for label,fn in [('median',statistics.median),('min',min),('max',max)]:
                C.require(math.isclose(float(group[label+'_'+field]),fn(values),rel_tol=1e-12),'Incorrect aggregate arithmetic')
    return dict(profile=p['profile'],official=bool(require_full),measurements=len(rows),
                calibration_sweeps=6*p['calibration_reps'],published_files=len(names),
                failed_attempts_retained=sum(r['returncode']!=0 for r in raw))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--allow-smoke',action='store_true',help='checks partial-matrix smoke evidence, never closes Part 4')
    args=parser.parse_args();print('PASS',verify_study(args.data,require_full=not args.allow_smoke))


if __name__=='__main__':main()
