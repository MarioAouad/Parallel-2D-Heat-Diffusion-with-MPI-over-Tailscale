#!/usr/bin/env python3
# Part 0 analysis: validate archived/full CSVs, derive parameters, draw plots.
# This is offline work on one computer. It creates NO MPI ranks and sends no
# benchmark traffic. It can be rerun without repeating a long experiment.
"""Fit one-way time = latency + bytes * seconds_per_byte to real CSV files."""

# argparse handles input files/output path; csv reads structured measurements;
# math supplies NaN for a parameter that cannot be physically interpreted.
# Path keeps file handling independent of the operating system.
import argparse
import csv
import math
from pathlib import Path

import matplotlib

# Use a file-rendering backend: Ubuntu Server has no desktop display.
# This must be selected before importing pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


# Validate one case before fitting. Sorting supports input row order changes.
# Reject duplicate/out-of-range/non-power-of-two sizes, inconsistent hosts,
# nonpositive times/counts and an incorrect RTT/2 relationship.
# The exact 22-size requirement intentionally rejects a short smoke-test CSV.
# No missing measurements are fabricated, extrapolated into the raw data, or
# replaced with zero. The separate verify_results.py also checks throughput,
# warm-up counts, file hashes and expected host placement.
def load_measurements(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) < 3:
        raise ValueError(f"{path}: need at least three measured sizes")
    required = {"label", "host0", "host1", "bytes", "iterations", "roundtrip_s", "oneway_s"}
    if not required.issubset(rows[0]):
        raise ValueError(f"{path}: missing required benchmark CSV columns")
    if len({(row["label"], row["host0"], row["host1"]) for row in rows}) != 1:
        raise ValueError(f"{path}: expected exactly one benchmark case per CSV")
    rows.sort(key=lambda row: int(row["bytes"]))
    sizes = np.array([int(row["bytes"]) for row in rows], dtype=np.int64)
    times = np.array([float(row["oneway_s"]) for row in rows])
    rtt = np.array([float(row["roundtrip_s"]) for row in rows])
    if len(set(sizes.tolist())) != len(sizes):
        raise ValueError(f"{path}: duplicate message sizes")
    if np.any(sizes < 8) or np.any(sizes > 16 * 1024 * 1024) or np.any(sizes & (sizes - 1)):
        raise ValueError(f"{path}: invalid message sizes")
    if not np.all(np.isfinite(times)) or np.any(times <= 0):
        raise ValueError(f"{path}: times must be finite and positive")
    if not np.all(np.isfinite(rtt)) or not np.allclose(rtt, 2 * times, rtol=1e-8, atol=1e-15):
        raise ValueError(f"{path}: one-way times must equal half the measured RTT")
    if any(int(row["iterations"]) <= 0 for row in rows):
        raise ValueError(f"{path}: iteration counts must be positive")
    # Python range ends BEFORE 25: exponents 3..24 give 8 B..16 MiB (22 entries).
    expected = np.array([1 << exponent for exponent in range(3, 25)])
    if not np.array_equal(sizes, expected):
        raise ValueError(f"{path}: incomplete full study; need all 22 sizes from 8 to 16777216 bytes")
    return rows, sizes, times


# Keep the original unconstrained all-size line as a diagnostic:
#   t_oneway = intercept + size_in_MiB * seconds_per_MiB.
# A negative intercept can minimize squared residuals without representing a
# physical negative startup time. Do not submit it as latency. The revised
# small-message-anchored model below is the provisional physical interpretation.
def fit_model(sizes, times):
    """Unconstrained all-size OLS retained as a diagnostic for existing results."""
    # Scale the x-axis for a well-conditioned least-squares solve.
    mib = sizes.astype(float) / (1024 * 1024)
    # Each matrix row is [1, sizeMiB]. Least squares chooses intercept and slope
    # to minimize the sum of squared errors. R^2 below describes curve fit only;
    # it is neither a confidence interval nor evidence that a route stayed fixed.
    design = np.column_stack((np.ones_like(mib), mib))
    latency_s, seconds_per_mib = np.linalg.lstsq(design, times, rcond=None)[0]
    predicted = design @ np.array([latency_s, seconds_per_mib])
    residual = float(np.sum((times - predicted) ** 2))
    total = float(np.sum((times - np.mean(times)) ** 2))
    r_squared = 1 - residual / total if total > 0 else math.nan
    return float(latency_s), float(seconds_per_mib), predicted, r_squared


# The professor asks for startup from small messages and bandwidth from large
# ones. Our documented choice uses 8,16,32,64-byte median half-RTT for startup
# and the five sizes 1,2,4,8,16 MiB to estimate transfer cost at fixed startup.
# It is one empirical estimator, not a uniquely mandated set of cutoffs.
def fit_physical_model(sizes, times, large_min_bytes=1024 * 1024):
    """Use small messages for startup and large messages for transfer cost.

    This follows the assignment's small-message/large-message interpretation.
    Estimates are still empirical and do not guarantee an unchanged route.
    """
    small = sizes <= 64
    large = sizes >= large_min_bytes
    if np.count_nonzero(small) < 3 or np.count_nonzero(large) < 3:
        raise ValueError("Need at least three small and three large message sizes")
    # Use the median of FOUR per-size averages; this is not a median over individual
    # packet delays or independent full sweeps. It is robust to one unusual small
    # size but does not quantify uncertainty without the underlying observations.
    latency = float(np.median(times[small]))
    large_mib = sizes[large].astype(float) / (1024 * 1024)
    # For fixed startup tau and x=sizeMiB, minimizing sum((y-tau-b*x)^2) gives
    # b = sum(x*(y-tau))/sum(x*x). Units are seconds per MiB; inverse is MiB/s.
    # A nonpositive slope is flagged by the caller rather than silently forced
    # positive. Route changes/noise can invalidate a single straight-line model.
    slope = float(np.dot(large_mib, times[large] - latency) /
                  np.dot(large_mib, large_mib))
    predicted = latency + slope * sizes.astype(float) / (1024 * 1024)
    residual = float(np.sum((times - predicted) ** 2))
    total = float(np.sum((times - np.mean(times)) ** 2))
    r_squared = 1 - residual / total if total > 0 else math.nan
    return latency, slope, predicted, r_squared


# Read all input files and validate them BEFORE creating analysis outputs.
# One input CSV corresponds to one measured full sweep, not one MPI rank.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_files", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, default=Path("results/analysis"))
    args = parser.parse_args()
    # Validate every input before producing reports.
    measurements = [(path, *load_measurements(path)) for path in args.csv_files]
    args.out.mkdir(parents=True, exist_ok=True)
    summary = []
    # For each sweep calculate both models. Save them side by side so corrections
    # remain auditable. Raw input CSVs are read only and are never rewritten.
    for path, rows, sizes, times in measurements:
        latency, slope, predicted, r_squared = fit_model(sizes, times)
        model_latency, model_slope, model_predicted, model_r_squared = fit_physical_model(sizes, times)
        model_bandwidth = 1 / model_slope if model_slope > 0 else math.nan
        bandwidth = 1 / slope if slope > 0 else math.nan
        warnings = []
        if latency < 0:
            warnings.append("negative_latency_fit")
        if slope <= 0:
            warnings.append("nonpositive_bandwidth_slope")
        # model_* fields are the provisional small/large-message model.
        # fitted_* fields retain the all-size OLS diagnostics.
        # seconds_per_byte divides seconds/MiB by 2^20; microseconds multiply seconds
        # by 10^6. MiB/s is a byte unit and must not be reported as megabits/s.
        row = {
            "source_csv": str(path),
            "label": rows[0]["label"],
            "host0": rows[0]["host0"],
            "host1": rows[0]["host1"],
            "model_method": "small_8_64B_median_then_fixed_intercept_fit_1_16MiB",
            "model_latency_us": model_latency * 1e6,
            "model_bandwidth_MiB_s": model_bandwidth,
            "model_seconds_per_byte": model_slope / (1024 * 1024),
            "model_r_squared": model_r_squared,
            "model_status": "provisional_positive_parameters" if model_slope > 0 else "nonpositive_model_slope",
            "fitted_latency_us": latency * 1e6,
            "small_message_median_us": float(np.median(times[sizes <= 64])) * 1e6,
            "small_message_min_us": float(np.min(times[sizes <= 64])) * 1e6,
            "small_message_max_us": float(np.max(times[sizes <= 64])) * 1e6,
            "seconds_per_byte": slope / (1024 * 1024),
            "fitted_bandwidth_MiB_s": bandwidth,
            "r_squared": r_squared,
            "fit_status": ";".join(warnings) or "positive_parameters",
        }
        summary.append(row)
        # Draw measured half-RTT and both fitted curves. Log axes cover 22 sizes without
        # compressing all small messages into a dot. Omit nonpositive fitted points
        # from log axes while retaining their warning and numeric diagnostic.
        fig, ax = plt.subplots(figsize=(8, 5), constrained_layout=True)
        ax.loglog(sizes, times * 1000, "o", label="Measured half-RTT")
        positive = predicted > 0
        ax.loglog(sizes[positive], predicted[positive] * 1000, "--", color="0.5", label="All-size OLS diagnostic")
        if model_slope > 0:
            ax.loglog(sizes, model_predicted * 1000, "-", label="Small-message anchored model")
        ax.set(xlabel="Message size (bytes)", ylabel="Estimated one-way time (ms)",
               title=f"{rows[0]['host0']} to {rows[0]['host1']}")
        ax.grid(True, which="both", alpha=0.2)
        ax.legend()
        fig.savefig(args.out / f"{path.stem}.png", dpi=180)
        plt.close(fig)
        print(f"{row['label']}: model latency={model_latency * 1e6:.3f} us, "
              f"model bandwidth={model_bandwidth:.3f} MiB/s, "
              f"model R^2={model_r_squared:.4f}, status={row['model_status']}; "
              f"all-size OLS diagnostic status={row['fit_status']}")
    # Write one derived summary row per input sweep. The table and PNGs are
    # reproducible analysis artifacts, not additional experiments.
    with (args.out / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    print(f"Saved summary.csv and plots in {args.out}")


# Run main only for a direct command; importing this module for validation
# tests exposes its functions without starting the command-line application.
if __name__ == "__main__":
    main()
