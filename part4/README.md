# Part 4: performance campaign

**Implementation ready; real Part 4 measurements are not collected yet.** The
reviewed Part 2/3 campaign is correctness evidence and a small timing check. It
does not replace this full performance matrix. The verified C++ solvers remain
unchanged; this part orchestrates, records, models and verifies their execution.

Start with the [VM run guide](RUN.md), [requirement checklist](DELIVERY.md),
[model explanation](MODEL.md) and [results policy](results/README.md).

| File | Role |
| --- | --- |
| `common.py` | Deterministic plan, placement, uneven-work counts, units and Task 8.2 model |
| `run_experiments.py` | Real guest preflight, probes, calibration, measurements, restart checkpoints |
| `analyze.py` | Offline tables, PNG/PDF plots, model overlays and generated report answers |
| `verify_results.py` | Offline manifest, matrix, raw-output, statistic and model checks |
| `tests/test_part4.py` | Synthetic pipeline/corruption/restart/model/Git-policy regressions; no VM evidence |
| `../scripts/run-part4.sh` | Full/smoke/resume/package commands and private return bundle |

## Preview and local tests

```bash
make plan-part4
make test-part4
```

`python3 part4/run_experiments.py --plan --slots 4,2,2` works without SSH or MPI.
Real work requires explicit `--run`; preview never creates measurements.

With eight slots the full plan contains 429 heat invocations:

- Serial: three VMs x five N x three repetitions = 45.
- Strong: two layouts x two placements x eight P x three N x three repetitions = 288.
- Weak: two layouts x two placements x eight P x three repetitions = 96.

There are also 16 placement probes, 18 calibration sweeps (six same/cross-guest
pairs x three repetitions) and before/after network snapshots. Default heat runs
use Case 1, **20 fixed steps**, **r=0.24**, no field output and three repetitions.
The assignment's 500 steps is an example, not a prescribed count. Twenty keeps
this slow-network campaign practical while increasing the previous timing count.
Use `--steps` to choose a different fixed count before starting a new campaign;
never change it halfway through or compare different step counts as raw times.

All P from one through checked capacity are tested. Strong N is
512,2048,8192; serial N is 512,1024,2048,4096,8192 on **each** VM. Weak scaling
uses `N=round(1024*sqrt(P))+1`: interior work per rank is approximately 1024^2.
The exact mean/min/max owned work is recorded, including integer-rounding effects.

## Recording and restarting

Every subprocess has an original private output record and a sanitized public
record, flushed to disk. Each successful parsed task is atomically checkpointed.
A retry skips completed tasks; failed attempts remain in the raw history. A
timeout preserves partial output and stops rather than pretending to complete.
Resume requires the same committed revision, source hashes, MPI, binaries and
CPU allocation. It first rejects still-running solver/benchmark processes. A
per-folder lock prevents concurrent users of the same campaign folder.

On restart do not delete anything or blindly launch a new full campaign. See
`RUN.md` for inspection, resume and packaging. A completed campaign is verified
offline; resume refuses to repeat it.

## Output

Each timestamped folder contains `metadata.json`, `state.json`,
`raw_runs.jsonl`, `measurements.csv`, `calibration.csv` and `analysis/`.
The latter contains summary/prediction CSVs, calibrated parameters, `REPORT.md`
and six pairs of PNG/PDF figures: serial baseline, strong time, strong speed-up,
strong efficiency, weak scaling and communication share. Strong time includes
the fitted model and a one-microsecond-latency counterfactual on the same axes;
weak scaling also overlays the model. Summary tables retain median/min/max.

`private/raw_runs.jsonl` keeps unredacted endpoints/hostnames. It is excluded
from the public manifest and Git, but retained in the private return bundle.
The metadata includes operator-supplied power/load/Wi-Fi notes, per-VM CPU/RAM/
compiler/MPI/build recipe/revision/binary hashes, actual placement probes and
transport/binding policies. No private configuration or key files are collected.

To reanalyze an archive without modifying it:

```bash
python3 part4/analyze.py --data /path/to/study --out part4/results/analysis-local/new-analysis
python3 part4/verify_results.py --data /path/to/study
```

The analysis output directory must be new. Reviewed raw data stays immutable.
Smoke results require `--allow-smoke`, and cannot close Part 4. Synthetic data
is rejected by the normal CLI verifier even if its arithmetic is consistent.
