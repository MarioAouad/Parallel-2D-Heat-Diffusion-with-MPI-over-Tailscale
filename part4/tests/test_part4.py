"""Synthetic temporary fixtures test the campaign pipeline; no cluster measurements."""
import contextlib
import csv
import io
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import common as C
import run_experiments as R
import analyze as A
import verify_results as V


def synthetic_hosts():
    sources={p:C.sha(C.ROOT/p) for p in C.SOURCES}
    return [dict(host=f'heat{k+1}',address=f'192.0.2.{k+1}',local=k==0,slots=n,vcpus=n,
                 inventory=dict(hostname=f'guest-private-{k+1}',vcpus=n,sources=sources,
                                revision='synthetic-test-only',dirty='',mpi='TEST DOUBLE, not MPI',
                                binaries={b:'a'*64 for b in ('heat','heat_mpi','heat_blocks','mpi_pingpong')}))
            for k,n in enumerate((4,2,2))]


class FakeCluster:
    def __init__(self,hosts,parameters):
        self.hosts,self.p=hosts,parameters
        self.calls=[]

    def __call__(self,command,**kwargs):
        self.calls.append(command)
        stderr=''
        if command[0]=='ssh':
            host=next(h for h in self.hosts if 'mpi@'+h['address'] in command)
            args=shlex.split(command[-1])
        else:
            host=self.hosts[0];args=command
        if args[:2]==['tailscale','status']:
            text=f"{host['address']} {host['inventory']['hostname']} synthetic-network-observation\n"
        elif command[0]=='mpirun' and R.PROBE in command:
            P=int(command[command.index('-np')+1]);mapping=command[command.index('--map-by')+1]
            ranks=C.placement([h['slots'] for h in self.hosts],P,mapping)
            text='\n'.join(json.dumps(dict(rank=k,host=self.hosts[h]['inventory']['hostname'])) for k,h in enumerate(ranks))
        elif command[0]=='mpirun' and any(Path(t).name=='mpi_pingpong' for t in command):
            addresses=command[command.index('--host')+1].split(',')
            pair=[next(h for h in self.hosts if h['address']==a.split(':')[0]) for a in addresses]
            if len(pair)==1:pair*=2
            a,b=[h['inventory']['hostname'] for h in pair]
            ts,slope=(2e-6,1e-9) if a==b else (.02,1e-6)
            maximum=int(command[command.index('--max-bytes')+1])
            iterations=command[command.index('--iterations')+1]
            label=command[command.index('--label')+1]
            text='label,host0,host1,bytes,iterations,warmup,roundtrip_s,oneway_s,effective_MiB_s\n'
            size=8
            while size<=maximum:
                one=ts+size*slope
                text+=f'{label},{a},{b},{size},{iterations},1,{2*one},{one},{size/2**20/one}\n'
                stderr+=f'Testing {size} bytes: {a} <-> {b}\n'
                size*=2
            stderr+='Finished successfully. CSV contains measured results.\n'
        else:
            def opt(flag):return args[args.index(flag)+1]
            N,steps,r=int(opt('--N')),int(opt('--steps')),float(opt('--r'))
            decomp=opt('--decomp');P=1 if decomp=='serial' else int(command[command.index('-np')+1])
            py,px=C.dims(P) if decomp=='blocks' else (P,1)
            comp=steps*((N-1)**2/P)*1e-6*(1+(len(self.calls)%3)*.01)
            comm=0 if decomp=='serial' else steps*(P-1)*.002
            total=comp+comm+1e-7
            dt=r*(1/N)**2
            text=f'decomp={decomp} P={P} case=1 N={N} steps={steps} r={r} dt={dt} T={steps*dt} t_total={total} t_comp={comp} t_comm={comm} minimum=0 maximum=1'
            if decomp!='serial':
                mapping=command[command.index('--map-by')+1]
                text+=f' nodes={len(set(C.placement([h["slots"] for h in self.hosts],P,mapping)))}'
            if decomp=='blocks':text+=f' Py={py} Px={px}'
        return subprocess.CompletedProcess(command,0,text,stderr)


class DesignTests(unittest.TestCase):
    def test_full_eight_slot_matrix_matches_assignment(self):
        tasks=C.design(C.default_parameters(),[4,2,2])
        self.assertEqual(len(tasks),429)
        self.assertEqual([sum(t['experiment']==x for t in tasks) for x in ('baseline','strong','weak')],[45,288,96])
        self.assertTrue(C.official_parameters(C.default_parameters(),8))

    def test_heterogeneous_capacity_and_rank_order(self):
        self.assertEqual(C.placement([4,2,2],8,'node'),[0,1,2,0,1,2,0,0])
        self.assertEqual(C.placement([4,2,2],8,'slot'),[0,0,0,0,1,1,2,2])
        with self.assertRaises(ValueError):C.placement([4,2,2],9,'node')

    def test_weak_rounding_tracks_interior_work(self):
        for P in range(1,9):
            N=C.weak_N(1024,P)
            self.assertLess(abs((N-1)**2/P/1024**2-1),.001)

    def test_model_known_two_by_two_value_and_zero_communication_p1(self):
        link=dict(valid=True,latency_s=.001,seconds_per_double=1e-7)
        result=C.predict(dict(N=9,P=4,Py=2,Px=2,decomp='blocks'),['h']*4,{'h':1e-6},{'h|h':link})
        self.assertAlmostEqual(result['model_total_s_per_step'],16e-6+2*(.001+4e-7))
        one=C.predict(dict(N=9,P=1,Py=1,Px=1,decomp='blocks'),['h'],{'h':1e-6},{})
        self.assertEqual(one['model_comm_s_per_step'],0)

    def test_fit_recovers_physical_units_and_flags_nonpositive_transfer(self):
        rows=[dict(bytes=2**i,oneway_s=.01+2**i*2e-6) for i in range(3,18)]
        # Small-message estimate includes finite small-payload cost, as documented.
        model=C.fit_link(rows,131072)
        self.assertTrue(model['valid']);self.assertAlmostEqual(model['seconds_per_double'],16e-6,delta=2e-8)
        self.assertFalse(C.fit_link([dict(bytes=2**i,oneway_s=.01) for i in range(3,18)],131072)['valid'])

    def test_remote_inventory_program_compiles(self):
        compile(R.inventory_program(),'<remote-inventory>','exec')

    def test_real_pingpong_progress_and_success_are_accepted(self):
        rows=[dict(bytes='8',host0='heat1',host1='heat2'),dict(bytes='16',host0='heat1',host1='heat2')]
        C.check_pingpong_diagnostics('Testing 8 bytes: heat1 <-> heat2\nTesting 16 bytes: heat1 <-> heat2\nFinished successfully. CSV contains measured results.\n',rows)

    def test_progress_without_final_success_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unexpected ping-pong diagnostic'):
            C.check_pingpong_diagnostics('Testing 8 bytes: heat1 <-> heat1\n',[dict(bytes='8',host0='heat1',host1='heat1')])

    def test_additional_mpi_warning_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError,'Unexpected ping-pong diagnostic'):
            C.check_pingpong_diagnostics('Testing 8 bytes: heat1 <-> heat1\nMPI WARNING\nFinished successfully. CSV contains measured results.\n',[dict(bytes='8',host0='heat1',host1='heat1')])

    def test_progress_wrong_host_or_size_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'Unexpected ping-pong diagnostic'):
            C.check_pingpong_diagnostics('Testing 16 bytes: heat1 <-> heat3\nFinished successfully. CSV contains measured results.\n',[dict(bytes='8',host0='heat1',host1='heat2')])


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.base=Path(cls.temp.name)
        cls.folder=cls.base/'SYNTHETIC-NOT-MEASURED';cls.folder.mkdir()
        cls.hosts=synthetic_hosts();cls.p=C.default_parameters(smoke=True);cls.p['reps']=3
        fake=FakeCluster(cls.hosts,cls.p)
        campaign=R.Campaign(cls.folder,cls.hosts,cls.p,executor=fake)
        meta=dict(mode='synthetic',status='incomplete',parameters=cls.p,hosts=cls.hosts,
                  revision='synthetic-test-only',sources=cls.hosts[0]['inventory']['sources'],
                  transport=R.TRANSPORT,reference_host='heat1',notes='SYNTHETIC fixtures only, no VM measurements')
        meta=campaign.public(meta)
        C.write_json(cls.folder/'metadata.json',meta)
        with contextlib.redirect_stdout(io.StringIO()):
            campaign.network('before:1');campaign.maps();campaign.calibrate();campaign.heat();campaign.network('after:1')
        campaign.export();A.analyze(cls.folder,cls.folder/'analysis')
        meta['status']='complete';C.write_json(cls.folder/'metadata.json',meta);C.manifest(cls.folder)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def copy(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        folder=Path(temp.name)/'fixture';shutil.copytree(self.folder,folder);return folder

    def verify(self,folder):return V.verify_study(folder,require_full=False,allow_synthetic=True)

    def mutate(self,folder,name,column,value):
        rows=C.read_csv(folder/name);rows[0][column]=value;C.write_csv(folder/name,rows);C.manifest(folder)

    def test_complete_synthetic_pipeline_and_official_rejection(self):
        self.assertEqual(self.verify(self.folder)['measurements'],90)
        with self.assertRaisesRegex(ValueError,'Synthetic'):
            V.verify_study(self.folder,require_full=True,allow_synthetic=True)

    def test_wrong_measurement_after_rehash_is_rejected(self):
        folder=self.copy();self.mutate(folder,'measurements.csv','seconds_per_step',999)
        with self.assertRaisesRegex(ValueError,'Measurement CSV/raw mismatch'):self.verify(folder)

    def test_wrong_median_after_rehash_is_rejected(self):
        folder=self.copy();self.mutate(folder,'analysis/summary.csv','median_seconds_per_step',999)
        with self.assertRaisesRegex(ValueError,'Summary does not recompute'):self.verify(folder)

    def test_wrong_model_after_rehash_is_rejected(self):
        folder=self.copy();self.mutate(folder,'analysis/predictions.csv','model_total_s_per_step',999)
        with self.assertRaisesRegex(ValueError,'Prediction does not recompute'):self.verify(folder)

    def test_duplicate_cannot_replace_missing_measurement(self):
        folder=self.copy();rows=C.read_csv(folder/'measurements.csv');rows[-1]=dict(rows[0]);C.write_csv(folder/'measurements.csv',rows);C.manifest(folder)
        with self.assertRaisesRegex(ValueError,'Missing/duplicate'):self.verify(folder)

    def test_raw_calibration_arithmetic_corruption_rejected(self):
        folder=self.copy();rows=[json.loads(line) for line in (folder/'raw_runs.jsonl').read_text().splitlines()]
        record=next(r for r in rows if r['task_id'].startswith('calibration:'))
        cells=record['stdout'].splitlines();parts=cells[1].split(',');parts[-1]='999999';cells[1]=','.join(parts);record['stdout']='\n'.join(cells)
        (folder/'raw_runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));C.manifest(folder)
        with self.assertRaisesRegex(ValueError,'ping-pong arithmetic'):self.verify(folder)

    def test_resume_skips_finished_heat_tasks(self):
        folder=self.copy();fake=FakeCluster(self.hosts,self.p);campaign=R.Campaign(folder,self.hosts,self.p,executor=fake)
        with contextlib.redirect_stdout(io.StringIO()):campaign.heat()
        self.assertEqual(fake.calls,[])
        last=C.design(self.p,[4,2,2])[-1]['id'];del campaign.state['completed'][last];C.write_json(folder/'state.json',campaign.state)
        resume=R.Campaign(folder,self.hosts,self.p,executor=fake)
        with contextlib.redirect_stdout(io.StringIO()):resume.heat()
        self.assertEqual(len(fake.calls),1)

    def test_private_endpoint_records_not_in_public_manifest(self):
        public=(self.folder/'raw_runs.jsonl').read_text()
        self.assertNotIn('192.0.2.',public);self.assertNotIn('guest-private-',public)
        self.assertIn('192.0.2.',(self.folder/'private/raw_runs.jsonl').read_text())
        self.assertFalse(any('private/' in r['file'] for r in json.loads((self.folder/'manifest.json').read_text())['published_files']))

    def test_removed_artifact_fails(self):
        folder=self.copy();(folder/'analysis/strong_time.png').unlink()
        with self.assertRaises(OSError):self.verify(folder)

    def test_timeout_output_is_preserved_without_completing_task(self):
        folder=self.copy()
        def timeout(command,**kwargs):
            raise subprocess.TimeoutExpired(command,3600,output=b'partial output',stderr=b'partial diagnostic')
        campaign=R.Campaign(folder,self.hosts,self.p,executor=timeout)
        with self.assertRaisesRegex(ValueError,'failed'):
            campaign.invoke('test-timeout',['test-command'])
        record=json.loads((folder/'raw_runs.jsonl').read_text().splitlines()[-1])
        self.assertEqual(record['returncode'],124)
        self.assertEqual(record['stdout'],'partial output')
        self.assertIn('TIMEOUT',record['stderr'])
        self.assertNotIn('test-timeout',campaign.state['completed'])

    def test_altered_actual_placement_rejected(self):
        folder=self.copy();rows=[json.loads(line) for line in (folder/'raw_runs.jsonl').read_text().splitlines()]
        r=next(r for r in rows if r['task_id']=='placement:node:2')
        values=[json.loads(line) for line in r['stdout'].splitlines()]
        values[1]['host']='heat1';r['stdout']='\n'.join(json.dumps(v) for v in values)
        (folder/'raw_runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));C.manifest(folder)
        with self.assertRaisesRegex(ValueError,'actual probe'):self.verify(folder)

    def test_changed_calibration_transport_rejected(self):
        folder=self.copy();rows=[json.loads(line) for line in (folder/'raw_runs.jsonl').read_text().splitlines()]
        r=next(r for r in rows if r['task_id'].startswith('calibration:'))
        r['command'][r['command'].index('tcp,self')]='vader,self'
        (folder/'raw_runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows));C.manifest(folder)
        with self.assertRaisesRegex(ValueError,'transport'):self.verify(folder)


class GitPolicyTests(unittest.TestCase):
    def ignored(self,path):
        return subprocess.run(['git','check-ignore','--no-index','-q',path],cwd=C.ROOT).returncode==0

    def test_experimental_and_private_material_ignored(self):
        for path in ('part4/results/runs/future/raw_runs.jsonl','part4/results/analysis-local/test.png',
                     'part4/results/2030-cluster/private/raw_runs.jsonl','output/example.tar.gz',
                     'part0/config/cluster.local.sh','build/heat'):
            with self.subTest(path=path):self.assertTrue(self.ignored(path))

    def test_reviewed_evidence_and_source_remain_publishable(self):
        for path in ('part4/run_experiments.py','part4/results/2030-cluster/measurements.csv',
                     'part4/results/2030-cluster/analysis/strong_time.png',
                     'part2/results/2026-11-21-retained-cluster/fields/serial_case1_N8.bin',
                     'part3/results/2026-11-21-retained-cluster/fields/blocks_case1_N8_P8.bin'):
            with self.subTest(path=path):self.assertFalse(self.ignored(path))


if __name__=='__main__':unittest.main()
