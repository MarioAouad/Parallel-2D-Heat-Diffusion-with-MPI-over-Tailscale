# 5. Analysis without running the experiment again

The VMs do not need to be online to analyze the archived data. This is an ordinary Python program reading files, not a distributed MPI job.

## First verify the evidence

From the repository root:

```bash
python3 part0/05-analysis/verify_results.py
```

The standard-library verifier checks the published file hashes, exactly six cases, each case's 22 powers-of-two sizes, expected hosts, positive times/counts, warm-up, RTT/2, effective throughput, progress lines and successful completion. The public-copy manifest records original/published hashes; all public copies anonymize identifying fields while numeric measurements are unchanged. It is a local consistency check, not a remote attestation of the live VMs.

## Reproduce the plots and table

On Ubuntu with NumPy and Matplotlib installed:

```bash
python3 part0/05-analysis/analyze_pingpong.py part0/results/2026-11-17/*/*.csv --out part0/results/analysis
```

Or use `make verify-results`, `make analyze`, and `make test-analysis`. `--out PATH` selects the destination (the Python default is `results/analysis`); the positional arguments are one or more full CSV paths; `--help` explains usage. Archived output uses repository-relative input paths for portability. `summary.csv` plus one PNG per input is generated. Input CSVs are never rewritten.

For fresh measurements, explicitly select the reviewed completed files in `part0/results/runs/full/` and write to a different analysis folder if comparing conditions. Never mix partial/smoke data into a table represented as a complete full study.

## Model and parameter meanings

The background notes use `t_msg(m) = t_s + m*t_w`, where `m` is bytes, `t_s` is startup seconds, and `t_w` is seconds per byte. Bandwidth is `1/t_w` bytes per second. For readable output our fit uses sizes in MiB; its slope has seconds/MiB and inverse has MiB/s.

The reviewed estimator takes the median of the four small-size half-RTT averages (8,16,32,64 B) as startup, then fits a fixed-intercept slope over the five largest sizes (1,2,4,8,16 MiB). For fixed startup `tau`, with `x=sizeMiB`, `b=sum(x*(y-tau))/sum(x*x)`. This minimizes squared residuals for that fixed intercept. It follows the professor's small/large interpretation, but these exact cutoffs are our documented choice, not the only possible valid estimator.

The original all-size unconstrained least-squares line remains a **diagnostic**. Four cases gave negative intercepts. That is a model-interpretation issue, not evidence of negative physical latency or a failed payload exchange. The corrected model retains the same recorded measurements. It does not rerun or repair the raw experiment.

| Summary fields | Interpretation |
| --- | --- |
| `source_csv`, `label`, `host0`, `host1` | Provenance and actual endpoints |
| `model_method` | Which estimator/cutoffs were used |
| `model_latency_us` | Provisional small-message startup reference, microseconds |
| `model_bandwidth_MiB_s` | Inverse large-message transfer slope, MiB/s |
| `model_seconds_per_byte` | Same transfer slope converted to seconds/byte |
| `model_r_squared`, `model_status` | Fit description and warnings, not confidence limits |
| `small_message_median_us`, `small_message_min_us`, `small_message_max_us` | Spread among four per-size small-message averages, not independent-run spread |
| `fitted_latency_us`, `seconds_per_byte`, `fitted_bandwidth_MiB_s` | Original all-size OLS diagnostic parameters |
| `r_squared`, `fit_status` | OLS diagnostic fit/warnings; negative intercepts stay visible |

A high R-squared describes the sampled curve, not a guarantee of fixed routing, a precise uncertainty estimate or good solver speed-up. The analyzer flags nonpositive slopes instead of inventing a positive bandwidth.

## Tests and their scope

```bash
python3 -m unittest discover -s part0/05-analysis/tests -v
```

The numerical tests use explicitly synthetic temporary data to check recovery of a known model, units, invalid/incomplete data and nonphysical-slope reporting. Synthetic fixtures are never placed in the measured-results archive. The real archive is checked separately. These tests do not execute a heat solver or constitute a new measurement on the VMs.

Read [results and route limitations](../results/README.md) before using these parameters to predict performance.
