"""Evidence-pipeline tests. MPI is mocked; these are not cluster-run evidence."""
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


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


VERIFY = module('part2_evidence_verify', ROOT/'part2/verify_results.py')
RUNNER = module('part2_evidence_runner', ROOT/'part2/run_experiments.py')
RECOVER = module('recover_sessions', ROOT/'llm_log/recover_sessions.py')
LEGACY = ROOT/'part2/results/2026-11-19-cluster'


def rehash(folder, name):
    p = folder/'manifest.json'
    manifest = json.loads(p.read_text(encoding='utf-8'))
    data = (folder/name).read_bytes()
    for entry in manifest['published_files']:
        if entry['file'] == name:
            entry.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            break
    else:
        manifest['published_files'].append(dict(file=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
    p.write_text(json.dumps(manifest), encoding='utf-8')


def mutate_rows(folder, name, change):
    path = folder/name
    with path.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns, rows = reader.fieldnames, list(reader)
    change(rows)
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    rehash(folder,name)


class LegacyChecks(unittest.TestCase):
    def test_legacy_is_record_only_and_strict_mode_rejects_missing_fields(self):
        self.assertFalse(VERIFY.verify_study(LEGACY)['fields'])
        with self.assertRaisesRegex(ValueError, 'Original binary fields unavailable'):
            VERIFY.verify_study(LEGACY, require_fields=True)

    def test_csv_timing_tampering_rejected_even_when_manifest_is_updated(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'study'
            shutil.copytree(LEGACY, folder)
            p = folder/'compare.csv'
            lines = p.read_text(encoding='utf-8').splitlines()
            parts = lines[1].split(',')
            parts[10] = '123'
            lines[1] = ','.join(parts)
            p.write_text('\n'.join(lines)+'\n', encoding='utf-8')
            rehash(folder, 'compare.csv')
            with self.assertRaisesRegex(ValueError, 'CSV/raw mismatch'):
                VERIFY.verify_study(folder)

    def test_missing_configuration_rejected_even_when_manifest_is_updated(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)/'study'
            shutil.copytree(LEGACY, folder)
            p = folder/'compare.csv'
            p.write_text('\n'.join(p.read_text(encoding='utf-8').splitlines()[:-1])+'\n', encoding='utf-8')
            rehash(folder, 'compare.csv')
            with self.assertRaisesRegex(ValueError, 'Missing, duplicate or extra'):
                VERIFY.verify_study(folder)


class RetainedFieldPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = shutil.which('g++')
        if not compiler:
            raise unittest.SkipTest('g++ needed for the serial reference in pipeline tests')
        cls.temp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.temp.name)
        cls.serial = cls.base/'heat.exe'
        subprocess.run([compiler, '-std=c++17', '-O2', '-ffp-contract=off', str(ROOT/'part1/heat_serial.cpp'),
                        '-o', str(cls.serial)], check=True, capture_output=True)
        cls.mpi = cls.base/'heat_mpi'
        cls.mpi.write_text('TEST DOUBLE ONLY: no MPI executable or cluster measurement', encoding='utf-8')
        cls.study = cls.base/'synthetic-pipeline-test'
        real_run = subprocess.run
        old = json.loads((LEGACY/'raw_runs.json').read_text(encoding='utf-8'))
        debug = {r['command'][r['command'].index('-np')+1]: r['stdout']
                 for r in old if '--debug-print' in r['command']}

        def fake(command, **kwargs):
            if command == ['mpirun', '--version']:
                return subprocess.CompletedProcess(command, 0, 'TEST DOUBLE (no MPI runtime)\n', '')
            if command[0] == 'bash':
                return subprocess.CompletedProcess(command, 0, '', '')
            if command[0] == 'mpirun':
                P = command[command.index('-np')+1]
                if '--debug-print' in command:
                    return subprocess.CompletedProcess(command, 0, debug[P], '')
                mpi_index = next(i for i, token in enumerate(command) if Path(token).name == 'heat_mpi')
                args = command[mpi_index+1:]
                args[args.index('--decomp')+1] = 'serial'
                p = real_run([str(cls.serial), *args], **kwargs)
                p.stdout = p.stdout.replace('decomp=serial P=1', f'decomp=strips P={P} nodes={min(int(P), 3)}')
                return p
            return real_run(command, **kwargs)

        # Keep the runner's portable executable label Linux-style while executing PE on Windows.
        argv = ['run_experiments.py', '--serial', str(cls.serial), '--mpi', str(cls.mpi), '--cluster',
                '--N', '8,9,10', '--figure-N', '8', '--figure-steps', '5', '--out', str(cls.study)]
        with patch.object(RUNNER,'cluster_slots',return_value=[dict(host=f'heat{k}',slots=2,vcpus=2) for k in (1,2,3)]), patch.object(sys, 'argv', argv), patch.object(RUNNER.subprocess, 'run', side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
            try:
                RUNNER.main()
            except SystemExit as e:
                if e.code:
                    raise
        # A Windows test executable has .exe; normalize only synthetic raw command labels.
        p = cls.study/'raw_runs.json'
        data = json.loads(p.read_text(encoding='utf-8'))
        for run in data:
            run['command'] = ['heat' if token == 'heat.exe' else token for token in run['command']]
        p.write_text(json.dumps(data), encoding='utf-8')
        rehash(cls.study, 'raw_runs.json')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy_study(self, temp):
        folder = Path(temp)/'study'
        shutil.copytree(self.study, folder)
        return folder

    def test_new_runner_retains_every_field_and_strict_verifier_reads_them(self):
        result = VERIFY.verify_study(self.study, require_fields=True)
        self.assertEqual(result['comparisons'], 36)
        self.assertEqual(result['pairs'], 38)
        self.assertTrue(result['fields'])
        self.assertEqual(len(list((self.study/'fields').glob('*.bin'))), 49)

    def test_missing_field_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy_study(temp)
            next((folder/'fields').glob('strips_*.bin')).unlink()
            with self.assertRaises(OSError):
                VERIFY.verify_study(folder, require_fields=True)

    def test_changed_bytes_fail_after_updating_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy_study(temp)
            rows = VERIFY.rows_of(folder/'compare.csv')
            name = rows[0]['strips_field']
            field = folder/'fields'/name
            data = bytearray(field.read_bytes())
            data[-1] ^= 1
            field.write_bytes(data)
            mutate_rows(folder,'compare.csv',lambda rows: [r.update(strips_sha256=hashlib.sha256(data).hexdigest()) for r in rows if r['strips_field'] == name])
            rehash(folder,'fields/'+name)
            with self.assertRaisesRegex(ValueError,'field bytes differ'):
                VERIFY.verify_study(folder,require_fields=True)

    def test_new_study_cannot_downgrade_to_record_only(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = self.copy_study(temp)
            rows = VERIFY.rows_of(folder/'compare.csv')
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
            folder = self.copy_study(temp)
            rows = VERIFY.rows_of(folder/'compare.csv')
            # Corrupt all parallel copies of one reference so pair equality still passes.
            reference = rows[0]['serial_field']
            changed = {reference} | {r['strips_field'] for r in rows if r['serial_field'] == reference}
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
                    for role in ('serial','strips'):
                        if row[role+'_field'] in hashes:
                            row[role+'_sha256'] = hashes[row[role+'_field']]
            mutate_rows(folder,'compare.csv',update)
            with self.assertRaisesRegex(ValueError,'boundary value is wrong'):
                VERIFY.verify_study(folder,require_fields=True)



class RecoveryChecks(unittest.TestCase):
    def test_recovery_preserves_visible_messages_and_excludes_reasoning(self):
        items = [dict(type='session_meta', payload=dict(id='test', cwd='/course/project')),
                 dict(type='turn_context', payload=dict(model='recorded-model-id')),
                 dict(type='response_item', payload=dict(type='message', role='user', content=[dict(type='input_text', text='full prompt\nline two')])),
                 dict(type='response_item', payload=dict(type='message', role='assistant', channel='analysis', content=[dict(type='output_text', text='PRIVATE REASONING')])),
                 dict(type='response_item', payload=dict(type='reasoning', text='PRIVATE REASONING')),
                 dict(type='response_item', payload=dict(type='message', role='assistant', channel='commentary', content=[dict(type='output_text', text='full progress')])),
                 dict(type='response_item', payload=dict(type='message', role='assistant', channel='final', content=[dict(type='output_text', text='full final')]))]
        source = '\n'.join(json.dumps(i) for i in items).encode()
        result = RECOVER.extract(source, Path('/course'))
        self.assertEqual(len(result['visible_messages']), 3)
        self.assertNotIn('PRIVATE REASONING', json.dumps(result))
        self.assertEqual(result['models'], ['recorded-model-id'])
        self.assertEqual(result['visible_messages'][0]['content'][0]['text'], 'full prompt\nline two')
        self.assertIsNone(RECOVER.extract(source, Path('/unrelated')))


if __name__ == '__main__':
    unittest.main()
