"""Offline checks for diagnostic evidence preservation; no VM access."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'diagnose-part4.py'
spec = importlib.util.spec_from_file_location('diagnose_part4', SCRIPT)
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


class DiagnosticTests(unittest.TestCase):
    def test_known_warning_is_not_confused_with_other_errors(self):
        warning = '[heat1:08804] plm:rsh: Warning: setpgid(8807,8807) failed in parent with errno=Permission denied(13)\n'
        self.assertEqual(D.warning_kind(warning), 'openmpi-parent-setpgid-only')
        for other in (warning+'MPI transport failed\n', warning.replace('parent', 'child'),
                      warning.replace('8807,8807', '8807,8808'), warning.replace('denied(13)', 'denied(1)')):
            self.assertEqual(D.warning_kind(other), 'other-diagnostic-needs-review')

    def test_collect_preserves_original_and_exposes_warning_only_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            (repo/'part0/config').mkdir(parents=True)
            (repo/'part0/config/hosts').write_text('192.0.2.1 slots=4\n192.0.2.2 slots=2\n192.0.2.3 slots=2\n')
            (repo/'part4').mkdir()
            (repo/'part4/run_experiments.py').write_text('# fixture\n')
            run = repo/'part4/results/runs/example'
            (run/'private').mkdir(parents=True)
            (run/'metadata.json').write_text(json.dumps(dict(status='incomplete', revision='fixture')))
            (run/'state.json').write_text(json.dumps(dict(completed={
                'baseline:0:512:1': dict(run_id=1, experiment='baseline'),
                'calibration:0:0:1': dict(run_id=2)})))
            raw = [dict(run_id=1, task_id='baseline:0:512:1', returncode=0, stderr='', stdout='summary'),
                   dict(run_id=2, task_id='calibration:0:0:1', returncode=0, stderr='normal progress', stdout='csv'),
                   dict(run_id=3, task_id='strong:node:6:8192:strips:1', returncode=0,
                        stderr='[heat1:123] plm:rsh: Warning: setpgid(456,456) failed in parent with errno=Permission denied(13)\n',
                        stdout='summary')]
            (run/'raw_runs.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in raw))
            (run/'private/raw_runs.jsonl').write_bytes(b'private-original\x00\xff')
            before = {p.relative_to(run).as_posix(): p.read_bytes() for p in run.rglob('*') if p.is_file()}
            def fake(command, timeout=30):
                if command[:3] == ['tailscale', 'ip', '-4']:
                    return dict(returncode=0, stdout='192.0.2.1\n', stderr='')
                return dict(returncode=0, stdout=json.dumps(dict(observations=[])), stderr='')
            with patch.object(D, 'execute', side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
                archive = D.collect(run, include_network=False)
            after = {p.relative_to(run).as_posix(): p.read_bytes() for p in run.rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            with tarfile.open(archive) as tar:
                root = archive.name.removesuffix('.tar.gz')
                review = json.load(tar.extractfile(root+'/run-review.json'))
                self.assertEqual(review['completed_heat_measurements'], 1)
                self.assertEqual(review['completed_calibration_sweeps'], 1)
                self.assertEqual(review['nonzero_exit_attempts'], 0)
                self.assertEqual(review['unselected_attempts'], 1)
                self.assertEqual(review['attempts_requiring_review'][0]['diagnostic_kind'], 'openmpi-parent-setpgid-only')
                for name, data in before.items():
                    self.assertEqual(tar.extractfile(root+'/original-run/example/'+name).read(), data)
                manifest = json.load(tar.extractfile(root+'/diagnostic-manifest.json'))
                for item in manifest:
                    data = tar.extractfile(root+'/'+item['file']).read()
                    self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])

    def test_guest_program_compiles_and_does_not_launch_mpi(self):
        code = D.guest_program(Path('/home/mpi/heat-project-repo'), ['192.0.2.2'])
        compile(code, '<guest diagnostic>', 'exec')
        self.assertNotIn("['mpirun','-np'", code)
        self.assertNotIn('sudo', code)


if __name__ == '__main__':
    unittest.main()
