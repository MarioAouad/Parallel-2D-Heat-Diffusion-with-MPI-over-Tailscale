# Part 1 delivery checklist

Part 1 technical work and evidence review are complete. The primary experiment
is the user-collected heat-1 Ubuntu run of 19 November 2026. This checklist is
the Part 1 handoff; it does not claim the later MPI parts or final course report
are complete.

| Requirement | Delivered evidence |
| --- | --- |
| C++17, one-command optimized build, contraction disabled | [Makefile](../Makefile), `make serial` |
| Cases 1, 2 and V with documented interface | [Solver](heat_serial.cpp), [usage guide](README.md) |
| Contiguous storage, single index, two swapped time levels | [Solver](heat_serial.cpp) |
| Loop-only timing and exact V norms | Solver and [raw Ubuntu outputs](results/2026-11-19-ubuntu/raw_runs.json) |
| Ordinary unstable r refused | Six passing correctness groups; explicit demo is isolated |
| Required five-grid convergence table and log-log plot | [CSV](results/2026-11-19-ubuntu/convergence.csv), [PNG](results/2026-11-19-ubuntu/convergence.png), [vector PDF](results/2026-11-19-ubuntu/convergence.pdf) |
| Task 6.7, 5% above stability bound | [Extrema CSV](results/2026-11-19-ubuntu/instability.csv), [PNG](results/2026-11-19-ubuntu/instability.png), [vector PDF](results/2026-11-19-ubuntu/instability.pdf) |
| Stable simulations and boundary conventions | [Case 1/2 heat maps](results/2026-11-19-ubuntu/cases.png) and binary-field checks |
| Reproducible experiments and offline evidence checks | [Experiment script](run_experiments.py), [serial checks](verify_serial.py), [archive verifier](verify_results.py) |
| Numerical interpretation for the report | [Part 1 analysis](ANALYSIS.md) |
| Written background tasks | [PDF, editable source and reproduction files](../docs/background-solutions/README.md) |

## Verified checks

- The Ubuntu console record shows six correctness groups ending with OK.
- All ten archived solver commands returned zero. Source hash matches the
  published serial reference.
- All five convergence rows match raw outputs and an independent discrete
  sine-mode calculation. Observed orders approach two.
- Instability extrema match the saved binary fields. Stable fields preserve
  their boundaries, bounds and reflection symmetries.
- Convergence, instability and Case 1/2 figures were visually inspected.
- All published original result files retain their exact source bytes and hashes.

## Public repository and private hand-in

GitHub contains reviewed CSVs, plots, PDFs, raw command JSON, metadata, manifests,
source and analysis. Reproducible `.bin` fields, original transfer archives,
private configuration and private full conversation records stay outside the
public commit. Their hashes/provenance are retained, and the experiment script
can regenerate fields. Preserve the full private archive for the course hand-in.

Complete earlier AI conversations and actual member/model/date metadata remain
an outstanding course-record item; the public index does not replace them.
Add actual team identification/contributions where the final submission requires
them. The final report (at most ten pages plus appendices) must later integrate
Parts 2-4. Use ANALYSIS.md as its numerical-verification material.

Parts 2 and 3 now implement strips and blocks with this unchanged serial reference.
Their retained-field evidence and Part 3 P=8 measurements are tracked separately;
the next implementation stage is Part 4.
