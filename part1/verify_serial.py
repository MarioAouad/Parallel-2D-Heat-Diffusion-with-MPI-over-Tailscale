"""Check the built serial reference against independent mathematical properties."""
import argparse
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest


class SerialChecks(unittest.TestCase):
    def run_heat(self, *args, expected=0):
        p = subprocess.run([str(EXE), *map(str, args)], capture_output=True,
                           text=True, timeout=30)
        self.assertEqual(p.returncode, expected, p.stdout + p.stderr)
        return dict(token.split('=', 1) for token in p.stdout.split()) if expected == 0 else p

    def field(self, case, steps, N=8, r=.2, extra=()):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'field.bin'
            result = self.run_heat('--case', case, '--N', N, '--r', r,
                                   '--steps', steps, '--out', path, *extra)
            data = path.read_bytes()
        self.assertEqual(len(data), 8*(N+1)**2)
        return result, struct.unpack('<' + 'd'*(N+1)**2, data)

    def test_one_step_known_values_and_case2_corners(self):
        for case in ['1', '2']:
            summary, u = self.field(case, 1)
            self.assertNotIn('err_inf', summary)
            self.assertEqual(summary['decomp'], 'serial')
            self.assertEqual(summary['P'], '1')
            self.assertEqual(u[1*9+4], .2)
            self.assertEqual(u[4*9+4], 0)
            self.assertEqual(u[1*9+1], .4 if case == '1' else .2)
            self.assertEqual(u[4*9+1], .2 if case == '1' else 0)
            for i in range(9):
                self.assertEqual(u[i], 1)
                self.assertEqual(u[8*9+i], 1)
            for j in range(1, 8):
                self.assertEqual(u[j*9], 1 if case == '1' else 0)
                self.assertEqual(u[j*9+8], 1 if case == '1' else 0)

    def test_both_buffers_boundaries_symmetry_and_maximum_principle(self):
        for case in ['1', '2']:
            for steps in [2, 3, 400]:
                with self.subTest(case=case, steps=steps):
                    _, u = self.field(case, steps)
                    self.assertGreaterEqual(min(u), 0)
                    self.assertLessEqual(max(u), 1)
                    for j in range(9):
                        for i in range(9):
                            self.assertAlmostEqual(u[j*9+i], u[j*9+8-i], places=14)
                            self.assertAlmostEqual(u[j*9+i], u[(8-j)*9+i], places=14)
                    for i in range(9):
                        self.assertEqual(u[i], 1)
                        self.assertEqual(u[8*9+i], 1)
                    for j in range(1, 8):
                        self.assertEqual(u[j*9], 1 if case == '1' else 0)
                        self.assertEqual(u[j*9+8], 1 if case == '1' else 0)
                    if case == '1' and steps == 400:
                        self.assertGreater(u[4*9+4], .999)

    def test_full_field_matches_discrete_sine_mode(self):
        N, steps, r = 16, 7, .2
        summary, u = self.field('V', steps, N, r)
        factor = (1-8*r*math.sin(math.pi/(2*N))**2)**steps
        for j in range(N+1):
            for i in range(N+1):
                expected = 0 if i in (0,N) or j in (0,N) else (
                    factor*math.sin(math.pi*i/N)*math.sin(math.pi*j/N))
                self.assertAlmostEqual(u[j*(N+1)+i], expected, places=14)
        exact_amp = math.exp(-2*math.pi**2*float(summary['T']))
        self.assertAlmostEqual(float(summary['err_inf']), abs(factor-exact_amp), places=14)
        self.assertAlmostEqual(float(summary['err_l2']), abs(factor-exact_amp)/2, places=14)

    def test_final_time_rounding_and_r_bound(self):
        for N, r, T in [(17,.23,.0031), (16,.2,.05), (8,.25,.001)]:
            s = self.run_heat('--case','V','--N',N,'--r',r,'--T',T)
            self.assertEqual(float(s['T']), T)
            self.assertLessEqual(float(s['r']), r)
            self.assertLessEqual(float(s['r']), .25)
            self.assertAlmostEqual(float(s['dt'])*int(s['steps']), T, places=15)
            self.assertEqual(float(s['t_comm']), 0)
            self.assertEqual(s['t_total'], s['t_comp'])

    def test_bad_inputs_are_rejected(self):
        bad = [('--N','8junk'), ('--N','-8'), ('--N','1'), ('--r','nan'),
               ('--r','inf'), ('--r','0'), ('--r','.2625'), ('--steps','0'),
               ('--steps','2junk'), ('--T','-1'), ('--T','inf'),
               ('--decomp','strips'), ('--case','X'), ('--unknown','1')]
        for flag, value in bad:
            with self.subTest(flag=flag, value=value):
                args = [] if flag in ('--steps', '--T') else ['--steps','1']
                p = self.run_heat(*args, flag, value, expected=1)
                self.assertIn('Error:', p.stderr)
        self.run_heat('--steps','1','--steps','2', expected=1)
        self.run_heat('--case','V','--r','.2625','--steps','1',
                      '--allow-unstable-demo', expected=1)
        self.run_heat('--T','.05','--steps','2', expected=1)
        self.run_heat('--steps', expected=1)

    def test_isolated_instability_demonstration(self):
        s, u = self.field('1', 200, 64, .2625, ('--allow-unstable-demo',))
        self.assertLess(min(u), -100)
        self.assertGreater(max(u), 100)
        self.assertNotIn('err_inf', s)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    EXE = args.exe.resolve()
    unittest.main(argv=['verify_serial.py'], verbosity=2)
