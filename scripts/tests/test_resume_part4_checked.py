"""Offline recovery tests: exact warning only, bounded retries, immutable history."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('resume_checked', ROOT/'scripts/resume-part4-checked.py')
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
sys.path.insert(0, str(ROOT/'part4'))
import common as C

WARNING = '[heat1:9209] plm:rsh: Warning: setpgid(9213,9213) failed in parent with errno=Permission denied(13)\n'


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name)
        (self.repo/'part4').mkdir()
        (self.repo/'part4/run_experiments.py').write_text('# synthetic launcher\n')
        (self.repo/'scripts').mkdir()
        (self.repo/'scripts/run-part4.sh').write_text('# synthetic packager\n')
        self.folder = self.repo/'part4/results/runs/test'
        self.folder.mkdir(parents=True)
        self.task = 'strong:node:2:16:strips:1'
        self.state = dict(completed={'placement:node:2': dict(run_id=1, rank_hosts=['heat1', 'heat2'])})
        C.write_json(self.folder/'state.json', self.state)
        self.meta = dict(mode='cluster', parameters=C.default_parameters(8, smoke=True),
                         hosts=[dict(slots=s) for s in [4, 2, 2]])
        C.write_json(self.folder/'metadata.json', self.meta)
        self.before = [dict(run_id=1, task_id='placement:node:2', returncode=0, command=['mpirun'], stdout='', stderr='')]
        self.record = dict(run_id=2, task_id=self.task, returncode=0, command=['mpirun'],
                           stderr=WARNING, wall_seconds=2,
                           stdout='decomp=strips P=2 nodes=2 case=1 N=16 steps=2 r=0.24 dt=0.0009375 '
                                  'T=0.001875 t_total=1 t_comp=0.1 t_comm=0.9 minimum=0 maximum=1\n')
        (self.folder/'raw_runs.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.before))

    def reason(self, record=None):
        return S.retry_reason(self.before, self.before+[record or self.record], self.folder, self.meta, C)

    def test_complete_summary_and_exact_warning_are_retryable_but_not_accepted(self):
        before = (self.folder/'state.json').read_bytes()
        self.assertEqual(self.reason(), self.task)
        self.assertEqual((self.folder/'state.json').read_bytes(), before)

    def test_transport_errors_child_warnings_and_nonzero_exits_stop(self):
        for stderr in (WARNING+'TCP peer failed\n', WARNING.replace('parent', 'child'),
                       WARNING.replace('9213,9213', '9213,9214'), WARNING.replace('denied(13)', 'denied(1)'), ''):
            record = dict(self.record, stderr=stderr)
            self.assertIsNone(self.reason(record))
        self.assertIsNone(self.reason(dict(self.record, returncode=1)))

    def test_no_new_record_or_changed_history_is_not_retryable(self):
        self.assertIsNone(S.retry_reason(self.before, self.before, self.folder, self.meta, C))
        changed = copy.deepcopy(self.before)
        changed[0]['stderr'] = 'changed'
        self.assertIsNone(S.retry_reason(self.before, changed+[self.record], self.folder, self.meta, C))

    def test_bad_summary_completed_task_and_calibration_are_not_retryable(self):
        self.assertIsNone(self.reason(dict(self.record, stdout='invalid summary')))
        self.assertIsNone(self.reason(dict(self.record, wall_seconds=0.5)))
        self.assertIsNone(self.reason(dict(self.record, task_id='calibration:0:1:1')))
        self.state['completed'][self.task] = dict(run_id=2)
        C.write_json(self.folder/'state.json', self.state)
        self.assertIsNone(self.reason())

    def test_source_change_is_refused_without_hash_override(self):
        meta = dict(sources={name:C.sha(ROOT/name) for name in C.SOURCES})
        original = copy.deepcopy(meta)
        self.assertEqual(set(S.frozen_common(ROOT, meta).SOURCES), set(C.SOURCES))
        meta['sources']['part2/heat_mpi.cpp'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'source changed'):
            S.frozen_common(ROOT, meta)
        self.assertEqual(original['sources']['part2/heat_mpi.cpp'], C.sha(ROOT/'part2/heat_mpi.cpp'))

    def supervise_fixture(self, action, retries=1, total_limit=2):
        fcntl = SimpleNamespace(LOCK_EX=1, LOCK_NB=2, flock=lambda *_: None)
        with patch.dict(sys.modules, fcntl=fcntl), patch.object(S, 'frozen_common', return_value=C), \
                patch.object(S.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as package, \
                contextlib.redirect_stdout(io.StringIO()):
            status = S.supervise(self.folder, 'Synthetic test only', per_task=retries,
                                 total_limit=total_limit, executor=action)
        return status, package

    def test_warning_retry_keeps_history_then_packages_clean_completion(self):
        calls = []
        initial_state = (self.folder/'state.json').read_bytes()
        def action(command, logfile):
            calls.append(command)
            raw = S.read_raw(self.folder)
            record = dict(self.record, run_id=len(raw)+1)
            if len(calls) == 2:
                record['stderr'] = ''
                self.assertEqual((self.folder/'state.json').read_bytes(), initial_state)
                self.state['completed'][self.task] = dict(run_id=record['run_id'])
                C.write_json(self.folder/'state.json', self.state)
            with (self.folder/'raw_runs.jsonl').open('a') as f:
                f.write(json.dumps(record)+'\n')
            return 1 if len(calls) == 1 else 0
        status, package = self.supervise_fixture(action)
        self.assertEqual(status, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(S.read_raw(self.folder)[1]['stderr'], WARNING)
        self.assertEqual(S.read_raw(self.folder)[2]['stderr'], '')
        package.assert_called_once()
        self.assertEqual(package.call_args.args[0][-2:], ['package', str(self.folder.resolve())])
        events = [json.loads(s) for s in (self.folder/'private/resume-supervisor.jsonl').read_text().splitlines()]
        self.assertEqual(sum(r['event']=='retry_exact_parent_warning' for r in events), 1)

    def test_persistent_warning_stops_at_retry_limit_and_does_not_package(self):
        calls = []
        def action(command, logfile):
            calls.append(command)
            record = dict(self.record, run_id=len(S.read_raw(self.folder))+1)
            with (self.folder/'raw_runs.jsonl').open('a') as f:
                f.write(json.dumps(record)+'\n')
            return 1
        status, package = self.supervise_fixture(action, retries=1)
        self.assertEqual(status, 1)
        self.assertEqual(len(calls), 2)
        package.assert_not_called()
        self.assertNotIn(self.task, json.loads((self.folder/'state.json').read_text())['completed'])

    def test_preflight_failure_does_not_retry_stale_warning(self):
        with (self.folder/'raw_runs.jsonl').open('a') as f:
            f.write(json.dumps(self.record)+'\n')
        calls = []
        def action(command, logfile):
            calls.append(command)
            return 1  # preflight stopped before invoking anything new
        status, package = self.supervise_fixture(action)
        self.assertEqual(status, 1)
        self.assertEqual(len(calls), 1)
        package.assert_not_called()

    def test_total_limit_can_disable_automatic_retries(self):
        calls = []
        def action(command, logfile):
            calls.append(command)
            with (self.folder/'raw_runs.jsonl').open('a') as f:
                f.write(json.dumps(self.record)+'\n')
            return 1
        status, package = self.supervise_fixture(action, retries=3, total_limit=0)
        self.assertEqual(status, 1)
        self.assertEqual(len(calls), 1)
        package.assert_not_called()


if __name__ == '__main__':
    unittest.main()
