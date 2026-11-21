# Part 4 delivery checklist

**Implementation complete; real cluster campaign and review pending.** No synthetic
test output or Part 3 timing table is presented as Part 4 measurement evidence.

| Assignment requirement | Implementation | Closure evidence still needed |
| --- | --- | --- |
| 8.1 fixed steps and r near stability limit | Default 20 steps/r=0.24, no --T or output, same heat parameters across the campaign | Full VM run |
| At least three runs, median/spread | Full profile uses three repetitions; CSVs preserve all rows and median/min/max | Verified full campaign |
| Power/load and Wi-Fi notes | --notes required; guest inventory, network snapshots and hardware metadata | Actual operator notes and controlled conditions |
| No oversubscription | Real nproc/slots check, explicit nooversubscribe, observed rank placement and core binding | Guest inventory and probe records |
| 8.2 serial on each VM at five N | 45 default measurements, per-step and per-grid/interior-node costs | Baseline CSV/raw outputs |
| Strong scaling, both layouts/placements, all P | 288 default measurements, N512/2048/8192, P1..8 | Curves and verified repetitions |
| Weak scaling and constant-work discussion | 96 default measurements, exact rounded work recorded | Weak time/efficiency plot |
| Communication share per run | Raw and summary fractions, plot and timer-maxima caveat | Recorded timers |
| 8.3 measured compute/communication model | Per-VM compute interpolation, same-transport Part0 benchmark reuse, placement-aware neighbor model | Physically valid fits and model overlays |
| Model/measured crossover, discrepancies | Generated report derives tested crossovers and notes assumptions | Interpretation of actual routes/load and observed differences |
| ts=1us counterfactual | Prediction CSV and dotted model curve | Measured campaign plus generated analysis |
| Advice for Tailscale | Generated report and measured selection tables | Team interpretation in final report |
| Scripts/raw output reproducibility | Restartable runner, verifier, public/private logs, hashes and source provenance | Reviewed archive |

The final report (at most ten pages plus appendices), actual team contribution
statements, full AI records and ten-minute live demonstration remain separate
final deliverables. Full checkpoint C3 requires the actual performance campaign,
not only this implementation or the already closed Part 2/3 correctness gaps.
