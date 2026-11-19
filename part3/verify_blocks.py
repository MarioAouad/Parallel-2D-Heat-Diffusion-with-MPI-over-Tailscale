"""Check the built blocks solver against the serial reference and MPI-specific properties.

Runs on ONE VM with oversubscription (correctness only). Every test group maps to
an assignment requirement of section 7; see part3/DELIVERY.md.
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
HEAD = re.compile(r'^rank (\d+): coords \((\d+),(\d+)\) of (\d+)x(\d+) grid, rows (\d+)\.\.(\d+), '
                  r'cols (\d+)\.\.(\d+), down=(\S+) up=(\S+) left=(\S+) right=(\S+)$')


class BlockChecks(unittest.TestCase):
    def mpi(self, P, *args, expected=0):
        cmd = ['mpirun', '-np', str(P), *MPIRUN_ARGS, str(MPI), *map(str, args)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
        return p

    def summary(self, text):
        return dict(token.split('=', 1) for token in text.strip().splitlines()[-1].split())

    def fields(self, P, *args):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder)/'serial.bin', Path(folder)/'blocks.bin'
            p = subprocess.run([str(SERIAL), '--decomp', 'serial', *map(str, args), '--out', str(a)],
                               capture_output=True, text=True, timeout=300)
            self.assertEqual(p.returncode, 0, p.stderr)
            s = self.summary(p.stdout)
            m = self.summary(self.mpi(P, '--decomp', 'blocks', *args, '--out', b).stdout)
            return s, m, a.read_bytes(), b.read_bytes()

    def debug(self, P, N, case='1', steps=1):
        text = self.mpi(P, '--case', case, '--N', N, '--r', .2, '--steps', steps, '--debug-print').stdout
        ranks, current = [], None
        for line in text.splitlines():
            m = HEAD.match(line)
            if m:
                g = m.groups()
                current = dict(rank=int(g[0]), cy=int(g[1]), cx=int(g[2]), Py=int(g[3]), Px=int(g[4]),
                               rows=(int(g[5]), int(g[6])), cols=(int(g[7]), int(g[8])),
                               down=g[9], up=g[10], left=g[11], right=g[12], lines=[])
                ranks.append(current)
            elif LINE.match(line):
                kind, j, values = LINE.match(line).groups()
                current['lines'].append((kind, int(j), values.split()))
        return ranks

    def test_process_grid_and_block_sizes(self):
        cases = [(9, 4, (2, 2), [(1, 4), (5, 8)], [(1, 4), (5, 8)]),
                 (10, 6, (3, 2), [(1, 3), (4, 6), (7, 9)], [(1, 5), (6, 9)]),
                 (8, 3, (3, 1), [(1, 3), (4, 5), (6, 7)], [(1, 7)]),
                 (8, 2, (2, 1), [(1, 4), (5, 7)], [(1, 7)])]
        for N, P, grid, row_ranges, col_ranges in cases:
            with self.subTest(N=N, P=P):
                ranks = self.debug(P, N)
                self.assertEqual([r['rank'] for r in ranks], list(range(P)))
                for r in ranks:
                    self.assertEqual((r['Py'], r['Px']), grid)
                    self.assertEqual(r['rank'], r['cy']*grid[1] + r['cx'])   # row-major Cartesian ranks
                    self.assertEqual(r['rows'], row_ranges[r['cy']])
                    self.assertEqual(r['cols'], col_ranges[r['cx']])
                    expect = lambda ok, other: str(other) if ok else 'none'
                    self.assertEqual(r['down'], expect(r['cy'] > 0, r['rank']-grid[1]))
                    self.assertEqual(r['up'], expect(r['cy'] < grid[0]-1, r['rank']+grid[1]))
                    self.assertEqual(r['left'], expect(r['cx'] > 0, r['rank']-1))
                    self.assertEqual(r['right'], expect(r['cx'] < grid[1]-1, r['rank']+1))

    def test_ghost_rows_and_columns_equal_neighbour_values(self):
        for case in ('1', '2'):
            for P in (4, 6):
                for steps in (1, 2, 5):
                    with self.subTest(case=case, P=P, steps=steps):
                        N = 8
                        ranks = self.debug(P, N, case, steps)
                        owned = {}
                        for r in ranks:
                            fx = r['cols'][0]
                            for kind, j, vals in r['lines']:
                                if kind == 'owned':
                                    for li in range(1, len(vals)-1):
                                        owned[(fx-1+li, j)] = vals[li]
                        self.assertEqual(len(owned), (N-1)**2)
                        for r in ranks:
                            fx, ncols = r['cols'][0], r['cols'][1]-r['cols'][0]+1
                            for kind, j, vals in r['lines']:
                                self.assertEqual(len(vals), ncols+2)
                                for li, v in enumerate(vals):
                                    i = fx-1+li
                                    ghost_col = li in (0, ncols+1)
                                    if kind != 'owned' and ghost_col:
                                        self.assertEqual(v, '-', 'corner ghosts are never exchanged')
                                    elif kind == 'ghost':
                                        self.assertEqual(v, owned[(i, j)], f'rank {r["rank"]} ghost row j={j}')
                                    elif kind == 'boundary':
                                        self.assertEqual(v, '1.000000')   # hot top/bottom in both cases
                                    elif ghost_col:
                                        side = r['left'] if li == 0 else r['right']
                                        expected = owned[(i, j)] if side != 'none' else (
                                            '1.000000' if case == '1' else '0.000000')
                                        self.assertEqual(v, expected, f'rank {r["rank"]} ghost column i={i} j={j}')

    def test_bit_identical_to_serial(self):
        for case, time in [('1', ('--steps', 30)), ('2', ('--steps', 30)), ('V', ('--T', .003))]:
            for N in (8, 9, 17):
                for P in (1, 2, 3, 4, 6):
                    with self.subTest(case=case, N=N, P=P):
                        s, m, a, b = self.fields(P, '--case', case, '--N', N, '--r', .2, *time)
                        self.assertEqual(len(b), 8*(N+1)**2)
                        self.assertEqual(a, b, 'field bytes differ from serial')
                        for key in ['steps', 'r', 'dt', 'T', 'minimum', 'maximum', 'err_inf', 'err_l2']:
                            self.assertEqual(s.get(key), m.get(key), key)

    def test_summary_fields_and_timers(self):
        for P, grid in ((1, (1, 1)), (4, (2, 2)), (6, (3, 2))):
            with self.subTest(P=P):
                m = self.summary(self.mpi(P, '--case', '1', '--N', 32, '--r', .2, '--steps', 40).stdout)
                self.assertEqual(m['decomp'], 'blocks')
                self.assertEqual((int(m['P']), int(m['Py']), int(m['Px'])), (P, *grid))
                self.assertGreaterEqual(int(m['nodes']), 1)
                total, comp, comm = (float(m[k]) for k in ['t_total', 't_comp', 't_comm'])
                self.assertTrue(total >= 0 and comp >= 0 and comm >= 0)
                self.assertLessEqual(comp, total*1.000001+1e-6)
                self.assertNotIn('err_inf', m)

    def test_maximum_principle_symmetry_and_unstable_demo(self):
        N = 16
        _, m, _, b = self.fields(4, '--case', '1', '--N', N, '--r', .2, '--steps', 300)
        u = struct.unpack('<' + 'd'*(N+1)**2, b)
        self.assertGreaterEqual(min(u), 0)
        self.assertLessEqual(max(u), 1)
        w = N+1
        for j in range(w):
            for i in range(w):
                self.assertAlmostEqual(u[j*w+i], u[j*w+N-i], places=14)
                self.assertAlmostEqual(u[j*w+i], u[(N-j)*w+i], places=14)
        s, m, a, b = self.fields(4, '--case', '1', '--N', 64, '--r', .2625, '--steps', 200,
                                 '--allow-unstable-demo')
        self.assertEqual(a, b, 'unstable run must still match serial bit for bit')
        self.assertLess(float(m['minimum']), -100)
        self.assertGreater(float(m['maximum']), 100)

    def test_bad_inputs_are_rejected_once(self):
        bad = [(6, ['--N', 3, '--steps', 1]),                     # 2 interior rows < 3 block rows
               (2, ['--decomp', 'serial', '--steps', 1]),
               (2, ['--decomp', 'strips', '--steps', 1]),
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
    parser.add_argument('--exe', type=Path, default=root/'build'/'heat_blocks')
    parser.add_argument('--serial', type=Path, default=root/'build'/'heat')
    parser.add_argument('--mpirun-args', default='--oversubscribe')
    args = parser.parse_args()
    MPI, SERIAL = args.exe.resolve(), args.serial.resolve()
    MPIRUN_ARGS = shlex.split(args.mpirun_args)
    unittest.main(argv=['verify_blocks.py'], verbosity=2)
