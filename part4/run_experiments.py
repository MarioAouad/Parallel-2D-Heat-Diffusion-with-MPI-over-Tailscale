"""Restartable Part 4 campaign. Use --plan first; only --run launches the cluster."""
import argparse
import csv
import getpass
from datetime import datetime, timezone
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import common as C

ROOT=C.ROOT
TRANSPORT=['--mca','pml','ob1','--mca','btl','tcp,self',
           '--mca','btl_tcp_if_include','tailscale0','--mca','oob_tcp_if_include','tailscale0']
PROBE="import os,socket,json;print(json.dumps({'rank':int(os.environ['OMPI_COMM_WORLD_RANK']),'host':socket.gethostname()}))"


def ints(s):
    return [int(v) for v in s.split(',')]


def mpi(hosts,P,mapping,executable,options=()):
    # Rank ordering is explicit, rather than inferred from a mapper's default.
    return ['mpirun','-np',str(P),'--host',','.join(f"{h['address']}:{h['slots']}" for h in hosts),
            '--map-by',mapping,'--rank-by',mapping,'--bind-to','core','--nooversubscribe',
            '--wdir',str(ROOT),'--mca','plm_rsh_args','-o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=15',
            *TRANSPORT,str(executable),*options]


def remote(host,command):
    return (command if host['local'] else ['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
            '-o','ConnectTimeout=15','mpi@'+host['address'],shlex.join(command)])


def inventory_program():
    code=("import json,hashlib,platform,pathlib,subprocess,socket,os;"
          f"root=pathlib.Path({str(ROOT)!r});"
          "get=lambda c:subprocess.check_output(c,cwd=root,text=True).strip();"
          "digest=lambda p:hashlib.sha256((root/p).read_bytes()).hexdigest();"
          f"print(json.dumps(dict(hostname=socket.gethostname(),vcpus=int(get(['nproc'])),"
          "platform=platform.platform(),cpu=get(['lscpu']),ram=get(['free','-b']),compiler=get(['g++','--version']),"
          "build_recipe=get(['make','-Bn','serial','strips','blocks','build/mpi_pingpong']),"
          "busy=subprocess.run(['pgrep','-x','heat|heat_mpi|heat_blocks|mpi_pingpong'],capture_output=True,text=True).stdout,"
          "mpi=get(['mpirun','--version']),revision=get(['git','rev-parse','HEAD']),"
          "dirty=get(['git','status','--porcelain']),"
          f"sources={{p:digest(p) for p in {C.SOURCES!r}}},"
          "binaries={p:digest('build/'+p) for p in ['heat','heat_mpi','heat_blocks','mpi_pingpong']})))")
    return code


def prepare_hosts():
    subprocess.run(['bash','-c',f'source {shlex.quote(str(ROOT/"part0/config/cluster.sh"))}'],check=True)
    spec=importlib.util.spec_from_file_location('slots',ROOT/'part0/config/check_slots.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    counts=module.check_slots(ROOT/'part0/config/hosts')
    local=module.local_tailscale_address()
    addresses=[s.split()[0] for s in (ROOT/'part0/config/hosts').read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
    hosts=[dict(h,address=a,local=a==local) for h,a in zip(counts,addresses)]
    C.require(len(hosts)==3 and sum(h['local'] for h in hosts)==1,'Launcher must be one of the configured VMs')
    C.require(all(h['slots']>=2 for h in hosts),'Calibration requires two real slots per VM')
    code=inventory_program()
    for h in hosts:
        result=subprocess.run(remote(h,['python3','-c',code]),capture_output=True,text=True,timeout=60,check=True)
        h['inventory']=json.loads(result.stdout)
        C.require(h['inventory']['vcpus']==h['vcpus'],'CPU count changed during preflight')
        C.require(not h['inventory']['busy'].strip(),h['host']+' still has a solver/benchmark running; inspect it before starting/resuming')
        C.require(not h['inventory']['dirty'],h['host']+' has uncommitted changes; synchronize a committed revision')
    C.require(len({h['inventory']['hostname'] for h in hosts})==3,'Guests must have distinct hostnames')
    for key in ('revision','sources','mpi'):
        C.require(all(h['inventory'][key]==hosts[0]['inventory'][key] for h in hosts),'VMs differ in '+key)
    C.require(hosts[0]['inventory']['sources']=={p:C.sha(ROOT/p) for p in C.SOURCES},'Launching source differs from guest source')
    return hosts


class Campaign:
    def __init__(self,folder,hosts,parameters,executor=None):
        self.folder,self.hosts,self.p=Path(folder),hosts,parameters
        self.executor=executor or subprocess.run
        self.state_path=self.folder/'state.json'
        self.state=json.loads(self.state_path.read_text()) if self.state_path.exists() else dict(completed={})
        self.replacements={h['address']:h['host'] for h in hosts}
        self.replacements.update({h['inventory']['hostname']:h['host'] for h in hosts})
        raw=self.folder/'raw_runs.jsonl'
        self.sequence=len(raw.read_text(encoding='utf-8').splitlines()) if raw.exists() else 0

    def public(self,value):
        text=json.dumps(value)
        for old,new in sorted(self.replacements.items(),key=lambda t:-len(t[0])):
            text=text.replace(old,new)
        return json.loads(re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b','[address]',text))

    def invoke(self,task_id,command,allow_stderr=False):
        start=time.monotonic()
        try:
            result=self.executor(command,capture_output=True,text=True,timeout=3600)
        except subprocess.TimeoutExpired as error:
            decode=lambda v: v.decode('utf-8',errors='replace') if isinstance(v,bytes) else (v or '')
            result=subprocess.CompletedProcess(command,124,decode(error.stdout),decode(error.stderr)+'\nTIMEOUT: local launcher exceeded 3600 seconds.')
        self.sequence+=1
        record=dict(run_id=self.sequence,task_id=task_id,command=command,returncode=result.returncode,
                    stdout=result.stdout,stderr=result.stderr,utc=datetime.now(timezone.utc).isoformat(),
                    wall_seconds=time.monotonic()-start)
        # Flush every invocation: even a crash before parsing preserves its original output.
        for path,value in [(self.folder/'private/raw_runs.jsonl',record),
                           (self.folder/'raw_runs.jsonl',self.public(record))]:
            path.parent.mkdir(parents=True,exist_ok=True)
            with path.open('a',encoding='utf-8') as f:
                f.write(json.dumps(value,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
        C.require(result.returncode==0,f'{task_id} failed; original output retained in raw_runs.jsonl')
        C.require(allow_stderr or not result.stderr.strip(),f'{task_id}: unexpected stderr; inspect raw_runs.jsonl')
        return self.public(record)

    def complete(self,task_id,value):
        self.state['completed'][task_id]=value
        C.write_json(self.state_path,self.state)

    def maps(self):
        for mapping in ('node','slot'):
            for P in self.p['P']:
                key=f'placement:{mapping}:{P}'
                if key in self.state['completed']:continue
                record=self.invoke(key,mpi(self.hosts,P,mapping,'python3',['-c',PROBE]))
                rows=sorted([json.loads(line) for line in record['stdout'].splitlines()],key=lambda r:r['rank'])
                expected=[self.hosts[i]['host'] for i in C.placement([h['slots'] for h in self.hosts],P,mapping)]
                C.require([r['rank'] for r in rows]==list(range(P)) and [r['host'] for r in rows]==expected,
                          'Actual MPI rank placement differs from declared '+key)
                self.complete(key,dict(run_id=record['run_id'],rank_hosts=expected))

    def calibrate(self):
        for rep in range(1,self.p['calibration_reps']+1):
            for a in range(3):
                for b in range(a,3):
                    key=f'calibration:{a}:{b}:{rep}'
                    if key in self.state['completed']:continue
                    selected=[dict(self.hosts[i],slots=2) for i in ([a] if a==b else [a,b])]
                    command=mpi(selected,2,'node',ROOT/'build/mpi_pingpong',
                                ['--label',f'heat{a+1}-heat{b+1}','--min-bytes','8',
                                 '--max-bytes',str(self.p['calibration_max_bytes']),
                                 '--iterations',str(self.p['calibration_iterations']),'--warmup','1'])
                    record=self.invoke(key,command,allow_stderr=True)
                    rows=list(csv.DictReader(io.StringIO(record['stdout'])))
                    C.check_pingpong_diagnostics(record['stderr'],rows)
                    for row in rows:
                        C.require((row['host0'],row['host1'])==(f'heat{a+1}',f'heat{b+1}'),'Calibration host placement differs')
                        C.require(float(row['oneway_s'])>0 and math.isfinite(float(row['oneway_s'])) and
                                  math.isclose(float(row['roundtrip_s']),2*float(row['oneway_s']),rel_tol=1e-10),
                                  'Invalid ping-pong measurement')
                    C.fit_link(rows,self.p['calibration_max_bytes'])
                    self.complete(key,dict(run_id=record['run_id'],rep=rep,link=f'heat{a+1}|heat{b+1}',rows=rows))
                    print('CALIBRATION',key,flush=True)

    def heat(self):
        tasks=C.design(self.p,[h['slots'] for h in self.hosts])
        for index,task in enumerate(tasks,1):
            key=task['id']
            if key in self.state['completed']:continue
            options=['--decomp',task['decomp'],'--case','1','--N',str(task['N']),
                     '--steps',str(self.p['steps']),'--r',str(self.p['r'])]
            if task['experiment']=='baseline':
                host=next(h for h in self.hosts if h['host']==task['host'])
                command=remote(host,[str(ROOT/'build/heat'),*options]);nodes=1
            else:
                binary='heat_mpi' if task['decomp']=='strips' else 'heat_blocks'
                command=mpi(self.hosts,task['P'],task['mapping'],ROOT/'build'/binary,options)
                nodes=len(set(self.state['completed'][f"placement:{task['mapping']}:{task['P']}"]['rank_hosts']))
            record=self.invoke(key,command)
            row=C.parse_summary(record['stdout'],task,self.p,nodes)
            self.complete(key,dict(row,run_id=record['run_id']))
            print(f"MEASURE {index}/{len(tasks)} {key} total/step={row['seconds_per_step']:.6g}s",flush=True)

    def network(self,stage):
        for host in self.hosts:
            key=f'network:{stage}:{host["host"]}'
            if key in self.state['completed']:continue
            # Observations, never a promise of route continuity.
            record=self.invoke(key,remote(host,['tailscale','status']),allow_stderr=True)
            self.complete(key,dict(run_id=record['run_id']))

    def export(self):
        completed=self.state['completed']
        measurements=[v for v in completed.values() if 'experiment' in v]
        calibration=[]
        for key,v in completed.items():
            if key.startswith('calibration:'):
                calibration.extend(dict(row,link=v['link'],rep=v['rep'],run_id=v['run_id']) for row in v['rows'])
        C.write_csv(self.folder/'measurements.csv',measurements)
        C.write_csv(self.folder/'calibration.csv',calibration)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',action='store_true',help='print the experiment plan without VM access (default)')
    parser.add_argument('--run',action='store_true',help='launch measured cluster work (otherwise print a plan)')
    parser.add_argument('--profile',choices=['full','smoke'],default='full')
    parser.add_argument('--slots',type=ints,default=[4,2,2],help='preview only; real run reads checked private configuration')
    parser.add_argument('--steps',type=int)
    parser.add_argument('--reps',type=int)
    parser.add_argument('--P',type=ints)
    parser.add_argument('--calibration-max-bytes',type=int)
    parser.add_argument('--calibration-iterations',type=int)
    parser.add_argument('--recalibrate',action='store_true',help='with --resume: redo all calibration sweeps; keep prior raw attempts')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--resume',type=Path,help='continue an interrupted, unreviewed campaign without repeating completed tasks')
    parser.add_argument('--notes',default='',help='required for --run: host power/load/Wi-Fi conditions; no credentials')
    args=parser.parse_args()
    C.require(not (args.plan and args.run),'Choose --plan or --run')
    if not args.run:
        C.require(len(args.slots)==3 and min(args.slots)>=2,'Preview needs three slot counts >=2')
        p=C.default_parameters(sum(args.slots),args.profile=='smoke')
        for key in ('steps','reps','P','calibration_max_bytes','calibration_iterations'):
            if getattr(args,key) is not None:p[key]=getattr(args,key)
        tasks=C.design(p,args.slots)
        print(json.dumps(dict(parameters=p,heat_invocations=len(tasks),
              counts={name:sum(t['experiment']==name for t in tasks) for name in ('baseline','strong','weak')},
              calibration_sweeps=6*p['calibration_reps'],placement_probes=2*len(p['P']),
              note='Preview only: no VM access, no measurements. --run --notes is required.'),indent=2))
        return
    C.require(args.notes.strip(),'Describe laptop power, background load and Wi-Fi with --notes')
    C.require(os.name=='posix' and getpass.getuser()=='mpi','Launch real campaigns as mpi inside an Ubuntu guest; --plan works on Windows')
    hosts=prepare_hosts()
    folder=(args.resume or args.out or ROOT/'part4/results/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')).resolve()
    C.require(folder.is_relative_to((ROOT/'part4/results/runs').resolve()),'Real campaign output/resume must stay under part4/results/runs; reviewed archives are immutable')
    if args.resume:
        C.require(args.recalibrate or (args.calibration_max_bytes is None and args.calibration_iterations is None),'Use --recalibrate to change calibration on resume')
        C.require(not any(getattr(args,k) is not None for k in ('steps','reps','P')),'Resume uses the saved plan, not new overrides')
        meta=json.loads((folder/'metadata.json').read_text());p=meta['parameters']
        if meta['status']=='complete':
            import verify_results
            try:
                verified=verify_results.verify_study(folder,require_full=p['profile']=='full')
            except (ValueError,OSError,KeyError):
                # A power loss can interrupt final manifest publication. Only this
                # ignored run directory is repairable, never a reviewed archive.
                meta['status']='incomplete'
                print('Finalization needs repair; replaying checkpoints, not completed measurements.',flush=True)
            else:
                print('Already complete and verified; no measurements repeated:',verified,flush=True)
                return
        C.require(meta['revision']==hosts[0]['inventory']['revision'] and
                  meta['sources']==hosts[0]['inventory']['sources'],'Code revision changed; keep campaigns separate')
        C.require([(h['host'],h['slots'],h['vcpus']) for h in hosts]==[(h['host'],h['slots'],h['vcpus']) for h in meta['hosts']],
                  'CPU allocation changed; keep campaigns separate')
        C.require(all(h['inventory']['binaries']==old['inventory']['binaries'] and h['inventory']['mpi']==old['inventory']['mpi']
                      for h,old in zip(hosts,meta['hosts'])),'Binaries/MPI changed since the interrupted run')
    else:
        p=C.default_parameters(sum(h['slots'] for h in hosts),args.profile=='smoke')
        for key in ('steps','reps','P','calibration_max_bytes','calibration_iterations'):
            if getattr(args,key) is not None:p[key]=getattr(args,key)
        C.require(p['steps']>0 and p['reps']>0,'Steps/repetitions must be positive')
        C.require(p['profile']!='full' or C.official_parameters(p,sum(h['slots'] for h in hosts)),'Full profile must cover the assignment matrix with >=3 repetitions and calibration covering halo sizes; use smoke for exploratory subsets')
        C.design(p,[h['slots'] for h in hosts])
        folder.mkdir(parents=True,exist_ok=False)
        meta=dict(schema=1,status='incomplete',mode='cluster',utc=datetime.now(timezone.utc).isoformat(),
                  parameters=p,hosts=hosts,revision=hosts[0]['inventory']['revision'],
                  sources=hosts[0]['inventory']['sources'],transport=TRANSPORT,
                  reference_host='heat1',binding='core',notes=args.notes,
                  model='Task8.2 busiest-rank; measured per-host compute, pairwise half-RTT calibration')
    if args.recalibrate:
        C.require(args.resume,'--recalibrate requires --resume')
        for key in ('calibration_max_bytes','calibration_iterations'):
            if getattr(args,key) is not None:p[key]=getattr(args,key)
    C.require(p['calibration_max_bytes']>=256 and p['calibration_max_bytes']<=16777216 and
              p['calibration_max_bytes'] & (p['calibration_max_bytes']-1)==0 and p['calibration_iterations']>0,'Invalid calibration size/count')
    C.require(os.name=='posix','Real campaigns must run inside an Ubuntu guest; --plan works on Windows')
    import fcntl
    (folder/'private').mkdir(exist_ok=True)
    lock=(folder/'private/campaign.lock').open('a')
    try:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise ValueError('This campaign folder is already in use by another process')
    campaign=Campaign(folder,hosts,p)
    if args.recalibrate:
        campaign.state['completed']={k:v for k,v in campaign.state['completed'].items() if not k.startswith('calibration:')}
        C.write_json(campaign.state_path,campaign.state)
        meta.setdefault('recalibrations',[]).append(dict(utc=datetime.now(timezone.utc).isoformat(),reason=campaign.public(args.notes)))
    if not args.resume:meta=campaign.public(meta)
    meta.setdefault('session_notes',[]).append(campaign.public(args.notes))
    C.write_json(folder/'metadata.json',meta)
    print('Results:',folder,flush=True)
    try:
        campaign.network('before:'+str(len(meta['session_notes'])))
        campaign.maps();campaign.calibrate();campaign.heat()
        campaign.network('after:'+str(len(meta['session_notes'])))
        campaign.export()
        observations=[json.loads(line) for line in (folder/'raw_runs.jsonl').read_text().splitlines() if line]
        meta['failed_attempts_retained']=sum(r['returncode']!=0 for r in observations)
        observations=[r for r in observations if r['task_id'].startswith('network:')]
        meta['network_snapshot_counts']=dict(snapshots=len(observations),
            relay_mentions=sum(r['stdout'].lower().count('relay') for r in observations),
            direct_mentions=sum(r['stdout'].lower().count('direct') for r in observations))
        C.write_json(folder/'metadata.json',meta)
        import analyze
        analyze.analyze(folder,folder/'analysis',replace=True)
        meta['status']='complete';meta['finished_utc']=datetime.now(timezone.utc).isoformat()
        C.write_json(folder/'metadata.json',meta);C.manifest(folder)
        import verify_results
        result=verify_results.verify_study(folder,require_full=p['profile']=='full')
        print('VERIFIED',result,flush=True)
    except BaseException:
        # Don't mark an analysis/verification failure as a completed campaign.
        meta['status']='incomplete';C.write_json(folder/'metadata.json',meta)
        print('Stopped; original output/checkpoints preserved. Resume with --run --resume',folder,flush=True)
        raise
    finally:
        lock.close()


if __name__=='__main__':
    main()
