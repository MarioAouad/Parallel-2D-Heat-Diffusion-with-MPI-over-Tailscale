"""CPU preflight regressions; all subprocesses are mocked, with no VM access."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('check_slots', Path(__file__).resolve().parents[1]/'check_slots.py')
SLOTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SLOTS)


class SlotChecks(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.hosts = Path(temp.name)/'hosts'
        self.hosts.write_text('192.0.2.1 slots=4\n192.0.2.2 slots=2\n192.0.2.3 slots=2\n')

    def fake(self, command, **kwargs):
        if command == ['tailscale', 'ip', '-4']:
            return subprocess.CompletedProcess(command, 0, '192.0.2.1\n', '')
        if command == ['nproc']:
            return subprocess.CompletedProcess(command, 0, '4\n', '')
        self.assertEqual(command[0], 'ssh')
        self.assertNotIn('192.0.2.1', command, 'The launcher must not SSH into itself')
        self.assertIn('BatchMode=yes', command)
        self.assertIn('StrictHostKeyChecking=yes', command)
        return subprocess.CompletedProcess(command, 0, '2\n', '')

    def test_reads_launcher_locally_and_remote_guests_with_verified_ssh(self):
        with patch.object(SLOTS.subprocess, 'run', side_effect=self.fake) as run:
            hosts = SLOTS.check_slots(self.hosts)
        self.assertEqual([h['vcpus'] for h in hosts], [4, 2, 2])
        self.assertEqual(sum(h['slots'] for h in hosts), 8)
        self.assertEqual(sum(c.args[0][0] == 'ssh' for c in run.call_args_list), 2)

    def test_local_cpu_limit_still_enforced(self):
        def fake(command, **kwargs):
            if command == ['nproc']:
                return subprocess.CompletedProcess(command, 0, '2\n', '')
            return self.fake(command, **kwargs)
        with patch.object(SLOTS.subprocess, 'run', side_effect=fake):
            with self.assertRaisesRegex(SystemExit, 'only 2 vCPUs'):
                SLOTS.check_slots(self.hosts)

    def test_remote_host_key_failure_is_preserved(self):
        def fake(command, **kwargs):
            if command[0] == 'ssh':
                return subprocess.CompletedProcess(command, 255, '', 'Host key verification failed.')
            return self.fake(command, **kwargs)
        with patch.object(SLOTS.subprocess, 'run', side_effect=fake):
            with self.assertRaisesRegex(SystemExit, 'heat2 over SSH: Host key verification failed'):
                SLOTS.check_slots(self.hosts)

    def test_missing_local_identity_stops_before_ssh(self):
        with patch.object(SLOTS.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'not connected')) as run:
            with self.assertRaisesRegex(SystemExit, 'Cannot identify this VM'):
                SLOTS.check_slots(self.hosts)
        self.assertEqual(run.call_count, 1)


if __name__ == '__main__':
    unittest.main()
