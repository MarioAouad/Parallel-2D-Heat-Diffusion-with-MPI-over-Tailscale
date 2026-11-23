# Part 4 delivery checklist

**Technical delivery complete, reviewed 24 November 2026.** The real
[three-VM study](results/2026-11-24-cluster/) passes strict full verification.
The required CPU/MPI performance study is complete; optional GPU work is omitted.

| Assignment requirement | Delivered evidence |
| --- | --- |
| Fixed comparable steps and near-limit r | All 429 heat runs: Case 1, 20 steps, r=0.24, no --T or field output |
| Three repeats and spread | 143 configurations x 3; measurements.csv and analysis/summary.csv |
| AC/load/Wi-Fi and real CPU allocation | Recorded notes/inventories; 4+2+2 vCPUs/slots; core binding/nooversubscribe; 16 observed placement probes |
| Serial baseline per VM, five N | 45 measurements, per-step/full-grid-node/interior-node rates, serial_baselines PNG/PDF |
| Both layouts, both placements, strong P=1..8 | 288 measurements; N=512,2048,8192; time/speed-up/efficiency PNG/PDF |
| Weak scaling | 96 measurements; approximately 1024^2 interior nodes/rank; exact rounded ownership; weak_scaling PNG/PDF |
| Communication share per run | Timers, ratios and spread; communication_share PNG/PDF; independent-maxima caveat |
| Measured model and matching transport | Per-guest compute rates; 18 fresh Part 0 ping-pong sweeps with TCP/self; positive physical fits, RMSE and overlays |
| Crossover and discrepancy answers | Final report: no tested cross-VM crossover; variability, phase ordering, topology and contention limitations |
| Part 3 P=4,8 layout prediction then check | layout-comparison.csv: 12 cases, both maps, 7 model/measured winner agreements; report page 8 |
| One-microsecond counterfactual | Prediction CSV and report page 9; only startup changed, bandwidth/compute held fixed |
| Tailscale advice | Measured best configurations and report recommendations; no route-continuity claim |
| Reproducibility | Runner, strict verifier, immutable CSVs and figures, original/private raw history and bounded-retry journal |

The [final report](../docs/final-report/final-report.pdf) has ten main pages plus
three plot appendices and names Mario Aouad, Mohamad Farchoukh and Bassem Haddad.
The team reported shared work across all stages; no exclusive roles were invented.
Technical C3 evidence is ready; instructor checkpoint acceptance is a separate event.

The whole-project hand-in still requires the team's ten-minute live presentation
and confirmation that all members' complete private AI histories are included.
Existing Case 1/2 three-guest field files and heat maps are present; they do not
establish that a live presentation has occurred. No new full performance or
correctness campaign is required merely to prepare that presentation.
