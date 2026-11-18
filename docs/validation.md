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

No heat-solver correctness or scaling test has been performed: that code is future work. Complete hardware/version records, earlier private transcripts and final course deliverables remain tracked separately.
