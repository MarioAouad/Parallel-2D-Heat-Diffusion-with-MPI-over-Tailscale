"""Check the built strips solver against the serial reference and MPI-specific properties.

Runs on ONE VM with oversubscription (correctness only). Every test group maps to
an assignment requirement of section 6; see part2/DELIVERY.md.
"""
import argparse
import re
import shlex
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path

LINE = re.compile(r'^\s+(boundary|ghost|owned)\s+j=\s*(\d+):(.*)$')
HEAD = re.compile(r'^rank (\d+): owns global rows (\d+)\.\.(\d+) \((\d+) rows\), down=(\S+) up=(\S+)$')


class StripChecks(unittest.TestCase):
    def mpi(self, P, *args, expected=0):
        cmd = ['mpirun', '-np', str(P), *MPIRUN_ARGS, str(MPI), *map(str, args)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
        return p

    def summary(self, text):
        return dict(token.split('=', 1) for token in text.strip().splitlines()[-1].split())

    def serial(self, *args):
        p = subprocess.run([str(SERIAL), *map(str, args)], capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 0, p.stderr)
        return self.summary(p.stdout)

    def fields(self, P, *args):
        """Run serial and strips with the same options; return both summaries and byte strings."""
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'serial.bin', Path(folder)/'strips.bin'
            s = self.serial('--decomp', 'serial', *args, '--out', a)
            m = self.summary(self.mpi(P, '--decomp', 'strips', *args, '--out', b).stdout)
            return s, m, a.read_bytes(), b.read_bytes()

    def debug(self, P, N, case='2', steps=1):
        text = self.mpi(P, '--case', case, '--N', N, '--r', .2, '--steps', steps, '--debug-print').stdout
        ranks, current = [], None
        for line in text.splitlines():
            if HEAD.match(line):
                g = HEAD.match(line).groups()
                current = dict(rank=int(g[0]), first=int(g[1]), last=int(g[2]), rows=int(g[3]),
                               down=g[4], up=g[5], lines={})
                ranks.append(current)
            elif LINE.match(line):
                kind, j, values = LINE.match(line).groups()
                current['lines'][(kind, int(j))] = values.split()
        return ranks

    def test_strip_sizes_follow_section_6_1(self):
        for N, P, sizes in [(9, 3, [3, 3, 2]), (10, 4, [3, 2, 2, 2]), (8, 2, [4, 3]), (9, 2, [4, 4])]:
            with self.subTest(N=N, P=P):
                ranks = self.debug(P, N)
                self.assertEqual([r['rank'] for r in ranks], list(range(P)))
                self.assertEqual([r['rows'] for r in ranks], sizes)
                self.assertEqual(ranks[0]['first'], 1)
                self.assertEqual(ranks[-1]['last'], N-1)
                for lower, upper in zip(ranks, ranks[1:]):
                    self.assertEqual(lower['last']+1, upper['first'])
                self.assertEqual(ranks[0]['down'], 'none')
                self.assertEqual(ranks[-1]['up'], 'none')

    def test_ghost_rows_equal_neighbour_rows(self):
        for P in (2, 3, 4):
            for steps in (1, 2, 5):
                with self.subTest(P=P, steps=steps):
                    ranks = self.debug(P, 8, steps=steps)
                    owned = {j: v for r in ranks for (k, j), v in r['lines'].items() if k == 'owned'}
                    for r in ranks:
                        for (kind, j), values in r['lines'].items():
                            if kind == 'ghost':
                                self.assertEqual(values, owned[j], f'rank {r["rank"]} ghost j={j}')
                            if kind == 'boundary':   # Case 2: hot top and bottom rows
                                self.assertIn(j, (0, 8))
                                self.assertEqual(set(values), {'1.000000'})

    def test_bit_identical_to_serial(self):
        for case, time in [('1', ('--steps', 30)), ('2', ('--steps', 30)), ('V', ('--T', .003))]:
            for N in (8, 9, 17):
                for P in (1, 2, 3, 4):
                    with self.subTest(case=case, N=N, P=P):
                        s, m, a, b = self.fields(P, '--case', case, '--N', N, '--r', .2, *time)
                        self.assertEqual(len(b), 8*(N+1)**2)
                        self.assertEqual(a, b, 'field bytes differ from serial')
                        for key in ['steps', 'r', 'dt', 'T', 'minimum', 'maximum', 'err_inf', 'err_l2']:
                            self.assertEqual(s.get(key), m.get(key), key)

    def test_summary_fields_and_timers(self):
        for P in (1, 3):
            with self.subTest(P=P):
                m = self.summary(self.mpi(P, '--case', '1', '--N', 32, '--r', .2, '--steps', 40).stdout)
                self.assertEqual(m['decomp'], 'strips')
                self.assertEqual(int(m['P']), P)
                self.assertGreaterEqual(int(m['nodes']), 1)
                total, comp, comm = (float(m[k]) for k in ['t_total', 't_comp', 't_comm'])
                self.assertTrue(total >= 0 and comp >= 0 and comm >= 0)
                # Each timer is a MAX over ranks, so comp alone never exceeds the total.
                self.assertLessEqual(comp, total*1.000001+1e-6)
                self.assertNotIn('err_inf', m)

    def test_maximum_principle_symmetry_and_unstable_demo(self):
        N = 16
        _, m, _, b = self.fields(3, '--case', '1', '--N', N, '--r', .2, '--steps', 300)
        u = struct.unpack('<' + 'd'*(N+1)**2, b)
        self.assertGreaterEqual(min(u), 0)
        self.assertLessEqual(max(u), 1)
        w = N+1
        for j in range(w):
            for i in range(w):
                self.assertAlmostEqual(u[j*w+i], u[j*w+N-i], places=14)
                self.assertAlmostEqual(u[j*w+i], u[(N-j)*w+i], places=14)
        s, m, a, b = self.fields(2, '--case', '1', '--N', 64, '--r', .2625, '--steps', 200,
                                 '--allow-unstable-demo')
        self.assertEqual(a, b, 'unstable run must still match serial bit for bit')
        self.assertLess(float(m['minimum']), -100)
        self.assertGreater(float(m['maximum']), 100)

    def test_bad_inputs_are_rejected_once(self):
        bad = [(4, ['--N', 4, '--steps', 1]),                     # 3 interior rows < 4 ranks
               (2, ['--decomp', 'serial', '--steps', 1]),
               (2, ['--decomp', 'blocks', '--steps', 1]),
               (2, ['--r', .2625, '--steps', 1]),
               (2, ['--N', 32, '--steps', 1, '--debug-print']),
               (2, ['--steps', 0]), (2, ['--T', .1, '--steps', 2]), (2, ['--case', 'X', '--steps', 1])]
        for P, args in bad:
            with self.subTest(P=P, args=args):
                p = subprocess.run(['mpirun', '-np', str(P), *MPIRUN_ARGS, str(MPI), *map(str, args)],
                                   capture_output=True, text=True, timeout=120)
                self.assertNotEqual(p.returncode, 0)
                self.assertEqual(p.stderr.count('Error:'), 1, 'error must be printed once, by rank 0')


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, default=root/'build'/'heat_mpi')
    parser.add_argument('--serial', type=Path, default=root/'build'/'heat')
    parser.add_argument('--mpirun-args', default='--oversubscribe')
    args = parser.parse_args()
    MPI, SERIAL = args.exe.resolve(), args.serial.resolve()
    MPIRUN_ARGS = shlex.split(args.mpirun_args)
    unittest.main(argv=['verify_strips.py'], verbosity=2)
