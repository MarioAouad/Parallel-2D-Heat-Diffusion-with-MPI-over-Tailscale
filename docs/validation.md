# Validation of the organized repository

The organization was checked on 18 November 2026. Preserve the distinction between historical cluster evidence and checks performed on this reorganized copy.

| Check | Outcome / scope |
| --- | --- |
| Original evidence consistency | 30 published files match their manifest; six cases, 22 sizes each, 132 rows; expected hosts, RTT/2, throughput and successful logs verified |
| Original measurement preservation | All 132 numeric records match private originals; public copies use aliases and strip network/account identifiers. Manifest distinguishes original and public hashes |
| C++ executable statement identity | Token comparison ignores comments/whitespace and confirms both programs retain the original executable token sequences |
| Analysis statement identity | Python AST comparison confirms comments did not change the reviewed analyzer's program |
| Numerical tests | Six tests passed: known-model recovery/units, small-large estimator, incomplete-data rejection, RTT inconsistency rejection, invalid slope handling, CLI warnings/plots |
| Analysis on real evidence | Recomputed all six fits and plots; every model/diagnostic value agrees with the previous reviewed analysis |
| Shell syntax | All six Bash files passed `bash -n` |
| Private configuration loader | Four no-network checks passed: missing file, placeholders, valid example addresses/rendered hostfile, and invalid octet rejection |
| Build recipe | `make -n` prints the two expected MPI C++ compiler recipes and creates only the intended build directory |
| Documentation/publication | Local Markdown links and result hashes checked; credential headers, email identifiers and real cluster addresses scanned |

The old flat-layout binaries ran successfully on the VMs, as documented in the historical evidence. The reorganized checkout's paths/build targets and helper scripts have **not** been installed and independently executed on all three VMs during this organization. The local host has no Linux MPI compiler available for a new native cluster build. We do not claim a new VM run merely from a dry run, code comparison, syntax check or Python test.

The appropriate later check, when the team is ready, is to clone the same commit to the same absolute path on all VMs, run `make`, and run hostname/hello plus a short two-rank smoke check. This is not a requirement to repeat the hours-long archived full sweeps now.

As of the 18 November organization, no heat-solver correctness or scaling test
had been performed. The dated update below supersedes that historical status.

## Review and serial implementation on 19 November 2026

- Preserved the exact supplied setup tar.gz privately and eight sanitized text
  records publicly, with original/public hashes. Three inventories and hostname
  placement pass. Four SSH directions pass; two fail on host-key trust. MPI
  hello fails on the third VM's working directory. `verify_setup.py` reports
  NOT READY and returns 1 for this known snapshot.
- Reverified the unchanged original 30 benchmark files / 132 rows and all six
  existing analysis tests.
- Adapted the existing serial task solver into the project interface, added
  Case 2 and its corner precedence, strict parsing, little-endian output,
  serial timing fields, and the isolated instability demonstration.
- Compiled on Windows using MSYS2 GCC 13.2.0 with C++17, O2, warnings, and
  ffp-contract=off. Compilation produced no warnings.
- All six serial correctness test groups passed, including full-field modal
  comparison, boundary/odd-even buffer checks, time rounding, output length,
  malformed/unstable input rejection, and known one-step values.
- The final executable reproduced five-grid second-order convergence at
  T=0.05, r=0.2: orders 2.00577, 2.00144, 2.00036, 2.00009. Task 6.7 shows the
  expected growing checkerboard and extrema near -303 and +302 at step 200.
  Convergence, instability and Case 1/2 images were visually inspected.

These results are in `part1/results/2026-11-19-windows/`. No Linux VM build/run
of the new serial source is claimed. A noninteractive local SSH attempt could
not authenticate, so no remote repair was performed. The exact instructions
are in [the Part 0 closeout](part0-closeout.md). Later MPI solver/scaling work,
complete earlier private transcripts and final deliverables remain outstanding.

## Final Part 0 recheck, 19 November 2026

The newly supplied archive was inspected after it became available in Downloads.
Its exact private copy has SHA-256
`e8885eb47f5542173dfb1e18de2f60706ea53dedf22ac5754eac75bb13dc8f6f`.
All four text records have source/public hashes; earlier failed logs remain.
The new heat-2 connectivity capture and six-rank hello both pass. Original
inventories, the other four SSH directions and hostname placement remain valid.

The setup verifier now verifies every archived text hash and selects the latest
timestamped capture for each check. Duplicate same-time copies must agree.
Default verification checks 12 archived records and reports all eight current
checks passing / Part 0 READY. `--initial-only` retains the original NOT READY
assessment, including the two SSH failures and failed hello. Both modes were
checked for their expected exit statuses (0 and 1). The original ping-pong
verifier again passes all 30 files and 132 rows.

Part 0 technical work is complete. The new data are user-collected terminal
evidence, not a new assistant-operated cluster experiment. Ubuntu Part 1
verification, later MPI solvers, the final report and complete earlier AI history
remain separate work.

## First native Ubuntu serial run

The user's pasted terminal output shows a successful fast-forward pull to
`8acc213`, native C++17/O2/ffp-contract=off compilation, and the V/N=16 run at
r=0.2, T=0.05. It reports 64 steps, err_inf=0.0016633705032857438 and
err_l2=0.00083168525164289075, matching the expected errors. Exact pasted bytes
are preserved privately, with a public solver-output/provenance record under
`part1/results/2026-11-19-ubuntu-smoke/`. The run timestamp was not supplied.
This confirms the Ubuntu smoke test; the full automated suite and five-grid
Ubuntu study are still pending. No broader numerical/performance claim is made.

## Ubuntu automated suite and study: user-supplied output

The next pasted terminal record reports six passing correctness groups, ending
with `OK`, and a successful five-grid convergence/modal check with orders
2.00577, 2.00144, 2.00036, 2.00009. The same study reports successful isolated
instability and stable Cases 1/2. Its output folder is
`/home/mpi/heat-project-repo/part1/results/runs/20261119T161615613935Z`.

These observations close the pending Ubuntu automated execution checks from
the earlier status. The precise CSVs, plots and metadata still need transfer
for local archive/visual review; the assistant has reviewed the user's console
output, not those VM-generated files. No new experiment is required merely
to collect them, and the suite's displayed runtime is not a Part 4 benchmark.

## Final Ubuntu artifact review and Part 1 delivery

Received the exact 252164-byte study archive, SHA-256
`babe3d4f0730f4f017a4b69a0de87e43677642a2d6c06295a2b028626233269b`.
All fourteen original members are retained privately; nine original report/data
files are published byte-for-byte with a manifest. Five reproducible binary
snapshots remain private and hashed. The run metadata source hash matches the
current C++ solver.

- All ten raw solver invocations have return code zero. Five convergence rows
  match their raw summaries, the independent discrete sine-mode errors and
  properly weighted L2 norms; reported orders recompute correctly near two.
- Three instability CSV extrema match their binary snapshots, with the expected
  overshoot/growing alternating pattern and fixed hot boundaries.
- Case 1/2 binary fields are finite, within [0,1], obey the exact edge/corner
  values and preserve horizontal/vertical reflection symmetry. All five binary
  snapshots have the 33800-byte format and equal the earlier corresponding
  Windows boundary-heated snapshots byte-for-byte; this is not MPI validation.
- All three Ubuntu PNG figures were visually inspected. The nine original public
  hashes and source provenance pass `part1/verify_results.py`; a corrupted
  temporary CSV copy is rejected by its hash check.
- Existing written task solutions were copied with provenance: 32-page PDF,
  all 25 required task numbers plus optional 6.5, editable LaTeX and supporting
  reproduction files. Sample PDF pages were rendered/inspected; the existing AI
  acknowledgement remains. A single absolute workspace prefix in raw commands
  is redacted and disclosed, with original/public hashes and private originals.

Part 1 analysis and the delivery checklist now link the report material. The
technical Parts 0/1 and C1 materials are ready. Complete earlier AI transcripts,
actual team details, later MPI work and the final full-project report/demo remain
course-submission responsibilities; no missing records or contributions were invented.
