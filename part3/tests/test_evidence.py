"""Part 3 evidence regressions; mocked MPI data is never cluster evidence."""
import contextlib
import csv
import hashlib
import importlib.util
import io
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT/'part3/results/2026-11-19-cluster'


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


VERIFY = load('part3_verify', 'part3/verify_results.py')
RUNNER = load('part3_runner', 'part3/run_experiments.py')


def rehash(folder, name):
    path = folder/'manifest.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    content = (folder/name).read_bytes()
    for entry in data['published_files']:
        if entry['file'] == name:
            entry.update(bytes=len(content), sha256=hashlib.sha256(content).hexdigest())
            break
    path.write_text(json.dumps(data), encoding='utf-8')


def mutate_rows(folder, name, change):
    path = folder/name
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns, rows = reader.fieldnames, list(reader)
    change(rows)
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)
    rehash(folder, name)


class LegacyChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)/'synthetic-test-copy'
        shutil.copytree(LEGACY, self.folder)

    def test_legacy_limitations_are_explicit(self):
        result = VERIFY.verify_study(self.folder)
        self.assertEqual((result['comparisons'], result['timing'], result['warnings']), (90, 36, 2))
        self.assertFalse(result['fields'])
        self.assertFalse(result['p8'])
        with self.assertRaisesRegex(ValueError, 'Original binary fields unavailable'):
            VERIFY.verify_study(self.folder, require_fields=True)
        with self.assertRaisesRegex(ValueError, 'P=4,8 timing'):
            VERIFY.verify_study(self.folder, require_p8=True)

    def test_altered_comparison_time_rejected_after_rehash(self):
        mutate_rows(self.folder, 'compare.csv', lambda r: r[0].update(t_total='999999'))
        with self.assertRaisesRegex(ValueError, 'Comparison CSV/raw mismatch'):
            VERIFY.verify_study(self.folder)

    def test_altered_timing_run_rejected_after_rehash(self):
        mutate_rows(self.folder, 'timing.csv', lambda r: r[0].update(t_comm='999999'))
        with self.assertRaisesRegex(ValueError, 'Timing CSV/raw mismatch'):
            VERIFY.verify_study(self.folder)

    def test_all_aggregate_columns_are_recomputed(self):
        for column in ['median_total_ms_per_step', 'median_comp_ms_per_step', 'median_comm_ms_per_step',
                       'min_comm_ms_per_step', 'max_comm_ms_per_step']:
            with self.subTest(column=column):
                with tempfile.TemporaryDirectory() as temp:
                    folder = Path(temp)/'test'
                    shutil.copytree(LEGACY, folder)
                    mutate_rows(folder, 'timing_summary.csv', lambda r: r[0].update({column: '999999'}))
                    with self.assertRaisesRegex(ValueError, 'does not recompute'):
                        VERIFY.verify_study(folder)

    def test_duplicate_repetition_cannot_replace_a_missing_one(self):
        def change(rows):
            rows[12] = dict(rows[0])
        mutate_rows(self.folder, 'timing.csv', change)
        with self.assertRaisesRegex(ValueError, 'Missing/duplicate timing repetition'):
            VERIFY.verify_study(self.folder)

    def test_modified_halo_is_rejected_even_when_both_records_are_updated(self):
        raw = self.folder/'raw_runs.json'
        runs = json.loads(raw.read_text())
        debug = next(r for r in runs if '--debug-print' in r['command'])
        old = debug['stdout']
        debug['stdout'] = old.replace('0.200000', '0.300000', 1)
        raw.write_text(json.dumps(runs), encoding='utf-8')
        text = self.folder/'debug_halo.txt'
        text.write_text(text.read_text().replace(old, debug['stdout']), encoding='utf-8')
        rehash(self.folder, 'raw_runs.json')
        rehash(self.folder, 'debug_halo.txt')
        with self.assertRaisesRegex(ValueError, 'Debug value disagrees'):
            VERIFY.verify_study(self.folder)

    def test_report_matrix_flag_accepts_a_complete_synthetic_p8_matrix(self):
        # Transform only a temporary fixture; this does not measure or claim real P=8 data.
        raw = self.folder/'raw_runs.json'
        runs = json.loads(raw.read_text())
        for run in runs:
            cmd = run['command']
            if '-np' in cmd and '--out' not in cmd and '--debug-print' not in cmd and cmd[cmd.index('-np')+1] == '6':
                cmd[cmd.index('-np')+1] = '8'
                run['stdout'] = run['stdout'].replace(' P=6 ', ' P=8 ').replace(' Py=3 Px=2 ', ' Py=4 Px=2 ')
        template = next(r for r in runs if '--debug-print' in r['command'])
        record = json.loads(json.dumps(template))
        record['command'][record['command'].index('-np')+1] = '8'
        lines = []
        values = VERIFY.part2_verify.recompute('1',8,.2,1)
        for rank in range(8):
            cy,cx = divmod(rank,2)
            fy,nr = VERIFY.part2_verify.split(cy,4,8)
            fx,nc = VERIFY.part2_verify.split(cx,2,8)
            down,up = ('none' if cy == 0 else rank-2),('none' if cy == 3 else rank+2)
            left,right = ('none' if cx == 0 else rank-1),('none' if cx == 1 else rank+1)
            lines.append(f'rank {rank}: coords ({cy},{cx}) of 4x2 grid, rows {fy}..{fy+nr-1}, cols {fx}..{fx+nc-1}, down={down} up={up} left={left} right={right}')
            for j in range(fy+nr,fy-2,-1):
                kind = 'owned' if fy <= j < fy+nr else ('boundary' if j in (0,8) else 'ghost')
                tokens = ['-' if j in (fy-1,fy+nr) and q in (0,nc+1) else f'{values[j*9+fx-1+q]:.6f}' for q in range(nc+2)]
                lines.append(f'  {kind} j= {j}: '+' '.join(tokens))
        lines.append(template['stdout'].splitlines()[-1].replace(' P=4 Py=2 ', ' P=8 Py=4 '))
        record['stdout'] = '\n'.join(lines)
        runs.append(record)
        debugpath = self.folder/'debug_halo.txt'
        debugpath.write_text(debugpath.read_text()+'\n'+record['stdout']+'\n',encoding='utf-8')
        rehash(self.folder,'debug_halo.txt')
        raw.write_text(json.dumps(runs), encoding='utf-8')
        def change(rows):
            for row in rows:
                if row['P'] == '6':
                    row['P'] = '8'
                    row['grid'] = '4x2' if row['decomp'] == 'blocks' else '8x1'
        for name in ['timing.csv', 'timing_summary.csv']:
            mutate_rows(self.folder, name, change)
        p = self.folder/'metadata.json'
        data = json.loads(p.read_text())
        data['parameters']['timing_np'] = [4, 8]
        data['cluster_slots'] = [dict(host='heat1',slots=4,vcpus=4),dict(host='heat2',slots=2,vcpus=2),dict(host='heat3',slots=2,vcpus=2)]
        p.write_text(json.dumps(data), encoding='utf-8')
        rehash(self.folder, 'metadata.json')
        rehash(self.folder, 'raw_runs.json')
        self.assertTrue(VERIFY.verify_study(self.folder, require_p8=True)['p8'])


class RetainedPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++')
        if not compiler:
            raise unittest.SkipTest('g++ is needed for the serial reference used by pipeline tests')
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.serial = cls.base/'heat.exe'
        subprocess.run([compiler, '-std=c++17', '-O2', '-ffp-contract=off', str(ROOT/'part1/heat_serial.cpp'),
                        '-o', str(cls.serial)], check=True, capture_output=True)
        cls.blocks, cls.strips = cls.base/'heat_blocks', cls.base/'heat_mpi'
        for path in (cls.blocks, cls.strips):
            path.write_text('TEST DOUBLE ONLY; no MPI executable or cluster evidence', encoding='utf-8')
        cls.study = cls.base/'synthetic-pipeline-test'
        real_run = subprocess.run
        old = json.loads((LEGACY/'raw_runs.json').read_text())
        debug = {r['command'][r['command'].index('-np')+1]: r['stdout'] for r in old if '--debug-print' in r['command']}

        def fake(command, **kwargs):
            if command == ['mpirun', '--version']:
                return subprocess.CompletedProcess(command, 0, 'TEST DOUBLE; no MPI runtime\n', '')
            if command[0] == 'bash':
                return subprocess.CompletedProcess(command, 0, '', '')
            if command[0] == 'mpirun':
                P = int(command[command.index('-np')+1])
                if '--debug-print' in command:
                    return subprocess.CompletedProcess(command, 0, debug[str(P)], '')
                index = next(i for i, token in enumerate(command) if Path(token).name in ('heat_blocks', 'heat_mpi'))
                decomp = 'blocks' if Path(command[index]).name == 'heat_blocks' else 'strips'
                args = command[index+1:]
                args[args.index('--decomp')+1] = 'serial'
                p = real_run([str(cls.serial), *args], **kwargs)
                grid = ''
                if decomp == 'blocks':
                    py, px = RUNNER.dims_create(P)
                    grid = f' Py={py} Px={px}'
                p.stdout = p.stdout.replace('decomp=serial P=1', f'decomp={decomp} P={P}{grid} nodes={min(P, 3)}')
                # Positive synthetic communication time keeps the test-only plot well defined.
                summary = dict(t.split('=', 1) for t in p.stdout.split())
                summary['t_comm'] = str(.002*int(summary['steps']))
                summary['t_total'] = str(float(summary['t_comp'])+float(summary['t_comm']))
                p.stdout = ' '.join(k+'='+v for k, v in summary.items())+'\n'
                return p
            return real_run(command, **kwargs)

        cls.argv = ['run_experiments.py', '--serial', str(cls.serial), '--strips', str(cls.strips),
                    '--blocks', str(cls.blocks), '--cluster', '--N', '8,9,10', '--figure-N', '8',
                    '--figure-steps', '5', '--timing-N', '8,9', '--timing-steps', '3', '--out', str(cls.study)]
        cls.fake = fake
        with patch.object(RUNNER, 'cluster_slots', return_value=[dict(host=f'heat{k}',slots=2,vcpus=2) for k in (1,2,3)]), patch.object(sys, 'argv', cls.argv), patch.object(RUNNER.subprocess, 'run', side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
            try:
                RUNNER.main()
            except SystemExit as error:
                if error.code:
                    raise
        path = cls.study/'raw_runs.json'
        runs = json.loads(path.read_text())
        for run in runs:
            run['command'] = ['heat' if token == 'heat.exe' else token for token in run['command']]
        path.write_text(json.dumps(runs), encoding='utf-8')
        rehash(cls.study, 'raw_runs.json')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy(self, temp):
        folder = Path(temp)/'study'
        shutil.copytree(self.study, folder)
        return folder

    def test_runner_retains_and_strict_verifier_compares_all_fields(self):
        r = VERIFY.verify_study(self.study, require_fields=True)
        self.assertEqual((r['comparisons'], r['pairs'], r['timing']), (45, 47, 24))
        self.assertEqual(len(list((self.study/'fields').glob('*.bin'))), 58)
        self.assertTrue(r['fields'])

    def test_layout_order_alternates_by_repetition(self):
        rows = VERIFY.rows_of(self.study/'timing.csv')
        for rep, first in [(1, 'strips'), (2, 'blocks'), (3, 'strips')]:
            self.assertEqual(next(r['decomp'] for r in rows if int(r['rep']) == rep), first)

    def test_deleted_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy(temp)
            next((folder/'fields').glob('blocks_*.bin')).unlink()
            with self.assertRaises(OSError):
                VERIFY.verify_study(folder, require_fields=True)

    def test_changed_bytes_fail_after_updating_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy(temp)
            rows = VERIFY.part2_verify.rows_of(folder/'compare.csv')
            name = rows[0]['blocks_field']
            field = folder/'fields'/name
            data = bytearray(field.read_bytes())
            data[-1] ^= 1
            field.write_bytes(data)
            mutate_rows(folder,'compare.csv',lambda rows: [r.update(blocks_sha256=hashlib.sha256(data).hexdigest()) for r in rows if r['blocks_field'] == name])
            rehash(folder,'fields/'+name)
            with self.assertRaisesRegex(ValueError,'field bytes differ'):
                VERIFY.verify_study(folder,require_fields=True)

    def test_new_study_cannot_downgrade_to_record_only(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy(temp)
            rows = VERIFY.part2_verify.rows_of(folder/'compare.csv')
            columns = [k for k in rows[0] if not k.endswith(('_sha256','_field'))]
            with (folder/'compare.csv').open('w',newline='',encoding='utf-8') as f:
                writer = csv.DictWriter(f,fieldnames=columns,extrasaction='ignore')
                writer.writeheader()
                writer.writerows(rows)
            rehash(folder,'compare.csv')
            with self.assertRaisesRegex(ValueError,'New study missing'):
                VERIFY.verify_study(folder)

    def test_equal_corrupted_boundaries_are_rejected_after_rehash(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy(temp)
            rows = VERIFY.part2_verify.rows_of(folder/'compare.csv')
            # Corrupt all parallel copies of one reference so pair equality still passes.
            reference = rows[0]['serial_field']
            changed = {reference} | {r['blocks_field'] for r in rows if r['serial_field'] == reference}
            hashes = {}
            for name in changed:
                field = folder/'fields'/name
                data = bytearray(field.read_bytes())
                data[:8] = struct.pack('<d',.99)
                field.write_bytes(data)
                hashes[name] = hashlib.sha256(data).hexdigest()
                rehash(folder,'fields/'+name)
            def update(rows):
                for row in rows:
                    for role in ('serial','blocks'):
                        if row[role+'_field'] in hashes:
                            row[role+'_sha256'] = hashes[row[role+'_field']]
            mutate_rows(folder,'compare.csv',update)
            with self.assertRaisesRegex(ValueError,'boundary value is wrong'):
                VERIFY.verify_study(folder,require_fields=True)

    def test_preflight_rejects_slots_above_real_cpus(self):
        hostfile = self.base/'test-hosts'
        hostfile.write_text('host-a slots=4\nhost-b slots=2\nhost-c slots=2\n',encoding='utf-8')
        with patch.object(RUNNER,'HOSTFILE',hostfile), patch.object(RUNNER.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'2\n','')):
            with self.assertRaisesRegex(SystemExit,'only 2 vCPUs'):
                RUNNER.cluster_slots()

    def test_preflight_accepts_eight_real_slots(self):
        hostfile = self.base/'test-eight-hosts'
        hostfile.write_text('host-a slots=4\nhost-b slots=2\nhost-c slots=2\n',encoding='utf-8')
        responses = [subprocess.CompletedProcess([],0,str(n)+'\n','') for n in (4,2,2)]
        with patch.object(RUNNER,'HOSTFILE',hostfile), patch.object(RUNNER.subprocess,'run',side_effect=responses):
            hosts = RUNNER.cluster_slots()
        self.assertEqual(sum(h['slots'] for h in hosts),8)
        self.assertIn('--nooversubscribe',RUNNER.CLUSTER_ARGS)

    def test_preflight_rejects_duplicate_hosts(self):
        hostfile = self.base/'test-duplicate-hosts'
        hostfile.write_text('host-a slots=2\nhost-a slots=2\nhost-c slots=2\n',encoding='utf-8')
        with patch.object(RUNNER,'HOSTFILE',hostfile), patch.object(RUNNER.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'2\n','')):
            with self.assertRaisesRegex(SystemExit,'Duplicate VM'):
                RUNNER.cluster_slots()


if __name__ == '__main__':
    unittest.main()
