"""Numerical/validation checks with synthetic TEMPORARY inputs, never raw results."""
import csv
import importlib.util
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

SOURCE = Path(__file__).resolve().parents[1] / "analyze_pingpong.py"
SPEC = importlib.util.spec_from_file_location("analysis", SOURCE)
ANALYSIS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYSIS)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        # Synthetic fixtures disappear after each test and cannot be confused
        # with the measured, hash-checked 17 November archive.
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def fixture(self, name, latency=0.002, slope=0.008, exponents=range(3, 25)):
        path = self.root / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["label", "host0", "host1", "bytes", "iterations", "warmup",
                             "roundtrip_s", "oneway_s", "effective_MiB_s"])
            for exponent in exponents:
                size = 1 << exponent
                one = latency + slope * size / 1048576
                writer.writerow(["synthetic_only", "synthetic0", "synthetic1", size,
                                 5, 1, 2 * one, one, size / 1048576 / one])
        return path

    def test_known_ols_model_and_units(self):
        _, sizes, times = ANALYSIS.load_measurements(self.fixture("linear"))
        latency, slope, _, r2 = ANALYSIS.fit_model(sizes, times)
        self.assertAlmostEqual(latency, 0.002, places=12)
        self.assertAlmostEqual(1 / slope, 125.0, places=8)
        self.assertAlmostEqual(slope / 1048576, 0.008 / 1048576, places=16)
        self.assertAlmostEqual(r2, 1.0, places=12)

    def test_small_message_anchor_and_large_transfer_regime(self):
        sizes = np.array([1 << exponent for exponent in range(3, 25)])
        times = 0.003 + 0.02 * sizes / 1048576
        times[sizes <= 64] = 0.003
        latency, slope, predicted, r2 = ANALYSIS.fit_physical_model(sizes, times)
        self.assertAlmostEqual(latency, 0.003, places=12)
        self.assertAlmostEqual(1 / slope, 50, places=10)
        self.assertTrue(np.all(predicted > 0))
        self.assertGreater(r2, 0.99999)

    def test_smoke_is_not_a_full_sweep(self):
        with self.assertRaisesRegex(ValueError, "incomplete full study"):
            ANALYSIS.load_measurements(self.fixture("smoke", exponents=range(3, 17)))

    def test_corrupted_half_rtt_is_rejected(self):
        path = self.fixture("bad")
        with path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["roundtrip_s"] = str(float(rows[0]["roundtrip_s"]) * 2)
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "half the measured RTT"):
            ANALYSIS.load_measurements(path)

    def test_nonpositive_transfer_slope_is_not_hidden(self):
        _, sizes, times = ANALYSIS.load_measurements(self.fixture("bad_slope", 0.01, -0.00001))
        self.assertLess(ANALYSIS.fit_physical_model(sizes, times)[1], 0)

    def test_cli_reports_invalid_fit_and_produces_plots(self):
        paths = [self.fixture("positive"), self.fixture("negative_intercept", -0.000001, 0.4),
                 self.fixture("negative_slope", 0.01, -0.00001)]
        out = self.root / "derived"
        run = subprocess.run([sys.executable, str(SOURCE), *map(str, paths), "--out", str(out)],
                             text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        with (out / "summary.csv").open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(rows[0]["fit_status"], "positive_parameters")
        self.assertEqual(rows[1]["fit_status"], "negative_latency_fit")
        self.assertEqual(rows[2]["model_status"], "nonpositive_model_slope")
        self.assertTrue(math.isnan(float(rows[2]["model_bandwidth_MiB_s"])))
        self.assertEqual(len(list(out.glob("*.png"))), 3)


if __name__ == "__main__":
    unittest.main()
